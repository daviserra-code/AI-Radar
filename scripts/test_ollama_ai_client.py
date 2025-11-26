import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT_DIR)

from app import ai_client

raw_title = "OpenAI presenta un nuovo modello LLM"
raw_text = "OpenAI ha annunciato oggi un nuovo modello di grandi dimensioni con migliori prestazioni e minori costi..."

article = ai_client.generate_article_from_news(raw_title, raw_text)

print("TITOLO:", article["title"])
print("CATEGORIA:", article["category"])
print("SUMMARY:", article["summary"][:200], "...")
print("CONTENT LEN:", len(article["content"]))
