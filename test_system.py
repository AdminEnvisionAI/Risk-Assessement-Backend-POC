"""
Test script to verify the integrated system is working correctly.
Run this before running the full main.py to catch any issues early.
"""

import os
import sys
from dotenv import load_dotenv

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    try:
        from langchain_core.messages import HumanMessage
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langgraph.graph import StateGraph
        from tavily import TavilyClient
        print("✓ All packages imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("\nPlease install missing packages:")
        print("pip install langchain-core langchain-google-genai langgraph tavily-python python-dotenv")
        return False

def test_env_vars():
    """Test if environment variables are set"""
    print("\nTesting environment variables...")
    load_dotenv()
    
    google_key = os.getenv("GOOGLE_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if not google_key:
        print("✗ GOOGLE_API_KEY not found in .env")
        return False
    else:
        print(f"✓ GOOGLE_API_KEY found (starts with: {google_key[:20]}...)")
    
    if not tavily_key:
        print("✗ TAVILY_API_KEY not found in .env")
        return False
    else:
        print(f"✓ TAVILY_API_KEY found (starts with: {tavily_key[:20]}...)")
    
    return True

def test_api_connections():
    """Test if API connections work"""
    print("\nTesting API connections...")
    load_dotenv()
    
    # Test Google API
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.0
        )
        response = llm.invoke("Say 'test successful'")
        print("✓ Google API connection successful")
        google_ok = True
    except Exception as e:
        print(f"✗ Google API connection failed: {e}")
        google_ok = False
    
    # Test Tavily API
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(os.getenv("TAVILY_API_KEY"))
        response = tavily.search(query="test", max_results=1)
        print("✓ Tavily API connection successful")
        tavily_ok = True
    except Exception as e:
        print(f"✗ Tavily API connection failed: {e}")
        tavily_ok = False
    
    return google_ok and tavily_ok

def test_module_structure():
    """Test if the deep_research module structure is correct"""
    print("\nTesting module structure...")
    
    required_files = [
        "deep_research/__init__.py",
        "deep_research/graph.py",
        "deep_research/nodes.py",
        "deep_research/state.py",
        "deep_research/prompts.py",
        "deep_research/risk_prompts.py",
        "deep_research/configuration.py",
        "deep_research/utils.py",
        "deep_research/struct.py"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print(f"✗ Missing files: {missing}")
        return False
    else:
        print("✓ All required module files present")
        return True

def test_graph_build():
    """Test if the graph can be built without errors"""
    print("\nTesting graph construction...")
    try:
        from deep_research.graph import agent_graph
        print("✓ Agent graph built successfully")
        return True
    except Exception as e:
        print(f"✗ Graph build failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directories():
    """Test if required directories exist or can be created"""
    print("\nTesting directories...")
    
    dirs = ["logs", "logs/section_content", "reports"]
    
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
            print(f"✓ Directory '{d}' ready")
        except Exception as e:
            print(f"✗ Cannot create directory '{d}': {e}")
            return False
    
    return True

def main():
    print("="*80)
    print("INTEGRATED SYSTEM TEST")
    print("="*80)
    print()
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment Variables", test_env_vars),
        ("Module Structure", test_module_structure),
        ("Graph Construction", test_graph_build),
        ("Directory Setup", test_directories),
        ("API Connections", test_api_connections)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
        print()
    
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    
    if all(results.values()):
        print("="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nThe system is ready to use. You can now run:")
        print("  python main.py")
        print("\nTo generate a risk assessment report!")
        return 0
    else:
        print("="*80)
        print("⚠️  SOME TESTS FAILED")
        print("="*80)
        print("\nPlease fix the issues above before running main.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
