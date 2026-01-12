"""
Custom VLM Model Wrapper for LangChain Integration (Fixed Version)

This module wraps the Gemma-2 + CLIP vision model with LangChain's BaseLLM interface.
Improvements:
- Matches standalone script prompt (Bahasa Indonesia).
- Uses higher precision (bfloat16) instead of 4-bit for better quality.
- Aligns generation parameters (beams, repetition penalty) with the best checkpoint.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import warnings
import os
import asyncio
import functools
from typing import Any, List, Optional
from PIL import Image
from pathlib import Path

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    CLIPVisionModel,
    AutoProcessor,
    BitsAndBytesConfig,
)
from langchain_core.language_models import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

# Suppress warnings
warnings.filterwarnings("ignore")

# ===============================================================
# CONFIGURATION
# ===============================================================

curr_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up levels to project root (Adjust if structure changes)
project_root = os.path.abspath(os.path.join(curr_dir, "../../../../../"))
BASE_DIR = os.path.join(project_root, "models")

# Pastikan nama file checkpoint benar
MODEL_PATH = os.path.join(BASE_DIR, "BLEU15.pt") 

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cuda":
    print(f"✅ CUDA Detected: {torch.cuda.get_device_name(0)}")
else:
    print("⚠️ CUDA NOT Detected. Running on CPU.")

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
GEMMA_MODEL_ID = "google/gemma-2-2b-it"
NUM_VIS_TOKEN = 50
TRIGGER_STR = "<start_image>"


# ===============================================================
# MODEL ARCHITECTURE (Must match training/standalone script)
# ===============================================================

class MyAdaptor(nn.Module):
    """Adapter to project vision embeddings to language model space."""
    
    def __init__(self, vis_token_embedding_size, word_embedding_size):
        super(MyAdaptor, self).__init__()
        self.vis_token_embedding_size = vis_token_embedding_size
        self.word_embedding_size = word_embedding_size
        self.adapter_mlp = nn.Sequential(
            nn.Linear(self.vis_token_embedding_size, self.word_embedding_size),
            nn.GELU(),
            nn.Linear(self.word_embedding_size, self.word_embedding_size)
        )

    def forward(self, img_output):
        return self.adapter_mlp(img_output)


class MyModel(nn.Module):
    """Custom VLM combining Gemma-2 language model with CLIP vision model."""
    
    def __init__(self):
        super(MyModel, self).__init__()
        
        # --- KONFIGURASI PENTING ---
        # Set ke False untuk kualitas maksimal (seperti script standalone).
        # Set ke True hanya jika VRAM < 12GB dan terjadi OOM.
        self.use_4bit = False  
        
        quantization_config = None
        if DEVICE == "cuda" and self.use_4bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16
            )

        print(f" -> Loading Gemma-2 (4-bit: {self.use_4bit})...")
        # Initialize Gemma-2
        self.model_language = AutoModelForCausalLM.from_pretrained(
            GEMMA_MODEL_ID,
            torch_dtype=torch.bfloat16,
            # Force CUDA to avoid CPU offloading for small models
            device_map="cuda" if DEVICE == "cuda" else None,
            quantization_config=quantization_config
        )
        self.tokenizer_language = AutoTokenizer.from_pretrained(GEMMA_MODEL_ID, padding_side='right')
        
        print(" -> Loading CLIP Vision...")
        # Initialize CLIP
        self.image_processor = AutoProcessor.from_pretrained(CLIP_MODEL_ID).image_processor
        self.model_image = CLIPVisionModel.from_pretrained(CLIP_MODEL_ID).to(DEVICE)

        self.word_embedding_size = self.model_language.config.hidden_size
        self.num_vocab = self.model_language.config.vocab_size
        self.trigger_str_img = TRIGGER_STR
        self.num_vis_token_summary = NUM_VIS_TOKEN
        self.vis_token_embedding_size = self.model_image.config.hidden_size
        
        # Initialize Adapter
        self.adaptor = MyAdaptor(self.vis_token_embedding_size, self.word_embedding_size)
        self.dummy_img_token = (" ".join(["the"] * self.num_vis_token_summary)).strip()

    def search_trigger_idx(self, text_token, trigger_str):
        """Find the position of trigger string in tokenized text."""
        all_token = text_token
        all_token_now = []
        dummy_start_token = None
        for token_idx in range(len(all_token)):
            token_now = int(all_token[token_idx].detach().cpu().numpy())
            all_token_now.append(token_now)
            token_as_string = self.tokenizer_language.batch_decode(
                [all_token_now],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]
            if trigger_str in token_as_string:
                dummy_start_token = token_idx + 1
                break
        return dummy_start_token

    def get_image_embed(self, image_input):
        """Extract and adapt image embeddings."""
        image_input_float = image_input.to(DEVICE, dtype=self.model_image.dtype)
        img_output = self.model_image(image_input_float)['last_hidden_state']
        img_output_bfloat16 = img_output.to(torch.bfloat16)
        img_embed = self.adaptor(img_output_bfloat16)
        return img_embed

    def split_and_replace(self, now_input_tokens, replacement_embed, start_loc):
        """Replace tokens at a specific location with embeddings."""
        num_token = len(replacement_embed)
        start_embed = now_input_tokens[0:start_loc]
        end_embed = now_input_tokens[start_loc + num_token:]
        replaced_embed = torch.cat((start_embed, replacement_embed.to(now_input_tokens.dtype), end_embed), 0)
        return replaced_embed

    def generate_answer_image(self, pil_image: Image.Image, max_new_tokens=60):
        """
        Generate caption with EXACT logic from the standalone evaluation script.
        Uses hardcoded indices to ensure image embeddings are inserted correctly.
        """
        # 1. Prompt template - HARUS SAMA PERSIS dengan script training/eval
        # Template: <start_of_turn>user\n<start_image> {50_dummy_tokens}\n<end_image>\nBerikan...
        instruction_now = f"<start_of_turn>user\n<start_image> {self.dummy_img_token}\n<end_image>\nBerikan deskripsi singkat gambar ini dalam Bahasa Indonesia!\n<end_of_turn>\n<start_of_turn>model\n"

        # 2. Tokenize text
        # Kita perlu input_ids untuk mendapatkan text embeddings awal
        inputs = self.tokenizer_language(instruction_now, return_tensors="pt")
        inputs = {k: v.to(self.model_language.device) for k, v in inputs.items()}

        # 3. Get Text Embeddings (Original)
        prompt_embeds = self.model_language.model.embed_tokens(inputs['input_ids'])

        # 4. Get Image Embeddings (Projected)
        image_input = self.image_processor(pil_image, return_tensors="pt")['pixel_values']
        img_embed = self.get_image_embed(image_input)

        # 5. CONCATENATION (The "Magic" Fix)
        # Di script eval, kamu pakai: prompt_embeds[0, :6] + img + prompt_embeds[0, 56:]
        # Index 6 adalah posisi tepat setelah <start_image>
        # Index 56 adalah posisi tepat setelah <end_image> (6 + 50 token dummy = 56)
        
        # Ambil bagian awal (sebelum gambar)
        part1 = prompt_embeds[0, :6] 
        # Ambil bagian akhir (setelah gambar - melewati 50 token dummy)
        part2 = prompt_embeds[0, 56:]
        
        # Gabungkan: [Awal] + [Gambar] + [Akhir]
        inputs_embeds = torch.cat((part1, img_embed[0], part2), 0).unsqueeze(0)

        # 6. Generate
        # PENTING: Jangan kirim attention_mask! 
        # Script eval kamu ada warning "The attention mask is not set...", itu artinya dia jalan TANPA mask.
        # Kalau kita kirim mask dari text asli, model bingung karena ada token gambar yang menyisip.
        
        if max_new_tokens is None: max_new_tokens = 60

        output_now = self.model_language.generate(
            inputs_embeds=inputs_embeds,
            max_new_tokens=max_new_tokens,
            num_beams=5,               # Beam search
            do_sample=False,           # Deterministic
            repetition_penalty=1.5,    # Penalty tinggi
            no_repeat_ngram_size=3,    # No repeat
            early_stopping=True,
            pad_token_id=self.tokenizer_language.eos_token_id
        )

        # 7. Decode output
        output_string = self.tokenizer_language.batch_decode(
            output_now,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        # 8. Clean text
        if "model\n" in output_string:
            return output_string.split("model\n")[-1].strip()
        else:
            return output_string.strip()

    def generate_answer_text(self, text_input: str, max_new_tokens=256, temperature=None):
        """Generate answer for text-only input."""

        if "<start_of_turn>" not in text_input:
             instruction_now = f"<start_of_turn>user\n{text_input}<end_of_turn>\n<start_of_turn>model\n"
        else:
             instruction_now = text_input

        if temperature is None:
            temperature = 0.7

        try:
            inputs = self.tokenizer_language(instruction_now, return_tensors="pt")
            inputs = {k: v.to(self.model_language.device) for k, v in inputs.items()}
            
            outputs = self.model_language.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0, 
                temperature=max(temperature, 0.01) if temperature > 0 else None,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                pad_token_id=self.tokenizer_language.eos_token_id
            )
            
            input_len = inputs['input_ids'].shape[1]
            generated_tokens = outputs[:, input_len:]
            output_text = self.tokenizer_language.decode(generated_tokens[0], skip_special_tokens=True)
            
            return output_text.strip()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error generating text: {str(e)}"


# ===============================================================
# LANGCHAIN LLM WRAPPER
# ===============================================================

class CustomVLMLLM(LLM):
    """
    LangChain LLM wrapper for custom Gemma-2 + CLIP VLM model.
    """

    model: MyModel = None
    device: str = DEVICE
    model_path: str = MODEL_PATH
    temperature: float = 0.7

    @property
    def _llm_type(self) -> str:
        return "custom_vlm"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.model is None:
            self._load_model()

    def _load_model(self):
        """Load the model and checkpoint."""
        print("Initializing custom VLM model...")
        self.model = MyModel()
        
        # Move adapter to device before loading state dict
        self.model.adaptor.to(self.device, dtype=torch.bfloat16)

        print(f"Loading checkpoint from: {self.model_path}")
        if os.path.exists(self.model_path):
            checkpoint = torch.load(self.model_path, map_location=self.device)
            # Load state dict into adaptor
            if 'model_state_dict' in checkpoint:
                self.model.adaptor.load_state_dict(checkpoint['model_state_dict'])
                print(f"Successfully loaded model from Epoch {checkpoint.get('epoch', 'N/A')}")
            else:
                # Fallback loading
                try:
                    self.model.adaptor.load_state_dict(checkpoint)
                except Exception as e:
                    print(f"Error loading state dict: {e}")
        else:
            print(f"WARNING: Model path {self.model_path} does not exist. Using random weights.")

        self.model.eval()
        print(f"✅ Custom VLM model ready on device: {self.device}")

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        if self.model is None:
            self._load_model()
            
        response = self.model.generate_answer_text(prompt, temperature=self.temperature)
        
        if run_manager:
            run_manager.on_llm_new_token(response)
            
        return response

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        if self.model is None:
            self._load_model()
            
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            functools.partial(self.model.generate_answer_text, prompt, temperature=self.temperature)
        )
        
        if run_manager:
            await run_manager.on_llm_new_token(response)
            
        return response

    async def astream(self, input: Any, config: Optional[Any] = None, **kwargs: Any):
        prompt = ""
        if isinstance(input, list):
             prompt = "\n\n".join([msg.content for msg in input])
        else:
             prompt = str(input)
             
        response = await self._acall(prompt)
        
        # Simulated streaming
        chunk_size = 4
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i+chunk_size]
            yield type('Chunk', (object,), {'content': chunk})()
            await asyncio.sleep(0.01)

    def invoke_with_image(self, image_path: str, prompt_text: str = None, max_new_tokens: int = 60) -> str:
        """
        Invoke the model with an image to generate a simple caption.
        """
        try:
            if not os.path.exists(image_path):
                return f"Error: Image file not found at {image_path}"

            image_raw = Image.open(image_path).convert("RGB")

            with torch.no_grad():
                caption = self.model.generate_answer_image(
                    image_raw,
                    max_new_tokens=max_new_tokens
                )
            return caption

        except Exception as e:
            return f"Error during inference: {str(e)}"

    def bind_tools(self, tools: list, **kwargs):
        self._bound_tools = tools
        return self


# ===============================================================
# GLOBAL MODEL INSTANCE & HELPERS
# ===============================================================

_custom_vlm_instance = None


def get_custom_vlm_model() -> CustomVLMLLM:
    """Get or create the global custom VLM model instance."""
    global _custom_vlm_instance
    if _custom_vlm_instance is None:
        _custom_vlm_instance = CustomVLMLLM()
    # Debug Singleton Identity
    print(f"DEBUG: Accessing VLM Model Instance ID: {id(_custom_vlm_instance)}")
    return _custom_vlm_instance

async def _maybe_handle_multimodal_and_augment(agent_input, max_new_tokens=60, model_name=None):
    """
    Helper function to check if input contains an image and invoke VLM.
    Integrates with RAG if 'rag' is in the agent name.
    """
    # Check if we have an image path in the input
    image_path = None
    if hasattr(agent_input, 'input'):
        if isinstance(agent_input.input, dict):
            image_path = agent_input.input.get('image_path')
        else:
            image_path = getattr(agent_input.input, 'image_path', None)
    
    if image_path:
        print(f"Multimodal input detected! Image path: {image_path}")
        
        # Check if RAG should be enabled
        use_rag = False
        agent_name = ""
        if hasattr(agent_input, 'agent_config') and agent_input.agent_config:
            if isinstance(agent_input.agent_config, dict):
                agent_name = agent_input.agent_config.get('agent_name', '')
            else:
                agent_name = getattr(agent_input.agent_config, 'agent_name', '')
            
            if agent_name and 'rag' in agent_name.lower():
                use_rag = True
        
        # Also enable RAG if user explicitly mentions it or asks a detailed question
        user_text = ""
        if isinstance(agent_input.input, dict):
            user_text = agent_input.input.get('text', '') or agent_input.input.get('messages', '')
        else:
            user_text = getattr(agent_input.input, 'messages', '')
        
        # Flatten user_text if it's a list of LangChain messages
        search_text = ""
        if isinstance(user_text, list):
            for msg in user_text:
                if hasattr(msg, 'content'):
                    search_text += f" {msg.content}"
                else:
                    search_text += f" {str(msg)}"
        elif isinstance(user_text, str):
            search_text = user_text
        
        if not use_rag and '@rag' in search_text.lower():
            use_rag = True
            print("✅ RAG enabled via @rag mention in prompt")
        
        # Check for MCP flag
        use_mcp = False
        if agent_name and 'rag' in agent_name.lower() and 'mcp' in agent_name.lower():
            use_mcp = True
            print("✅ RAG via Supabase MCP enabled")

        if use_rag:
            print(f"✅ RAG enabled for analysis")

        # Step 1: Native Retrieval (Fast Local Vector Search)
        retrieved_images = []
        if use_rag:
            try:
                # Fast local ID lookup (Synchronous, fast)
                from microservice.rag.service.rag._image_rag_utils import retrieval_by_image
                retrieved_images = retrieval_by_image(image_path, top_k=1)
            except Exception as e:
                print(f"Error in native RAG: {e}")

        # Step 2: PARALLEL EXECUTION (MCP I/O + VLM GPU)
        from concurrent.futures import ThreadPoolExecutor
        
        rag_context = ""
        mcp_records = []
        use_mcp_flag = False
        vlm_analysis = ""
        
        # Helper wrapper for thread
        def _execute_mcp_logic_safe_wrapper():
            return _fetch_mcp_enrichment(agent_name, retrieved_images)

        def _execute_vlm_logic_safe_wrapper():
            print(f"   🔍 [Step 2/3] Generating basic image caption with VLM...")
            vlm_instance = get_custom_vlm_model()
            try:
                return vlm_instance.invoke_with_image(image_path, max_new_tokens=60)
            except Exception as e:
                print(f"   ⚠️ VLM Generation Failed: {e}")
                return "Analisis visual tidak tersedia."

        import time
        t_start_parallel = time.time()
        print("   🚀 Starting Parallel Execution (VLM + MCP)...")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_mcp = executor.submit(_execute_mcp_logic_safe_wrapper)
            future_vlm = executor.submit(_execute_vlm_logic_safe_wrapper)
            
            # Wait for both to complete
            vlm_analysis = future_vlm.result()
            t_vlm_done = time.time()
            print(f"   ⏱️ [Performance] VLM Finished in {t_vlm_done - t_start_parallel:.2f}s")
            
            try:
                rag_context, mcp_records, use_mcp_flag = future_mcp.result(timeout=15)
            except Exception as e:
                print(f"   ⚠️ MCP Parallel Fetch Failed/Timed out: {e}")
                rag_context = ""
                mcp_records = []
                use_mcp_flag = False # Ensure flag is reset on timeout/error
            
            t_mcp_done = time.time()
            print(f"   ⏱️ [Performance] MCP Finished in {t_mcp_done - t_start_parallel:.2f}s")
            print(f"   ⏱️ [Performance] Total Parallel Block: {max(t_vlm_done, t_mcp_done) - t_start_parallel:.2f}s")

            # AGGRESSIVE MEMORY CLEANUP
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("   🧹 CUDA Cache Cleared between Steps")

        # Step 3: Construct Final Prompt
        print("   🔍 [Step 3/3] Building context for Agent LLM...")
        
        context_parts = []
        
        # Build Natural Language Context
        rag_instruction = ""
        if rag_context:
             rag_instruction = (
                f"INFORMASI DETIL GAMBAR (SUMBER TERPERCAYA):\n{rag_context}\n\n"
                "⚠️ INSTRUKSI MENJAWAB:\n"
                "1. Gunakan informasi di atas untuk menjawab dengan LENGKAP dan MENDETAIL.\n"
                "2. SEBUTKAN SECARA SPESIFIK: Warna, Pakaian, Objek, dan Aktivitas yang tercatat di data.\n"
                "3. JANGAN mengaku mendapat info dari database, tapi ceritakan seolah Anda melihatnya sendiri.\n"
                "4. Jika ada konflik antara analisis visual VLM dan data di atas, PRIORITASKAN data di atas.\n"
                "5. Berikan deskripsi yang hidup, akurat, dan kaya informasi (jangan terlalu singkat)."
             )
             context_parts.append(rag_instruction)
        
        context_parts.append(f"\nANALISIS VISUAL TAMBAHAN (VLM): {vlm_analysis}")
        
        full_context = "\n\n".join(context_parts)
        
        # Modify Agent Input
        if isinstance(agent_input.input, dict):
            agent_input.input['context'] = f"{agent_input.input.get('context', '')}\n\n{full_context}"
        else:
            current_context = getattr(agent_input.input, 'context', '')
            setattr(agent_input.input, 'context', f"{current_context}\n\n{full_context}")
        
        # PERFORMANCE FIX: Force cleanup to prevent slowdowns over time
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        print("🧹 Memory cleanup executed.")
        
        return agent_input, vlm_analysis, use_mcp_flag

    return agent_input, None, False

# ==================================================================================
# HELPER: PARALLEL MCP FETCHING
# ==================================================================================

def _fetch_mcp_enrichment(agent_name, retrieved_images):
    """
    Standalone function to handle the complex MCP SQL retrieval, parsing, and formatting.
    Designed to run in a background thread.
    Returns: (formatted_context_string, raw_records_list, is_mcp_used_bool)
    """
    import json
    import re
    import ast
    import os
    
    rag_context = ""
    mcp_records = []
    use_mcp = False

    # Check if we should run MCP
    # Only use MCP if 'rag' AND 'mcp' are in the agent name
    if not (agent_name and "rag" in agent_name.lower() and "mcp" in agent_name.lower()):
         # If simple RAG, convert native tuples to basic context
         if retrieved_images:
            try:
                desc_list = []
                for item in retrieved_images:
                    # Handle tuple (id, score, meta) or dict
                    if isinstance(item, tuple) and len(item) > 2:
                        meta = item[2]
                        caption = meta.get('caption', 'No description')
                        desc_list.append(caption)
                    elif isinstance(item, dict):
                         meta = item.get('metadata', item)
                         caption = meta.get('caption', 'No description')
                         desc_list.append(caption)
                
                if desc_list:
                    rag_context = "\n".join([f"[Referensi Visual {i+1}]: {d}" for i, d in enumerate(desc_list)])
            except: pass
         return rag_context, mcp_records, use_mcp

    # MCP Logic
    try:
        print(f"   🔍 [Parallel] Retrieving similar images via Supabase MCP...")
        
        # Get Project ID (Hardcoded for stability)
        project_id = "wxunkovembyfyeocdxnh" 

        if not retrieved_images:
            return "Tidak ada gambar serupa yang ditemukan.", [], True

        # Extract Filenames for SQL
        target_filenames = []
        
        # Robust ID Extraction
        for item in retrieved_images:
            try:
                raw_id = "unknown"
                if isinstance(item, tuple) and len(item) > 0:
                     # ID is usually the first element in (id, score, metadata)
                     raw_id = item[0]
                elif isinstance(item, dict):
                     raw_id = item.get('id', 'unknown')
                
                if raw_id and raw_id != "unknown":
                    # Clean ID
                    clean_id = str(raw_id).replace('indoor_', '').replace('outdoor_', '').replace('street_', '')
                    target_filenames.append(clean_id)
            except: continue
        
        if not target_filenames:
             return "", [], True

        formatted_ids = ",".join([f"'{fid}'" for fid in target_filenames])
        
        # Dynamic MCP Client 
        # We need to create a temporary client connection since we are in a thread
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # Port 10399 is the robust one
        # Define Async Worker
        async def run_mcp_safe():
            mcp_port = 10399
            print(f"   💓 [Parallel] Connecting to Supabase MCP at port {mcp_port}...")
            async with MultiServerMCPClient(
                {"Supabase MCP ": {"url": f"http://localhost:{mcp_port}/sse", "transport": "sse"}}
            ) as client:
                print(f"   ✅ [Parallel] Connected to MCP Server.")
                
                # Get LangChain Tools
                tools = client.get_tools()
                sql_tool = next((t for t in tools if t.name == "execute_sql"), None)
                
                if not sql_tool:
                    print(f"   ⚠️ Tool 'execute_sql' not found. Available: {[t.name for t in tools]}")
                    return []

                print(f"   Note: Fetching detailed facts for IDs: {formatted_ids[:50]}...")
            
                sql_query = f"""
                SELECT * FROM image_indoor WHERE image_id IN ({formatted_ids})
                UNION ALL
                SELECT * FROM image_outdoor WHERE image_id IN ({formatted_ids})
                UNION ALL
                SELECT * FROM image_street WHERE image_id IN ({formatted_ids})
                """
                
                # Invoke LangChain Tool
                return await sql_tool.ainvoke({"query": sql_query, "project_id": project_id})

        # Initialize (Async Loop inside Thread)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(run_mcp_safe())
            use_mcp = True
            
            # --- Parsing Logic ---
            if isinstance(result, list):
                mcp_records = result
            else:
                 # Robust Text Parsing
                target_str = str(result)
                if hasattr(result, 'content'): target_str = str(result.content)
                
                match = re.search(r'\[.*\]', target_str, re.DOTALL)
                raw_data = []
                
                if match:
                    candidate = match.group(0)
                    try: raw_data = json.loads(candidate)
                    except:
                        try:
                            cleaned = candidate.replace('\\"', '"').replace('\\n', ' ')
                            raw_data = json.loads(cleaned)
                        except:
                            try: raw_data = ast.literal_eval(candidate)
                            except: pass
                    
                    if not raw_data:
                        try:
                             wrapped = f'"{candidate}"' 
                             s1 = json.loads(wrapped)
                             if isinstance(s1, str): raw_data = json.loads(s1)
                        except: pass
                
                # Double Encoded Check
                if isinstance(raw_data, str):
                    try: raw_data = json.loads(raw_data)
                    except: 
                         try: raw_data = ast.literal_eval(raw_data)
                         except: pass

                # Validate
                if isinstance(raw_data, list):
                     for rec in raw_data:
                         if isinstance(rec, dict):
                             # Fact Normalization
                             final_facts = {}
                             raw_facts = rec.get('facts') or rec.get('image_facts') or rec.get('facts_json')
                             if isinstance(raw_facts, str):
                                 try: 
                                      if raw_facts.strip().startswith('{'): raw_facts = json.loads(raw_facts)
                                 except: pass
                             
                             if isinstance(raw_facts, dict):
                                 for k, v in raw_facts.items():
                                     final_facts[k] = v
                                     if k.startswith('Q'): final_facts[k.lower()] = v
                                     if k.startswith('q'): final_facts[k.upper()] = v
                             
                             rec['facts'] = final_facts
                             mcp_records.append(rec)
            
            if mcp_records:
                print(f"   ✅ [Parallel] MCP Success! {len(mcp_records)} records.")
            else:
                print(f"   ⚠️ [Parallel] MCP Validated but NO records parsed.")

        finally:
            # Cleanup loop
            loop.close()

    except Exception as e:
        print(f"   ⚠️ [Parallel] MCP Execution Error: {e}")
        # Fallback to simple descriptions
        desc_list = []
        for item in retrieved_images:
             try:
                 if isinstance(item, tuple): desc_list.append(item[2].get('caption'))
                 else: desc_list.append(item.get('caption'))
             except: pass
        rag_context = "\n".join(str(d) for d in desc_list)
        return rag_context, [], use_mcp

    # Format RAG Context (Final)
    rag_list = []
    for i, item in enumerate(mcp_records, 1):
        caption = item.get('caption') or item.get('caption_raw') or "No Caption"
        facts = item.get('facts', {})
        
        fact_desc = ""
        if facts:
             q1 = facts.get('Q1') or facts.get('q1') or "-"
             q2 = facts.get('Q2') or facts.get('q2') or "-"
             q3 = facts.get('Q3') or facts.get('q3') or "-"
             fact_desc = f"Detail: {q1} | Konteks: {q2} | Ciri: {q3}"
        else:
             fact_desc = "Detail tidak tersedia."

        rag_list.append(f"[Referensi Visual {i}]: {caption}.. {fact_desc}")

    rag_context = "\n".join(rag_list)
    return rag_context, mcp_records, use_mcp