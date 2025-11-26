# LLM Observatory – Portale AI-driven (MVP)

## Visione

Portale di informazione, analisi e monitoraggio continuo su:

- LLM (cloud e local)
- Framework & tool (LangChain, Transformers, ChromaDB, ecc.)
- Hardware AI-ready (MiniPC, AI box, GPU)
- Trend e novità del mondo AI

I contenuti vengono:

- **raccolti** da feed RSS (OpenAI, Hugging Face, Google AI, ...)
- **rielaborati** da un modello LLM (per ora Ollama 3B in locale)
- **pubblicati** come articoli con categorie e riassunti
- **integrabili** con commento editoriale di Davide tramite interfaccia admin

---

## Architettura MVP

- Backend: **FastAPI**
- DB: **SQLite** (file `llm_observatory.db` nella root)
- ORM: **SQLAlchemy**
- Template engine: **Jinja2**
- LLM: **Ollama** in locale (default `llama3.2:3b`)
- Raccoglitori news: feed RSS via **feedparser**

Directory principali:

- `app/`
  - `main.py`: entrypoint FastAPI (rotte web)
  - `database.py`: connessione DB / sessioni
  - `models.py`: modelli SQLAlchemy (`Article`, `Category`)
  - `crud.py`: operazioni su articoli e categorie
  - `ai_client.py`: integrazione con Ollama (prompt + parsing JSON)
  - `templates/`: HTML (home, dettaglio, categorie, admin)
  - `static/styles.css`: stile dark, techy, minimal
- `scripts/`
  - `news_sources.py`: feed RSS e parsing
  - `fetch_and_generate.py`: pipeline ingest (feed -> LLM -> DB)
  - `test_ollama_ai_client.py`: test rapido del layer AI
- `requirements.txt`: dipendenze Python

---

## Flusso logico

1. **Ingest automatico** (`scripts/fetch_and_generate.py`)
   - legge i feed RSS
   - estrae titolo + testo grezzo
   - chiama `ai_client.generate_article_from_news()`
   - crea un `Article` nel DB con:
     - `title`
     - `summary`
     - `content`
     - `category` (LLM / Frameworks / Hardware / Market / Altro)
     - `source_url`

2. **Portale web** (`app/main.py`)
   - `GET /` → home con gli ultimi articoli
   - `GET /article/{slug}` → dettaglio articolo
   - `GET /category/{slug}` → vista per categoria
   - `GET /admin/new` + `POST /admin/new` → form semplice per creare articoli (es. editoriali di Davide)

3. **Layer LLM (Ollama)** (`app/ai_client.py`)
   - costruisce un prompt che chiede JSON strutturato
   - chiama `ollama.chat()` sul modello locale
   - estrae il blocco JSON dalla risposta
   - normalizza la categoria

---

## Come usarlo

### 1. Installazione dipendenze

Assicurati di avere Python 3.10+.

```bash
pip install -r requirements.txt
```

Installa e avvia **Ollama** e scarica un modello, ad esempio:

```bash
ollama pull llama3.2:3b
```

Se usi un modello diverso, cambia `MODEL_NAME` in `app/ai_client.py`.

---

### 2. Avvio del portale

Dalla root del progetto (`llm_observatory/`):

```bash
uvicorn app.main:app --reload
```

Poi apri il browser su:

```text
http://127.0.0.1:8000
```

- Home → lista articoli
- `/admin/new` → creare articoli manualmente (es. editoriali, analisi personali)

---

### 3. Popolare il portale con notizie AI reali

Lancia la pipeline di ingest:

```bash
python scripts/fetch_and_generate.py
```

Questo farà:

- leggere i feed RSS
- generare articoli tramite Ollama
- salvarli in SQLite

Ricaricando la home vedrai le nuove card.

---

## Prossimi step possibili

- Aggiungere **ChromaDB** per ricerca semantica su tutti gli articoli (RAG interno).
- Aggiungere pagina `/search` con box di ricerca.
- Introdurre grafici "Radar" per mostrare trend (LLM, hardware, framework).
- Spostare il DB da SQLite a PostgreSQL per produzione.
- Quando arriva il **GMKtec EVO X2 (128 GB RAM)**:
  - usare modelli più grandi in locale
  - aggiungere altri servizi (benchmark, analisi offline, ecc.)

Questo MVP è pensato per essere semplice da espandere: il cervello (LLM) è isolato in `ai_client.py`, il che rende facile passare da un modello all'altro senza cambiare il resto del portale.
