"""Établissements du corpus : repérage dans une question et rattachement des passages.

Sert aux questions qui citent plusieurs établissements (« à l'UBO et à l'ENIB ») : le score du
reranker est calculé sur la question entière, et la mention de plusieurs établissements le dilue
au point de faire passer la bonne page sous le seuil d'abstention. On cherche donc le sujet seul,
puis on répartit les passages par établissement.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Etablissement:
    nom: str
    mention: re.Pattern[str]
    prefixes: tuple[str, ...]  # préfixes des identifiants de sources (data/sources.yaml)

    def possede(self, source_id: str) -> bool:
        return source_id.startswith(self.prefixes)


ETABLISSEMENTS = (
    Etablissement(
        "l'ENIB / Bretagne INP",
        re.compile(r"\benib\b|\bbretagne[ -]inp\b", re.IGNORECASE),
        ("enib-", "bretagne-inp-"),
    ),
    Etablissement(
        "l'Université de Brest (UBO)",
        re.compile(r"\bubo\b|\buniversit[ée] de brest\b", re.IGNORECASE),
        ("ubo-",),
    ),
    Etablissement(
        "IMT Atlantique",
        re.compile(r"\bimt(?: atlantique)?\b", re.IGNORECASE),
        ("imt-",),
    ),
)

_ALTERNATIVES = "|".join(e.mention.pattern for e in ETABLISSEMENTS)
# Mention d'un établissement avec ce qui la relie au reste de la phrase :
# « à l'UBO », « et à l'ENIB », « , de l'Université de Brest », « ou IMT Atlantique »…
_MENTION_COMPLETE = re.compile(
    r"\s*(?:,|\bet\b|\bou\b)?\s*(?:\b(?:à|a|de|du|pour|chez|dans|en)\s+|\bd['’]\s*)?"
    rf"(?:l['’]\s*|la\s+|le\s+)?(?:{_ALTERNATIVES})",
    re.IGNORECASE,
)


def etablissements_cites(question: str) -> list[Etablissement]:
    """Établissements mentionnés, dans l'ordre du corpus."""
    return [e for e in ETABLISSEMENTS if e.mention.search(question)]


def sans_etablissements(question: str, garder: Etablissement | None = None) -> str:
    """La question sans les établissements cités, sauf `garder`.

    « … mon année à l'UBO et à l'ENIB ? » → « … mon année ? » (sujet seul)
    ou « … mon année à l'UBO ? » (garder = UBO).
    """

    def retirer(match: re.Match[str]) -> str:
        return match.group(0) if garder and garder.mention.search(match.group(0)) else ""

    sujet = _MENTION_COMPLETE.sub(retirer, question)
    sujet = re.sub(r"\s+([.,])", r"\1", sujet)
    return re.sub(r"\s{2,}", " ", sujet).strip()
