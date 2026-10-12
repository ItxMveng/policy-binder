# Évaluation — Studeria Assistant

> **Résultats exploratoires.** 60 questions (40 avec réponse, 20 hors corpus) sur 9 documents : chaque taux est donné avec son intervalle de confiance à 95 % (Wilson). Le jeu d'évaluation n'est pas encore validé par Francis (`eval/A-VALIDER.md`) : les chiffres pourront bouger après relecture.

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

| Métrique | Base naïve (dense seule, k = 5) — 12/10/2026 |
|---|---|
| Exactitude | **42,5 %** (17/40) — IC 95 % : 29–58 % |
| Correct ou partiel | 57,5 % (23/40) — IC 95 % : 42–71 % |
| Citations correctes (réponses données) | 88,0 % (22/25) — IC 95 % : 70–96 % |
| Contexte : page attendue récupérée | 62,5 % (25/40) — IC 95 % : 47–76 % |
| Contexte : document attendu récupéré | 97,5 % (39/40) — IC 95 % : 87–100 % |
| **Refus injustifiés** | **37,5 %** (15/40) — IC 95 % : 24–53 % |
| **Abstention correcte (hors corpus)** | **100 %** (20/20) — IC 95 % : 84–100 % |
| Latence p50 / p95 | 1,0 s / 2,0 s |
| Tokens moyens (entrée / sortie) | 1 313 / 189 |
| Coût pour 1 000 questions (tarif public) | 0,31 $ |

Source : `eval/results/baseline-dense.json`.

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

## Limites
- 60 questions : les intervalles sont larges, seuls les écarts importants seront interprétables.
- Le juge est lui-même un LLM : ses verdicts « partiel » / « incorrect » doivent être relus sur un échantillon.
- Latence mesurée depuis un portable vers une API gratuite partagée : elle n'est pas représentative d'un déploiement en production.
