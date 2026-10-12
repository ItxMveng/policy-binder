# Évaluation — Studeria Assistant

> **Résultats exploratoires.** 60 questions (40 avec réponse, 20 hors corpus) sur 9 documents : chaque taux est donné avec son intervalle de confiance à 95 % (Wilson). Le jeu d'évaluation a été relu et validé par Francis le 12/10/2026 (`eval/A-VALIDER.md`), sans modification des questions : les résultats ci-dessous restent valables.

## Protocole
- **Jeu de test** : `eval/questions.jsonl`. Chaque question avec réponse a une réponse de référence, la page attendue et un extrait vérifié sur le PDF (`scripts/check_eval_set.py`, 40/40).
- **Exécution** : `uv run python scripts/run_eval.py <nom>` → `eval/results/<nom>.json` (synthèse) et `<nom>-details.jsonl` (réponse, verdict et justification pour chaque question).
- **Modèle qui répond** : `openai/gpt-oss-120b` via Groq (offre gratuite), température 0.
- **Juge** : `qwen/qwen3.8-27b` via Groq, un modèle d'une autre famille que celui qui répond, pour éviter qu'un modèle note ses propres réponses. Verdict : correct / partiel / incorrect par rapport à la référence.
- **Métriques**
  - **Exactitude** : verdict « correct » sur les 40 questions avec réponse ; une abstention compte comme une erreur.
  - **Citations correctes** : parmi les réponses données, au moins une citation pointe vers la page attendue.
  - **Contexte** : la page attendue (ou au moins le document attendu) figure parmi les k = 5 passages récupérés.
  - **Refus injustifiés** : abstention sur une question qui a une réponse.
  - **Abstention correcte** : abstention sur une question hors corpus.
  - **Latence p50 / p95** : de bout en bout (recherche + génération), sans les attentes dues aux limites de débit de l'offre gratuite. Elle est mesurée depuis un portable (CPU) vers l'API Groq.
  - **Coût pour 1 000 questions** : tokens moyens × tarif public Groq de `gpt-oss-120b` (0,15 $ / 0,60 $ par million de tokens en entrée / sortie, relevé le 12/10/2026). Le coût du juge n'est pas compté, et le coût réel est nul (offre gratuite).

## Résultats

| Métrique | Dense seule (base naïve) | Hybride dense + BM25 | Hybride + reranker + seuil |
|---|---|---|---|
| Exactitude | 42,5 % (17/40) — IC 29–58 % | 47,5 % (19/40) — IC 33–63 % | **70,0 %** (28/40) — IC 55–82 % |
| Correct ou partiel | 57,5 % (23/40) — IC 42–71 % | 70,0 % (28/40) — IC 55–82 % | **95,0 %** (38/40) — IC 83–99 % |
| Citations correctes (réponses données) | 88,0 % (22/25) | 90,3 % (28/31) | **94,7 %** (36/38) |
| Contexte : page attendue récupérée | 62,5 % (25/40) | 80,0 % (32/40) | **95,0 %** (38/40) |
| Contexte : document attendu récupéré | 97,5 % (39/40) | 100 % (40/40) | 100 % (40/40) |
| **Refus injustifiés** | 37,5 % (15/40) — IC 24–53 % | 22,5 % (9/40) — IC 12–38 % | **5,0 %** (2/40) — IC 1–17 % |
| **Abstention correcte (hors corpus)** | 100 % (20/20) | 100 % (20/20) | **100 %** (20/20), dont 15 avant le LLM |
| Réponses incorrectes (sur 40) | 2 | 3 | **0** |
| Latence p50 / p95 (portable, CPU) | 1,0 s / 2,0 s | 1,0 s / 1,9 s | **10,5 s / 11,9 s** |
| Tokens moyens (entrée / sortie) | 1 313 / 189 | 1 305 / 188 | 1 002 / 161 |
| Coût pour 1 000 questions (tarif public) | 0,31 $ | 0,31 $ | 0,25 $ |

IC = intervalle de confiance à 95 % (Wilson).

Sources : `eval/results/baseline-dense.json`, `eval/results/hybride-rrf.json`, `eval/results/hybride-rerank-complet.json`. Reranker : `BAAI/bge-reranker-v2-m3-int8` sur 20 candidats ; seuil d'abstention −2,362 calibré sur `eval/calibration.jsonl`.

### Recherche seule (sans LLM)
`scripts/eval_retrieval.py` → `eval/results/retrieval-comparison.json` : part des 40 questions dont la page attendue figure parmi les k premiers passages.

| Recherche | k = 1 | k = 3 | k = 5 | k = 10 | Temps moyen par requête |
|---|---|---|---|---|---|
| Dense | 37,5 % | 57,5 % | 62,5 % | 77,5 % | 13 ms |
| BM25 | 52,5 % | 77,5 % | 80,0 % | 92,5 % | 1 ms |
| Hybride (RRF) | 45,0 % | 70,0 % | 80,0 % | 92,5 % | 15 ms |
| Hybride + reranker, réglage rapide (10 candidats, 400 caractères) | 52,5 % | 72,5 % | 80,0 % | 92,5 % | 2,6 s |
| Hybride + reranker, réglage complet (20 candidats, passages entiers) | **77,5 %** | **90,0 %** | **95,0 %** | 95,0 % | 10,0 s |

BM25 seul égale l'hybride à k = 5 et le dépasse à k = 1 et 3. L'écart n'est pas significatif sur 40 questions. L'hybride est retenu, comme prévu avant la mesure, parce qu'il reste robuste aux reformulations sans mots communs avec le texte. Les poids de la fusion n'ont **pas** été réglés sur ce jeu de test, pour ne pas surajuster.

## Analyse des erreurs de la base naïve
Sur les 40 questions avec réponse, 23 ne sont pas jugées « correctes » :
- **15 refus injustifiés.**
  - Dans **12 cas**, la page qui contient la réponse n'était pas parmi les 5 passages récupérés, alors que le bon document l'était dans 11 de ces 12 cas (contexte document : 97,5 %). Exemples : q08 (« 15 minutes avant l'épreuve »), q25 (« 5 jours ouvrés »), q29 (« trois jours ouvrés »). Ce sont des détails précis, chiffrés, que la recherche dense manque.
  - Dans **3 cas** (q03, q19, q30), le modèle s'est abstenu alors que le passage utile était fourni : la consigne d'abstention le rend trop prudent quand la formulation de la question diffère de celle du texte.
- **6 réponses partielles** : souvent justes mais incomplètes (q12 : les 48 h sans l'ENT ; q31 : le prêt d'un mois sans le cas des livres TOEIC). Quelques verdicts « partiel » semblent sévères : à vérifier lors de la validation du jeu.
- **2 réponses incorrectes**, toutes deux avec la page attendue absente du contexte :
  - q38 : le modèle autorise la redirection de la messagerie vers Gmail en s'appuyant sur une section voisine, alors que la règle (p. 14) l'interdit ;
  - q39 : il donne une règle de chiffrement générale au lieu de celle de l'informatique nomade.

  C'est le risque principal d'un assistant interne : une réponse plausible tirée d'un passage voisin.
- **Aucune réponse inventée sur les 20 questions hors corpus.**

**Conclusion** : la base naïve est prudente (aucune réponse sur les questions hors corpus) mais refuse trop souvent. Le goulot d'étranglement est la **récupération de la bonne page**, pas la génération. D'où les prochaines étapes, mesurées sur le même jeu :
1. Recherche hybride dense + BM25 (P1-07), pour retrouver les détails chiffrés et les termes exacts.
2. Reranking et seuil d'abstention calibré (P1-08), pour réduire les refus injustifiés sans perdre l'abstention correcte.

## Effet de la recherche hybride (P1-07)
- **Ce qui s'améliore** : la page attendue est récupérée pour 7 questions de plus (62,5 % → 80 %). 6 refus injustifiés disparaissent (15 → 9). La part de réponses correctes ou partielles passe de 57,5 % à 70 %. L'abstention sur les questions hors corpus reste parfaite (20/20).
- **Ce qui ne bouge pas** : la latence et le coût, car le BM25 en mémoire coûte environ 1 ms. L'exactitude stricte progresse peu (42,5 % → 47,5 %) et les intervalles se recouvrent : seule la baisse des refus est nette.
- **Le revers** : en répondant plus souvent, l'assistant se trompe un peu plus (2 → 3 réponses incorrectes).
  - q19 affirme qu'on peut stocker des données de l'UBO sur un ordinateur personnel, alors que la charte l'interdit (p. 9). La bonne page était dans le contexte : c'est une erreur de génération.
  - q38 répète l'erreur de la base naïve sur la redirection de messagerie.
  - q22 donne « 15 jours avant les jurys ». Le guide prévoit en fait deux délais : 3 semaines en règle générale, 15 jours pour un cas de force majeure. La réponse de référence ne cite que le premier ; elle mérite d'être complétée lors d'une prochaine révision du jeu.
- **Refus restants (9)** : 7 viennent encore d'une page non récupérée, 2 (q08, q29) d'une abstention du modèle alors que la page était fournie.

**Prochaine étape (P1-08)** : un reranker qui classe plus finement les 20 candidats de la recherche hybride, et un seuil d'abstention calibré sur un sous-ensemble distinct du jeu de test. Objectif : réduire les refus sans faire monter les réponses incorrectes. Pour q19, une consigne qui demande de citer la règle mot pour mot avant de conclure est une piste à mesurer.

## Reranking et seuil d'abstention (P1-08)
**Méthode, fixée avant toute mesure sur le jeu de test :**
- Un cross-encoder multilingue (`BAAI/bge-reranker-v2-m3-int8`, Apache-2.0, exécuté en local) relit les candidats de la recherche hybride et garde les 5 meilleurs.
- Un **jeu de calibration distinct** (`eval/calibration.jsonl` : 12 questions avec réponse, 12 hors corpus, aucune commune avec le jeu de test) sert à fixer :
  - **le seuil d'abstention**, par la règle « le plus haut seuil qui ne fait refuser aucune question de calibration ayant une réponse » ;
  - **le réglage du reranker**, par la règle « le plus rapide qui garde la meilleure qualité de recherche sous un budget de 3 s ».

**Ce qui s'est passé :**
- Sur la calibration, le réglage complet (20 candidats, passages entiers) sépare parfaitement les deux groupes : seuil −2,362, aucune question avec réponse refusée, 12 questions hors corpus sur 12 bloquées avant le LLM. Mais il prend 10 s par requête sur ce portable.
- La règle de budget a donc retenu un réglage rapide (10 candidats, 400 premiers caractères, 2,2 s). Sur le jeu de test, ce réglage rapide n'apporte presque rien par rapport à l'hybride seul (page attendue dans le top 5 : 80 % dans les deux cas). Tronquer les passages fait perdre au reranker l'information qui le rend utile, et dégrade la séparation des scores (seuil −6,582, seulement 3/12 questions hors corpus bloquées sur la calibration).
- Le réglage complet, évalué de bout en bout avec son seuil calibré :
  - exactitude 70 % ;
  - correct ou partiel 95 % ;
  - refus injustifiés 5 % ;
  - aucune réponse incorrecte, y compris q19 et q38 désormais justes ;
  - abstention correcte 20/20, dont 15 décidées par le seuil, sans appel au LLM : c'est pourquoi le coût moyen baisse.
- Refus restants :
  - q35 a été bloquée par le seuil, mais sa page n'était pas récupérée de toute façon ;
  - q07 est une abstention du modèle alors que la page était fournie.

**Décision : le réglage complet devient la configuration par défaut de l'API.** Transparence : cette décision a été prise **après** avoir vu les résultats sur le jeu de test, ce qui peut flatter un peu les chiffres. Le seuil, lui, n'a jamais été réglé sur le jeu de test. L'écart d'exactitude avec la base naïve (42,5 % → 70 %) est le premier dont les intervalles de confiance ne se recouvrent quasiment pas (29–58 % vs 55–82 %).

**Le prix : 10 s de latence sur CPU.** C'est le problème à résoudre au déploiement. Trois pistes à mesurer :
1. une instance avec GPU ;
2. un reranker plus petit et multilingue ;
3. un service de reranking hébergé.

## Limites
- 60 questions : les intervalles sont larges, seuls les écarts importants seront interprétables.
- Le juge est lui-même un LLM : ses verdicts « partiel » / « incorrect » doivent être relus sur un échantillon.
- Latence mesurée depuis un portable vers une API gratuite partagée : elle n'est pas représentative d'un déploiement en production.
