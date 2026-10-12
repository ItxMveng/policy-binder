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

| Métrique | Base naïve : dense seule (12/10) | Hybride dense + BM25, RRF (12/10) |
|---|---|---|
| Exactitude | 42,5 % (17/40) — IC 29–58 % | **47,5 %** (19/40) — IC 33–63 % |
| Correct ou partiel | 57,5 % (23/40) — IC 42–71 % | **70,0 %** (28/40) — IC 55–82 % |
| Citations correctes (réponses données) | 88,0 % (22/25) — IC 70–96 % | 90,3 % (28/31) — IC 75–97 % |
| Contexte : page attendue récupérée | 62,5 % (25/40) — IC 47–76 % | **80,0 %** (32/40) — IC 65–90 % |
| Contexte : document attendu récupéré | 97,5 % (39/40) — IC 87–100 % | 100 % (40/40) — IC 91–100 % |
| **Refus injustifiés** | 37,5 % (15/40) — IC 24–53 % | **22,5 %** (9/40) — IC 12–38 % |
| **Abstention correcte (hors corpus)** | 100 % (20/20) — IC 84–100 % | **100 %** (20/20) — IC 84–100 % |
| Réponses incorrectes (sur 40) | 2 | 3 |
| Latence p50 / p95 | 1,0 s / 2,0 s | 1,0 s / 1,9 s |
| Tokens moyens (entrée / sortie) | 1 313 / 189 | 1 305 / 188 |
| Coût pour 1 000 questions (tarif public) | 0,31 $ | 0,31 $ |

IC = intervalle de confiance à 95 % (Wilson).

Sources : `eval/results/baseline-dense.json`, `eval/results/hybride-rrf.json`.

### Recherche seule (sans LLM)
`scripts/eval_retrieval.py` → `eval/results/retrieval-comparison.json` : part des 40 questions dont la page attendue figure parmi les k premiers passages.

| Recherche | k = 1 | k = 3 | k = 5 | k = 10 | Temps moyen par requête |
|---|---|---|---|---|---|
| Dense | 37,5 % | 57,5 % | 62,5 % | 77,5 % | 14 ms |
| BM25 | 52,5 % | 77,5 % | 80,0 % | 92,5 % | 1,4 ms |
| Hybride (RRF) | 45,0 % | 70,0 % | 80,0 % | 92,5 % | 16 ms |

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

## Limites
- 60 questions : les intervalles sont larges, seuls les écarts importants seront interprétables.
- Le juge est lui-même un LLM : ses verdicts « partiel » / « incorrect » doivent être relus sur un échantillon.
- Latence mesurée depuis un portable vers une API gratuite partagée : elle n'est pas représentative d'un déploiement en production.
