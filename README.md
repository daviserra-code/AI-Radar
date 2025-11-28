# AI-Radar – Portale AI News Bilingue con RAG

## Visione

Portale automatizzato di informazione, analisi e monitoraggio continuo su:

- **LLM** (cloud e on-premise)
- **Framework & tool** (LangChain, Transformers, ChromaDB, ecc.)
- **Hardware AI-ready** (MiniPC, AI box, GPU)
- **Trend e novità** del mondo AI

I contenuti vengono:

- **Raccolti** automaticamente da 14 feed RSS (OpenAI, HuggingFace, Google AI, Anthropic, AlphaSignal.ai, TechCrunch, The Verge, Ars Technica, ecc.)
- **Rielaborati** da un modello LLM locale (Ollama) in **italiano e inglese**
- **Pubblicati** come articoli con categorie, immagini e link alle fonti
- **Integrati** con sistema di autenticazione, commenti e ricerca semantica RAG

---

## Architettura Attuale

### Stack Tecnologico

- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 16 (produzione)
- **ORM**: SQLAlchemy
- **Template engine**: Jinja2
- **LLM**: Ollama locale (attualmente llama3.2:latest, presto 70B)
- **Vector Store**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
- **Scheduler**: APScheduler (ingest automatico ogni 5 minuti)
- **Autenticazione**: JWT tokens + bcrypt password hashing
- **Deployment**: Docker Compose (3 container: app, db, ollama)

### Directory Structure

- `app/`
  - `main.py`: FastAPI routes (web, API, auth)
  - `database.py`: PostgreSQL connection
  - `models.py`: SQLAlchemy models (Article, Category, User, Comment)
  - `crud.py`: Database operations
  - `ai_client.py`: Ollama integration (bilingual generation)
  - `auth.py`: JWT authentication & user management
  - `rag.py`: ChromaDB semantic search implementation
  - `templates/`: HTML templates (Jinja2)
  - `static/styles.css`: Dark neon-themed UI
- `scripts/`
  - `news_sources.py`: 14 RSS feeds management + image extraction
  - `fetch_and_generate.py`: Automated ingest pipeline
- `docker-compose.yml`: Container orchestration
- `Dockerfile`: Application container build
- `requirements.txt`: Python dependencies

---

## Come Funzionano RAG, ChromaDB e PostgreSQL

### PostgreSQL - Database Relazionale
**Ruolo**: Archiviazione strutturata e permanente di tutti i dati.

**Cosa memorizza**:
- **Articoli completi**: titolo, contenuto, riassunto (italiano + inglese), metadata
- **Categorie**: LLM, Frameworks, Hardware, Market, Altro
- **Utenti**: credenziali, stato abbonamento, profili
- **Commenti**: discussioni sugli articoli con relazioni user-article
- **Immagini e link**: URL immagini estratte da RSS, link alle fonti originali

**Perché PostgreSQL**: 
- Gestione robusta delle relazioni (foreign keys)
- Transazioni ACID per integrità dei dati
- Supporto per query complesse e aggregazioni
- Scalabilità per produzione

### ChromaDB - Vector Database
**Ruolo**: Ricerca semantica intelligente sugli articoli.

**Come funziona**:
1. **Indicizzazione** (all'avvio e quando arrivano nuovi articoli):
   - Ogni articolo viene convertito in **embedding vettoriale** usando sentence-transformers
   - Gli embeddings catturano il significato semantico del contenuto
   - Vengono memorizzati in ChromaDB con metadata (ID, titolo, slug)

2. **Ricerca semantica** (quando un utente cerca):
   - Query dell'utente → embedding vettoriale
   - ChromaDB trova gli articoli più simili per **similarità coseno**
   - Restituisce i risultati ranked per rilevanza semantica
   - Non serve match esatto delle parole: capisce sinonimi e concetti

**Esempio**: 
- Query: "modelli linguistici locali"
- Trova articoli su: "Ollama", "LLaMA on-premise", "Self-hosted LLMs"
- Anche se non contengono le parole esatte della query

### RAG (Retrieval-Augmented Generation)
**Ruolo**: Ricerca semantica per scoprire contenuti rilevanti.

**Implementazione attuale**:
- `rag.py` gestisce l'indicizzazione e la ricerca
- Usa ChromaDB come vector store
- All'avvio, indicizza tutti gli articoli esistenti (~27 articoli attuali)
- Quando arrivano nuovi articoli, vengono automaticamente aggiunti all'indice

**Flusso**:
```
User Query → Embedding → ChromaDB Search → Top-K Results → Display
```

**Nota**: Il RAG non è ancora usato per la generazione degli articoli (LLM genera solo da RSS), ma è pronto per features future come:
- Suggerimenti articoli correlati
- Ricerca avanzata nel portale
- Context injection per risposte AI personalizzate

---

## Flusso Logico Completo

### 1. Ingest Automatico (Scheduler)
**Ogni 5 minuti**, APScheduler esegue `fetch_and_generate.py`:

1. **Fetch RSS**: Scarica ultimi articoli da 14 feed RSS
2. **Image Extraction**: Estrae immagini da media_content, thumbnails, enclosures
3. **Check Duplicati**: Verifica se l'URL è già nel database
4. **LLM Generation**: 
   - Passa titolo + testo grezzo a Ollama
   - Richiede output in **italiano E inglese** (bilingual)
   - Genera articolo dettagliato (800-1500 parole) con sezioni markdown
   - Estrae categoria (LLM/Frameworks/Hardware/Market/Altro)
5. **Database Save**: Salva in PostgreSQL con tutti i campi (IT + EN + immagine)
6. **RAG Indexing**: Aggiunge l'embedding vettoriale a ChromaDB

### 2. Portale Web
- `GET /` → Homepage con grid di articoli (immagini, titoli, categorie)
- `GET /article/{slug}` → Dettaglio articolo con:
  - Toggle lingua (IT ↔ EN) via JavaScript
  - Immagine in evidenza
  - Pulsante "VAI ALLA FONTE ORIGINALE"
  - Sistema commenti per utenti registrati
- `GET /category/{slug}` → Filtra per categoria
- `GET /search?q=...` → Ricerca semantica via ChromaDB (RAG)
- `GET /register`, `GET /login` → Autenticazione JWT
- `POST /article/{slug}/comment` → Aggiungi commento (solo utenti abbonati)

### 3. Layer LLM (Ollama)
**Attualmente**: llama3.2:latest (~3B parametri)
**Prossimamente**: 70B model su GMKtec EVO X2 (128GB RAM)

**Prompt bilingual**:
- Sistema: "Sei un giornalista tecnologico professionista..."
- User: Richiede generazione **simultanea** in italiano e inglese
- Output: JSON con `title`, `title_en`, `summary`, `summary_en`, `content`, `content_en`, `category`
- Handling robusto: gestisce backticks, nested objects, escape characters

---

## Deployment (Docker)

### Setup attuale:

```bash
docker-compose up -d
```

**Containers**:
1. `llmobs_app` (porta 8000): FastAPI application
2. `llmobs_db` (porta 5433→5432): PostgreSQL 16
3. `ollama` (porta 11434): Ollama LLM server (collegato via ainetwork)

**Network**: Tutti i container comunicano su `ainetwork` (bridge network custom)

**Environment Variables**:
```env
DATABASE_URL=postgresql+psycopg2://llmobs_user:llmobs_pass@db:5432/llmobs_db
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:latest
INGEST_INTERVAL_MINUTES=5
```

---

## Features Implementate

### ✅ Generazione Bilingual
- Articoli in **italiano** (default) con toggle per **inglese**
- LLM genera entrambe le versioni simultaneamente
- Ottimizzato per modello 70B (prompt migliorato per italiano naturale)

### ✅ Sistema di Autenticazione
- Registrazione utenti con bcrypt password hashing
- Login con JWT tokens (HTTP-only cookies)
- Gestione stato abbonamento
- Solo utenti abbonati possono commentare

### ✅ Commenti e Community
- Sistema commenti per articoli
- Badge "Subscriber" per utenti abbonati
- Delete per i propri commenti
- Display cronologico con username e timestamp

### ✅ Ricerca Semantica (RAG)
- ChromaDB vector store con ~27 articoli indicizzati
- Embeddings con sentence-transformers (all-MiniLM-L6-v2)
- Ricerca per similarità coseno
- Aggiornamento automatico dell'indice per nuovi articoli

### ✅ Immagini e Media
- Estrazione automatica da RSS feeds
- Display su homepage (thumbnail 180px) e dettaglio (full width)
- Fallback graceful se immagine non disponibile

### ✅ Link alle Fonti
- Pulsante prominente "VAI ALLA FONTE ORIGINALE"
- Link diretti in tutte le card e dettagli articolo
- Attributo `target="_blank"` per apertura in nuova tab

---

## Come Usarlo

### 1. Prerequisiti

- Docker & Docker Compose
- Ollama installato e modello scaricato:
  ```bash
  ollama pull llama3.2:latest
  ```

### 2. Avvio

```bash
# Build e start containers
docker-compose up -d --build

# Connect Ollama to ainetwork (if not connected)
docker network connect ainetwork ollama

# Verifica containers
docker ps
```

### 3. Accesso

- **Web App**: http://localhost:8000
- **Database**: localhost:5433 (user: llmobs_user, pass: llmobs_pass, db: llmobs_db)
- **Ollama API**: http://localhost:11434

### 4. Popolamento Automatico

Lo scheduler APScheduler popola automaticamente ogni 5 minuti.

**Ingest manuale**:
```bash
docker exec llmobs_app python scripts/fetch_and_generate.py
```

### 5. Database Management

**Migrations**:
```bash
# Add columns
docker exec llmobs_db psql -U llmobs_user -d llmobs_db -c "ALTER TABLE articles ADD COLUMN ..."

# Check data
docker exec llmobs_db psql -U llmobs_user -d llmobs_db -c "SELECT title, created_at FROM articles ORDER BY created_at DESC LIMIT 5;"
```

---

## RSS Feeds (14 sources)

### Major AI Labs
- OpenAI Blog
- HuggingFace Blog
- Google AI Blog
- Anthropic News

### LLM & ML News
- LangChain Blog
- Ollama Blog
- **AlphaSignal.ai** (nuovo!)

### Tech News (AI focused)
- TechCrunch AI
- The Verge AI
- Ars Technica AI

### Developer/Framework News
- PyTorch Blog
- TensorFlow Blog

### Hardware & Local AI
- Tom's Hardware
- AnandTech

---

## Roadmap

### Dicembre 2025 (GMKtec EVO X2 Arrival)
- ✅ Upgrade a modello LLM 70B locale
- 🔄 Migliore qualità italiano (il 70B è molto più fluente)
- 🔄 Generazione più veloce con 128GB RAM

### Q1 2026
- Dashboard "Radar" con grafici trend (LLM, hardware, framework)
- Suggerimenti articoli correlati (powered by RAG)
- Newsletter automatica (digest settimanale)
- Admin panel completo per gestione contenuti

### Future
- Multi-tenancy per più portali AI
- API pubblica per developers
- Plugin system per nuovi feed/sources
- Benchmark automatici hardware AI

---

## Tech Notes

### Perché questo stack?

- **FastAPI**: Veloce, async, ottima DX con type hints
- **PostgreSQL**: Robusto, scalabile, supporto JSON
- **ChromaDB**: Semplice da usare, embedding nativi, perfetto per RAG
- **Ollama**: Privacy-first, modelli local, no API costs
- **Docker**: Reproducible, facile deploy, isolamento

### Performance

- Ingest: ~2-3 minuti per ciclo (21 news x 14 feeds)
- LLM generation: ~30-60s per articolo (attuale 3B model)
- RAG search: <100ms per query
- DB queries: <10ms (indexed)

### Security

- JWT tokens con expiration
- Bcrypt password hashing (cost factor 12)
- HTTP-only cookies (XSS protection)
- SQL injection protection via SQLAlchemy ORM
- CORS configurato per localhost

---

## Contributi

Repository: https://github.com/daviserra-code/AI-Radar

Issues e PR sono benvenute!

---

## License

MIT License - vedi LICENSE file per dettagli.
