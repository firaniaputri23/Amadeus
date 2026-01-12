"""
Script to populate Supabase vector database with image embeddings from the data directory.

This script:
1. Reads images and captions from CSV files
2. Generates embeddings using CLIP vision model
3. Stores them in Supabase vector database (without deleting existing data)
"""

import os
import sys
import csv
import json
from pathlib import Path
from typing import List, Dict, Tuple
import warnings
from PIL import Image

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add parent directories to path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent.parent))

from dotenv import load_dotenv
import torch
from transformers import CLIPModel, CLIPProcessor

# Import storage client
from microservice.rag.service.storage_database._storage_utils import SupabaseStorageClient

load_dotenv()


class ImageEmbedder:
    """
    Image embedder using CLIP ViT-Large model for both images and text.
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Use ViT-Large to generate 768-dimensional embeddings
        self.clip_model_id = "openai/clip-vit-large-patch14"
        
        print(f"🔧 Initializing CLIP ViT-Large model for image embeddings on {self.device}...")
        self.processor = CLIPProcessor.from_pretrained(self.clip_model_id)
        # Use full CLIP model (not just vision) for consistency
        self.model = CLIPModel.from_pretrained(
            self.clip_model_id,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        
        self.model.eval()
        print(f"✅ CLIP ViT-Large model ready! (768-dimensional embeddings)")
    
    def embed_image(self, image_path: str) -> List[float]:
        """
        Generate embedding for a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Embedding vector as list of floats (768 dimensions)
        """
        try:
            # Load and process image
            image = Image.open(image_path).convert('RGB')
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embedding using get_image_features
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            # Convert to list (handle bfloat16)
            embedding = image_features[0].cpu().float().numpy().tolist()
            return embedding
        except Exception as e:
            print(f"❌ Error embedding image {image_path}: {e}")
            return None
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using CLIP's text encoder.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                # CLIP text encoder
                from transformers import CLIPTextModel
                text_model = CLIPTextModel.from_pretrained(self.clip_model_id).to(self.device)
                text_features = text_model(**inputs).pooler_output
                # Normalize
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
            embedding = text_features[0].cpu().numpy().tolist()
            return embedding
        except Exception as e:
            print(f"❌ Error embedding text: {e}")
            return None
    
    @property
    def embedding_dim(self) -> int:
        """Get dimension of embeddings (CLIP uses 512)."""
        return 512


class ImageVectorPopulator:
    """
    Populates Supabase with image embeddings.
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.embedder = ImageEmbedder()
        self.storage_client = SupabaseStorageClient()
        
        # Categories to process
        self.categories = ["image_indoor", "image_outdoor", "image_street"]
    
    def read_csv(self, csv_path: Path) -> List[Dict]:
        """
        Read image metadata from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            List of dictionaries containing image metadata
        """
        records = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
            print(f"📄 Read {len(records)} records from {csv_path.name}")
        except Exception as e:
            print(f"❌ Error reading {csv_path}: {e}")
        return records
    
    def process_category(self, category: str) -> List[Dict]:
        """
        Process a single category (indoor/outdoor/street).
        
        Args:
            category: Category name (e.g., "image_indoor")
            
        Returns:
            List of records with embeddings
        """
        csv_path = self.data_dir / f"{category}.csv"
        image_dir = self.data_dir / category
        
        if not csv_path.exists():
            print(f"⚠️  CSV not found: {csv_path}")
            return []
        
        if not image_dir.exists():
            print(f"⚠️  Image directory not found: {image_dir}")
            return []
        
        print(f"\n📂 Processing category: {category}")
        records = self.read_csv(csv_path)
        
        processed_records = []
        for idx, record in enumerate(records, 1):
            image_id = record.get('image_id', '')
            caption_raw = record.get('caption_raw', '')
            # Handle both 'facts' and 'image_facts' columns from CSV
            facts = record.get('facts') or record.get('image_facts', '{}')
            
            image_path = image_dir / image_id
            
            if not image_path.exists():
                print(f"⚠️  [{idx}/{len(records)}] Image not found: {image_id}")
                continue
            
            # Generate image embedding
            print(f"🖼️  [{idx}/{len(records)}] Processing: {image_id}")
            image_embedding = self.embedder.embed_image(str(image_path))
            
            if image_embedding is None:
                continue
            
            # Prepare metadata
            try:
                facts_dict = json.loads(facts) if isinstance(facts, str) else facts
            except:
                facts_dict = {}
            
            # Create combined text for better retrieval
            combined_text = f"{caption_raw}\n\nFacts: {json.dumps(facts_dict, ensure_ascii=False)}"
            
            processed_record = {
                'file_id': f"{category}_{image_id}",
                'category': category.replace('image_', ''),  # indoor/outdoor/street
                'image_id': image_id,
                'image_path': str(image_path.relative_to(self.data_dir.parent)),
                'caption_raw': caption_raw,
                'facts': facts_dict,
                'content': combined_text,  # For text search
                'embedding': image_embedding,
                'metadata': {
                    'category': category.replace('image_', ''),
                    'source': 'csv_import',
                    'has_facts': bool(facts_dict)
                }
            }
            
            processed_records.append(processed_record)
            print(f"✅ [{idx}/{len(records)}] Processed: {image_id}")
        
        return processed_records
    
    def insert_to_database_by_category(self, records: List[Dict]):
        """
        Insert records into appropriate Supabase tables by category.
        Updates existing records instead of creating duplicates.
        
        Args:
            records: List of records to insert
        """
        if not records:
            print("⚠️  No records to insert")
            return
        
        from supabase import create_client
        import os
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        # Group records by category
        categorized = {
            'indoor': [],
            'outdoor': [],
            'street': []
        }
        
        for record in records:
            category = record['category']
            if category in categorized:
                # Map to existing schema
                # Note: image_indoor uses 'facts', but image_outdoor and image_street use 'image_facts'
                facts_key = 'facts' if category == 'indoor' else 'image_facts'
                
                db_record = {
                    'image_id': record['image_id'],
                    'image_url': record['image_path'],  # Using path as URL
                    'caption_raw': record['caption_raw'],
                    facts_key: record['facts'],  # Use correct column name per table
                    'embedding': record['embedding']
                }
                categorized[category].append(db_record)
        
        # Insert/update into each table
        table_mapping = {
            'indoor': 'image_indoor',
            'outdoor': 'image_outdoor',
            'street': 'image_street'
        }
        
        for category, category_records in categorized.items():
            if not category_records:
                continue
                
            table_name = table_mapping[category]
            print(f"\n💾 Processing {len(category_records)} records for '{table_name}'...")
            
            try:
                # Process records one by one to handle duplicates
                total_inserted = 0
                total_updated = 0
                total_skipped = 0
                
                for idx, db_record in enumerate(category_records, 1):
                    image_id = db_record['image_id']
                    
                    # Check if record already exists
                    existing = client.table(table_name).select("id").eq("image_id", image_id).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Record exists - update it
                        record_id = existing.data[0]['id']
                        client.table(table_name).update(db_record).eq("id", record_id).execute()
                        total_updated += 1
                        if idx % 5 == 0 or idx == len(category_records):
                            print(f"🔄 Updated {total_updated}, Inserted {total_inserted}, Skipped {total_skipped} / {len(category_records)}")
                    else:
                        # Record doesn't exist - insert it
                        client.table(table_name).insert(db_record).execute()
                        total_inserted += 1
                        if idx % 5 == 0 or idx == len(category_records):
                            print(f"✅ Updated {total_updated}, Inserted {total_inserted}, Skipped {total_skipped} / {len(category_records)}")
                
                print(f"🎉 Completed {table_name}: {total_inserted} inserted, {total_updated} updated!")
                
            except Exception as e:
                print(f"❌ Error inserting to {table_name}: {e}")
                import traceback
                traceback.print_exc()
    
    def populate_all(self):
        """
        Process all categories and populate the database.
        Inserts into existing tables: image_indoor, image_outdoor, image_street
        """
        print("=" * 60)
        print("🚀 Starting Image Vector Population")
        print("=" * 60)
        
        all_records = []
        
        for category in self.categories:
            records = self.process_category(category)
            all_records.extend(records)
        
        print(f"\n📊 Summary:")
        print(f"   - Total records processed: {len(all_records)}")
        print(f"   - Indoor: {len([r for r in all_records if r['category'] == 'indoor'])}")
        print(f"   - Outdoor: {len([r for r in all_records if r['category'] == 'outdoor'])}")
        print(f"   - Street: {len([r for r in all_records if r['category'] == 'street'])}")
        
        # Insert to database by category
        self.insert_to_database_by_category(all_records)
        
        print("\n" + "=" * 60)
        print("✨ Population Complete!")
        print("=" * 60)


def main():
    """Main function to run the population script."""
    # Set data directory (adjust this path as needed)
    data_dir = r"C:\Users\Firania\Downloads\Amadeus\Amadeus\data"
    
    
    print(f"📍 Data directory: {data_dir}")
    print(f"📍 Target tables: image_indoor, image_outdoor, image_street")
    print()
    
    # Create populator and run
    populator = ImageVectorPopulator(data_dir)
    populator.populate_all()


if __name__ == "__main__":
    main()
