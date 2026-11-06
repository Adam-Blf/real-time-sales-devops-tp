# Changelog

Toutes les évolutions notables de ce dépôt sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions : [SemVer](https://semver.org/lang/fr/).

## [1.0.0] - 2026-11-06

### Ajouté

- API découpée en modules `domain` et `messaging`, producteur Kafka partagé.
- Tests unitaires des règles métier, tests d'intégration API vers Kafka et Spark vers PostgreSQL, test E2E de bout en bout.
- Jenkins configuré par code (CasC) avec administrateur local, pipeline Checkout, Install, tests, Build, Deploy, E2E, SonarQube et Quality Gate.
- Outillage SonarQube (`tools/`) pour créer le projet et lire le Quality Gate.
- Déploiement Kubernetes local (`k8s/`) et preuves d'exécution (`docs/evidence/`).
- Rapport PDF des deux TP, régénérable avec `python docs/rapport/build.py`, avec contrôle de mise en page.
- README vitrine (badges, architecture Mermaid), licence MIT, fichier `VERSION` et workflow de release sur tag.

### Corrigé

- Course sur la création du topic et rejeu dans le job de streaming.
