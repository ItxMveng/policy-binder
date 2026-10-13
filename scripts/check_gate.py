"""Échoue (code 1) si les résultats d'une évaluation passent sous les seuils de eval/ci_gate.json.

Usage : uv run python scripts/check_gate.py eval/results/<nom>.json
"""

import json
import sys
from pathlib import Path

from policy_binder.evaluation import Gate, Summary, check_gate


def main() -> int:
    results = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    summary = Summary.model_validate(results["resultats"])
    root = Path(__file__).resolve().parents[1]
    gate = Gate.model_validate(json.loads((root / "eval" / "ci_gate.json").read_text("utf-8")))
    failures = check_gate(summary, gate)
    print(
        f"correct ou partiel {summary.exactitude_correct_ou_partiel.count}"
        f"/{summary.exactitude_correct_ou_partiel.total}, "
        f"abstention correcte {summary.abstention_correcte.count}"
        f"/{summary.abstention_correcte.total}, "
        f"incorrectes {summary.reponses_incorrectes}, "
        f"refus injustifiés {summary.refus_injustifies.count}"
    )
    for failure in failures:
        print(f"::error::Seuil d'évaluation non atteint : {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
