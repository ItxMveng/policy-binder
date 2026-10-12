# ROADMAP — P1 : Studeria Assistant (12 → 23 octobre 2026)

## Baseline fonctionnelle
- [x] P1-01 Sources officielles et téléchargement — data/sources.yaml (≥ 6 documents, URL vérifiées, date de consultation), scripts/download_sources.py, data/raw/ ignoré par git, tests du chargement des sources (fait le 2026-10-11)
- [x] P1-02 Ingestion PDF en passages — extraction du texte page par page, nettoyage, découpage avec chevauchement et métadonnées (document, page), tests (fait le 2026-10-11)
- [x] P1-03 Index dense et recherche (base naïve) — embeddings multilingues locaux, index Qdrant local, commande de recherche, tests avec un embedder factice (fait le 2026-10-11)
- [x] P1-04 Réponse avec citations — interface LLMProvider + implémentation Mistral, prompt à citations [n], abstention si aucun passage, API POST /ask, tests avec un fournisseur factice (fait le 2026-10-11)

## Jeu d'évaluation et mesure
- [x] P1-05 Jeu d'évaluation versionné — eval/questions.jsonl (40 avec réponse + source attendue, 20 hors corpus), schéma Pydantic, test de cohérence avec sources.yaml (fait le 2026-10-11)
- [x] P1-06 Mesure des erreurs de la base naïve — script d'évaluation (exactitude par juge LLM, citations, précision du contexte, abstention correcte, refus injustifiés, latence p50/p95, coût / 1 000 questions), résultats exploratoires dans docs/evaluation.md (fait le 2026-10-12)

## Amélioration de la récupération et de l'abstention
- [ ] P1-07 Recherche hybride dense + BM25 — fusion par rangs (RRF), mesure comparée à la base naïve
- [ ] P1-08 Reranking et seuil d'abstention — reranker, seuil calibré sur un sous-ensemble distinct du jeu de test, mesure des refus injustifiés et de l'abstention correcte
- [ ] P1-09 Évaluation en CI — 20 questions en CI bloquantes sous le seuil, évaluation complète sur tag

## Déploiement et observabilité
- [ ] P1-10 Interface de chat — React + Vite + TypeScript, citations cliquables vers la page du document
- [ ] P1-11 Traces Langfuse et protection de la démo — traces de chaque requête (latence, tokens), limite par IP et quota quotidien
- [ ] P1-12 Déploiement — Terraform + Cloud Run (europe-west9) + Qdrant Cloud + Vercel, URL publique fonctionnelle
- [ ] P1-13 Rapport docs/evaluation.md — protocole, jeu de test, résultats, comparaison base naïve vs version finale
- [ ] P1-14 README étude de cas + GIF de démo
