import networkx as nx
import difflib
import requests
import json
import os
import numpy as np
from typing import List, TypedDict, Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END


# --- CONFIGURATION ---
# Set to True to enable real LLM (Gemini + Tavily + NASA)
USE_REAL_LLM = True 
DEFAULT_DISRUPTION_DAYS = 60 
np.random.seed(42)

# Initialize Gemini 2.5 Flash for performance
if USE_REAL_LLM:
    try:
        if os.environ.get("GOOGLE_API_KEY"):
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
        else:
            llm = None
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize Gemini LLM: {e}")
        llm = None
else:
    llm = None

# ==========================================
# 1. KNOWLEDGE GRAPH (Tuned for High Impact Demo)
# ==========================================
def build_resilio_graph():
    """
    Constructs the supply chain digital twin.
    View: 'PharmaCorp A' is the Internal Company. Everyone else is a Partner.
    """
    G = nx.DiGraph()
    
    # --- LOCATIONS ---
    G.add_node("Mock_Town_NJ_USA", type="Location", lat=40.57, lon=-74.65)     
    G.add_node("North_Cove_NC_USA", type="Location", lat=35.73, lon=-82.00)  
    G.add_node("Rocky_Mount_NC_USA", type="Location", lat=35.93, lon=-77.79) 
    G.add_node("Mumbai_Zone_A", type="Location", lat=19.07, lon=72.87)       
    G.add_node("Rotterdam_Port_EU", type="Location", lat=51.92, lon=4.47)    
    
    # --- SUPPLIERS ---
    G.add_node("PharmaCorp_A_Internal", type="Internal Mfg", reliability=0.98)
    G.add_node("PharmaCorp_B_Tier1", type="Partner (Tier 1)", reliability=0.90)
    G.add_node("PharmaCorp_C_Tier1", type="Partner (Tier 1)", reliability=0.99)
    G.add_node("PharmaCorp_D_Tier2", type="Partner (Tier 2)", reliability=0.85)
    G.add_node("EU_Logistics", type="Logistics Partner", reliability=0.92)

    # --- PRODUCTS (All set to Low Inventory for Demo Drama) ---
    # Product X = Finished BioTherapy - Zero Inventory (Vein-to-Vein)
    G.add_node("Product_X_BioTherapy", type="Product (Finished)", revenue_annual=500_000_000, inventory_weeks=0)
    
    # Product Y = Sterile Injectable - Low Inventory
    G.add_node("Product_Y_Sterile", type="Product (Component)", revenue_annual=1_200_000_000, inventory_weeks=2)
    
    # Product Z = Critical Commodity (Saline proxy) - Reduced to 2 weeks for demo
    G.add_node("Product_Z_Commodity", type="Product (Component)", revenue_annual=300_000_000, inventory_weeks=2)
    
    # --- INGREDIENTS ---
    # Reduced Buffers to ensure even moderate delays cause impact (2-4 weeks max)
    G.add_node("BioTherapy_Raw", type="Ingredient", inventory_weeks=4)  # Was 8, now 4 weeks
    G.add_node("API_Generic_Raw", type="Ingredient", inventory_weeks=4)  # Was 12, now 4 weeks

    # --- EDGES (Physical Flow) ---
    # Locations -> Entities
    G.add_edge("Mock_Town_NJ_USA", "PharmaCorp_A_Internal", relationship="LOCATED_AT", lead_time_days=0)
    G.add_edge("North_Cove_NC_USA", "PharmaCorp_B_Tier1", relationship="LOCATED_AT", lead_time_days=0)
    G.add_edge("Rocky_Mount_NC_USA", "PharmaCorp_C_Tier1", relationship="LOCATED_AT", lead_time_days=0)
    G.add_edge("Mumbai_Zone_A", "PharmaCorp_D_Tier2", relationship="LOCATED_AT", lead_time_days=0)
    G.add_edge("Rotterdam_Port_EU", "EU_Logistics", relationship="LOCATED_AT", lead_time_days=0)
    
    # Manufacturing Flow
    G.add_edge("PharmaCorp_A_Internal", "Product_X_BioTherapy", relationship="MANUFACTURES", lead_time_days=14)
    G.add_edge("PharmaCorp_C_Tier1", "Product_Y_Sterile", relationship="MANUFACTURES", lead_time_days=21)
    G.add_edge("PharmaCorp_B_Tier1", "Product_Z_Commodity", relationship="MANUFACTURES", lead_time_days=7)
    G.add_edge("PharmaCorp_D_Tier2", "BioTherapy_Raw", relationship="MANUFACTURES", lead_time_days=30)
    G.add_edge("PharmaCorp_D_Tier2", "API_Generic_Raw", relationship="MANUFACTURES", lead_time_days=45)
    
    # Dependencies
    G.add_edge("BioTherapy_Raw", "PharmaCorp_A_Internal", relationship="SHIPPED_TO", lead_time_days=14)
    G.add_edge("BioTherapy_Raw", "Product_X_BioTherapy", relationship="KEY_INGREDIENT", lead_time_days=2)  # Updated to 2 days (internal material handling/prep time)
    G.add_edge("API_Generic_Raw", "Product_Y_Sterile", relationship="KEY_INGREDIENT", lead_time_days=2)  # Updated to 2 days (internal material handling/prep time)
    
    # Logistics
    G.add_edge("EU_Logistics", "BioTherapy_Raw", relationship="TRANSPORTS", lead_time_days=5)
    G.add_edge("EU_Logistics", "API_Generic_Raw", relationship="TRANSPORTS", lead_time_days=5)
    
    # Critical Dependencies
    G.add_edge("Product_Z_Commodity", "Product_X_BioTherapy", relationship="REQUIRED_FOR_ADMINISTRATION", lead_time_days=1)  # Updated to 1 day (kitting/staging time)
    G.add_edge("Product_Y_Sterile", "Product_X_BioTherapy", relationship="REQUIRED_FOR_SURGERY", lead_time_days=1)  # Updated to 1 day (kitting/staging time)
    
    return G

KG = build_resilio_graph()

# ==========================================
# 2. TOOLS
# ==========================================
def check_nasa_eonet(category="Wildfires"):
    try:
        url = "https://eonet.gsfc.nasa.gov/api/v3/events"
        resp = requests.get(url, params={"category": category, "status": "open", "limit": 5}, timeout=3)
        if resp.status_code == 200 and resp.json().get('events'):
            return [f"NASA Event: {e['title']} at {e['geometry']}" for e in resp.json()['events']]
    except: pass
    return ["NASA EONET: No satellite anomalies detected."]

def verify_with_tavily(query):
    try:
        if os.environ.get("TAVILY_API_KEY"):
            return f"Tavily: Found {len(TavilySearchResults(max_results=2).invoke(query))} sources."
    except: pass
    return "Tavily: Skipped (No Key)."

def fuzzy_find_entity(query, graph):
    if not query or query == "Unknown": return None
    q = query.lower()
    # Updated: Add location keywords for better matching
    # Priority order: specific locations first, then generic regions
    if any(kw in q for kw in ["mock town", "car-t", "cart", "biotherapy", "nj", "jersey", "new jersey"]): return "PharmaCorp_A_Internal"
    if "north cove" in q or "iv fluid" in q: return "PharmaCorp_B_Tier1"
    if "rocky mount" in q: return "PharmaCorp_C_Tier1"
    if "india" in q or "mumbai" in q: return "PharmaCorp_D_Tier2"
    if "rotterdam" in q or ("port" in q and ("rotterdam" in q or "eu" in q or "netherlands" in q)): return "EU_Logistics"
    # Fallback: generic location matching (less specific)
    if "north carolina" in q or ("nc" in q and "carolina" in q):
        # Default to North Cove (Partner B) if no specific city mentioned
        if "rocky mount" in q:
            return "PharmaCorp_C_Tier1"
        else:
            return "PharmaCorp_B_Tier1"
    matches = difflib.get_close_matches(query, list(graph.nodes()), n=1, cutoff=0.4)
    return matches[0] if matches else None

# ==========================================
# 3. EMPIRICAL DISRUPTION PROFILES (Tuned for Demo)
# ==========================================
# Increased durations to guarantee they exceed the 2-4 week inventory buffers
DISRUPTION_PROFILES = {
    "Tornado": (90, 15),       # 3 months (Wipes out 2w buffer) - Rocky Mount scenario
    "Hurricane": (60, 10),     # 2 months (Wipes out 4w buffer) - North Cove scenario - BOOSTED from 45
    "Fire": (75, 14),          # 2.5 months (Wipes out 4w buffer) - Mumbai scenario - BOOSTED from 60
    "Strike": (45, 10),        # 1.5 months (Wipes out 4w buffer) - EU Logistics - BOOSTED from 14
    "Logistics": (21, 5),      # 3 weeks (Wipes out 0w buffer for Product X) - Mock Town scenario - BOOSTED from 10
    "FDA": (90, 30),           # Regulatory hold is long
    "Default": (45, 7)         # Generic fallback
}

def get_disruption_params(event_text):
    text = event_text.lower()
    if "tornado" in text: return DISRUPTION_PROFILES["Tornado"]
    if "hurricane" in text or "flood" in text: return DISRUPTION_PROFILES["Hurricane"]
    if "fire" in text or "explosion" in text: return DISRUPTION_PROFILES["Fire"]
    if "strike" in text or "labor" in text: return DISRUPTION_PROFILES["Strike"]
    if "logistics" in text or "truck" in text: return DISRUPTION_PROFILES["Logistics"]
    if "fda" in text or "regulatory" in text: return DISRUPTION_PROFILES["FDA"]
    return DISRUPTION_PROFILES["Default"]

def predict_financial_impact_range(products, event_text, source_entity, graph, simulations=1000):
    risk_report = {}
    total_loss_samples = np.zeros(simulations)
    
    mean_days, sigma_days = get_disruption_params(event_text)
    disruption_dist = np.maximum(np.random.normal(loc=mean_days, scale=sigma_days, size=simulations), 0)
    
    d_p5 = float(np.percentile(disruption_dist, 5))
    d_p95 = float(np.percentile(disruption_dist, 95))
    
    for prod in products:
        try:
            path = nx.shortest_path(graph, source=source_entity, target=prod)
            path_inventory_weeks = sum([graph.nodes[n].get('inventory_weeks', 0) for n in path])
        except:
            path_inventory_weeks = graph.nodes[prod].get('inventory_weeks', 0)
            
        inv_days = path_inventory_weeks * 7
        daily_rev_avg = graph.nodes[prod].get('revenue_annual', 0) / 365
        daily_rev_dist = np.maximum(np.random.normal(loc=daily_rev_avg, scale=daily_rev_avg * 0.2, size=simulations), 0)
        
        gap_days_dist = np.maximum(disruption_dist - inv_days, 0)
        loss_dist = gap_days_dist * daily_rev_dist
        total_loss_samples += loss_dist
        
        risk_report[prod] = {
            "inventory_days": inv_days,
            "disruption_p5": d_p5,
            "disruption_p95": d_p95,
            "gap_p5": float(np.percentile(gap_days_dist, 5)),
            "gap_p95": float(np.percentile(gap_days_dist, 95)),
            "days_uncovered_avg": float(np.mean(gap_days_dist)),
            "loss_p5": float(np.percentile(loss_dist, 5)), 
            "loss_p50": float(np.percentile(loss_dist, 50)), 
            "loss_p95": float(np.percentile(loss_dist, 95))
        }
        
    return {
        "total_p5": float(np.percentile(total_loss_samples, 5)),
        "total_expected": float(np.mean(total_loss_samples)),
        "total_p95": float(np.percentile(total_loss_samples, 95)),
        "details": risk_report
    }

# ==========================================
# 4. AGENTS
# ==========================================
class AuditReport(BaseModel):
    hallucination_check: bool; math_check: bool; faithfulness_score: int; is_safe_to_present: bool

class AgentState(TypedDict):
    input_news: str; verification_log: str; detected_entity: Optional[str]; detected_event: str
    event_severity: float; impacted_products: List[str]; risk_calculations: dict
    recommended_action: str; audit_report: Optional[AuditReport]

def sentinel_agent(state: AgentState):
    print(f"📡 SENTINEL: Scanning '{state['input_news']}'...")
    nasa_data = check_nasa_eonet()
    tavily_data = verify_with_tavily(state['input_news'])
    context = f"{tavily_data}\nNASA: {str(nasa_data)[:50]}..."
    
    entity, event = "Unknown", "Unknown"
    
    # --- UPDATED MOCK LOGIC: Prioritize Locations before Generic Events ---
    news = state['input_news'].lower()
    
    # 1. Prioritize Specific Locations/Partners (check locations first)
    if "rocky mount" in news:
        entity = "PharmaCorp_C_Tier1"
        if "tornado" in news:
            event = "EF3 Tornado (Direct Hit)"
        elif "hurricane" in news or "flood" in news:
            event = "Hurricane Flooding"
        elif "fire" in news:
            event = "Factory Fire"
        else:
            event = "Production Disruption"
            
    elif "north cove" in news:
        entity = "PharmaCorp_B_Tier1"
        if "hurricane" in news or "helene" in news or "flood" in news:
            event = "Hurricane Flooding"
        elif "fire" in news:
            event = "Factory Fire"
        elif "tornado" in news:
            event = "Tornado Damage"
        else:
            event = "Production Disruption"
            
    elif "north carolina" in news or ("nc" in news and "carolina" in news):
        # Generic North Carolina - check for specific cities
        if "rocky mount" in news:
            entity = "PharmaCorp_C_Tier1"
            if "tornado" in news:
                event = "EF3 Tornado (Direct Hit)"
            elif "fire" in news:
                event = "Factory Fire"
            elif "hurricane" in news:
                event = "Hurricane Impact"
            else:
                event = "Production Disruption"
        else:
            # Default to North Cove (Partner B) for generic NC
            entity = "PharmaCorp_B_Tier1"
            if "hurricane" in news or "helene" in news or "flood" in news:
                event = "Hurricane Flooding"
            elif "fire" in news:
                event = "Factory Fire"
            elif "tornado" in news:
                event = "Tornado Damage"
            else:
                event = "Production Disruption"
            
    elif "rotterdam" in news or ("port" in news and "eu" in news):
        entity = "EU_Logistics"
        if "strike" in news:
            event = "Port Strike"
        elif "fire" in news:
            event = "Port Facility Fire"
        elif "hurricane" in news:
            event = "Severe Weather Disruption"
        else:
            event = "Logistics Disruption"
            
    elif "nj" in news or "mock town" in news or "car-t" in news or "biotherapy" in news or "jersey" in news:
        entity = "PharmaCorp_A_Internal"
        if "fire" in news:
            event = "Internal Facility Fire"
        elif "hurricane" in news or "flood" in news:
            event = "Hurricane Impact"
        elif "tornado" in news:
            event = "Tornado Damage"
        elif "logistics" in news or "truck" in news:
            event = "Internal Logistics Failure"
        else:
            event = "Internal Production Disruption"
    
    # 2. Fallback to Generic Regions/Types (only if no specific location found)
    elif "india" in news or "mumbai" in news:
        entity = "PharmaCorp_D_Tier2"
        if "fire" in news:
            event = "Factory Fire"
        elif "hurricane" in news:
            event = "Monsoon Flooding"
        else:
            event = "Production Disruption"
            
    elif "fire" in news:
        # Generic fire defaults to Tier 2 if no other location found
        entity = "PharmaCorp_D_Tier2"
        event = "Factory Fire (Generic)"
        
    real_entity = fuzzy_find_entity(entity, KG)
    if not real_entity: real_entity = fuzzy_find_entity(state['input_news'], KG)
    
    # If still no entity found, set to None (will be caught by auditor)
    if not real_entity:
        print("   ⚠️ No graph node matched. Alert will be blocked by auditor.")
        return {"detected_entity": None, "detected_event": "Unknown", "event_severity": 0.0, "verification_log": context}
    
    return {"detected_entity": real_entity, "detected_event": event, "event_severity": 0.0, "verification_log": context}

def detective_agent(state):
    if not state['detected_entity']: return {"impacted_products": []}
    
    impacted = []
    # Depth 4 to catch deep Tier 2 impact
    for u, v in list(nx.bfs_edges(KG, state['detected_entity'], depth_limit=4)):
        if KG.nodes[v].get('type', '').startswith('Product'): 
            impacted.append(v)
    
    # Sort for consistent display X, Y, Z
    def product_sort_key(name):
        if '_X_' in name: return 0
        if '_Y_' in name: return 1
        return 2
    return {"impacted_products": sorted(impacted, key=product_sort_key)}

def quantifier_agent(state):
    if not state['impacted_products']: return {"risk_calculations": {"total_expected": 0, "details": {}}}
    return {"risk_calculations": predict_financial_impact_range(
        state['impacted_products'], 
        state['detected_event'],
        state['detected_entity'], 
        KG
    )}

def strategist_agent(state):
    loss = state.get('risk_calculations', {}).get('total_expected', 0)
    event = state.get('detected_event', '')
    if "Tornado" in event: action = "CRITICAL: Partner C Facility Lost. Activate emergency allocation. Seek FDA waiver."
    elif "Flooding" in event: action = "CRITICAL: Commodity Shortage. Secure allocation for Product X."
    elif loss > 1_000_000: action = f"HIGH RISK: Expected Impact ${loss:,.0f}. Expedite shipment from Tier 2."
    else: action = "SAFE: Inventory covers disruption."
    return {"recommended_action": action}

def auditor_agent(state):
    """
    Validates the agent output before presentation.
    Safety checks:
    1. Entity must be grounded to knowledge graph (not None/Unknown)
    2. Entity must exist in the graph
    3. Risk calculations must be valid (non-empty if products exist)
    """
    # Check 1: Entity grounding (hallucination check)
    detected_entity = state.get('detected_entity')
    entity_grounded = detected_entity is not None and detected_entity != "Unknown" and detected_entity in KG.nodes()
    
    # Check 2: Event must be detected (not "Unknown")
    detected_event = state.get('detected_event', 'Unknown')
    event_valid = detected_event != "Unknown"
    
    # Check 3: Math integrity - risk calculations should exist and be valid
    risk_calc = state.get('risk_calculations', {})
    math_valid = True
    if risk_calc:
        # Check if risk calculations have expected structure
        if 'total_expected' not in risk_calc or 'details' not in risk_calc:
            math_valid = False
        # Check if details are valid
        if risk_calc.get('details'):
            for prod, details in risk_calc['details'].items():
                if not isinstance(details, dict) or 'loss_p50' not in details:
                    math_valid = False
                    break
    
    # Overall safety: All checks must pass
    is_safe = entity_grounded and event_valid and math_valid
    
    # Calculate faithfulness score (0-5 scale)
    faithfulness_score = 0
    if entity_grounded: faithfulness_score += 2
    if event_valid: faithfulness_score += 1
    if math_valid: faithfulness_score += 2
    
    return {
        "audit_report": AuditReport(
            hallucination_check=entity_grounded,
            math_check=math_valid,
            faithfulness_score=faithfulness_score,
            is_safe_to_present=is_safe
        )
    }

def check_audit(state) -> Literal["approved", "retry"]:
    """
    Conditional edge function: always approves to allow workflow to complete.
    The dashboard will check is_safe_to_present and block unsafe results from display.
    This prevents infinite retry loops while still allowing the audit to mark unsafe results.
    """
    # Always approve to complete workflow - dashboard will handle blocking unsafe results
    return "approved"

def build_workflow():
    wf = StateGraph(AgentState)
    wf.add_node("sentinel", sentinel_agent); wf.add_node("detective", detective_agent)
    wf.add_node("quantifier", quantifier_agent); wf.add_node("strategist", strategist_agent)
    wf.add_node("auditor", auditor_agent)
    wf.set_entry_point("sentinel")
    wf.add_edge("sentinel", "detective"); wf.add_edge("detective", "quantifier")
    wf.add_edge("quantifier", "strategist"); wf.add_edge("strategist", "auditor")
    wf.add_conditional_edges("auditor", check_audit, {"approved": END, "retry": "sentinel"})
    return wf.compile()