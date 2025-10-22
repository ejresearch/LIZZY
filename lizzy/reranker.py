"""
Cohere Reranker Integration for LightRAG

Improves RAG quality by reranking retrieved results using Cohere's
reranking model before passing to LLM for synthesis.
"""

import os
from typing import List, Dict
from pathlib import Path
import cohere
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

console = Console()


class CohereReranker:
    """
    Rerank LightRAG results using Cohere's reranking API.

    This improves relevance by reordering retrieved chunks based on
    semantic similarity to the query, beyond simple vector distance.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Cohere reranker.

        Args:
            api_key: Cohere API key (defaults to COHERE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")

        if not self.api_key:
            console.print("[yellow]⚠️  COHERE_API_KEY not set. Reranking disabled.[/yellow]")
            self.client = None
        else:
            self.client = cohere.Client(self.api_key)

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        model: str = "rerank-english-v3.0"
    ) -> List[Dict]:
        """
        Rerank documents using Cohere.

        Args:
            query: The search query
            documents: List of document texts to rerank
            top_n: Number of top results to return
            model: Cohere rerank model to use

        Returns:
            List of reranked results with scores
        """
        if not self.client or not documents:
            # Return original order if reranking unavailable
            return [
                {"index": i, "text": doc, "relevance_score": 1.0}
                for i, doc in enumerate(documents[:top_n])
            ]

        try:
            # Call Cohere rerank API
            results = self.client.rerank(
                model=model,
                query=query,
                documents=documents,
                top_n=min(top_n, len(documents))
            )

            # Format results
            reranked = []
            for result in results.results:
                reranked.append({
                    "index": result.index,
                    "text": documents[result.index],
                    "relevance_score": result.relevance_score
                })

            return reranked

        except Exception as e:
            console.print(f"[yellow]⚠️  Reranking failed: {e}. Using original order.[/yellow]")
            return [
                {"index": i, "text": doc, "relevance_score": 1.0}
                for i, doc in enumerate(documents[:top_n])
            ]

    def is_available(self) -> bool:
        """Check if reranker is available."""
        return self.client is not None


def rerank_lightrag_results(
    query: str,
    chunks: List[str],
    top_n: int = 10
) -> List[str]:
    """
    Convenience function to rerank LightRAG chunks.

    Args:
        query: Original query
        chunks: Text chunks from LightRAG
        top_n: Number of results to return

    Returns:
        Reranked list of text chunks
    """
    reranker = CohereReranker()

    if not reranker.is_available():
        return chunks[:top_n]

    results = reranker.rerank(query, chunks, top_n=top_n)
    return [r["text"] for r in results]


# Example usage
if __name__ == "__main__":
    # Test reranker
    reranker = CohereReranker()

    if reranker.is_available():
        query = "romantic comedy midpoint structure"
        docs = [
            "The midpoint is where the relationship reaches a false high",
            "Act 2 contains the fun and games section",
            "The midpoint often features a major revelation",
            "Character arcs should deepen in Act 2B",
            "The midpoint is page 60 in a 120-page script"
        ]

        results = reranker.rerank(query, docs, top_n=3)

        console.print("\n[bold cyan]Reranking Test:[/bold cyan]")
        console.print(f"Query: {query}\n")

        for i, result in enumerate(results, 1):
            console.print(f"{i}. [green]{result['text']}[/green]")
            console.print(f"   Score: {result['relevance_score']:.3f}\n")
    else:
        console.print("[red]Reranker not available. Set COHERE_API_KEY environment variable.[/red]")
