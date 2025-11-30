# Standard library imports
import json
import os
import re
from typing import List, TypedDict, Optional, Literal
import difflib
import yaml

# Third-party imports
import numpy as np
import networkx as nx
import requests
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# ==========================================
# CONFIGURATION LOADING
# ==========================================
def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config YAML file. If None, uses default 'config.yaml' in project root.
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Default to config.yaml in project root (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"⚠️ Warning: Config file not found at {config_path}. Using default hardcoded config.")
        return {}
    except yaml.YAMLError as e:
        print(f"⚠️ Warning: Error parsing YAML config: {e}. Using default hardcoded config.")
        return {}

# Load configuration early so it's available for graph building
_CONFIG = load_config() or {}
INVENTORY_OVERRIDES = _CONFIG.get("inventory_overrides", {}) or {}

# --- CONFIGURATION ---
# Auto-detect if real LLM should be used based on API key presence
# Can be overridden by environment variable USE_REAL_LLM=true/false
USE_REAL_LLM_ENV = os.environ.get("USE_REAL_LLM", "").lower()
if USE_REAL_LLM_ENV == "true":
    USE_REAL_LLM = True
elif USE_REAL_LLM_ENV == "false":
    USE_REAL_LLM = False
else:
    # Auto-detect: enable if GOOGLE_API_KEY is present
    USE_REAL_LLM = bool(os.environ.get("GOOGLE_API_KEY"))

DEFAULT_DISRUPTION_DAYS = 60 
np.random.seed(42)

# Initialize Gemini 2.5 Flash for performance
llm = None
if USE_REAL_LLM:
    try:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if google_api_key and google_api_key != "your_google_api_key_here":
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
        else:
            USE_REAL_LLM = False
            llm = None
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize Gemini LLM: {e}")
        USE_REAL_LLM = False
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
    # Use inventory override from config if available
    product_x_inv = INVENTORY_OVERRIDES.get("Product_X_BioTherapy", 0)
    G.add_node("Product_X_BioTherapy", type="Product (Finished)", revenue_annual=500_000_000, inventory_weeks=product_x_inv)
    
    # Product Y = Sterile Injectable - Low Inventory
    product_y_inv = INVENTORY_OVERRIDES.get("Product_Y_Sterile", 2)
    G.add_node("Product_Y_Sterile", type="Product (Component)", revenue_annual=1_200_000_000, inventory_weeks=product_y_inv)
    
    # Product Z = Critical Commodity (Saline proxy) - Reduced to 2 weeks for demo
    product_z_inv = INVENTORY_OVERRIDES.get("Product_Z_Commodity", 2)
    G.add_node("Product_Z_Commodity", type="Product (Component)", revenue_annual=300_000_000, inventory_weeks=product_z_inv)
    
    # --- INGREDIENTS ---
    # Reduced Buffers to ensure even moderate delays cause impact (2-4 weeks max)
    # Use inventory override from config if available
    biotherapy_raw_inv = INVENTORY_OVERRIDES.get("BioTherapy_Raw", 4)
    G.add_node("BioTherapy_Raw", type="Ingredient", inventory_weeks=biotherapy_raw_inv)
    api_raw_inv = INVENTORY_OVERRIDES.get("API_Generic_Raw", 4)
    G.add_node("API_Generic_Raw", type="Ingredient", inventory_weeks=api_raw_inv)

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
# 2. ENTITY MATCHING CONFIGURATION
# ==========================================
# Data-driven configuration for entity matching
# This replaces hardcoded keyword matching with a maintainable structure

class EntityMatcher:
    """
    Professional entity matching system that uses graph structure and configurable keyword mappings.
    Provides priority-based matching with conflict resolution.
    """
    
    def __init__(self, graph):
        self.graph = graph
        self.entity_keywords = self._build_entity_keyword_map()
        self.conflict_patterns = self._build_conflict_patterns()
        self.fuzzy_cutoff = 0.6  # String similarity threshold
    
    def _build_entity_keyword_map(self):
        """
        Build keyword mapping from graph structure and known entity aliases.
        Returns: dict mapping entity_id -> list of keyword patterns
        """
        # Extract location-entity relationships from graph
        location_entity_map = {}
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            if node_data.get('type') in ['Internal Mfg', 'Partner (Tier 1)', 'Partner (Tier 2)', 'Logistics Partner']:
                # Find associated location
                for neighbor in self.graph.predecessors(node):
                    neighbor_data = self.graph.nodes.get(neighbor, {})
                    if neighbor_data.get('type') == 'Location':
                        location_name = neighbor.lower().replace('_', ' ')
                        location_entity_map[node] = location_name.split()
        
        # Define keyword patterns for each entity
        # Priority: specific keywords first, then location-based, then product-based
        return {
            "PharmaCorp_A_Internal": {
                "primary_keywords": ["mock town", "car-t", "cart", "biotherapy"],
                "location_keywords": ["nj", "jersey", "new jersey"],
                "product_keywords": [],
                "conflict_exclusions": ["new york"]  # Don't match if these are present
            },
            "PharmaCorp_B_Tier1": {
                "primary_keywords": ["north cove", "iv fluid"],
                "location_keywords": ["north carolina", "nc"],
                "product_keywords": [],
                "conflict_exclusions": ["rocky mount"]  # Rocky Mount takes priority
            },
            "PharmaCorp_C_Tier1": {
                "primary_keywords": ["rocky mount"],
                "location_keywords": ["north carolina", "nc"],
                "product_keywords": [],
                "conflict_exclusions": []
            },
            "PharmaCorp_D_Tier2": {
                "primary_keywords": ["mumbai"],
                "location_keywords": ["india"],
                "product_keywords": [],
                "conflict_exclusions": ["new"]  # Avoid matching "New York" to "New India"
            },
            "EU_Logistics": {
                "primary_keywords": ["rotterdam"],
                "location_keywords": ["netherlands"],
                "product_keywords": [],
                "conflict_exclusions": []
            }
        }
    
    def _build_conflict_patterns(self):
        """
        Define patterns that should prevent matching to avoid false positives.
        Returns: dict mapping entity -> list of exclusion patterns
        """
        return {
            "north carolina": {
                "specificity_order": ["rocky mount", "north cove"],
                "default": "PharmaCorp_B_Tier1"  # Default if no specific city
            }
        }
    
    def _has_conflict(self, query: str, entity_id: str) -> bool:
        """Check if query contains patterns that should exclude this entity match."""
        entity_config = self.entity_keywords.get(entity_id, {})
        exclusions = entity_config.get("conflict_exclusions", [])
        
        for exclusion in exclusions:
            if exclusion.lower() in query.lower():
                return True
        return False
    
    def _matches_keywords(self, query: str, entity_id: str) -> bool:
        """Check if query matches any keywords for this entity."""
        if entity_id not in self.entity_keywords:
            return False
        
        config = self.entity_keywords[entity_id]
        query_lower = query.lower()
        
        # Check primary keywords (highest priority)
        for keyword in config.get("primary_keywords", []):
            if keyword.lower() in query_lower:
                return True
        
        # Check location keywords
        location_matched = False
        for keyword in config.get("location_keywords", []):
            if keyword.lower() in query_lower:
                location_matched = True
                break
        
        # For location-based matching, also check conflict exclusions
        if location_matched and self._has_conflict(query, entity_id):
            return False
        
        return location_matched
    
    def find_entity(self, query: str) -> Optional[str]:
        """
        Find the best matching entity for a given query.
        
        Args:
            query: Text query to match against entities
            
        Returns:
            Entity ID if match found, None otherwise
        """
        if not query or query == "Unknown":
            return None
        
        query_lower = query.lower()
        
        # Priority 1: Specific keyword matching (highest confidence)
        for entity_id, config in self.entity_keywords.items():
            if self._matches_keywords(query_lower, entity_id):
                # Verify entity exists in graph
                if entity_id in self.graph.nodes():
                    return entity_id
        
        # Priority 2: Handle region-level conflicts (e.g., "North Carolina" -> check for specific cities)
        conflict_config = self.conflict_patterns.get("north carolina", {})
        if "north carolina" in query_lower or ("nc" in query_lower and "carolina" in query_lower):
            specificity_order = conflict_config.get("specificity_order", [])
            for specific_location in specificity_order:
                if specific_location.lower() in query_lower:
                    # Find entity for specific location
                    for entity_id in self.entity_keywords:
                        if specific_location.lower() in " ".join(
                            self.entity_keywords[entity_id].get("primary_keywords", [])
                        ):
                            if entity_id in self.graph.nodes():
                                return entity_id
            
            # Use default if no specific city found
            default_entity = conflict_config.get("default")
            if default_entity and default_entity in self.graph.nodes():
                return default_entity
        
        # Priority 3: Fuzzy string matching against graph node names (lowest confidence)
        # Only use if query is very similar to a node name to prevent false positives
        node_names = list(self.graph.nodes())
        matches = difflib.get_close_matches(query, node_names, n=1, cutoff=self.fuzzy_cutoff)
        
        if matches:
            matched_node = matches[0]
            # Only return if it's an entity node (not a location, product, or ingredient)
            node_data = self.graph.nodes[matched_node]
            node_type = node_data.get('type', '')
            if any(entity_type in node_type for entity_type in 
                   ['Internal Mfg', 'Partner', 'Logistics']):
                return matched_node
        
        return None

# Initialize entity matcher with the knowledge graph
_entity_matcher = None

def _get_entity_matcher():
    """Get or create the singleton entity matcher instance."""
    global _entity_matcher
    if _entity_matcher is None:
        _entity_matcher = EntityMatcher(KG)
    return _entity_matcher

def fuzzy_find_entity(query, graph):
    """
    Find entity in graph using intelligent keyword and fuzzy matching.
    
    This is a wrapper that maintains backward compatibility while using
    the new professional EntityMatcher class.
    
    Args:
        query: Text query to match
        graph: NetworkX graph (for backward compatibility)
        
    Returns:
        Entity ID if found, None otherwise
    """
    matcher = _get_entity_matcher()
    return matcher.find_entity(query)

# ==========================================
# 3. TOOLS
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
    """
    Verify query with Tavily search API.
    Returns tuple of (message, search_count) where search_count is 1 if API key exists and search was made, 0 otherwise.
    """
    try:
        if os.environ.get("TAVILY_API_KEY"):
            results = TavilySearchResults(max_results=2).invoke(query)
            search_count = 1  # Tavily charges per search query
            return f"Tavily: Found {len(results)} sources.", search_count
    except: pass
    return "Tavily: Skipped (No Key).", 0

# ==========================================
# 3. CENTRALIZED EVENT & LOCATION CONFIGURATION
# ==========================================
# Load configuration from YAML file with fallback to defaults

def _load_event_types_from_config(config: dict) -> dict:
    """Load event types from config or use defaults."""
    if "event_types" in config:
        event_types = {}
        for event_name, event_config in config["event_types"].items():
            # Convert list [mean, sigma] to tuple (mean, sigma)
            disruption_days = tuple(event_config["disruption_days"]) if "disruption_days" in event_config else (45, 7)
            event_types[event_name] = {
                "keywords": event_config.get("keywords", []),
                "disruption_days": disruption_days,
                "description": event_config.get("description", event_name)
            }
        return event_types
    
    # Default hardcoded values if config not available
    return {
        "Tornado": {"keywords": ["tornado"], "disruption_days": (90, 15), "description": "Tornado"},
        "Hurricane": {"keywords": ["hurricane", "flood", "helene"], "disruption_days": (60, 10), "description": "Hurricane"},
        "Fire": {"keywords": ["fire", "explosion"], "disruption_days": (75, 14), "description": "Fire"},
        "Strike": {"keywords": ["strike", "labor"], "disruption_days": (45, 10), "description": "Strike"},
        "Logistics": {"keywords": ["logistics", "truck", "delivery", "shipping"], "disruption_days": (21, 5), "description": "Logistics"},
        "FDA": {"keywords": ["fda", "regulatory"], "disruption_days": (90, 30), "description": "FDA"},
        "Production Disruption": {"keywords": ["disruption", "production"], "disruption_days": (45, 7), "description": "Production Disruption"}
    }

def _load_location_entity_map_from_config(config: dict) -> dict:
    """Load location to entity mappings from config or use defaults."""
    if "location_entity_map" in config:
        return config["location_entity_map"]
    
    # Default hardcoded values
    return {
        "rocky mount": "PharmaCorp_C_Tier1",
        "north cove": "PharmaCorp_B_Tier1",
        "north carolina": "PharmaCorp_B_Tier1",
        "nc": "PharmaCorp_B_Tier1",
        "rotterdam": "EU_Logistics",
        "netherlands": "EU_Logistics",
        "port": "EU_Logistics",
        "nj": "PharmaCorp_A_Internal",
        "new jersey": "PharmaCorp_A_Internal",
        "jersey": "PharmaCorp_A_Internal",
        "mock town": "PharmaCorp_A_Internal",
        "india": "PharmaCorp_D_Tier2",
        "mumbai": "PharmaCorp_D_Tier2"
    }

def _load_location_event_descriptions_from_config(config: dict) -> dict:
    """Load location-specific event descriptions from config or use defaults."""
    if "location_event_descriptions" in config:
        # Convert nested dict to tuple-keyed dict for compatibility
        descriptions = {}
        for location, events in config["location_event_descriptions"].items():
            for event_type, description in events.items():
                descriptions[(location.lower(), event_type)] = description
        return descriptions
    
    # Default hardcoded values
    return {
        ("rocky mount", "Tornado"): "EF3 Tornado (Direct Hit)",
        ("rocky mount", "Hurricane"): "Hurricane Flooding",
        ("rocky mount", "Fire"): "Factory Fire",
        ("north cove", "Hurricane"): "Hurricane Flooding",
        ("north cove", "Fire"): "Factory Fire",
        ("north cove", "Tornado"): "Tornado Damage",
        ("north carolina", "Tornado"): "Tornado Damage",
        ("north carolina", "Hurricane"): "Hurricane Impact",
        ("north carolina", "Fire"): "Factory Fire",
        ("rotterdam", "Strike"): "Port Strike",
        ("rotterdam", "Fire"): "Port Facility Fire",
        ("rotterdam", "Hurricane"): "Severe Weather Disruption",
        ("port", "Strike"): "Port Strike",
        ("nj", "Fire"): "Internal Facility Fire",
        ("nj", "Hurricane"): "Hurricane Impact",
        ("nj", "Tornado"): "Tornado Damage",
        ("nj", "Logistics"): "Internal Logistics Failure",
        ("mock town", "Logistics"): "Internal Logistics Failure",
        ("india", "Fire"): "Factory Fire",
        ("india", "Strike"): "Labor Strike",
        ("india", "Hurricane"): "Monsoon Flooding",
        ("mumbai", "Fire"): "Factory Fire",
        ("mumbai", "Strike"): "Labor Strike",
    }

def _load_default_event_descriptions_from_config(config: dict) -> dict:
    """Load default event descriptions from config or use defaults."""
    if "default_event_descriptions" in config:
        return config["default_event_descriptions"]
    
    # Default hardcoded values
    return {
        "Tornado": "Tornado Damage",
        "Hurricane": "Hurricane Impact",
        "Fire": "Factory Fire",
        "Strike": "Labor Strike",
        "Logistics": "Logistics Disruption",
        "FDA": "Regulatory Hold",
        "Production Disruption": "Production Disruption"
    }

def _load_location_priority_from_config(config: dict) -> list:
    """Load location priority order from config or use defaults."""
    if "location_priority" in config:
        return config["location_priority"]
    
    # Default hardcoded values
    return [
        "rocky mount", "north cove", "mock town", "rotterdam", "mumbai",
        "north carolina", "nc", "new jersey", "jersey", "nj",
        "india", "netherlands", "port"
    ]

# Initialize configuration from YAML file
EVENT_TYPES = _load_event_types_from_config(_CONFIG)
LOCATION_ENTITY_MAP = _load_location_entity_map_from_config(_CONFIG)
LOCATION_EVENT_DESCRIPTIONS = _load_location_event_descriptions_from_config(_CONFIG)
DEFAULT_EVENT_DESCRIPTIONS = _load_default_event_descriptions_from_config(_CONFIG)
LOCATION_PRIORITY = _load_location_priority_from_config(_CONFIG)

def get_event_type_from_text(text: str) -> Optional[str]:
    """Detect event type from text using keyword matching."""
    text_lower = text.lower()
    for event_type, config in EVENT_TYPES.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                return event_type
    return None

def get_disruption_params(event_text: str) -> tuple:
    """Get disruption parameters (mean_days, sigma_days) for an event."""
    event_type = get_event_type_from_text(event_text)
    if event_type and event_type in EVENT_TYPES:
        return EVENT_TYPES[event_type]["disruption_days"]
    # Return default if no match
    return EVENT_TYPES["Production Disruption"]["disruption_days"]

def get_event_description(location_keyword: str, event_type: str) -> str:
    """Get location-specific event description, or fall back to default."""
    # Try exact location match first
    if (location_keyword.lower(), event_type) in LOCATION_EVENT_DESCRIPTIONS:
        return LOCATION_EVENT_DESCRIPTIONS[(location_keyword.lower(), event_type)]
    
    # Try default description
    if event_type in DEFAULT_EVENT_DESCRIPTIONS:
        return DEFAULT_EVENT_DESCRIPTIONS[event_type]
    
    # Final fallback
    return event_type

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
    token_usage: Optional[dict]  # Track API usage: {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int, "tavily_searches": int}

def sentinel_agent(state: AgentState):
    nasa_data = check_nasa_eonet()
    tavily_data, tavily_searches = verify_with_tavily(state['input_news'])
    context = f"{tavily_data}\nNASA: {str(nasa_data)[:50]}..."
    
    entity, event = "Unknown", "Unknown"
    llm_used = False
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "tavily_searches": tavily_searches}
    
    # Print Tavily usage if search was made (useful for API monitoring)
    if tavily_searches > 0:
        print(f"✅ Tavily API: {tavily_searches} search query/queries")
    
    # --- USE REAL LLM IF AVAILABLE ---
    if llm is not None and USE_REAL_LLM:
        try:
            prompt = f"""Extract the supply chain entity and event type from this news:
"{state['input_news']}"

Available entities in our supply chain (ONLY match if location matches):
- PharmaCorp_A_Internal (Mock Town, New Jersey, NJ)
- PharmaCorp_B_Tier1 (North Cove, North Carolina, NC)
- PharmaCorp_C_Tier1 (Rocky Mount, North Carolina, NC)
- PharmaCorp_D_Tier2 (Mumbai, India)
- EU_Logistics (Rotterdam, Netherlands, EU)

IMPORTANT: If the location in the news does NOT match any of the above locations, return "Unknown" for entity.
Only match entities when the location explicitly matches (e.g., "New York" should return "Unknown", not any of the above entities).

Respond in JSON format only, no other text:
{{"entity": "entity_name_or_Unknown", "event": "event_description"}}"""

            response = llm.invoke(prompt)
            llm_used = True  # Mark that LLM was actually invoked
            
            # Extract token usage from response
            # Google Generative AI stores token usage in response.usage_metadata
            # Format: {'input_tokens': int, 'output_tokens': int, 'total_tokens': int}
            # Based on debug output, this is where the data is located
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    if isinstance(usage, dict):
                        # Direct extraction - Google Generative AI uses input_tokens/output_tokens
                        token_usage = {
                            "prompt_tokens": int(usage.get('input_tokens', 0)),
                            "completion_tokens": int(usage.get('output_tokens', 0)),
                            "total_tokens": int(usage.get('total_tokens', 0)),
                            "tavily_searches": tavily_searches
                        }
                        if token_usage["total_tokens"] > 0:
                            print(f"✅ Gemini API: {token_usage['prompt_tokens']} prompt + {token_usage['completion_tokens']} completion = {token_usage['total_tokens']} total tokens")
            except Exception as e:
                print(f"⚠️ Error extracting token usage: {e}")
                # Keep default zero values
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to parse JSON response
            try:
                # Extract JSON from response if wrapped in markdown code blocks
                if '```' in content:
                    json_str = content.split('```')[1].replace('json', '').strip()
                    # Remove markdown code block markers
                    json_str = re.sub(r'^```json\s*', '', json_str)
                    json_str = re.sub(r'\s*```$', '', json_str)
                else:
                    # Try to find JSON object in the response
                    json_match = re.search(r'\{[^{}]*"entity"[^{}]*\}', content)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = content.strip()
                
                parsed = json.loads(json_str)
                entity = parsed.get('entity', 'Unknown')
                event = parsed.get('event', 'Unknown')
                
                # If LLM successfully extracted, use it even if event is generic
                # Only use fallback if BOTH are Unknown (meaning LLM completely failed)
                if entity != "Unknown":
                    # LLM found an entity, trust it even if event parsing had issues
                    if event == "Unknown":
                        # Event parsing failed, but entity is good - extract event from original text using config
                        event_type = get_event_type_from_text(state['input_news'])
                        if event_type:
                            event = event_type
                        else:
                            event = "Production Disruption"
            except json.JSONDecodeError:
                # Keep entity/event as Unknown to use fallback
                pass
            except Exception:
                # Keep entity/event as Unknown to use fallback
                pass
        except Exception:
            # Fall back to keyword matching on error
            pass
    
    # Only use fallback if LLM wasn't used OR if LLM completely failed (both Unknown)
    # If LLM extracted entity successfully, don't override with mock logic
    use_fallback = not llm_used or (entity == "Unknown" and event == "Unknown")
    
    # --- FALLBACK: MOCK LOGIC (keyword matching using centralized config) ---
    # Use mock logic only if LLM wasn't used or completely failed
    if use_fallback:
        news = state['input_news'].lower()
        matched_location = None
        
        # 1. Find matching location (prioritize specific locations first)
        # Check in priority order: specific cities > states > countries
        for loc_keyword in LOCATION_PRIORITY:
            if loc_keyword in news:
                matched_location = loc_keyword
                if loc_keyword in LOCATION_ENTITY_MAP:
                    entity = LOCATION_ENTITY_MAP[loc_keyword]
                    break
        
        # Handle special cases
        if "north carolina" in news or ("nc" in news and "carolina" in news):
            if "rocky mount" in news:
                matched_location = "rocky mount"
                entity = LOCATION_ENTITY_MAP["rocky mount"]
            else:
                matched_location = "north carolina"
                entity = LOCATION_ENTITY_MAP["north carolina"]
        elif "car-t" in news or "biotherapy" in news or ("cart" in news and "mock" not in news):
            matched_location = "mock town"
            entity = LOCATION_ENTITY_MAP["mock town"]
        elif ("port" in news and ("rotterdam" in news or "eu" in news)) or "netherlands" in news:
            matched_location = "rotterdam"
            entity = LOCATION_ENTITY_MAP["rotterdam"]
        
        # 2. Detect event type from text
        if matched_location:
            event_type = get_event_type_from_text(news)
            if event_type:
                # Get location-specific event description
                event = get_event_description(matched_location, event_type)
            else:
                event = DEFAULT_EVENT_DESCRIPTIONS.get("Production Disruption", "Production Disruption")
        elif "fire" in news:
            # Generic fire with unknown location
            entity = "Unknown"
            event = "Fire (Unknown Location)"
        else:
            # Try to match generic event and see if we can infer location
            event_type = get_event_type_from_text(news)
            if event_type:
                event = DEFAULT_EVENT_DESCRIPTIONS.get(event_type, event_type)
    
    # Use fuzzy matching to find the actual graph node
    # Only try fuzzy matching if entity is not Unknown
    if entity != "Unknown":
        real_entity = fuzzy_find_entity(entity, KG)
    else:
        # If entity is Unknown, try fuzzy matching on the original input
        # but this should only match if it's actually in our supply chain
        real_entity = fuzzy_find_entity(state['input_news'], KG)
        if not real_entity:
            print(f"⚠️ No matching entity found for: {state['input_news']}")
    
    # If still no entity found, set to None (will be caught by auditor)
    if not real_entity:
        print("⚠️ No graph node matched. Alert will be blocked by auditor.")
        return {"detected_entity": None, "detected_event": "Unknown", "event_severity": 0.0, "verification_log": context, "token_usage": token_usage}
    
    return {"detected_entity": real_entity, "detected_event": event, "event_severity": 0.0, "verification_log": context, "token_usage": token_usage}

def detective_agent(state):
    if not state['detected_entity']: return {"impacted_products": [], "token_usage": state.get('token_usage', {})}
    
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
    return {"impacted_products": sorted(impacted, key=product_sort_key), "token_usage": state.get('token_usage', {})}

def quantifier_agent(state):
    if not state['impacted_products']: return {"risk_calculations": {"total_expected": 0, "details": {}}, "token_usage": state.get('token_usage', {})}
    return {
        "risk_calculations": predict_financial_impact_range(
            state['impacted_products'], 
            state['detected_event'],
            state['detected_entity'], 
            KG
        ),
        "token_usage": state.get('token_usage', {})
    }

def strategist_agent(state):
    loss = state.get('risk_calculations', {}).get('total_expected', 0)
    event = state.get('detected_event', '')
    if "Tornado" in event: action = "CRITICAL: Partner C Facility Lost. Activate emergency allocation. Seek FDA waiver."
    elif "Flooding" in event: action = "CRITICAL: Commodity Shortage. Secure allocation for Product X."
    elif loss > 1_000_000: action = f"HIGH RISK: Expected Impact ${loss:,.0f}. Expedite shipment from Tier 2."
    else: action = "SAFE: Inventory covers disruption."
    return {"recommended_action": action, "token_usage": state.get('token_usage', {})}

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
        ),
        "token_usage": state.get('token_usage', {})
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