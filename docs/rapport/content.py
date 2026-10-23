"""Contenu du rapport des deux TP Real-Time Sales (CI/CD puis Kubernetes)."""
from pathlib import Path

FIG = Path(__file__).parent / "figures"

TITLE = "Industrialisation et déploiement d'une pipeline Data temps réel"
SUB = ("TP CI/CD avec Jenkins et SonarQube, puis TP Kubernetes sur Minikube\n"
       "Mastère Data Engineering et Intelligence Artificielle")

META = [
    ("Auteur", "Adam BELOUCIF"),
    ("Numéro étudiant", "20220055"),
    ("Module", "DevOps, tests logiciels et CI/CD"),
    ("Promotion", "M2 Data Engineering et IA, 2026-2027"),
    ("Date du rapport", "22 octobre 2026"),
]

TAGLINE = ("J'ai d'abord rendu une API de ventes, Kafka, Spark et PostgreSQL testables et contrôlés "
           "à chaque commit, puis je les ai déployés dans un cluster Kubernetes local.")

C = []
a = C.append

# ------------------------------------------------------------------ contexte
a(("h1", "Contexte et livrables"))
a(("p", "Les deux TP portent sur le même projet fil rouge, une plateforme d'analyse des ventes "
        "en temps réel fournie par l'enseignant. Une API FastAPI reçoit des commandes et publie "
        "un événement dans le topic Kafka sales.orders. Un job PySpark Structured Streaming lit ce "
        "topic, écarte les commandes invalides et écrit le résultat dans la table processed_orders "
        "de PostgreSQL."))
a(("p", "Le premier TP demandait d'industrialiser cette chaîne avec trois niveaux de tests, une "
        "pipeline Jenkins et un Quality Gate SonarQube. Le second reprend le même dépôt et le "
        "déploie sur Minikube avec des manifestes Kubernetes écrits à la main. J'ai travaillé sur "
        "la branche dev d'un fork publié sur GitHub, et le travail est proposé en Pull Request "
        "vers main."))
a(("kpi", [("56", "tests automatisés"), ("100 %", "couverture du code applicatif"),
           ("0", "bug, vulnérabilité ou duplication"), ("5", "Deployments Kubernetes")]))
a(("table", ["Élément", "Emplacement"],
   [["Dépôt", "github.com/Adam-Blf/real-time-sales-devops-tp, branche dev"],
    ["Pull Request", "github.com/Adam-Blf/real-time-sales-devops-tp/pull/1"],
    ["Tests", "tests/unit, tests/integration, tests/e2e"],
    ["CI", "Jenkinsfile, docker/jenkins, tools/quality_gate.py"],
    ["Qualité", "sonar-project.properties, tools/sonar_setup.py"],
    ["Kubernetes", "dossier k8s/"],
    ["Sorties brutes", "docs/evidence (logs Jenkins, Quality Gate, kubectl)"]],
   [1.0, 3.2], "Tableau 1. Où trouver chaque livrable"))

# ------------------------------------------------------------------ architecture
a(("h1", "Architecture de la plateforme"))
a(("p", "Toute l'infrastructure démarre avec une seule commande, docker compose up, y compris "
        "Jenkins et SonarQube. La figure 1 résume le flux de données et la chaîne de "
        "contrôle qui l'entoure."))
a(("figure", str(FIG / "schema-pipeline.png"), "Figure. Flux de données et chaîne de contrôle"))
a(("p", "Avant d'écrire le moindre test, j'ai découpé l'API, qui tenait en un seul fichier. Les "
        "règles métier sont passées dans app/domain.py, sans aucune dépendance à Kafka. On y trouve le "
        "modèle Order, le catalogue, le calcul du montant et la construction de l'événement. La "
        "publication vit dans app/messaging.py avec un producteur Kafka unique, alors que le code "
        "d'origine en ouvrait un nouveau à chaque requête. Les routes ne font plus que relier les "
        "deux et traduire les erreurs en codes HTTP, 404 pour un produit inconnu, 422 pour une "
        "donnée invalide et 503 quand Kafka ne répond pas."))
a(("figure", str(FIG / "swagger.png"), "Figure. Les trois routes de l'API, documentation Swagger générée par FastAPI"))
a(("p", "Une fois la plateforme lancée, les dix conteneurs tournent côte à côte. Kafka et PostgreSQL "
        "déclarent une sonde de santé, sur laquelle s'appuient les dépendances de démarrage."))
a(("figure", str(FIG / "term-compose.png"), "Figure. La plateforme démarrée avec Docker Compose"))

# ------------------------------------------------------------------ tests
a(("h1", "Stratégie de tests"))
a(("p", "J'ai suivi la pyramide classique, avec beaucoup de tests unitaires rapides, quelques "
        "tests d'intégration sur les vrais services et un seul scénario de bout en bout. Chaque "
        "niveau a sa propre étape Jenkins, et un échec dit tout de suite à quel étage se trouve "
        "le problème."))
a(("table", ["Niveau", "Dossier", "Ce qui est réel", "Tests", "Durée"],
   [["Unitaire", "tests/unit", "rien, Kafka est simulé", "50", "1,5 s"],
    ["Intégration", "tests/integration", "API, Kafka, Spark, PostgreSQL", "5", "8 s"],
    ["End-to-End", "tests/e2e", "toute la plateforme", "1", "1,5 s"]],
   [1.0, 1.2, 2.0, 0.6, 0.6], "Tableau 2. Les trois niveaux de tests"))
a(("p", "Le sujet interdisait les attentes arbitraires du type time.sleep(30). Les tests "
        "d'intégration et E2E passent tous par une fonction wait_for qui interroge la condition "
        "à intervalle régulier et lève une erreur explicite, avec la dernière exception "
        "rencontrée, dès que le délai maximal est dépassé. Un test qui échoue dit ce qu'il "
        "attendait, au lieu de rester bloqué trente secondes pour rien."))
a(("p", "Les adresses des services viennent de variables d'environnement. Les mêmes tests "
        "tournent depuis mon poste, où Kafka répond sur localhost:9092, et depuis Jenkins, qui "
        "joint les services par leur nom dans le réseau Docker."))

a(("h2", "Tests unitaires"))
a(("p", "Les cas listés par le sujet sont tous couverts, la plupart avec des tests paramétrés "
        "qui balayent les bornes. Le tableau 3 fait la correspondance."))
a(("table", ["Cas demandé", "Ce que vérifient les tests"],
   [["Montant total", "cinq calculs dont 3 x 100 = 300 et 3 x 0,1 = 0,3, arrondi au centime"],
    ["Quantité", "1 et 1000 acceptés, 0, -1, -50, 1001 et une chaîne refusés"],
    ["Prix", "0,01 à 100 000 acceptés, 0, négatif, au-delà du plafond et texte refusés"],
    ["Identifiants", "client et produit vides, d'un seul caractère ou absents refusés"],
    ["Identifiant de commande", "format ORD- suivi de 10 hexadécimaux, 1000 tirages tous distincts"],
    ["Événement", "tous les champs présents, valeurs recopiées, horodatage ISO 8601 avec fuseau"],
    ["Routes HTTP", "commande publiée, 404 sans publication, 422 sur quatre charges, 503"]],
   [1.3, 3.4], "Tableau 3. Correspondance entre le sujet et les tests unitaires"))
a(("p", "La couverture du paquet app atteint 100 %, mesurée par pytest-cov et publiée dans "
        "SonarQube sous forme de fichier coverage.xml."))
a(("figure", str(FIG / "term-unit.png"), "Figure. Les 50 tests unitaires et la couverture ligne par ligne"))

a(("h2", "Tests d'intégration"))
a(("p", "Le test A vérifie le couple API et Kafka. Il poste une commande à l'API réellement "
        "démarrée, puis un consommateur ouvert dans un groupe neuf lit le topic jusqu'à trouver "
        "l'événement qui porte le même order_id. Le test compare ensuite le client, le produit, "
        "la quantité et le montant, ici 4 x 89,90 = 359,6."))
a(("p", "Le test B écrit directement dans Kafka, sans passer par l'API, et attend la ligne "
        "correspondante dans processed_orders. Un second test publie une commande invalide "
        "suivie d'une commande valide qui sert de marqueur. Les deux tombent dans la même "
        "partition, et Spark les lit dans l'ordre. Quand le marqueur arrive en base, la commande "
        "invalide a forcément été traitée avant lui, et elle doit être absente. J'obtiens la "
        "preuve du filtrage sans attendre un délai choisi au hasard."))
a(("figure", str(FIG / "term-integration.png"),
   "Figure. Les tests d'intégration et E2E, lancés contre la plateforme démarrée"))

a(("h2", "Scénario de bout en bout"))
a(("p", "Le test E2E reprend la commande du sujet, le client C100 qui achète trois produits P001 "
        "à 100. Il vérifie que l'API répond, envoie la commande et attend la ligne en base. Le "
        "contrôle final porte sur le client, le produit, la quantité et le montant attendu de 300."))
a(("code", "Given  l'infrastructure démarrée (GET /api/health renvoie UP)\n"
           "When   POST /api/orders {customer_id: C100, product_id: P001, quantity: 3, unit_price: 100}\n"
           "Then   une ligne apparaît dans processed_orders avec total_amount = 300",
   "Figure. Le scénario E2E"))

# ------------------------------------------------------------------ jenkins
a(("h1", "Pipeline Jenkins"))
a(("p", "Je n'ai rien configuré à la main dans l'interface de Jenkins. Son image installe la CLI "
        "Docker, Python et les plugins nécessaires. Un fichier de configuration as code crée le "
        "compte administrateur, enregistre le jeton SonarQube comme identifiant et déclare le job "
        "real-time-sales-pipeline, branché sur la branche dev et interrogé toutes les deux "
        "minutes. Supprimer le conteneur et le recréer redonne exactement le même Jenkins."))
a(("code", "Checkout -> Install -> Unit Tests -> Integration Tests -> Build -> Deploy\n"
           "         -> E2E Tests -> SonarQube Analysis -> Quality Gate",
   "Figure. Les étapes du Jenkinsfile"))
a(("p", "L'étape Build reconstruit les images de l'API et du job Spark, et l'étape Deploy les "
        "redémarre avant l'E2E. Le scénario de bout en bout valide le code du commit en cours, "
        "pas une image construite la veille. L'analyse SonarQube tourne dans un conteneur frère "
        "qui partage le workspace de Jenkins. L'étape Quality Gate lance ensuite un petit script "
        "Python qui attend la fin du traitement côté serveur, affiche chaque condition et renvoie "
        "un code d'erreur si le Gate n'est pas vert. Les rapports JUnit des trois niveaux et le "
        "fichier de couverture sont archivés à chaque build."))
a(("figure", str(FIG / "jenkins-job.png"),
   "Figure. Historique du job. Les builds #2 et #4 se sont arrêtés, #3 et #5 sont passés"))
a(("p", "L'historique montre deux arrêts qui prouvent que la pipeline bloque vraiment. Le build "
        "#2 avait tous ses tests verts mais s'est arrêté à l'étape Quality Gate, faute de trouver "
        "le rapport du scanner (le correctif est décrit plus loin). Le build #4 s'est lancé tout "
        "seul après un push, à un moment où Kafka était arrêté sur mon poste. Il a échoué dès les "
        "tests d'intégration et n'est jamais allé jusqu'au build des images. Le build #5, lancé "
        "une fois la plateforme redémarrée, est vert sur le dernier commit."))
a(("figure", str(FIG / "jenkins-tests.png"),
   "Figure. Résultats du build #3, 56 tests répartis sur les trois niveaux"))
a(("p", "La fin de la console du build #5 montre l'étape Quality Gate. Le script affiche chaque "
        "condition avec la valeur mesurée, et Jenkins conclut sur un succès."))
a(("figure", str(FIG / "term-gate.png"), "Figure. Sortie de l'étape Quality Gate dans la console Jenkins"))

# ------------------------------------------------------------------ sonar
a(("h1", "Analyse SonarQube et Quality Gate"))
a(("p", "Le fichier sonar-project.properties analyse app, spark et tools, déclare tests comme "
        "code de test et lit le rapport de couverture. J'ai exclu le job Spark et l'outillage CI "
        "du calcul de couverture. Ils sont validés par les tests d'intégration et par Jenkins "
        "lui-même, et leur imposer des tests unitaires aurait surtout servi à gonfler un chiffre."))
a(("p", "Le serveur se configure par script, avec tools/sonar_setup.py. Il crée le projet et le "
        "Quality Gate, puis écrit un jeton d'analyse dans le fichier .env, que Git ignore et que "
        "Docker Compose transmet à Jenkins."))
a(("table", ["Condition du Quality Gate", "Seuil"],
   [["Couverture", "au moins 80 %"], ["Bugs", "aucun"], ["Vulnérabilités", "aucune"],
    ["Duplications", "au plus 3 %"]],
   [2.5, 2.0], "Tableau 4. Conditions du Gate « Data Pipeline Gate »"))

a(("h2", "Mesure avant et après"))
a(("p", "Pour comparer, j'ai analysé le code d'origine de l'enseignant, avec ses trois tests de "
        "départ, dans un projet SonarQube séparé et sous le même Gate. Il échoue sur deux "
        "conditions."))
a(("figure", str(FIG / "sonar-avant.png"),
   "Figure. Code d'origine, Quality Gate en échec"))
a(("p", "La vulnérabilité, classée critique, vient du job Spark. Il écrivait son checkpoint dans "
        "/tmp, un répertoire où tout le monde peut écrire. La couverture de 70,7 % s'explique par "
        "les règles de validation, que les tests de départ ne vérifiaient qu'en partie. Il n'y "
        "avait en revanche ni bug, ni code smell, ni duplication."))
a(("figure", str(FIG / "sonar-vulnerabilite.png"),
   "Figure. La vulnérabilité du code d'origine, ligne 79 de spark/sales_stream.py"))
a(("figure", str(FIG / "sonar-apres.png"),
   "Figure. Code livré, Quality Gate validé"))
a(("table", ["Mesure", "Code d'origine", "Code livré"],
   [["Couverture", "70,7 %", "100 %"], ["Bugs", "0", "0"],
    ["Vulnérabilités", "1 (critique)", "0"], ["Code smells", "0", "0"],
    ["Duplications", "0 %", "0 %"], ["Quality Gate", "en échec", "validé"]],
   [1.6, 1.4, 1.4], "Tableau 5. Comparaison des deux analyses"))

# ------------------------------------------------------------------ difficultés
a(("h1", "Problèmes rencontrés et corrections"))
a(("p", "Le dépôt de départ démarrait, mais plusieurs défauts n'apparaissaient qu'au premier "
        "test sérieux. Le plus gênant était le job Spark. Au premier démarrage, il s'abonnait "
        "au topic avant que Kafka ne l'ait créé, plantait sur UnknownTopicOrPartitionException "
        "et ne redémarrait jamais. J'ai ajouté un service kafka-init qui crée le topic, et Spark "
        "attend maintenant sa fin avant de démarrer."))
a(("p", "Le redémarrage révélait le défaut suivant. Le checkpoint étant dans /tmp, il "
        "disparaissait avec le conteneur, et Spark relisait le topic depuis le début. Les "
        "commandes déjà en base provoquaient alors une violation de clé primaire. Le checkpoint "
        "est désormais sur un volume, et l'insertion utilise ON CONFLICT DO NOTHING pour qu'un "
        "micro-batch rejoué ne casse plus rien. Ce même déplacement a fait disparaître la "
        "vulnérabilité relevée par SonarQube."))
a(("table", ["Symptôme", "Cause", "Correction"],
   [["Spark meurt au premier démarrage", "abonnement avant la création du topic",
     "service kafka-init et redémarrage automatique"],
    ["Doublons de clé primaire", "checkpoint perdu, relecture depuis le début",
     "volume de checkpoint et insertion idempotente"],
    ["Écriture impossible depuis les exécuteurs", "psycopg2 absent de l'image Spark",
     "insertion côté driver, partition par partition"],
    ["SonarQube refuse admin/admin", "compte initial sans mot de passe utilisable",
     "réinitialisation documentée, mot de passe aléatoire dans .env"],
    ["Jenkins ignore sa configuration", "fichier copié dans un dossier masqué par un volume",
     "fichier déplacé hors du volume"],
    ["Build #2 arrêté au Quality Gate", "rapport du scanner écrit dans /tmp, perdu à la sortie",
     "dossier de travail du scanner placé dans le workspace"],
    ["Kafka ne repart pas après un arrêt brutal", "nœud du broker encore présent dans ZooKeeper",
     "redémarrage automatique du conteneur Kafka"]],
   [1.5, 1.6, 1.7], "Tableau 6. Défauts corrigés pendant le TP CI/CD"))
a(("callout", "Secrets",
   "Aucun mot de passe ni jeton n'est dans le dépôt. Les identifiants de Jenkins et de "
   "SonarQube sont générés au hasard et rangés dans .env, et Jenkins masque le jeton dans ses "
   "logs. GitGuardian a signalé deux jetons sur la Pull Request. Vérification faite, il "
   "s'agissait de deux identifiants de commit, qui ont la même forme que les anciens jetons "
   "SonarQube.", "info"))

# ------------------------------------------------------------------ kubernetes
a(("h1", "Déploiement sur Kubernetes"))
a(("p", "Le second TP reprend le même projet sur Minikube. Le cluster de mon poste hébergeait "
        "déjà les déploiements d'un autre cours dans le namespace default, et je n'ai pas voulu "
        "y toucher. Toute la plateforme vit dans un namespace dédié, sales."))
a(("figure", str(FIG / "schema-kubernetes.png"), "Figure. La plateforme déployée dans le cluster"))
a(("table", ["Fichier", "Ressources"],
   [["00-namespace.yaml", "Namespace sales"],
    ["01-configmap.yaml", "hôtes Kafka et PostgreSQL, topic, base, utilisateur"],
    ["02-postgres-init.yaml", "script de création de la table processed_orders"],
    ["postgres.yaml", "volume persistant, Deployment, Service postgres"],
    ["kafka.yaml", "ZooKeeper et Kafka (Deployments et Services), Job de création du topic"],
    ["api-deployment.yaml", "Deployment sales-api, sondes sur /api/health"],
    ["api-service.yaml", "Service sales-api sur le port 8000"],
    ["spark-streaming.yaml", "volume des checkpoints, Deployment spark-streaming"]],
   [1.5, 3.2], "Tableau 7. Les manifestes du dossier k8s"))

a(("h2", "Adaptations par rapport à Docker Compose"))
a(("p", "Les noms de services du compose ne valent rien dans le cluster. Les composants joignent "
        "les Services Kubernetes, kafka:9092 et postgres:5432, et ces adresses sont centralisées "
        "dans la ConfigMap. Kafka n'a plus besoin que d'un listener, puisque tous ses clients sont "
        "dans le cluster. Le mot de passe de PostgreSQL est dans un Secret que je crée à la main "
        "avec une valeur aléatoire, et aucun manifeste ne le contient."))
a(("p", "Les images Confluent m'ont coûté le plus de temps. Pour chaque Service, Kubernetes "
        "injecte dans les Pods des variables comme KAFKA_PORT=tcp://10.110.182.112:9092. Or ces "
        "images lisent toute variable qui commence par KAFKA_ ou ZOOKEEPER_ comme un réglage, et "
        "refusent de démarrer. La ligne enableServiceLinks: false, posée sur chaque Pod, coupe "
        "cette injection. La sonde de disponibilité de Kafka, qui lançait la commande "
        "kafka-topics, posait un autre problème. Elle démarre une JVM complète et dépassait le "
        "délai de dix secondes sur un nœud Minikube chargé, si bien que Kafka redémarrait en "
        "boucle. Une sonde TCP sur le port 9092 a réglé le problème."))
a(("p", "Spark tourne en mode local[2] dans un seul Deployment, avec la même image et le même "
        "job. Le couple master et worker du compose aurait doublé la mémoire nécessaire pour un "
        "gain nul sur un nœud unique. Les images de l'API et de Spark sont construites dans "
        "Minikube et déclarées avec imagePullPolicy: Never."))

a(("h2", "État du cluster et test du flux"))
a(("figure", str(FIG / "term-k8s-state.png"), "Figure. Le nœud Minikube et les ressources du namespace sales"))
a(("p", "J'ai exposé l'API avec kubectl port-forward, sur le port local 8001 parce que l'API du "
        "compose occupait déjà le 8000, puis envoyé la commande du sujet. L'API a renvoyé un montant "
        "de 300, et la ligne est apparue dans PostgreSQL quelques secondes plus tard. Le flux complet "
        "fonctionne dans le cluster."))
a(("figure", str(FIG / "term-k8s-flow.png"), "Figure. Une commande traverse Kafka et Spark jusqu'à PostgreSQL"))

a(("h2", "Mise à l'échelle et suppression d'un Pod"))
a(("p", "Le passage à trois réplicas a créé deux Pods en quelques secondes, et le Deployment est "
        "passé à 3/3. Le Service sales-api répartit alors les requêtes entre les trois. Revenir à "
        "un réplica a supprimé les deux Pods en trop."))
a(("figure", str(FIG / "term-k8s-scale.png"), "Figure. Passage de un à trois réplicas, puis retour à un"))
a(("figure", str(FIG / "term-k8s-heal.png"), "Figure. Suppression d'un Pod de l'API et création de son remplaçant"))
a(("p", "Quand j'ai supprimé le Pod de l'API, le ReplicaSet a constaté qu'il restait zéro Pod "
        "pour un souhaité. Il en a créé un nouveau dans la même seconde, avant même que l'ancien "
        "ait fini de s'arrêter. Le remplaçant est devenu prêt six secondes plus tard, au moment "
        "où sa sonde /api/health a répondu. Kubernetes ne relance pas le Pod supprimé, il en crée "
        "un autre, avec un autre nom et une autre adresse IP. C'est pour cette raison qu'on "
        "s'adresse toujours au Service, dont l'adresse ne change pas."))

# ------------------------------------------------------------------ bilan
a(("h1", "Bilan"))
a(("p", "Dans le premier TP, les tests ont surtout servi à faire apparaître des défauts. Le "
        "test d'intégration Spark a révélé le plantage au démarrage et les doublons au "
        "redémarrage, et le Quality Gate a relevé le checkpoint dans /tmp que je n'avais pas vu."))
a(("p", "Le passage à Kubernetes m'a surtout appris que la configuration d'un compose ne se "
        "recopie pas. Les noms DNS changent, les variables injectées par les Services entrent en "
        "conflit avec les images, et une sonde mal choisie suffit à faire tourner un service en "
        "boucle. La suite logique serait de brancher ce déploiement sur la pipeline Jenkins, "
        "que le sujet laissait hors du périmètre."))

# Numérotation des figures dans l'ordre d'apparition, pour qu'un ajout ne la décale jamais.
_n = 0
for _i, _item in enumerate(C):
    if _item[0] in ("figure", "code") and len(_item) > 2 and _item[2].startswith("Figure. "):
        _n += 1
        C[_i] = (_item[0], _item[1], f"Figure {_n}. " + _item[2][len("Figure. "):]) + tuple(_item[3:])

SPEC = {
    "title": TITLE,
    "subtitle": SUB,
    "block_label": "TP DevOps et Kubernetes",
    "meta": META,
    "tagline": TAGLINE,
    "content": C,
}
