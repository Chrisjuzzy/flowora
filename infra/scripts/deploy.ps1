$root = Resolve-Path "$PSScriptRoot\..\.."

kubectl apply -k "$root\infra\k8s"
kubectl rollout status deployment/flowora-api -n flowora
kubectl rollout status deployment/flowora-worker -n flowora
kubectl rollout status deployment/flowora-beat -n flowora
