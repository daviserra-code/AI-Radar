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



def _call_llm(prompt: str, glossary: Dict[str, str] = None) -> str:
    """
    Chiama il modello Ollama in locale usando HTTPX per controllo timeout.
    Ritorna il testo della risposta (content) così com'è. 
    Timeout impostato a 120 secondi.
    """
    import logging
    import httpx
    
    logger = logging.getLogger(__name__)
    
    # URL di default se OLLAMA_HOST non è settato o è solo base url
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    # Assicurati che l'host non abbia trailing slash
    host = host.rstrip("/")
    url = f"{host}/api/chat"

    # COSTRUZIONE DEL GLOSSARIO DINAMICO
    glossary_text = ""
    if glossary:
        glossary_lines = []
        for banned, correct in glossary.items():
            glossary_lines.append(f'- "{correct}" -> [USAL] (MAI: "{banned}")')
        glossary_text = "\n".join(glossary_lines)
    
    system_prompt = f"""Sei un Redattore Tech Senior per una testata italiana d'élite (stile Wired/Ars Technica).
Il tuo compito è RISCRIVERE (non tradurre letteralmente) notizie tech dall'inglese all'italiano, mantenendo un tono professionale, fluido e naturale.

GLOSSARIO TECNICO OBBLIGATORIO (MANDATORY):
Devi usare SEMPRE i termini a sinistra, MAI quelli a destra.
- "LLM" o "Large Language Models"  -> [USAL] (MAI: "Modelli di linguaggio grande")
- "Fine-tuning"                    -> [USAL] (MAI: "Sintonizzazione fine")
- "Framework"                      -> [USAL] (MAI: "Quadro" o "Cornice")
- "Pipeline"                       -> [USAL] (MAI: "Tubatura" o "Condotto")
- "Token"                          -> [USAL] (MAI: "Gettoni")
- "Benchmark"                      -> [USAL] (MAI: "Panchina" o "Riferimento")
- "Embeddings"                     -> [USAL] (MAI: "Immergimenti")
- "Deploy" / "Deployment"          -> [USAL] o "Rilascio" (MAI: "Schieramento")
- "Open Source"                    -> [USAL] (MAI: "Sorgente aperta")
- "Silicon" (contesto chip)        -> "Silicio" (MAI: "Silicone")
{glossary_text}

LINEE GUIDA STILISTICHE:
1.  **Mantieni l'inglese per i termini tecnici**: Se non c'è una traduzione italiana consolidata (es. "RAG", "Inference", "Buffer"), lascia il termine in inglese.
2.  **Evita i calchi**: Non dire "è stato rilasciato da Meta", dì "Meta ha rilasciato".
3.  **Sii giornalistico**: Usa un linguaggio tecnico ma accessibile agli addetti ai lavori.
4.  **No traduzioni ridicole**: Se una frase suona stupida in italiano ("ossa di frutto di mare"), è sbagliata. Riscrivila o omettila se non sei sicuro del senso.
5.  **RISPETTA IL GLOSSARIO SYSTEM**: Usa i termini tecnici inglesi (LLM, Framework, Pipeline, ecc.) dove appropriato. NON tradurli mai in modo letterale.

OUTPUT FORMAT:
Rispondi ESCLUSIVAMENTE con un JSON valido come richiesto.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.3,
        },
        "stream": False,
    }

    try:
        logger.info(f"Chiamata a Ollama (model={MODEL_NAME}) su {url}...")
        
        # TIMEOUT ESPLICITO: 120 secondi
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            response_data = resp.json()
            
        logger.info("Risposta ricevuta da Ollama.")
    except Exception as e:
        logger.error(f"Errore nella chiamata a Ollama (HTTPX): {e}")
        raise LLMError(f"Errore nella chiamata a Ollama: {e}")

    try:
        content = response_data["message"]["content"]
    except Exception:
        logger.error(f"Risposta inattesa: {response_data}")
        raise LLMError(f"Risposta inattesa da Ollama: {response_data}")

    return content



def build_news_prompt(raw_title: str, raw_text: str) -> str:
    """
    Costruisce un prompt per trasformare una news grezza in:
    """
    return f"""
Sei un Redattore Capo di una testata tech italiana di alto livello.
Hai ricevuto il seguente lancio di agenzia (spesso in inglese) e devi trasformarlo in un articolo premium per i tuoi lettori italiani.

FONTE GREZZA:
[TITOLO]: {raw_title}
[TESTO]: {raw_text}

ISTRUZIONI OPERATIVE:
1. Analizza il contenuto e identifica i punti chiave della notizia
2. RISCRIVI in ITALIANO CORRETTO E FLUENTE - NON tradurre letteralmente
3. Se il testo originale è breve, espandi con contesto tecnico rilevante (senza inventare fatti)
4. Usa terminologia italiana naturale.
5. **RISPETTA IL GLOSSARIO SYSTEM**: Usa i termini tecnici inglesi (LLM, Framework, Pipeline, ecc.) dove appropriato. NON tradurli mai in modo letterale.

IMPORTANTE - CONTROLLO QUALITÀ:
- Verifica attentamente TUTTE le concordanze grammaticali (genere, numero, tempo verbale)
- Controlla che gli articoli siano corretti (il/lo/la, i/gli/le)
- Rileggi per eliminare errori di ortografia o sintassi
- Assicurati che le frasi siano ben costruite e scorrevoli

OUTPUT RICHIESTO (JSON):
Devi produrre un JSON valido con questi campi:
- "title": Titolo accattivante in Italiano (max 90 char).
- "title_en": Titolo in Inglese.
- "summary": Sommario giornalistico in Italiano (max 80 parole).
- "summary_en": Summary in English.
- "content": L'articolo completo in ITALIANO (Markdown). Deve essere ricco, diviso in paragrafi con titoli (##).
- "content_en": The complete article in ENGLISH (Markdown).
- "category": Scegli UNA tra [LLM, Frameworks, Hardware, Market, Other].

Esempio JSON:
{{
  "title": "Nuova svolta per i modelli Llama...",
  "content": "## Introduzione\\n\\nMeta ha annunciato oggi...",
  ...
}}

IMPORTANTE:
- Restituisci SOLO il JSON.
- Assicurati che il JSON sia sintatticamente perfetto.
"""


def _extract_json_block(text: str) -> str:
    """
    Extracts JSON block by finding the outer-most matching braces,
    ignoring braces inside strings.
    """
    # 1. Try to find content within ```json code fence (safest if model complies)
    import re
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        # Check if the regex match is actually valid JSON (it might have stopped early on nested braces if regex is weak)
        # But if we assume the model closes the code block correctly, we can trust the content inside the block.
        # Actually better to rely on the sophisticated parser for the content inside, 
        # or just take the block if it looks complete.
        # Let's trust the parser below more, but use the code block start as a hint.
        block_content = match.group(1)
        # Verify if balanced? No, let's just fall through to the robust parser
        # starting from the first { found in the text.
        pass

    # Find the first '{'
    start_index = text.find('{')
    if start_index == -1:
        raise LLMError("No JSON object found (missing '{')")

    # Parsing state
    balance = 0
    in_string = False
    escape = False
    
    end_index = -1
    
    for i, char in enumerate(text[start_index:], start=start_index):
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == '{':
                balance += 1
            elif char == '}':
                balance -= 1
                if balance == 0:
                    end_index = i
                    break
    
    if end_index != -1:
        json_candidate = text[start_index : end_index + 1]
        
        # Cleanup potential backticks inside keys/values if the model hallucinated them
        # E.g. "key": `value` -> "key": "value"
        # Be careful not to break valid json
        candidate_clean = re.sub(r':\s*`([^`]*)`', r': "\1"', json_candidate)
        
        # Remove trailing commas before closing braces/brackets
        candidate_clean = re.sub(r',\s*([}\]])', r'\1', candidate_clean, flags=re.DOTALL)
        
        return candidate_clean

    raise LLMError("Could not find matching closing '}' for JSON block")



def generate_article_from_news(raw_title: str, raw_text: str, glossary: Dict[str, str] = None) -> Dict[str, str]:
    """
    Dato un titolo + testo grezzo, interroga il LLM e ritorna
    un dict pronto per creare un Article.
    """
    prompt = build_news_prompt(raw_title, raw_text)
    raw_response = _call_llm(prompt, glossary=glossary)

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
    
    # Same handling for English content
    content_en = data.get("content_en", "")
    if isinstance(content_en, dict):
        parts = []
        for key, value in content_en.items():
            if isinstance(value, dict):
                parts.append(f"## {key.replace('_', ' ').title()}")
                for subkey, subvalue in value.items():
                    parts.append(f"### {subkey.replace('_', ' ').title()}")
                    parts.append(str(subvalue).strip().strip('"""').strip())
            else:
                parts.append(f"## {key.replace('_', ' ').title()}")
                parts.append(str(value).strip().strip('"""').strip())
        content_en = "\n\n".join(parts)
    elif not isinstance(content_en, str):
        content_en = str(content_en)

    return {
        "title": data.get("title", "").strip(),
        "summary": data.get("summary", "").strip(),
        "content": content.strip(),
        "title_en": data.get("title_en", "").strip(),
        "summary_en": data.get("summary_en", "").strip(),
        "content_en": content_en.strip(),
        "category": category,
    }