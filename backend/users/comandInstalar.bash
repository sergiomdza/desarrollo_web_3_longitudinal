kind create cluster --name web3
kubectl create namespace proyecto-final

docker pull mongo:7.0
kind load docker-image mongo:7.0 --name web3

kubectl apply -f kubernetes/mongo_statefulset.yaml
kubectl apply -f kubernetes/equipo_5/backend_deployment.yaml 
kubectl rollout status statefulset/mongo -n proyecto-final
kubectl rollout status deployment/backend -n proyecto-final
kubectl get pods -n proyecto-final
kubectl get services -n proyecto-final

kubectl port-forward service/backend-service 8000:8000 -n proyecto-final

poetry run fastapi dev app/main.py