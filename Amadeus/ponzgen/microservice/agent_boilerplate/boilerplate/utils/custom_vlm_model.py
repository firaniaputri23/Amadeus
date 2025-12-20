"""
Custom VLM Model Wrapper for LangChain Integration

This module wraps the Gemma-2 + CLIP vision model with LangChain's BaseLLM interface,
enabling it to work seamlessly with the agent boilerplate.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import warnings
import os
from typing import Any, List, Optional
from PIL import Image
from pathlib import Path

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    CLIPVisionModel,
    AutoProcessor,
)
from langchain_core.language_models import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

# ===============================================================
# CONFIGURATION
# ===============================================================

curr_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up 5 levels from .../ponzgen/microservice/agent_boilerplate/boilerplate/utils/ to project root
project_root = os.path.abspath(os.path.join(curr_dir, "../../../../../"))
BASE_DIR = os.path.join(project_root, "models")
MODEL_PATH = os.path.join(BASE_DIR, "BLEU11.pt")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
GEMMA_MODEL_ID = "google/gemma-2-2b-it"
NUM_VIS_TOKEN = 50
TRIGGER_STR = "<start_image>"


# ===============================================================
# MODEL ARCHITECTURE (From BLEU-4_11.88.ipynb)
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
        img_embed = self.adapter_mlp(img_output)
        return img_embed


class MyModel(nn.Module):
    """Custom VLM combining Gemma-2 language model with CLIP vision model."""
    
    def __init__(self):
        super(MyModel, self).__init__()
        # Initialize Gemma-2
        self.model_language = AutoModelForCausalLM.from_pretrained(
            GEMMA_MODEL_ID,
            dtype=torch.bfloat16,
            device_map="auto" if DEVICE == "cuda" else None
        )
        self.tokenizer_language = AutoTokenizer.from_pretrained(GEMMA_MODEL_ID, padding_side='right')
        
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

    def generate_answer_text(self, text_input: str, max_new_tokens=256):
        """Generate answer for text-only input."""

        # 1. Basic format check for Gemma
        if "<start_of_turn>" not in text_input:
             instruction_now = f"<start_of_turn>user\n{text_input}<end_of_turn>\n<start_of_turn>model\n"
        else:
             instruction_now = text_input

        try:
            # 2. Tokenize
            inputs = self.tokenizer_language(instruction_now, return_tensors="pt")
            inputs = {k: v.to(self.model_language.device) for k, v in inputs.items()}
            
            # 3. Generate
            # 3. Generate
            outputs = self.model_language.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True, 
                temperature=0.7,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                pad_token_id=self.tokenizer_language.eos_token_id
            )
            
            # 4. Decode
            input_len = inputs['input_ids'].shape[1]
            generated_tokens = outputs[:, input_len:]
            output_text = self.tokenizer_language.decode(generated_tokens[0], skip_special_tokens=True)
            
            return output_text.strip()
        except Exception as e:
            print(f"ERROR in generate_answer_text: {e}")
            import traceback
            traceback.print_exc()
            return f"Error generating text: {str(e)}"

    def generate_answer_image(self, pil_image: Image.Image, max_new_tokens=64):
        """Generate answer given an image."""
        # 1. Create prompt
        instruction_now = "<start_of_turn>user\n"
        instruction_now += f"<start_image> {self.dummy_img_token}\n<end_image>\n"
        instruction_now += f"Create a simple description of the image!\n<end_of_turn>\n<start_of_turn>model\n"

        # 2. Tokenize prompt
        prompt_tokens = self.tokenizer_language([instruction_now], padding=False, return_tensors="pt")
        prompt_tokens = {k: v.to(self.model_language.device) for k, v in prompt_tokens.items()}

        # 3. Get text embeddings
        prompt_embeds = self.model_language.model.embed_tokens(prompt_tokens['input_ids'])

        # 4. Get image embeddings
        image_input = self.image_processor([pil_image], return_tensors="pt")['pixel_values']
        img_embed = self.get_image_embed(image_input)

        # 5. Find replacement location
        tokens_text_now = prompt_tokens['input_ids'][0].detach().cpu()
        dummy_location = self.search_trigger_idx(tokens_text_now, self.trigger_str_img)

        if dummy_location is None:
            print("WARNING: Could not find trigger string in prompt.")
            return ""

        # 6. Replace embeddings
        replaced_embeds = self.split_and_replace(prompt_embeds[0], img_embed[0], dummy_location)
        replaced_embeds = replaced_embeds.unsqueeze(0)

        # DEBUG: Print shapes
        # print(f"DEBUG: replaced_embeds shape: {replaced_embeds.shape}")
        # print(f"DEBUG: attention_mask shape: {prompt_tokens['attention_mask'].shape}")
        # print(f"DEBUG: max_new_tokens: {max_new_tokens}")
        # print(f"DEBUG: device: {self.model_language.device}")

        # Ensure max_new_tokens is set
        if max_new_tokens is None:
            max_new_tokens = 64

        # 7. Generate
        output_now = self.model_language.generate(
            inputs_embeds=replaced_embeds,
            attention_mask=prompt_tokens['attention_mask'],
            max_new_tokens=max_new_tokens,
            num_beams=5,
            do_sample=False,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
            pad_token_id=self.tokenizer_language.eos_token_id
        )

        # 8. Decode
        output_string = self.tokenizer_language.batch_decode(
            output_now,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        # 9. Clean output
        parts = output_string.split("model\n")
        if len(parts) > 1:
            return parts[-1].strip()
        else:
            return output_string.strip()


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

    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return "custom_vlm"

    def __init__(self, **kwargs):
        """Initialize the custom VLM LLM."""
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
                print(f"Successfully loaded model from Epoch {checkpoint.get('epoch', 'N/A')}, Step {checkpoint.get('global_step', 'N/A')}")
            else:
                print("WARNING: 'model_state_dict' not found in checkpoint. Loading assuming full state dict or other format.")
                # Try loading directly if it's just the state dict
                try:
                    self.model.adaptor.load_state_dict(checkpoint)
                except Exception as e:
                    print(f"Error loading state dict: {e}")
        else:
            print(f"WARNING: Model path {self.model_path} does not exist. Model initialized with random weights.")

        self.model.eval()
        print(f"✅ Custom VLM model ready on device: {self.device}")

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Run the LLM on the given prompt and input.
        """
        if self.model is None:
            print("DEBUG: Model is None, calling _load_model")
            self._load_model()
            
        response = self.model.generate_answer_text(prompt)
        
        # CRITICAL FIX: Emit the token callback so the frontend receives the data
        if run_manager:
            run_manager.on_llm_new_token(response)
        else:
            # print("DEBUG: No run_manager provided, skipping token emission")
            pass
            
        return response

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Async version of _call with streaming support."""
        if self.model is None:
            self._load_model()
            
        # Run generation in a separate thread to not block the event loop
        import asyncio
        import functools
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            functools.partial(self.model.generate_answer_text, prompt)
        )
        
        # Emit the token callback asynchronously
        # For non-streaming models like this one, we just emit the whole response as one token
        # unless we implement true streaming in generate_answer_text
        if run_manager:
            await run_manager.on_llm_new_token(response)
            
        return response

    async def astream(self, input: Any, config: Optional[Any] = None, **kwargs: Any):
        """Streaming support for Custom VLM."""
        # This is strictly for the agent_field_autofill which expects an astream method
        # The input is usually a list of messages, but we just need the last one's content
        prompt = ""
        if isinstance(input, list):
             # It's a list of BaseMessages, concatenate them
             # This ensures SystemMessages are included in the prompt
             prompt = "\n\n".join([msg.content for msg in input])
        else:
             prompt = str(input)
             
        response = await self._acall(prompt)
        
        # Yield the response in chunks (simulated streaming)
        chunk_size = 4
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i+chunk_size]
            yield type('Chunk', (object,), {'content': chunk})()
            import asyncio
            await asyncio.sleep(0.01) # Small delay to simulate streaming

    def invoke_with_image(self, image_path: str, prompt_text: str = None, max_new_tokens: int = 64) -> str:
        """
        Invoke the model with an image.
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
        """
        Bind tools to the model (required for LangChain ReAct agents).
        
        This is a pass-through method since our custom VLM doesn't natively support
        tool calling like OpenAI models. The actual tool invocation is handled by
        the ReAct agent framework, not the model itself.
        
        Args:
            tools: List of tools to bind
            **kwargs: Additional arguments
            
        Returns:
            self (for method chaining)
        """
        # Store tools for reference (optional)
        self._bound_tools = tools
        # Return self to support method chaining
        return self




# ===============================================================
# GLOBAL MODEL INSTANCE & HELPER
# ===============================================================

_custom_vlm_instance = None


def get_custom_vlm_model() -> CustomVLMLLM:
    """Get or create the global custom VLM model instance."""
    global _custom_vlm_instance
    if _custom_vlm_instance is None:
        _custom_vlm_instance = CustomVLMLLM()
    return _custom_vlm_instance

async def _maybe_handle_multimodal_and_augment(agent_input, max_new_tokens=64, model_name=None):
    """
    Helper function to check if input contains an image and invoke VLM if so.
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
        
        print("Using Custom VLM...")
        vlm = get_custom_vlm_model()
        vlm_response = vlm.invoke_with_image(image_path, max_new_tokens=max_new_tokens)
        
        print(f"VLM Response: {vlm_response}")
        
        # Augment the user message with the VLM description
        original_message = ""
        if isinstance(agent_input.input, dict):
            original_message = agent_input.input.get('text', '') or agent_input.input.get('messages', '')
            # Update input with VLM context
            agent_input.input['context'] = f"{agent_input.input.get('context', '')}\n\n[Image Description]: {vlm_response}"
        else:
            original_message = getattr(agent_input.input, 'messages', '')
            # Update input with VLM context
            current_context = getattr(agent_input.input, 'context', '')
            setattr(agent_input.input, 'context', f"{current_context}\n\n[Image Description]: {vlm_response}")
            


    return agent_input
