# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MailMind AI is an AI-powered email assistant that uses a three-phase agent architecture:
1. **Learning Phase** - Analyzes historical emails to create "Skills" (automated response templates)
2. **Execution Phase** - Classifies incoming emails and matches them to Skills for draft generation
3. **Evolution Phase** - Learns from human edits to refine Skills over time

## Commands

### Backend (Python/FastAPI)

```bash
# From /backend directory
cd backend

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server (with auto-reload)
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# API docs available at http://localhost:8000/docs
```

### Frontend (Next.js)

```bash
# From /frontend directory
cd frontend

npm install
npm run dev      # Development server at http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint
```

## Architecture

### Monorepo Structure

```
email-assistant-demo/
├── backend/           # FastAPI REST API (Python 3.11+)
│   ├── agents/        # Three-phase Agent system
│   │   ├── base_agent.py       # BaseAgent with Claude API integration
│   │   ├── learning_agent.py   # Analyzes emails → creates Skills
│   │   ├── execution_agent.py  # Processes emails → generates drafts
│   │   ├── evolution_agent.py  # Learns from human edits
│   │   └── tools.py            # 7 Agent tools for Claude SDK
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # API routes (6 routers including agents_router)
│   ├── services/      # Business logic
│   ├── data/          # SQLite database and skills.json
│   ├── main.py        # FastAPI app entry point
│   └── config.py      # Pydantic settings
├── frontend/          # Next.js 14 React SPA
└── docs/              # Documentation
```

### Database Models

- **Email** - Email content, classification, priority scoring
- **Reply** - AI draft + human edits + send status
- **Skill** - Name, trigger_keywords, rules, usage stats
- **SkillSourceEmail** - Links Skills to training source emails
- **SkillChangeLog** - Tracks Skill evolution history (V-05)

### Agent API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/learn` | POST | Trigger learning (background job) |
| `/api/agents/execute` | POST | Process single email, generate reply |
| `/api/agents/evolve` | POST | Learn from human edits |
| `/api/agents/status` | GET | System and agent status |
| `/api/agents/jobs/{job_id}` | GET | Check background job status |
| `/api/agents/batch-execute` | POST | Process multiple emails |

### Legacy Endpoints (still functional)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/emails/sync` | Sync emails from Zoho |
| `POST /api/skills/learn` | Legacy learning endpoint |
| `POST /api/replies/generate` | Generate AI draft |
| `GET /api/oauth/authorize` | Initiate Zoho OAuth |

## Environment Variables

Backend `.env`:
- `ANTHROPIC_API_KEY` - Claude API key
- `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET` - Zoho OAuth
- `ZOHO_EMAIL` - Zoho mailbox email
- `FRONTEND_URL` - For CORS
- `ZOHO_REDIRECT_URI` - OAuth callback URL

Frontend `.env.local`:
- `NEXT_PUBLIC_API_URL` - Backend URL (default: http://localhost:8000)

## Agent System Details

### LearningAgent
- Fetches customer service emails from database
- Groups by category, calls Claude to extract patterns
- Creates Skills with trigger_keywords and rules
- Records source emails for traceability (SkillSourceEmail)

### ExecutionAgent
- Classifies email if not already classified
- Matches Skills with detailed confidence scoring
- Generates reply using templates or Claude
- Marks low-confidence emails for escalation (E-06)

### EvolutionAgent
- Compares AI draft with human-edited version
- Analyzes differences using Claude
- Applies improvements: keywords, rules, templates
- Records changes to SkillChangeLog (V-05)
