# CLAUDE.md — règles du dépôt (campagne Stage 2027)

## Contexte
Projet de portfolio de Francis Itoua, construit pour décrocher un stage Ingénieur IA appliquée & MLOps. Francis doit pouvoir expliquer chaque ligne en entretien : la clarté prime sur l'astuce.
Spécification : SPEC.md · Plan : ROADMAP.md · Journal : JOURNAL.md

### Contexte propre au projet (P1 — Guichet des règlements)
- Problème : les collaborateurs perdent du temps à chercher dans les règlements, procédures et politiques internes ; un assistant qui invente des réponses est inutilisable en interne.
- Données : documents institutionnels PUBLICS de l'ENIB (Bretagne INP), de l'Université de Brest (UBO) et d'IMT Atlantique — règlements intérieurs, règles de scolarité et d'examens, chartes — traités comme des « politiques internes ». Les URL officielles et la date de consultation sont dans `data/sources.yaml` ; `scripts/download_sources.py` télécharge les PDF dans `data/raw/` (jamais versionné) ; le pipeline d'ingestion les convertit.
- Évaluation : 60 questions (40 avec réponse dans le corpus, 20 hors corpus) dans `eval/questions.jsonl`, validées par Francis. Métriques : exactitude (juge LLM + vérification des citations), précision du contexte récupéré, abstention correcte, refus injustifiés sur les questions qui ont une réponse, latence p50/p95, coût pour 1 000 questions ; base naïve (dense seul) vs version finale. Les résultats sont présentés comme exploratoires (petit jeu de test). CI : 20 questions.
- Hors périmètre : Kubernetes, ArgoCD, multi-tenant, authentification.
- Definition of Done : celle de 06_PROJETS.md (README étude de cas, tests et CI verts avec évaluation en CI, API Cloud Run via Terraform + front Vercel, docs/evaluation.md, une fiche par ticket, entrée « LIVRÉ » avec 3 chiffres et l'URL de démo).

## Stack imposée
Python 3.12, uv, FastAPI, Pydantic v2, pytest, ruff, mypy · React + Vite + TypeScript (Vercel) · Docker · GitHub Actions · Terraform → Cloud Run europe-west9 · API Mistral derrière l'interface LLMProvider · Langfuse · secrets dans GitHub Secrets / Secret Manager / .env non versionné.

## Workflow de chaque session
1. Lis SPEC.md, ROADMAP.md et les 3 dernières entrées de JOURNAL.md.
2. Prends le premier ticket « [ ] » de ROADMAP.md. Un ticket par session ; deux si le premier a pris moins de 30 minutes.
3. Implémente avec ses tests. Lance pytest, ruff et mypy --strict sur src/ jusqu'au vert.
4. Coche le ticket « [x] » avec la date.
5. Écris docs/explications/<ticket>.md : ce qui a été fait, pourquoi ce choix plutôt que l'alternative la plus courante, schéma si utile, 5 questions d'entretien avec leurs réponses.
6. Ajoute une entrée en haut de JOURNAL.md (format ci-dessous).
7. Commit au format Conventional Commits, push sur main, vérifie que la CI passe.
8. Termine par : résumé en 5 lignes, « Prochaine session : <ticket suivant> », et les 2 questions de la fiche que Francis doit savoir répondre à voix haute.

## Format JOURNAL.md — lu automatiquement par l'agent LinkedIn : n'invente jamais rien
## AAAA-MM-JJ — <ticket>
- Fait : …
- Chiffre mesuré : … (ou « aucun »)
- Décision technique : … (le compromis en une phrase)
- Visuel disponible : <chemin d'une capture ou d'un GIF dans docs/media/> (ou « aucun »)
Jour de livraison : entrée « ## AAAA-MM-JJ — LIVRÉ » avec les 3 chiffres clés et l'URL de démo.

## Interdits
Secret dans le dépôt · chiffre non mesuré dans README ou JOURNAL · dépendance non justifiée · test désactivé pour faire passer la CI.
