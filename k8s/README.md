# Déploiement Kubernetes local

Compte rendu complet : [docs/kubernetes.md](../docs/kubernetes.md).

```bash
docker compose down                       # libère les ports, garde les volumes
minikube start --driver=docker --memory=6144 --cpus=4

# Images du projet, construites dans Minikube
minikube image build -t sales-api:tp3 -f docker/api/Dockerfile .
minikube image build -t sales-spark-streaming:tp3 -f docker/spark/Dockerfile .

# Namespace puis mot de passe PostgreSQL aléatoire, jamais commité
kubectl apply -f k8s/00-namespace.yaml
kubectl -n sales create secret generic postgres-credentials \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)"

kubectl apply -f k8s/
kubectl -n sales get pods,deployments,services

kubectl -n sales port-forward service/sales-api 8000:8000
```

Toutes les ressources sont dans le namespace `sales` : ajouter `-n sales` aux commandes `kubectl` du sujet.
