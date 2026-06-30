# LabelX Multi-Agent Workflow Explainer

The LabelX backend is powered by a LangGraph StateGraph that orchestrates multiple autonomous agents to analyze food labels.

## Shared State: `AnalysisState`
All agents read from and write to a shared typed dictionary called `AnalysisState`. This state holds:
- **Inputs**: `ingredients` (list of strings), `user_profile` (dict with conditions, allergies, expertise).
- **Control Flags**: `invalid_product`, `retry_count`, `validated`.
- **Results**: `research_results`, `report`, `score`, `feedback`, `status_updates`.

## 1. Supervisor Agent (`supervisor.py`)
The orchestrator of the graph. It uses pure deterministic Python logic to route the workflow.
- **Relevance Gate**: Uses a quick LLM check to ensure the input actually represents food. If not (e.g., shampoo), it sets `invalid_product = True` and ends the workflow early.
- **Routing**: If `research_results` is empty, it routes to `Research`. If `report` is missing, it routes to `Analysis`. If `validated` is False, it routes to `Critic`. If everything is done, it terminates.

## 2. Research Agent (`research_agent.py`)
Responsible for data gathering.
- **Qdrant Batch Search**: First, it embeds all ingredients in parallel using FastEmbed and searches the Qdrant vector database in a single batch request.
- **Redis Cache & Tavily Fallback**: For any ingredient with a Qdrant confidence score below 0.7, it falls back to the live internet. It concurrently checks Redis for cached Tavily searches. If absent, it queries the Tavily API, parses the result using Gemini, and caches it in Redis for 24 hours.

## 3. Analysis Agent (`analysis_agent.py`)
The primary generator of the report.
- Uses **Gemini 3.1 Flash-Lite** (with "medium" thinking level instructions).
- Combines the raw research data, the user's health conditions, and their expertise level to generate a fully personalized JSON report. It adapts language to be simpler for beginners or highly scientific for experts.

## 4. Critic Agent (`critic_agent.py`)
The quality assurance layer.
- Uses **Gemini 3.1 Flash-Lite** (with "low" thinking level instructions) for fast, strict validation.
- Evaluates the Analysis Agent's report against 6 rigorous gates:
  1. Completeness
  2. Allergen check
  3. Score consistency
  4. Personalization
  5. Relevance
  6. Clarity
- If any gate fails, it generates specific feedback, clears the report state, and increments `retry_count`, forcing the Supervisor to route back to the Analysis Agent.
- If it fails 3 times, it injects a safety disclaimer and forces validation.
