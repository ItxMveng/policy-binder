---
title: Le Classeur
emoji: 📁
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: API de Le Classeur (réponses citées sur des règlements)
---

# Le Classeur — API

API de démonstration de [Le Classeur](https://github.com/ItxMveng/policy-binder) : questions sur des règlements et chartes publics (ENIB, Université de Brest, IMT Atlantique), réponses avec la page exacte du document officiel, ou « je ne trouve pas ».

- `GET /health` · `GET /sources` · `POST /ask {"question": "..."}`
- Démo limitée : 10 questions par adresse sur 10 minutes, 300 par jour.
- Code, évaluation et explications : https://github.com/ItxMveng/policy-binder

Ce Space est publié automatiquement par GitHub Actions ; ne pas le modifier ici.
