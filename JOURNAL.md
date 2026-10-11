# JOURNAL

## 2026-10-11 — P1-01 Sources officielles et téléchargement
- Fait : corpus de 9 documents publics (ENIB / Bretagne INP, Université de Brest, IMT Atlantique) référencés dans data/sources.yaml avec URL officielle et date de consultation ; script de téléchargement avec contrôle du format PDF et empreinte SHA-256.
- Chiffre mesuré : 9 URL officielles sur 9 répondent avec un PDF (vérification du 2026-10-11 par scripts/download_sources.py)
- Décision technique : versionner les URL et le script plutôt que les PDF : corpus reproductible, sans redistribuer les documents des établissements.
- Visuel disponible : aucun

## 2026-10-11 — P1-00 Démarrage
- Fait : kickoff de Studeria Assistant — SPEC.md, ROADMAP.md de 14 tickets, squelette Python 3.12 (uv, FastAPI, ruff, mypy strict, pytest), Dockerfile et CI GitHub Actions.
- Chiffre mesuré : aucun
- Décision technique : corpus de documents institutionnels publics (ENIB, Université de Brest, IMT Atlantique) référencés par URL et téléchargés par script, plutôt que des PDF versionnés dans le dépôt.
- Visuel disponible : aucun
