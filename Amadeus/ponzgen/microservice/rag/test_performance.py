"""
Performance testing script for Image RAG system.

This script tests and compares:
1. VLM without RAG (baseline)
2. VLM with RAG
3. Different categories
4. Response quality and time
"""

import requests
import time
import json
from typing import List, Dict
from datetime import datetime


class ImageRAGTester:
    """Test harness for Image RAG performance evaluation."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    def test_connection(self) -> bool:
        """Test if server is running."""
        try:
            response = requests.get(f"{self.base_url}/image-rag/stats", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_stats(self) -> Dict:
        """Get current database statistics."""
        response = requests.get(f"{self.base_url}/image-rag/stats")
        return response.json() if response.status_code == 200 else {}
    
    def test_search(self, query: str, category: str = None, top_k: int = 5) -> Dict:
        """Test image search without response generation."""
        start_time = time.time()
        
        payload = {
            "query": query,
            "top_k": top_k
        }
        if category:
            payload["category"] = category
        
        response = requests.post(
            f"{self.base_url}/image-rag/search",
            json=payload
        )
        
        elapsed = time.time() - start_time
        
        result = {
            "type": "search",
            "query": query,
            "category": category,
            "top_k": top_k,
            "success": response.status_code == 200,
            "time": elapsed,
            "data": response.json() if response.status_code == 200 else None
        }
        
        self.results.append(result)
        return result
    
    def test_rag_query(self, query: str, category: str = None, 
                       model_name: str = "custom-vlm", top_k: int = 5) -> Dict:
        """Test full RAG pipeline with VLM response generation."""
        start_time = time.time()
        
        payload = {
            "query": query,
            "top_k": top_k,
            "model_name": model_name,
            "temperature": 0.0
        }
        if category:
            payload["category"] = category
        
        response = requests.post(
            f"{self.base_url}/image-rag/query",
            json=payload
        )
        
        elapsed = time.time() - start_time
        
        result = {
            "type": "rag_query",
            "query": query,
            "category": category,
            "model": model_name,
            "top_k": top_k,
            "success": response.status_code == 200,
            "time": elapsed,
            "data": response.json() if response.status_code == 200 else None
        }
        
        self.results.append(result)
        return result
    
    def run_test_suite(self):
        """Run comprehensive test suite."""
        print("=" * 70)
        print("🚀 Image RAG Performance Test Suite")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check connection
        print("🔍 Testing connection...")
        if not self.test_connection():
            print("❌ Cannot connect to server. Make sure it's running on", self.base_url)
            return
        print("✅ Server is running")
        print()
        
        # Get stats
        print("📊 Database Statistics:")
        stats = self.get_stats()
        print(json.dumps(stats, indent=2))
        print()
        
        # Test queries
        test_cases = [
            {
                "name": "Indoor workspace search",
                "query": "people working with laptops at desks",
                "category": "indoor",
                "top_k": 5
            },
            {
                "name": "Coffee shop scene",
                "query": "barista preparing coffee drinks",
                "category": "indoor",
                "top_k": 3
            },
            {
                "name": "Outdoor nature",
                "query": "natural outdoor environment with plants",
                "category": "outdoor",
                "top_k": 5
            },
            {
                "name": "Street scene",
                "query": "people walking on urban streets",
                "category": "street",
                "top_k": 3
            },
            {
                "name": "Cross-category (no filter)",
                "query": "groups of people gathered together",
                "category": None,
                "top_k": 5
            }
        ]
        
        print("=" * 70)
        print("🔍 Test 1: Search Performance (Retrieval Only)")
        print("=" * 70)
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['name']}")
            print(f"  Query: {test['query']}")
            print(f"  Category: {test['category'] or 'All'}")
            
            result = self.test_search(
                query=test['query'],
                category=test['category'],
                top_k=test['top_k']
            )
            
            if result['success']:
                print(f"  ✅ Success in {result['time']:.2f}s")
                print(f"  Retrieved: {result['data']['total_results']} images")
                if result['data']['results']:
                    top_result = result['data']['results'][0]
                    print(f"  Top result: {top_result['image_id']} (similarity: {top_result['similarity']:.4f})")
            else:
                print(f"  ❌ Failed in {result['time']:.2f}s")
        
        print("\n" + "=" * 70)
        print("🤖 Test 2: Full RAG with VLM (Retrieval + Generation)")
        print("=" * 70)
        
        rag_test_cases = [
            {
                "name": "Indoor activity analysis",
                "query": "What activities are people doing in these indoor spaces?",
                "category": "indoor",
                "top_k": 5
            },
            {
                "name": "Workspace description",
                "query": "Describe the work environments shown in the images",
                "category": "indoor",
                "top_k": 3
            },
            {
                "name": "Outdoor environment",
                "query": "What kind of outdoor environments are visible?",
                "category": "outdoor",
                "top_k": 3
            }
        ]
        
        for i, test in enumerate(rag_test_cases, 1):
            print(f"\n[{i}/{len(rag_test_cases)}] {test['name']}")
            print(f"  Query: {test['query']}")
            print(f"  Category: {test['category']}")
            
            result = self.test_rag_query(
                query=test['query'],
                category=test['category'],
                model_name="custom-vlm",
                top_k=test['top_k']
            )
            
            if result['success']:
                print(f"  ✅ Success in {result['time']:.2f}s")
                response_text = result['data']['response']
                print(f"  Response length: {len(response_text)} chars")
                print(f"  Retrieved images: {len(result['data']['retrieved_images'])}")
                print(f"  Response preview: {response_text[:150]}...")
            else:
                print(f"  ❌ Failed in {result['time']:.2f}s")
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary statistics."""
        print("\n" + "=" * 70)
        print("📊 Test Summary")
        print("=" * 70)
        
        # Overall stats
        total_tests = len(self.results)
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        print(f"\nTotal tests: {total_tests}")
        print(f"Successful: {len(successful)} ({len(successful)/total_tests*100:.1f}%)")
        print(f"Failed: {len(failed)} ({len(failed)/total_tests*100:.1f}%)")
        
        if successful:
            # Search tests
            search_tests = [r for r in successful if r['type'] == 'search']
            if search_tests:
                avg_search_time = sum(r['time'] for r in search_tests) / len(search_tests)
                print(f"\nSearch (retrieval only):")
                print(f"  Average time: {avg_search_time:.2f}s")
                print(f"  Min time: {min(r['time'] for r in search_tests):.2f}s")
                print(f"  Max time: {max(r['time'] for r in search_tests):.2f}s")
            
            # RAG tests
            rag_tests = [r for r in successful if r['type'] == 'rag_query']
            if rag_tests:
                avg_rag_time = sum(r['time'] for r in rag_tests) / len(rag_tests)
                print(f"\nRAG (retrieval + generation):")
                print(f"  Average time: {avg_rag_time:.2f}s")
                print(f"  Min time: {min(r['time'] for r in rag_tests):.2f}s")
                print(f"  Max time: {max(r['time'] for r in rag_tests):.2f}s")
        
        # By category
        print(f"\nResults by category:")
        categories = set(r.get('category') for r in self.results if r.get('category'))
        for cat in sorted(categories):
            cat_results = [r for r in successful if r.get('category') == cat]
            if cat_results:
                avg_time = sum(r['time'] for r in cat_results) / len(cat_results)
                print(f"  {cat}: {len(cat_results)} tests, avg {avg_time:.2f}s")
        
        print("\n" + "=" * 70)
        print(f"✅ Test suite completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    def save_results(self, filename: str = "test_results.json"):
        """Save test results to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")


def main():
    """Run the test suite."""
    import sys
    
    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = ImageRAGTester(base_url=base_url)
    tester.run_test_suite()
    
    # Save results
    tester.save_results("image_rag_test_results.json")


if __name__ == "__main__":
    main()
