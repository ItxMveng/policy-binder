# JOURNAL

## 2026-10-12 — P1-07 Recherche hybride dense + BM25
- Fait : recherche hybride : BM25 écrit à la main (tokenisation française, environ 1,4 ms par requête) fusionné avec la recherche dense par Reciprocal Rank Fusion ; comparaison de la recherche seule (dense / BM25 / hybride) puis évaluation complète sur les 60 questions validées ; l'API utilise l'hybride par défaut.
- Chiffre mesuré : hybride vs base naïve (eval/results/hybride-rrf.json) : page attendue récupérée 80 % vs 62,5 %, refus injustifiés 22,5 % vs 37,5 %, correct ou partiel 70 % vs 57,5 %, abstention hors corpus 20/20 inchangée, réponses incorrectes 3 vs 2
- Décision technique : fusion par rangs (RRF) sans aucun réglage sur le jeu de test, plutôt qu'une moyenne pondérée de scores à calibrer : on évite de surajuster, au prix de ne pas prendre BM25 seul, aussi bon ici.
- Visuel disponible : aucun

## 2026-10-12 — Validation du jeu d'évaluation
- Fait : les 60 questions du jeu d'évaluation ont été relues par Francis sur les PDF (page de validation locale avec liens vers la bonne page) ; aucune question modifiée.
- Chiffre mesuré : aucun
- Décision technique : garder les questions hors corpus dont la réponse existe ailleurs (CVEC, CROUS…) : c'est précisément le cas où l'assistant doit s'abstenir au lieu de répondre de mémoire.
- Visuel disponible : aucun

## 2026-10-12 — P1-06 Mesure des erreurs de la base naïve
- Fait : premier appel réel au modèle (Groq, offre gratuite, gpt-oss-120b : l'offre gratuite de Mistral n'ouvre plus l'API) et évaluation de la base naïve sur les 60 questions avec juge LLM d'une autre famille (Qwen), intervalles de Wilson et analyse des erreurs dans docs/evaluation.md. Résultats exploratoires, jeu pas encore validé par Francis.
- Chiffre mesuré : base naïve (eval/results/baseline-dense.json) : exactitude 42,5 % (17/40, IC 95 % 29–58 %), refus injustifiés 37,5 % (15/40), abstention correcte 20/20 sur les questions hors corpus, latence p50 1,0 s / p95 2,0 s, 0,31 $ pour 1 000 questions au tarif public
- Décision technique : mesurer le contexte au niveau document et page : le bon document est trouvé dans 97,5 % des cas mais la bonne page dans 62,5 %, donc l'effort va sur la recherche (hybride + reranking) plutôt que sur le prompt.
- Visuel disponible : aucun

## 2026-10-11 — P1-05 Jeu d'évaluation versionné
- Fait : jeu d'évaluation versionné de 60 questions (40 avec réponse de référence, page attendue et extrait vérifiable ; 20 hors corpus) dans eval/questions.jsonl, avec schéma, test de cohérence en CI et script de vérification sur les PDF. À valider par Francis (procédure dans eval/A-VALIDER.md).
- Chiffre mesuré : 40 extraits de référence sur 40 retrouvés sur la page attendue (scripts/check_eval_set.py, 2026-10-11)
- Décision technique : questions écrites comme un utilisateur et vérifiées mécaniquement, plutôt que générées par un LLM : mesure plus honnête, au prix d'un petit jeu dont les résultats resteront exploratoires.
- Visuel disponible : aucun

## 2026-10-11 — P1-04 Réponse avec citations
- Fait : réponse avec citations : interface LLMProvider et implémentation Mistral, prompt à passages numérotés (titre + page), abstention par phrase imposée, API POST /ask ; testé avec un fournisseur factice, pas encore avec le vrai modèle (clé Mistral non configurée).
- Chiffre mesuré : aucun
- Décision technique : logique RAG écrite à la main (environ 100 lignes) plutôt qu'une chaîne de framework : prompt, citations et abstention restent visibles, testables et évaluables.
- Visuel disponible : aucun

## 2026-10-11 — P1-03 Index dense et recherche (base naïve)
- Fait : index dense de la base naïve : embeddings multilingues locaux (MiniLM, sans clé ni coût par appel) dans Qdrant en mode embarqué, scripts de construction et de recherche avec document et page.
- Chiffre mesuré : aucun
- Décision technique : embeddings locaux derrière une interface Embedder : reproductible et gratuit, et remplaçable par mistral-embed si l'évaluation le justifie.
- Visuel disponible : aucun

## 2026-10-11 — P1-02 Ingestion PDF en passages
- Fait : pipeline d'ingestion : texte extrait page par page, nettoyé (césures, sommaires), découpé en passages de 1 000 caractères au plus avec chevauchement et métadonnées document + page.
- Chiffre mesuré : 546 passages pour 9 documents (sortie de scripts/ingest.py)
- Décision technique : un passage ne traverse jamais une page : citations exactes, au prix d'articles parfois répartis sur deux passages.
- Visuel disponible : aucun

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
