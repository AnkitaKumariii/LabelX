# 🧪 LabelX — AI Food Label Analyzer

> **Paste or photograph food ingredients → Get a personalized AI safety report in seconds.**

LabelX is a full-stack web application that uses a **multi-agent LangGraph workflow** powered by **Gemini 2.0 Flash** to analyze food ingredients and generate personalized safety reports based on your health profile.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Multi-Agent AI** | Supervisor → Research → Analysis → Critic (LangGraph) |
| **Personalized Reports** | Adapts to diabetes, hypertension, celiac, PKU, and more |
| **Live Streaming** | Server-Sent Events show real-time agent progress |
| **Vector Search** | Qdrant + FastEmbed for 70+ ingredient embeddings |
| **Web Fallback** | Tavily search for unknown ingredients |
| **OCR** | Upload product photos → Tesseract extracts text |
| **Color-Coded Results** | 🔴 Harmful / 🟡 Caution / 🟢 Safe badges |
| **Health Score Gauge** | 0–100 animated score with condition-aware scoring |

---

## 🏗️ Architecture

```
React Frontend (Vercel)
     ↓ Axios / Fetch SSE
FastAPI Backend (Render)
     ↓
LangGraph Workflow
├── Supervisor Agent   — routing hub
├── Research Agent     — Qdrant (FastEmbed) → Tavily fallback
├── Analysis Agent     — Gemini 2.0 Flash report generation
└── Critic Agent       — 4-gate validation, 3 retries max
     ↓
Qdrant Cloud          — 70+ food additive embeddings
Redis Cloud           — profile & history storage
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system
- Qdrant Cloud account → [cloud.qdrant.io](https://cloud.qdrant.io)
- Redis Cloud account → [redis.com/try-free](https://redis.com/try-free)
- Gemini API key → [aistudio.google.com](https://aistudio.google.com)
- Tavily API key → [tavily.com](https://tavily.com)

### Backend

```bash
cd backend
cp .env.example .env
# Fill in all API keys in .env

pip install -r requirements.txt

# Seed the Qdrant vector database (run once)
python services/seed_qdrant.py

# Start the server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `REDIS_URL` | Redis connection string |
| `FRONTEND_URL` | Deployed Vercel URL (for CORS) |

### Frontend (Vercel)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Deployed backend URL (e.g. `https://labelx.onrender.com`) |

---

## 🤖 Agent Design

### Supervisor Agent
Routes between agents based on state flags in `AnalysisState`. Acts as the workflow hub — all agents return to it after completing.

### Research Agent
1. Embeds ingredient name with **FastEmbed** (`BAAI/bge-small-en-v1.5`)
2. Searches **Qdrant Cloud** (cosine similarity, threshold: 0.7)
3. Falls back to **Tavily** web search if confidence < 0.7
4. Passes raw Tavily results to **Gemini** for structured parsing

### Analysis Agent
- Calls **Gemini 2.0 Flash** with full research data + user profile
- **Beginner mode**: Plain language, no jargon
- **Expert mode**: E-numbers, biochemical effects, regulatory classifications
- **Condition-specific**: Diabetes → hidden sugars, Hypertension → sodium sources, Celiac → gluten, PKU → aspartame

### Critic Agent — 4 Validation Gates

| Gate | Check |
|---|---|
| Completeness | All `n` ingredients have a report entry |
| Allergen Check | All user allergens are flagged in the report |
| Score Consistency | 3+ harmful ingredients → score must be < 40 |
| Personalization | User health conditions mentioned in report |

On failure → clears report → sends feedback to Analysis Agent → retry (max 3).
After 3 failures → returns best-effort report with disclaimer.

---

## 🗄️ Data Sources

- **Primary**: 70+ food additive records seeded into Qdrant (see `backend/services/seed_qdrant.py`)
- **Web fallback**: Tavily real-time web search
- **Expand with**: [Open Food Facts API](https://world.openfoodfacts.org/data), [EWG Food Scores](https://www.ewg.org/foodscores/)

---

## 🌐 Deployment

### Backend → Render
1. Connect GitHub repo to Render
2. Root directory: `backend`
3. Build command auto-installs Tesseract (see `render.yaml`)
4. Set all env vars in Render dashboard
5. Set `FRONTEND_URL` to your Vercel app URL

### Frontend → Vercel
1. Connect GitHub repo to Vercel
2. Root directory: `frontend`
3. Framework: Vite
4. Set `VITE_API_URL` to your Render backend URL

---

## 📁 Project Structure

```
LabelX/
├── backend/
│   ├── main.py                  # FastAPI app + CORS
│   ├── graph.py                 # LangGraph StateGraph
│   ├── agents/
│   │   ├── state.py             # AnalysisState TypedDict
│   │   ├── supervisor.py        # Routing hub
│   │   ├── research_agent.py    # Qdrant + Tavily
│   │   ├── analysis_agent.py    # Gemini report writer
│   │   └── critic_agent.py      # 4-gate validator
│   ├── routes/
│   │   ├── analyze.py           # POST /api/analyze (SSE)
│   │   ├── profile.py           # POST/GET/PUT /api/profile
│   │   └── history.py           # GET /api/history/{id}
│   └── services/
│       ├── redis_service.py     # Profile & history storage
│       ├── qdrant_service.py    # Vector search with FastEmbed
│       ├── ocr_service.py       # Tesseract OCR
│       ├── gemini_service.py    # LLM helpers
│       └── seed_qdrant.py       # Database seeder (run once)
└── frontend/
    └── src/
        ├── pages/
        │   ├── ProfileSetup.jsx  # 3-step profile wizard
        │   ├── Analyze.jsx       # Ingredient input + live SSE
        │   └── Results.jsx       # Report with gauge & badges
        └── components/
            ├── HealthGauge.jsx   # Animated SVG gauge
            ├── IngredientBadge.jsx # Expandable color badge
            ├── SummaryCard.jsx   # Stat cards
            └── AgentProgress.jsx # Live progress panel
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)
