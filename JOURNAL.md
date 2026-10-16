# JOURNAL

## 2026-10-16 — P1-14 README étude de cas + GIF de démo (fait le 2026-10-16)
- Fait : README réécrit au format étude de cas (problème et coût, approche, architecture, résultats mesurés, démo, lancement local en 3 commandes, limites) et GIF de démo enregistré sur le site public (réponse citée puis abstention) ; scripts/prepare.py pour préparer le corpus et l'index en une commande.
- Chiffre mesuré : aucun nouveau chiffre (le README reprend les mesures publiées dans docs/evaluation.md et la latence en ligne du 16/10)
- Décision technique : un GIF enregistré par script sur le vrai site plutôt qu'une maquette, montrant aussi l'abstention, qui est la proposition de valeur du projet.
- Visuel disponible : docs/media/demo.gif

## 2026-10-16 — P1-12 Déploiement
- Fait : déploiement public : API sur Azure Container Apps (Terraform, connexion GitHub sans mot de passe par OIDC, image publique sur ghcr.io sans texte des règlements), index sur Qdrant Cloud, front sur Vercel (https://policy-binder.vercel.app) ; Terraform Cloud Run conservé et validé en CI.
- Chiffre mesuré : latence de l'API publique : médiane 8,2 s, maximum 8,6 s sur 6 questions (environ 12,5 s pour la première question après mise à zéro) — reranker gardé, sous le seuil de 15 s fixé avant la mesure
- Décision technique : Azure Container Apps au lieu de Cloud Run : Cloud Run exige un compte de facturation et Hugging Face un abonnement payant pour les Spaces Docker ; l'infrastructure reste décrite en Terraform pour les deux clouds.
- Visuel disponible : aucun

## 2026-10-16 — P1-13 Rapport docs/evaluation.md
- Fait : rapport d'évaluation complet dans docs/evaluation.md : synthèse, jeux de questions, protocole, résultats des trois configurations avec intervalles de confiance, analyse des erreurs, évaluation en CI, commandes de reproduction et limites ; répartition des questions par établissement corrigée après recomptage.
- Chiffre mesuré : version finale vs base naïve : exactitude 70 % (IC 55–82 %) vs 42,5 % (IC 29–58 %), refus injustifiés 5 % vs 37,5 %, 0 réponse incorrecte, abstention hors corpus 20/20 ; latence médiane 10,5 s sur CPU
- Décision technique : montrer la démarche et ce qui n'a pas marché plutôt qu'un seul tableau final : les chiffres sont plus crédibles, et les limites sont écrites avant qu'on les demande.
- Visuel disponible : aucun

## 2026-10-13 — P1-11 Traces Langfuse et protection de la démo
- Fait : traces Langfuse de chaque question (recherche, génération, abstention) via une interface Tracer, actives seulement avec les clés ; protection de la démo : 10 questions par IP sur 10 minutes et 300 par jour, réponse 429 au-delà ; trace réelle vérifiée dans Langfuse.
- Chiffre mesuré : première trace réelle : 11,6 s au total, dont 10,5 s de recherche (reranker sur CPU) et 1,2 s de génération (gpt-oss-120b, 1 203 tokens en entrée, 380 en sortie)
- Décision technique : compteurs en mémoire plutôt que Redis pour la démo à une instance : exacts et gratuits, à remplacer par un stockage partagé si l'on passe à plusieurs instances.
- Visuel disponible : aucun

## 2026-10-13 — P1-10 Interface de chat
- Fait : interface de chat React + Vite + TypeScript : renvois [n] cliquables vers le passage utilisé et lien vers le PDF officiel ouvert à la bonne page, abstention présentée à part, thème clair/sombre, mobile ; route /sources et CORS côté API ; tests Vitest et job front en CI.
- Chiffre mesuré : aucun (vérification de bout en bout en local : réponse correcte citant la charte des examens, page 3)
- Décision technique : lier au PDF officiel à la page exacte plutôt qu'héberger les documents : l'utilisateur vérifie chez l'établissement, sans redistribution.
- Visuel disponible : aucun

## 2026-10-13 — Renommage définitif : Le Classeur
- Fait : le projet s'appelle désormais « Le Classeur » (choix de Francis, à la place de « Guichet des règlements ») ; dépôt github.com/ItxMveng/policy-binder (les anciennes adresses redirigent), paquet Python policy_binder.
- Chiffre mesuré : aucun
- Décision technique : un nom simple et concret — le classeur où l'on range les règlements et où l'on vient chercher la bonne page — plutôt qu'un nom de marque.
- Visuel disponible : aucun

## 2026-10-13 — Renommage : Guichet des règlements
- Fait : le projet « Studeria Assistant » s'appelle désormais « Guichet des règlements » ; dépôt renommé en github.com/ItxMveng/policy-help-desk (les anciennes adresses redirigent), paquet Python policy_help_desk.
- Chiffre mesuré : aucun
- Décision technique : un nom qui dit ce que fait le produit (on vient poser sa question au guichet, la réponse cite le texte) plutôt qu'un nom de marque.
- Visuel disponible : aucun

## 2026-10-13 — P1-09 Évaluation en CI
- Fait : évaluation en CI : 20 questions (une sur trois, règle fixe) à chaque changement du système, bloquantes sous des seuils fixés avant la première exécution ; évaluation complète des 60 questions à chaque tag v*, résultats publiés en artefact ; job désactivé proprement sans le secret LLM_API_KEY.
- Chiffre mesuré : essai local du sous-ensemble CI (eval/results/ci-local.json) : correct ou partiel 12/14, abstention correcte 6/6, 1 réponse incorrecte, 1 refus injustifié — seuils respectés
- Décision technique : seuils en nombre de questions avec une marge mesurée (11/14 pour un score actuel de 12–13/14), sauf l'abstention hors corpus exigée à 6/6 : la CI tolère le bruit du LLM mais pas une réponse inventée.
- Visuel disponible : aucun

## 2026-10-13 — P1-08 Reranking et seuil d'abstention
- Fait : reranker cross-encoder local (bge-reranker-v2-m3) sur 20 candidats de la recherche hybride, et seuil d'abstention qui évite d'appeler le LLM quand aucun passage n'est pertinent ; seuil et réglage calibrés sur 24 questions distinctes du jeu de test ; configuration par défaut de l'API.
- Chiffre mesuré : hybride + reranker + seuil (eval/results/hybride-rerank-complet.json) : exactitude 70 % (IC 55–82 %) contre 42,5 % pour la base naïve, refus injustifiés 5 % contre 37,5 %, 0 réponse incorrecte, abstention hors corpus 20/20 dont 15 sans appel au LLM ; latence p50 10,5 s sur CPU de portable
- Décision technique : seuil fixé sur un jeu de calibration distinct par une règle écrite avant la mesure, plutôt que réglé sur le jeu de test ; le prix du gain de qualité est une latence de 10 s sur CPU, à traiter au déploiement.
- Visuel disponible : aucun

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
