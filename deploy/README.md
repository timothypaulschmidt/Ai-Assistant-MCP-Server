# Deploying the MCP server to k3s

Runs in the same namespace as the AI Assistant (`ai-assistant`), reachable only inside the
cluster as `http://mcp-server:8000/mcp`. **Do not add an Ingress or NodePort**: the server
has deliberately unsafe tools.

## 1. Build and push the image (Windows, Docker Desktop running)

```powershell
cd <your clone of Ai-Assistant-MCP-Server>
git checkout main; git pull
docker build -t timothypaulschmidt/ai-assistant-mcp-server:v0.1.1 .
docker login            # once per machine
docker push timothypaulschmidt/ai-assistant-mcp-server:v0.1.1
```

The tag must match `newTag` in `deploy/k8s/kustomization.yaml`. Change both together when
the code changes.

## 2. Copy the deploy folder to the cluster and apply

```powershell
scp -r deploy administrator@k3s-qa.fortinetlabs.com:~/mcp-deploy
```

On the VM (the AI Assistant stack must already exist, because it creates the namespace):

```bash
kubectl apply -k ~/mcp-deploy/k8s
kubectl -n ai-assistant get pods -l app.kubernetes.io/name=mcp-server
kubectl -n ai-assistant logs deploy/mcp-server
```

## 3. Reset the lab

The data lives in a temporary volume, so restarting the pod regenerates it from the seed:

```bash
kubectl -n ai-assistant rollout restart deployment/mcp-server
```

## 4. Switch safe / vulnerable

Edit `MCP_MODE` in `deploy/k8s/deployment.yaml` (`safe` or `vulnerable`), copy the folder
again and re-apply. The pod is replaced and the data starts fresh.
