"""Recherche lexicale BM25, écrite à la main (une soixantaine de lignes, aucune dépendance).

BM25 retrouve ce que la recherche dense rate : chiffres, sigles et termes exacts
(« 15 minutes », « CVEC », « eduroam »). Le corpus (quelques centaines de passages) tient en RAM.
"""

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

from studeria_assistant.index import ScoredChunk
from studeria_assistant.ingest import Chunk

# Mots-outils français fréquents : ils n'aident pas à distinguer les passages.
_STOPWORDS_TEXT = (
    "a au aux avec ce ces cet cette d da dans de des du elle en est et etre il ils je l la le "
    "les leur leurs lui m ma mais me meme mes moi mon n ne nos notre nous on ou par pas pour "
    "qu que qui s sa se ses si son sont sur t ta te tes toi ton tu un une vos votre vous y c "
    "j puis peut faut quel quelle quels quelles comment combien quand ai as avons avez ont "
    "sera "
)
STOPWORDS = frozenset(_STOPWORDS_TEXT.split())
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Minuscules, accents retirés (« délai » = « delai »), mots-outils retirés, chiffres gardés."""
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return [t for t in _TOKEN.findall(folded) if t not in STOPWORDS]


class BM25Index:
    def __init__(self, chunks: Sequence[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self._docs = [Counter(tokenize(chunk.text)) for chunk in self.chunks]
        self._lengths = [sum(doc.values()) for doc in self._docs]
        self._avg_length = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        document_frequency: Counter[str] = Counter()
        for doc in self._docs:
            document_frequency.update(doc.keys())
        n = len(self._docs)
        # IDF de BM25 (variante toujours positive) : un terme rare pèse plus qu'un terme courant.
        self._idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def score(self, query_terms: list[str], position: int) -> float:
        doc = self._docs[position]
        norm = self.k1 * (1 - self.b + self.b * self._lengths[position] / self._avg_length)
        total = 0.0
        for term in query_terms:
            frequency = doc.get(term, 0)
            if frequency:
                total += self._idf[term] * frequency * (self.k1 + 1) / (frequency + norm)
        return total

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        terms = tokenize(query)
        scores = [(self.score(terms, i), i) for i in range(len(self.chunks))]
        best = sorted((s for s in scores if s[0] > 0), reverse=True)[:k]
        return [ScoredChunk(chunk=self.chunks[i], score=s) for s, i in best]
