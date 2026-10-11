# Jeu d'évaluation — à valider par Francis

Statut : **rédigé par Claude Code le 11/10/2026, pas encore validé.** Tant que cette ligne n'est pas remplacée par « validé par Francis le … », les résultats d'évaluation restent provisoires.

## Ce qu'il faut vérifier (environ 45 minutes)
Pour chacune des 40 questions `q01`–`q40` de `questions.jsonl` :
1. Ouvrir le PDF (`data/raw/<source_id>.pdf`, après `uv run python scripts/download_sources.py`) à la page indiquée (`page` = numéro de page du lecteur PDF).
2. Vérifier que `reference_answer` est exacte et complète au regard du texte.
3. Vérifier que la question est formulée comme la poserait un étudiant ou un collaborateur.

Pour chacune des 20 questions `h01`–`h20` : vérifier qu'aucun des 9 documents n'y répond. Une question hors corpus à laquelle un document répond en réalité fausserait le taux d'abstention.

Contrôle automatique déjà fait : `uv run python scripts/check_eval_set.py` confirme que l'extrait `evidence` de chaque question figure sur la page attendue (40/40 le 11/10/2026). Ce contrôle prouve que la source est la bonne, pas que la réponse rédigée est juste : c'est l'objet de la relecture.

## Comment corriger
Modifier directement la ligne dans `questions.jsonl`, relancer `uv run pytest tests/test_evalset.py` et `uv run python scripts/check_eval_set.py`, puis commiter avec le message `test(p1): validation du jeu d'évaluation`.
