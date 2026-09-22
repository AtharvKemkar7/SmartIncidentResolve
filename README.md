# AI Kubernetes Agent

On-demand Kubernetes troubleshooting with AI. This repository is a monorepo with a FastAPI orchestrator and a Next.js UI.

```text
Frontend
    ↓
FastAPI Backend (Orchestrator)
    ↓
Kubernetes Investigation Layer
    ↓
AI Kubernetes Agent
    ↓
LLM Reasoning
    ↓
Root Cause + Suggested Fix
```

This is not a Kubernetes controller or operator. Investigation runs when a user requests it.

## Project structure

```text
.
├── backend/          FastAPI orchestrator
├── frontend/         Next.js UI
├── docs/             Project documentation
├── prompts/          Prompt templates
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.12+ and Node.js 20+ for local development

## Quick start

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

## Environment variables

Copy the example files and fill in values when you add Kubernetes and AI later.

Backend (`backend/.env.example`):

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
KUBECONFIG_PATH=
```

Frontend (`frontend/.env.example`):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Health check

`GET /health`

```json
{
  "status": "healthy",
  "service": "ai-kubernetes-agent"
}
```

## Dashboard

Open http://localhost:3000 and sign in with `demo@local.dev` / `demo`.

The dashboard lists every context in your kubeconfig. Select a cluster, then click **Investigate Cluster**.

Progress, diagnosis, and investigation history appear on the same page.

## Investigate cluster

`POST /investigate`

Optional body: `{ "cluster": "minikube" }`

Runs the Kubernetes investigation layer (pods, logs, events, deployments, networking) via `kubectl`, then asks the AI agent for a diagnosis. Set `KUBECONFIG_PATH` and `OPENROUTER_API_KEY`.

```json
{
  "status": "success",
  "investigation": {
    "pods": {},
    "logs": {},
    "events": {},
    "deployments": {},
    "network": {}
  },
  "diagnosis": {
    "root_cause": "DATABASE_URL missing",
    "explanation": "Application cannot connect to DB.",
    "fix": "Add missing environment variable.",
    "kubectl_command": "kubectl edit deployment payment-service",
    "prevention": "Fail startup when required env vars are missing.",
    "confidence": 92,
    "confidence_reasoning": "Pod CrashLoopBackOff plus logs showing the missing env var."
  }
}
```

## Failure scenarios

Apply sample failures, then investigate that cluster:

```bash
kubectl apply -f k8s/failures/crashloop.yaml
kubectl apply -f k8s/failures/imagepull.yaml
kubectl apply -f k8s/failures/oomkilled.yaml
kubectl apply -f k8s/failures/selector-mismatch.yaml
```
