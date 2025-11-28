# 🛡️ RESILIO: The Cognitive Supply Chain Engine

**Agentic GraphRAG for Pharmaceutical Resilience**

**Status:** 🏆 Kaggle GenAI Agents Capstone Submission  
**Track:** Enterprise / Business  
**Deployment:** [Link to Video Demo] | [Link to Kaggle Notebook Demo]

---

## 🚨 The Business Problem

Pharma supply chains are fragile. Standard AI agents fail in the enterprise because they are:

- **"Frozen in Time"** - Training data cutoff means they miss real-time events
- **"Deterministic"** - They cannot verify if a fire reported on Twitter is real
- **"Unaware"** - They cannot pinpoint exact location relative to a factory

---

## 💡 The Solution: Resilio

Resilio is a **Cognitive Supply Chain Engine**. It combines:

- **Unstructured Intelligence** (News) 
- **Geospatial Verification** (NASA Satellites)
- **Structured Reasoning** (Graph Theory)

---

## 🏆 Competitive Advantage

| Feature | Standard RAG Bot | RESILIO Engine |
|---------|------------------|----------------|
| **Data Freshness** | Training Data Cutoff | Live Web Search (Tavily) |
| **Ground Truth** | Hallucinated Coordinates | Satellite Verification (NASA EONET) |
| **Reasoning** | Single-step retrieval | Multi-hop Graph Traversal (BFS) |
| **Risk Model** | Point Estimate ($3M) | Monte Carlo Probabilistic Range |
| **Trust** | Black Box | Auditor Agent Guardrails |

---

## 🛠️ Architecture: The "Truth Sandwich"

We wrap every LLM generation in **deterministic code layers**:

### Layer 1: Live Verification (Tavily + NASA)

The **Sentinel Agent** queries:
- **Tavily** to confirm the event exists
- **NASA EONET** to detect thermal anomalies at coordinates

### Layer 2: Entity Grounding

The extracted entity is **forced to match** a valid node ID in our NetworkX graph.

### Layer 3: Probabilistic Math

Risk is calculated via **Python** using Monte Carlo simulations to generate **P5/P95 confidence intervals**.

---

## 🔄 Agent Workflow (LangGraph)

```
Sentinel (Detect) → Detective (Trace) → Quantifier (Calculate) → Strategist (Decide) → Auditor (Verify)
```

### Agent Descriptions

1. **📡 Sentinel Agent** - Detect & Verify
   - Scans news input for supply chain disruptions
   - Uses LLM with Tavily (web search) and NASA EONET (geospatial verification)
   - Maps events to entities in the knowledge graph

2. **🕵️ Detective Agent** - Trace Impact
   - Traverses the knowledge graph using **Breadth-First Search (BFS)**
   - Finds impacted products downstream
   - Detects hidden dependencies (e.g., Saline → CAR-T)

3. **📊 Quantifier Agent** - Calculate Risk
   - Runs **Monte Carlo simulation** (1000 iterations)
   - Calculates financial risk ranges (P5, Expected, P95)
   - Computes inventory gap days

4. **🎯 Strategist Agent** - Recommend Action
   - Analyzes risk magnitude and event type
   - Generates context-specific recommended actions

5. **⚖️ Auditor Agent** - Validate & Approve
   - Validates entity grounding (hallucination check)
   - Verifies math integrity
   - Approves or blocks results for presentation

---

## 🚀 Installation & Usage

### Option 1: Local Execution

**1. Clone the repository:**

```bash
git clone https://github.com/codingnoodle/resilio.git
cd resilio
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Set API Keys (Linux/Mac):**

```bash
export GOOGLE_API_KEY="your_key"
export TAVILY_API_KEY="your_key"
```

**4. Run the Control Tower:**

```bash
streamlit run ui/dashboard.py
```

Open `http://localhost:8501` in your browser.

### Option 2: Docker Deployment

Deploy Resilio as a microservice on Google Cloud Run.

**Build Container:**

```bash
docker build -t resilio-app .
```

**Run Container:**

```bash
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your_key" \
  -e TAVILY_API_KEY="your_key" \
  -e PORT=8080 \
  resilio-app
```

**Deploy to Google Cloud Run:**

```bash
gcloud run deploy resilio \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY="your-key",TAVILY_API_KEY="your-key"
```

---

## ⚙️ Configuration

### Zero-Dependency Mode (Mock)

Set `USE_REAL_LLM = False` in `src/resilio_core.py` to run in deterministic mock mode (no API calls required).

**Valid inputs in Zero-Dependency Mode:**
- **Locations:** North Carolina, Rocky Mount, North Cove, New Jersey, Mock Town, Mumbai, Rotterdam
- **Partners:** Pfizer, Baxter, Janssen, PharmaCorp, India
- **Disruptions:** Fire, Tornado, Hurricane, Strike, Floods, Logistics

### Real LLM Mode

Set `USE_REAL_LLM = True` and ensure API keys are set. The system will use:

- **Google Gemini 2.0 Flash Lite** for entity/event extraction
- **Tavily Search** for web verification
- **NASA EONET** for geospatial verification

---

## 🧪 Testing & Validation

Run the automated test suite to verify the Anti-Hallucination Guardrails:

```bash
python src/testing.py
```

**Test Coverage:**
- ✅ Entity grounding (fuzzy matching)
- ✅ Location-priority logic
- ✅ Probabilistic math integrity
- ✅ Hallucination prevention
- ✅ Internal BioTherapy scenario
- ✅ Multiple event types per location

---

## 📂 Project Structure

```
resilio/
├── src/
│   ├── resilio_core.py      # The "Brain" - Graph, Agents, Monte Carlo engine
│   └── testing.py           # Unit tests for risk math and grounding logic
├── ui/
│   ├── dashboard.py         # The Streamlit "Control Tower" interface
│   └── workflow_diagram.svg  # Multi-agent workflow diagram
├── Dockerfile               # Container configuration
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── RISK_CALCULATION_EXPLAINED.md  # Detailed risk calculation methodology
```

### Key Files

- **`src/resilio_core.py`** - Main application logic, agents, knowledge graph
- **`ui/dashboard.py`** - Streamlit UI with visualizations
- **`src/testing.py`** - Unit tests

---

## 📊 Knowledge Graph Structure

### Locations
- **Mock Town, NJ (USA)** - Internal manufacturing facility
- **North Cove, NC (USA)** - Partner B facility
- **Rocky Mount, NC (USA)** - Partner C facility
- **Mumbai, India** - Partner D facility
- **Rotterdam, EU** - Logistics hub

### Entities
- **PharmaCorp A (Internal)** - Internal manufacturing
- **PharmaCorp B (Tier 1 Partner)** - IV Fluid supplier
- **PharmaCorp C (Tier 1 Partner)** - Sterile injectable supplier
- **PharmaCorp D (Tier 2 Partner)** - Raw material supplier
- **EU Logistics** - European logistics partner

### Products
- **Product X BioTherapy** - Finished BioTherapy product (CAR-T proxy)
- **Product Y Sterile** - Sterile injectable component
- **Product Z Commodity** - Critical commodity component

### Ingredients
- **BioTherapy Raw** - BioTherapy precursor material
- **API Generic Raw** - Generic API raw material

---

## 📚 Documentation

- **[Risk Calculation Explained](RISK_CALCULATION_EXPLAINED.md)** - Detailed methodology for Monte Carlo simulation
- **Dashboard Guide** - Interactive UI with knowledge graph visualization

---

## 📝 License

MIT License

---

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

---

## 📧 Contact

For questions or issues, please open an issue on [GitHub](https://github.com/codingnoodle/resilio).
