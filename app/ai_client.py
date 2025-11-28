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
                {"role": "system", "content": "Rispondi sempre in italiano."},
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
Sei un analista di notizie specializzato in intelligenza artificiale.

Ho questa notizia grezza (titolo + testo).

TITOLO:
[INIZIO_TITOLO]
{raw_title}
[FINE_TITOLO]

TESTO:
[INIZIO_TESTO]
{raw_text}
[FINE_TESTO]

1. Riscrivi un titolo chiaro e tecnico in massimo 90 caratteri.
2. Scrivi un riassunto in 2-3 frasi (max ~80 parole) che spieghi il punto chiave.
3. Scrivi un contenuto esteso e DETTAGLIATO in italiano (800-1500 parole) con:
   - Introduzione con contesto
   - Sezioni con sottotitoli (usa ## per i titoli)
   - Dettagli tecnici specifici
   - Implicazioni pratiche
   - Conclusione con prospettive future
   - Usa Markdown per formattazione (grassetto, liste, codice)
4. Scegli UNA sola categoria tra: LLM, Frameworks, Hardware, Market, Altro.

IMPORTANTE:
- Rispondi SOLO in JSON valido.
- Nessun commento fuori dal JSON, nessun testo prima o dopo.
- Usa esattamente queste chiavi: "title", "summary", "content", "category".
- NON usare backticks (`) nel JSON, usa solo virgolette doppie (").
- Il campo "content" deve essere una SINGOLA STRINGA, NON un oggetto o array.
- Usa \\n per le newline nella stringa del content.
- NON usare triple-quotes (""") o altri delimitatori speciali.

Esempio di formato (rispetta esattamente questo schema):

{{
  "title": "Titolo breve...",
  "summary": "Riassunto in 2-3 frasi...",
  "content": "## Introduzione\\n\\nContenuto lungo con sezioni...\\n\\n## Dettagli\\n\\nAltro contenuto...\\n\\n## Conclusione\\n\\nContenutofinal...",
  "category": "LLM"
}}

RICORDA: "content" è una STRINGA, non un oggetto!
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