# Deploying the MCP server to k3s

Runs in the same namespace as the AI Assistant (`ai-assistant`), reachable only inside the
cluster as `http://mcp-server:8000/mcp`. **Do not add an Ingress or NodePort**: the server
has deliberately unsafe tools.

## 1. Build and push the image (Windows, Docker Desktop running)

```powershell
cd <your clone of MCP-Server>
git checkout main; git pull
docker build -t timothypaulschmidt/mcp-server:v0.2.1 .
docker login            # once per machine
docker push timothypaulschmidt/mcp-server:v0.2.1
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

## 2b. Create the admin token (once)

The `/admin/*` routes let the operator reset the ticket queue and insert tickets while the
server runs. They are not MCP tools, so no model can call them. They need a token, kept in
a Kubernetes Secret (never in git):

```bash
kubectl -n ai-assistant create secret generic mcp-admin \
  --from-literal=token="$(openssl rand -hex 24)"
kubectl -n ai-assistant rollout restart deployment/mcp-server    # pick the Secret up
```

Try it from inside the cluster (the Service is ClusterIP only):

```bash
TOKEN=$(kubectl -n ai-assistant get secret mcp-admin -o jsonpath='{.data.token}' | base64 -d)
kubectl -n ai-assistant run curl --rm -it --image=curlimages/curl --restart=Never -- \
  curl -s -H "Authorization: Bearer $TOKEN" http://mcp-server:8000/admin/stats
```

| Route | Body | Does |
|---|---|---|
| `GET /admin/stats` | | tickets by status, poisoned ticket ids, banking row count, emails in outbox |
| `POST /admin/reset` | `{"scenario": "empty" \| "normal10" \| "poisoned10", "full": false}` | reset the queue; `full: true` also rebuilds every table from the seed |
| `POST /admin/insert` | `{"kind": "normal" \| "poisoned", "count": 3}` | add open tickets while an agent runs |

## 3. Reset the lab (whole pod)

The data lives in a temporary volume, so restarting the pod regenerates it from the seed:

```bash
kubectl -n ai-assistant rollout restart deployment/mcp-server
```

## 4. Switch safe / vulnerable

Edit `MCP_MODE` in `deploy/k8s/deployment.yaml` (`safe` or `vulnerable`), copy the folder
again and re-apply. The pod is replaced and the data starts fresh.
