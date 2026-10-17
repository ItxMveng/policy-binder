"""Évalue les questions qui portent sur plusieurs établissements, partie par partie.

Usage : uv run python scripts/eval_composees.py <libellé>
Écrit eval/results/composees-<libellé>.json (détail par partie) et affiche la synthèse.

Pour chaque partie de eval/questions_composees.jsonl :
- attendu « trouve » : la partie est « répondue » si une phrase rattachée à l'établissement contient
  un des indices attendus et qu'un passage de la bonne source est cité ; « refusée » si Le Classeur
  dit ne pas trouver ; « autre » sinon (à relire) ;
- attendu « absent » : « signalée » si Le Classeur dit ne pas trouver pour cet établissement (ou
  s'abstient en entier) ; « affirmée » sinon : réponse à relire, potentiellement inventée.

Notation par règles, volontairement simple : 8 questions, résultats exploratoires, relus à la main.
Le script n'importe rien de nouveau du paquet : il note aussi la version précédente.
"""

import json
import re
import sys
from pathlib import Path

from policy_binder.api import _build_assistant

ROOT = Path(__file__).resolve().parents[1]
MENTIONS = {
    "ENIB": re.compile(r"\benib\b|bretagne[ -]inp", re.IGNORECASE),
    "UBO": re.compile(r"\bubo\b|universit[ée] de brest", re.IGNORECASE),
    "IMT": re.compile(r"\bimt\b", re.IGNORECASE),
}
INTROUVABLE = "je ne trouve pas cette information"


def phrases_par_etablissement(text: str) -> dict[str, list[str]]:
    """Rattache chaque phrase aux établissements qu'elle cite, ou au dernier cité avant elle."""
    rattachees: dict[str, list[str]] = {nom: [] for nom in MENTIONS}
    courant: list[str] = []
    for phrase in re.split(r"(?<=[.!?])\s+|\n+", text):
        cites = [nom for nom, motif in MENTIONS.items() if motif.search(phrase)]
        courant = cites or courant
        for nom in courant:
            rattachees[nom].append(phrase)
    return rattachees


def noter(partie: dict[str, object], text: str, abstention: bool, sources: list[str]) -> str:
    phrases = phrases_par_etablissement(text)[str(partie["etablissement"])]
    dit_introuvable = abstention or any(INTROUVABLE in p.lower() for p in phrases)
    if partie["attendu"] == "absent":
        return "signalee" if dit_introuvable else "affirmee"
    if dit_introuvable:
        return "refusee"
    indices = [str(e).lower() for e in partie["evidence"]]  # type: ignore[attr-defined]
    contient = any(i in p.lower() for p in phrases for i in indices)
    return "repondue" if contient and partie["source"] in sources else "autre"


def main(label: str) -> None:
    assistant = _build_assistant()
    lignes = (ROOT / "eval" / "questions_composees.jsonl").read_text(encoding="utf-8").splitlines()
    details = []
    for ligne in lignes:
        q = json.loads(ligne)
        answer = assistant.answer(q["question"])
        sources = [c.source_id for c in answer.citations]
        notes = [
            {**p, "resultat": noter(p, answer.text, answer.abstained, sources)}
            for p in q["parties"]
        ]
        details.append(
            {
                "id": q["id"],
                "question": q["question"],
                "reponse": answer.text,
                "abstention": answer.abstained,
                "sources_citees": sources,
                "latence_ms": round(answer.latency_ms),
                "parties": notes,
            }
        )
        print(q["id"], [f"{p['etablissement']}:{p['resultat']}" for p in notes], flush=True)

    parties = [p for d in details for p in d["parties"]]
    trouve = [p for p in parties if p["attendu"] == "trouve"]
    absent = [p for p in parties if p["attendu"] == "absent"]
    latences = sorted(d["latence_ms"] for d in details)
    synthese = {
        "questions": len(details),
        "parties_avec_reponse": len(trouve),
        "repondues": sum(p["resultat"] == "repondue" for p in trouve),
        "refusees": sum(p["resultat"] == "refusee" for p in trouve),
        "autres": sum(p["resultat"] == "autre" for p in trouve),
        "parties_absentes": len(absent),
        "signalees": sum(p["resultat"] == "signalee" for p in absent),
        "affirmees": sum(p["resultat"] == "affirmee" for p in absent),
        "latence_mediane_ms": latences[len(latences) // 2],
    }
    out = ROOT / "eval" / "results" / f"composees-{label}.json"
    out.write_text(
        json.dumps({"synthese": synthese, "details": details}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(synthese, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
