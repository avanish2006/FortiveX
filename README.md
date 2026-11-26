# SalesPilot AI 🎙️

**Autonomous AI Sales Voice Agent** — Talk to customers, qualify leads, book appointments and update your CRM — all hands-free.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                          │
│   Next.js UI  ─── WebSocket (audio) ─── REST API (data)       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────────────────────────────┐     │
│  │  Voice Layer │  │        LangGraph Agent                │     │
│  │  STT/TTS     │  │  ┌──────────┐  ┌────────────────┐   │     │
│  │  WebSocket   │  │  │  Intent  │  │  RAG Retrieval │   │     │
│  └──────┬───────┘  │  │  Router  │  │  (FAISS/LC)    │   │     │
│         │          │  └────┬─────┘  └────────────────┘   │     │
│         ▼          │       │  ┌───────────────────────┐   │     │
│  ┌──────────────┐  │  ┌────▼──▼──────┐               │   │     │
│  │  Transcript  │  │  │   Tools       │               │   │     │
│  │  Store       │  │  │  ─ Calendar  │               │   │     │
│  └──────────────┘  │  │  ─ HubSpot   │               │   │     │
│                    │  │  ─ Email     │               │   │     │
│                    │  │  ─ BANT Qual │               │   │     │
│                    │  │  ─ Sentiment │               │   │     │
│                    │  └──────────────┘               │   │     │
│                    └──────────────────────────────────┘   │     │
│                                                            │     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐    │     │
│  │ Postgres │  │  Redis   │  │  FAISS Vector Store   │    │     │
│  │ (CRM/DB) │  │ (Session)│  │  (RAG Knowledge Base) │    │     │
│  └──────────┘  └──────────┘  └──────────────────────┘    │     │
└─────────────────────────────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────────┐
         ▼              ▼                  ▼
   Google Calendar  HubSpot CRM      SMTP Email
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Launch all services
docker compose up --build

# 3. Open the app
open http://localhost:3000
```

## Key Features

| Feature | Technology |
|---------|-----------|
| Voice STT | OpenAI Whisper |
| Voice TTS | OpenAI TTS / ElevenLabs |
| AI Agent | LangGraph + GPT-4o |
| RAG | LangChain + FAISS |
| CRM | HubSpot API |
| Calendar | Google Calendar API |
| Database | PostgreSQL + pgvector |
| Cache / Sessions | Redis |
| Frontend | Next.js 14 + Tailwind CSS |

## Project Structure

```
FortiveX/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── main.py           # App entry point
│   │   ├── agent/            # LangGraph orchestrator
│   │   ├── voice/            # STT + TTS
│   │   ├── rag/              # RAG engine
│   │   ├── integrations/     # Calendar, CRM, Email
│   │   ├── models/           # DB models (SQLAlchemy)
│   │   ├── routers/          # FastAPI routers
│   │   └── core/             # Config, security, deps
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Next.js 14 frontend
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   ├── components/       # UI components
│   │   ├── hooks/            # Custom React hooks
│   │   └── lib/              # API client, utils
│   ├── package.json
│   └── Dockerfile
├── docs/              # Sample knowledge base documents
├── docker-compose.yml
└── .env.example
```

## Scalability Notes

- **Stateless workers**: Backend is fully stateless (session in Redis), scale horizontally with Kubernetes HPA.
- **Vector DB migration**: FAISS → Qdrant or pgvector for distributed search at scale.
- **Message queue**: Add Celery + Redis for async TTS/STT at high load.
- **CDN**: Serve TTS audio blobs via S3 + CloudFront.
- **Cost at 100k users**: ~$2,400/month (estimated, see `/docs/cost_analysis.md`).

## Security

- JWT authentication on all endpoints.
- API keys stored only in environment variables.
- Input validation on all voice/text inputs.
- Rate limiting per session and per IP.
- HTTPS enforced in production via Nginx + Let's Encrypt.

---
*Built for the FortiveX AI Engineering Interview — November 2026*
