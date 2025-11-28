"""
ai_client.py

Layer di integrazione tra il portale e il modello LLM.
Questa versione usa Ollama in locale.

Assunzioni:
- Ollama gira su: http://127.0.0.1:11434 (o quello che imposti in OLLAMA_HOST)
- Hai già scaricato un modello, es. "llama3.2:3b"
"""

from typing import Dict
import json
import os
import ollama


# Cambia qui il nome del modello se serve
#MODEL_NAME = "llama3.2:3b"  # oppure il modello che hai in `ollama list`
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


class LLMError(Exception):
    pass


def _call_llm(prompt: str) -> str:
    """
    Chiama il modello Ollama in locale usando la libreria ufficiale.
    Ritorna il testo della risposta (content) così com'è.
    """
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a professional tech journalist. Write clear, accurate, and grammatically correct articles in English."},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
    except Exception as e:
        raise LLMError(f"Errore nella chiamata a Ollama: {e}")

    try:
        content = response["message"]["content"]
    except Exception:
        raise LLMError(f"Risposta inattesa da Ollama: {response}")

    return content


def build_news_prompt(raw_title: str, raw_text: str) -> str:
    """
    Costruisce un prompt per trasformare una news grezza in:
      - titolo ottimizzato
      - riassunto
      - articolo esteso
      - categoria macro (LLM / Frameworks / Hardware / Market / Altro)
    """
    return f"""
You are a professional AI and technology news analyst.

I have this raw news article (title + text).

TITLE:
[START_TITLE]
{raw_title}
[END_TITLE]

TEXT:
[START_TEXT]
{raw_text}
[END_TEXT]

1. Rewrite a clear, technical title in maximum 90 characters.
2. Write a summary in 2-3 sentences (max ~80 words) explaining the key point.
3. Write an extended and DETAILED article in English (800-1500 words) with:
   - Introduction with context
   - Sections with subheadings (use ## for headers)
   - Specific technical details
   - Practical implications
   - Conclusion with future outlook
   - Use Markdown formatting (bold, lists, code)
4. Choose ONE category from: LLM, Frameworks, Hardware, Market, Other.

IMPORTANT:
- Reply ONLY with valid JSON.
- No comments outside JSON, no text before or after.
- Use exactly these keys: "title", "summary", "content", "category".
- DO NOT use backticks (`) in JSON, use only double quotes (").
- The "content" field must be a SINGLE STRING, NOT an object or array.
- Use \\n for newlines in the content string.
- DO NOT use triple-quotes or other special delimiters.
- Write in clear, grammatically correct English.

Format example (follow this schema exactly):

{{
  "title": "Short title...",
  "summary": "Summary in 2-3 sentences...",
  "content": "## Introduction\\n\\nLong content with sections...\\n\\n## Details\\n\\nMore content...\\n\\n## Conclusion\\n\\nFinal content...",
  "category": "LLM"
}}

REMEMBER: "content" is a STRING, not an object!
"""


def _extract_json_block(text: str) -> str:
    """
    I modelli piccoli a volte si "scordano" di stare zitti.
    Qui cerchiamo il primo '{' e l'ultima '}' e proviamo a estrarre un blocco JSON.
    Inoltre, rimuoviamo i markdown code blocks se presenti e gestiamo i backticks nei valori.
    """
    # Rimuovi i markdown code blocks se presenti
    text = text.replace("```json", "").replace("```", "")
    
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("Impossibile trovare un blocco JSON nella risposta del modello.")
    
    json_block = text[start : end + 1]
    
    # Fix: il modello a volte usa backticks per valori multilinea invece di stringhe JSON valide
    # Sostituisci pattern come "content": `...` con "content": "..."
    # Dobbiamo gestire anche il caso multilinea
    import re
    
    # Pattern per trovare "key": `multiline value` e sostituirlo con "key": "escaped value"
    def replace_backtick_value(match):
        key = match.group(1)
        value = match.group(2)
        # Escape delle virgolette e newline nel valore
        value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{key}": "{value}"'
    
    # Cerca pattern come "key": `value`
    json_block = re.sub(r'"(\w+)":\s*`([^`]*)`', replace_backtick_value, json_block, flags=re.DOTALL)
    
    return json_block


def generate_article_from_news(raw_title: str, raw_text: str) -> Dict[str, str]:
    """
    Dato un titolo + testo grezzo, interroga il LLM e ritorna
    un dict pronto per creare un Article.
    """
    prompt = build_news_prompt(raw_title, raw_text)
    raw_response = _call_llm(prompt)

    # Proviamo a fare il parse robusto del JSON
    try:
        json_str = _extract_json_block(raw_response)
        data = json.loads(json_str)
    except Exception as e:
        raise LLMError(
            f"Errore nel parsing JSON dalla risposta del modello: {e}\nRisposta:\n{raw_response}"
        )

    # normalizziamo un minimo la categoria
    cat_raw = data.get("category", "Altro") or "Altro"
    cat = cat_raw.strip().lower()
    if "llm" in cat:
        category = "LLM"
    elif "frame" in cat:
        category = "Frameworks"
    elif "hard" in cat or "gpu" in cat or "mini" in cat:
        category = "Hardware"
    elif "market" in cat or "mercato" in cat:
        category = "Market"
    else:
        category = "Altro"

    # Gestisci il caso in cui content sia un oggetto invece di una stringa
    content = data.get("content", "")
    if isinstance(content, dict):
        # Se il modello ha restituito un oggetto, converti in stringa markdown
        parts = []
        for key, value in content.items():
            if isinstance(value, dict):
                parts.append(f"## {key.replace('_', ' ').title()}")
                for subkey, subvalue in value.items():
                    parts.append(f"### {subkey.replace('_', ' ').title()}")
                    parts.append(str(subvalue).strip().strip('"""').strip())
            else:
                parts.append(f"## {key.replace('_', ' ').title()}")
                parts.append(str(value).strip().strip('"""').strip())
        content = "\n\n".join(parts)
    elif not isinstance(content, str):
        content = str(content)

    return {
        "title": data["title"].strip(),
        "summary": data["summary"].strip(),
        "content": content.strip(),
        "category": category,
    }