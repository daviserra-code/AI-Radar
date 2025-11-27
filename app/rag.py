import os
import logging
from typing import List

import chromadb
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from . import models
from .ai_client import _call_llm, LLMError

logger = logging.getLogger("ai_observer.rag")

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_store")
EMBED_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)

# Client ChromaDB (persistente su filesystem)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection("articles")

_embedder: SentenceTransformer | None = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info("Caricamento modello di embedding: %s", EMBED_MODEL_NAME)
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedder


def _embed(texts: List[str]) -> List[List[float]]:
    model = _get_embedder()
    vectors = model.encode(texts, show_progress_bar=False)
    return vectors.tolist()


def rebuild_index(db: Session) -> None:
    """
    Ricostruisce completamente l'indice Chroma a partire dagli articoli in DB.
    Viene chiamato allo startup e dopo ogni ingest di news.
    """
    articles: List[models.Article] = db.query(models.Article).all()

    # Puliamo la collection
    try:
        _collection.delete(where={})
    except Exception:
        # Se è già vuota o altro, non ci interessa troppo
        pass

    if not articles:
        logger.info("Nessun articolo in DB: indice RAG vuoto.")
        return

    ids = [str(a.id) for a in articles]
    documents = [f"{a.title}\n\n{a.content}" for a in articles]
    metadatas = [
        {
            "slug": a.slug,
            "title": a.title,
            "category": a.category.name if a.category else "Generale",
        }
        for a in articles
    ]

    embeddings = _embed(documents)
    _collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    logger.info("Indicizzati %d articoli in ChromaDB.", len(articles))


def get_relevant_articles(
    db: Session, question: str, top_k: int = 5
) -> List[models.Article]:
    """
    Ritorna una lista di articoli dal DB ordinati per rilevanza rispetto alla domanda.
    """
    try:
        count = _collection.count()
    except Exception:
        count = 0

    if count == 0:
        logger.info("Collection Chroma vuota: nessun documento per RAG.")
        return []

    query_emb = _embed([question])[0]
    result = _collection.query(query_embeddings=[query_emb], n_results=top_k)

    id_lists = result.get("ids") or []
    if not id_lists or not id_lists[0]:
        return []

    id_strs = id_lists[0]
    try:
        ids = [int(x) for x in id_strs]
    except ValueError:
        logger.warning("IDs non parsabili in int: %s", id_strs)
        return []

    articles = db.query(models.Article).filter(models.Article.id.in_(ids)).all()
    by_id = {a.id: a for a in articles}
    ordered = [by_id[i] for i in ids if i in by_id]
    return ordered


def build_answer(question: str, articles: List[models.Article]) -> str:
    """
    Costruisce una risposta in linguaggio naturale usando il contesto degli articoli passati.
    Usa il LLM locale via _call_llm.
    """
    if not articles:
        return (
            "Per ora non ho abbastanza articoli in archivio per rispondere in modo serio. "
            "Appena l'Observer avrà un po' più di storico, potrò collegare meglio i puntini."
        )

    context_parts = []
    for idx, art in enumerate(articles, start=1):
        category = art.category.name if art.category else "Generale"
        context_parts.append(
            f"[{idx}] Titolo: {art.title}\n"
            f"Categoria: {category}\n"
            f"Contenuto:\n{art.content}\n"
        )

    context_text = "\n\n".join(context_parts)

    prompt = f"""
Sei un analista tecnico ma ironico specializzato in infrastrutture LLM on-prem,
stack locali, framework e hardware.

Ti fornisco alcuni estratti di articoli del nostro archivio (indicati tra [1], [2], ...).
Usa SOLO queste informazioni come base per la risposta.

CONTESTO:
{context_text}

DOMANDA DELL'UTENTE:
{question}

ISTRUZIONI:
- Rispondi in italiano.
- Tono: tecchy ma leggibile, leggermente ironico, senza diventare una macchietta.
- Se qualcosa non è coperto dal contesto, dillo esplicitamente invece di inventare.
- Alla fine della risposta aggiungi una riga:
  "Fonti interne: [1] Titolo..., [2] Titolo..., ..."
  usando i titoli degli articoli sopra.

Rispondi con testo normale, senza JSON.
"""

    try:
        answer = _call_llm(prompt)
    except LLMError as e:
        logger.error("Errore LLM nella answer RAG: %s", e)
        raise

    return answer.strip()
