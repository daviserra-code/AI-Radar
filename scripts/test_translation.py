
import sys
import os

# Force UTF-8 encoding for Windows consoles
sys.stdout.reconfigure(encoding='utf-8')

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai_client import generate_article_from_news

def test_translation():
    test_cases = [
        {
            "title": "New Large Language Models are changing the world",
            "text": "The new Large Language Models (LLMs) are becoming more powerful. They are used for many tasks. Also, ensure your Power Supply Unit is adequate."
        },
        {
            "title": "Nostalgia: Floppy disk shaped cash card",
            "text": "A new pre-paid cash card looks like a floppy disk. It brings back nostalgia for the 90s."
        }
    ]

    print("Running translation tests...\n")

    for i, case in enumerate(test_cases):
        print(f"--- Test Case {i+1} ---")
        print(f"Original Title: {case['title']}")
        print(f"Original Text: {case['text']}")
        
        try:
            article = generate_article_from_news(case['title'], case['text'])
            print("\nGenerated Article:")
            print(f"Title: {article['title']}")
            print(f"Summary: {article['summary']}")
            print(f"Content Snippet: {article['content'][:200]}...")
            
            # Basic validation
            content_lower = article['content'].lower()
            title_lower = article['title'].lower()
            
            if "modelli di lingua grandi" in content_lower or "modelli di lingua grandi" in title_lower:
                print("❌ FAILED: Found 'Modelli di Lingua Grandi'")
            else:
                print("✅ PASSED: No 'Modelli di Lingua Grandi'")
                
            if "potenze elettromagnetiche" in content_lower:
                print("❌ FAILED: Found 'potenze elettromagnetiche'")
            else:
                print("✅ PASSED: No 'potenze elettromagnetiche'")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    test_translation()
