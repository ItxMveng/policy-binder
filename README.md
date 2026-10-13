# Le Classeur

**Posez votre question sur le règlement : Le Classeur répond en citant la page, ou dit qu'il ne sait pas.**

Assistant documentaire fiable et évalué : il répond aux questions sur des règlements et chartes en citant les passages utilisés, et dit « je ne sais pas » quand l'information n'est pas dans les documents.

**Statut : en construction (12 → 23 octobre 2026).** Aucun résultat n'est publié avant d'avoir été mesuré. Avancement : [ROADMAP.md](ROADMAP.md) · journal : [JOURNAL.md](JOURNAL.md) · spécification : [SPEC.md](SPEC.md).

Corpus : documents institutionnels publics de l'ENIB (Bretagne INP), de l'Université de Brest et d'IMT Atlantique, téléchargés depuis leurs sites officiels (liste dans `data/sources.yaml`).

## Lancer en local
```bash
uv sync
uv run pytest
uv run uvicorn policy_binder.api:app --reload
```

## Évaluation
Résultats et protocole : [docs/evaluation.md](docs/evaluation.md).
```bash
uv run python scripts/run_eval.py mon-essai --retrieval hybride --rerank --min-score -2.362
```
En CI ([.github/workflows/eval.yml](.github/workflows/eval.yml)), 20 questions sont évaluées à chaque changement du système et bloquent sous les seuils de `eval/ci_gate.json` ; les 60 questions sont évaluées à chaque tag `v*`. Le job a besoin du secret `LLM_API_KEY` (clé Groq), à ajouter avec `gh secret set LLM_API_KEY` ; sans lui, il s'arrête avec un avertissement.
