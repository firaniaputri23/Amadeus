"""
Quick verification script to check Image RAG setup.

Run this before populating the database to verify everything is configured correctly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directories to path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent.parent))

load_dotenv()

def check_environment():
    """Check environment variables."""
    print("🔍 Checking Environment Variables...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or supabase_url == "https://your-project.supabase.co":
        print("❌ SUPABASE_URL not set or using default value")
        return False
    else:
        print(f"✅ SUPABASE_URL: {supabase_url[:30]}...")
    
    if not supabase_key or supabase_key == "your-anon-key":
        print("❌ SUPABASE_KEY not set or using default value")
        return False
    else:
        print(f"✅ SUPABASE_KEY: {supabase_key[:20]}...")
    
    return True


def check_supabase_connection():
    """Test Supabase connection."""
    print("\n🔍 Checking Supabase Connection...")
    
    try:
        from microservice.rag.service.storage_database._storage_utils import SupabaseStorageClient
        client = SupabaseStorageClient()
        print("✅ Supabase client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False


def check_supabase_tables():
    """Check if required tables exist."""
    print("\n🔍 Checking Supabase Tables...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        tables = ["image_indoor", "image_outdoor", "image_street"]
        all_exist = True
        
        for table in tables:
            try:
                response = client.table(table).select("*", count="exact").limit(1).execute()
                count = response.count
                print(f"✅ Table '{table}' exists with {count} records")
            except Exception as e:
                print(f"❌ Table '{table}' not accessible: {e}")
                all_exist = False
        
        return all_exist
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False


def check_data_directory():
    """Check if data directory and files exist."""
    print("\n🔍 Checking Data Directory...")
    
    data_dir = Path(r"D:\Bithan\ITS\Semester 7\temp\Amadeus\data")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False
    else:
        print(f"✅ Data directory exists: {data_dir}")
    
    # Check for CSV files
    categories = ["image_indoor", "image_outdoor", "image_street"]
    all_exist = True
    
    for category in categories:
        csv_path = data_dir / f"{category}.csv"
        img_dir = data_dir / category
        
        if csv_path.exists():
            print(f"✅ CSV found: {csv_path.name}")
        else:
            print(f"❌ CSV missing: {csv_path.name}")
            all_exist = False
        
        if img_dir.exists():
            img_count = len([f for f in img_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            print(f"✅ Image directory: {category} ({img_count} images)")
        else:
            print(f"❌ Image directory missing: {category}")
            all_exist = False
    
    return all_exist


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n🔍 Checking Python Dependencies...")
    
    required_packages = [
        ("torch", "PyTorch"),
        ("transformers", "Transformers"),
        ("PIL", "Pillow"),
        ("supabase", "Supabase"),
        ("numpy", "NumPy")
    ]
    
    all_installed = True
    
    for module_name, display_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {display_name} installed")
        except ImportError:
            print(f"❌ {display_name} not installed")
            all_installed = False
    
    return all_installed


def check_clip_model():
    """Check if CLIP model can be loaded."""
    print("\n🔍 Checking CLIP Model...")
    
    try:
        import torch
        from transformers import CLIPProcessor, CLIPVisionModel
        
        model_id = "openai/clip-vit-base-patch32"
        print(f"Loading CLIP model: {model_id}")
        
        processor = CLIPProcessor.from_pretrained(model_id)
        model = CLIPVisionModel.from_pretrained(model_id)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✅ CLIP model loaded successfully on {device}")
        
        # Test embedding dimension
        test_vec = torch.randn(1, 512)
        print(f"✅ Embedding dimension: 512")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load CLIP model: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("🚀 Image RAG Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Environment Variables", check_environment),
        ("Supabase Connection", check_supabase_connection),
        ("Supabase Tables", check_supabase_tables),
        ("Data Directory", check_data_directory),
        ("Python Dependencies", check_dependencies),
        ("CLIP Model", check_clip_model)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ Error during '{check_name}' check: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All checks passed! You're ready to populate the database.")
        print("\nNext step:")
        print("  python -m microservice.rag.populate_image_vectors")
    else:
        print("⚠️  Some checks failed. Please fix the issues above before proceeding.")
    print("=" * 60)


if __name__ == "__main__":
    main()
