# Studeria Assistant

Assistant documentaire fiable et évalué : il répond aux questions sur des règlements et chartes en citant les passages utilisés, et dit « je ne sais pas » quand l'information n'est pas dans les documents.

**Statut : en construction (12 → 23 octobre 2026).** Aucun résultat n'est publié avant d'avoir été mesuré. Avancement : [ROADMAP.md](ROADMAP.md) · journal : [JOURNAL.md](JOURNAL.md) · spécification : [SPEC.md](SPEC.md).

Corpus : documents institutionnels publics de l'ENIB (Bretagne INP), de l'Université de Brest et d'IMT Atlantique, téléchargés depuis leurs sites officiels (liste dans `data/sources.yaml`).

## Lancer en local
```bash
uv sync
uv run pytest
uv run uvicorn studeria_assistant.api:app --reload
```
