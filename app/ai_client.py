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

Esempio di formato (rispetta questo schema):

{{
  "title": "Titolo...",
  "summary": "Riassunto...",
  "content": "Contenuto lungo...",
  "category": "LLM"
}}
"""


def _extract_json_block(text: str) -> str:
    """
    I modelli piccoli a volte si "scordano" di stare zitti.
    Qui cerchiamo il primo '{' e l'ultima '}' e proviamo a estrarre un blocco JSON.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("Impossibile trovare un blocco JSON nella risposta del modello.")
    return text[start : end + 1]


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

    return {
        "title": data["title"].strip(),
        "summary": data["summary"].strip(),
        "content": data["content"].strip(),
        "category": category,
    }