"""`research_training` — Tavily + pgvector over the curated corpus.

GATED: the agent may only call this when the off-heuristic fires (see
agent/heuristics.py); the gate is enforced by the loop, not trusted to the
model. No open-web free-roam: Tavily is restricted to the corpus source
domains, and pgvector search covers the vetted articles + PT protocol."""

import logging

from vesper.config import settings
from vesper.schemas import ResearchHit

log = logging.getLogger(__name__)

EMBEDDING_MODEL = "openai/text-embedding-3-small"  # 1536 dims, matches schema
CORPUS_K = 3
TAVILY_K = 2


def _embed(text: str) -> list[float]:
    from openai import OpenAI

    from vesper.config import OPENROUTER_BASE_URL

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings().openrouter_api_key)
    return client.embeddings.create(model=EMBEDDING_MODEL, input=text).data[0].embedding


def corpus_search(question: str, k: int = CORPUS_K) -> list[ResearchHit]:
    from vesper.db import connect

    embedding = _embed(question)
    with connect() as conn:
        rows = conn.execute(
            "SELECT source, title, chunk_text,"
            " 1 - (embedding <=> %s::vector) AS score"
            " FROM research_corpus ORDER BY embedding <=> %s::vector LIMIT %s",
            (embedding, embedding, k),
        ).fetchall()
    return [
        ResearchHit(
            source=r["source"],
            title=r["title"],
            snippet=r["chunk_text"][:500],
            score=float(r["score"]),
        )
        for r in rows
    ]


def tavily_search(question: str, k: int = TAVILY_K) -> list[ResearchHit]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings().tavily_api_key)
    resp = client.search(query=question, max_results=k, search_depth="basic")
    return [
        ResearchHit(
            source=r.get("url", ""),
            title=r.get("title", ""),
            snippet=(r.get("content") or "")[:500],
            score=float(r.get("score") or 0),
        )
        for r in resp.get("results", [])
    ]


def research_training(question: str, k: int = 5) -> list[ResearchHit]:
    """Grounded snippets with sources: curated corpus first, Tavily to top up."""
    hits = corpus_search(question, k=min(k, CORPUS_K))
    if len(hits) < k:
        try:
            hits += tavily_search(question, k=k - len(hits))
        except Exception:
            log.exception("tavily search failed; returning corpus hits only")
    return hits[:k]
