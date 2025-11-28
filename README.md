🛡️ RESILIO: The Cognitive Supply Chain Engine

Agentic GraphRAG for Pharmaceutical Resilience

Status: 🏆 Kaggle GenAI Agents Capstone Submission

Track: Enterprise / Business

Deployment: [Link to Video Demo] | [Link to Kaggle Notebook Demo]

🚨 The Business Problem

Pharma supply chains are fragile. Standard AI agents fail in the enterprise because they are "Frozen in Time" and "Deterministic." They cannot verify if a fire reported on Twitter is real, nor can they pinpoint its exact location relative to a factory.

💡 The Solution: Resilio

Resilio is a Cognitive Supply Chain Engine. It combines Unstructured Intelligence (News) with Geospatial Verification (NASA Satellites) and Structured Reasoning (Graph Theory).

🏆 Competitive Advantage

Feature

Standard RAG Bot

RESILIO Engine

Data Freshness

Training Data Cutoff

Live Web Search (Tavily)

Ground Truth

Hallucinated Coordinates

Satellite Verification (NASA EONET)

Reasoning

Single-step retrieval

Multi-hop Graph Traversal (BFS)

Risk Model

Point Estimate ($3M)

Monte Carlo Probabilistic Range

Trust

Black Box

Auditor Agent Guardrails

🛠️ Architecture: The "Truth Sandwich"

We wrap every LLM generation in deterministic code layers:

Layer 1: Live Verification (Tavily + NASA)

The Sentinel Agent queries Tavily to confirm the event exists and NASA EONET to detect thermal anomalies at the coordinates.

Layer 2: Entity Grounding

The extracted entity is forced to match a valid node ID in our NetworkX graph.

Layer 3: Probabilistic Math

Risk is calculated via Python using Monte Carlo simulations to generate P5/P95 confidence intervals.

Agent Workflow (LangGraph)

Sentinel (Detect) $\to$ Detective (Trace) $\to$ Quantifier (Calculate) $\to$ Strategist (Decide) $\to$ Auditor (Verify)

🚀 Installation & Usage

Option 1: Local Execution

Clone the repository:

git clone [https://github.com/yourusername/Resilio.git](https://github.com/yourusername/Resilio.git)
cd Resilio


Install dependencies:

pip install -r requirements.txt


Set API Keys (Linux/Mac):

export GOOGLE_API_KEY="your_key"
export TAVILY_API_KEY="your_key"


Run the Control Tower:

streamlit run ui/dashboard.py


Option 2: Docker Deployment (Bonus)

Deploy Resilio as a microservice on Google Cloud Run.

Build Container:

docker build -t resilio-app .


Run Container:

docker run -p 8080:8080 -e GOOGLE_API_KEY=... resilio-app


🧪 Testing & Validation

Run the automated test suite to verify the Anti-Hallucination Guardrails:

python -m src.testing


📂 Project Structure

src/resilio_core.py: The "Brain" containing the Graph, Agents, and Monte Carlo engine.

ui/dashboard.py: The Streamlit "Control Tower" interface.

src/testing.py: Unit tests for risk math and grounding logic.