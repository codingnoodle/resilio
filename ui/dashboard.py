import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import sys
import os
import re
import networkx as nx

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.resilio_core import build_workflow, KG, USE_REAL_LLM

def format_entity_name(entity_name: str) -> str:
    if not entity_name or entity_name == "None": return "Unknown Entity"
    entity_display_map = {
        "PharmaCorp_A_Internal": "PharmaCorp A (Internal)",
        "PharmaCorp_B_Tier1": "PharmaCorp B (Tier 1 Partner)",
        "PharmaCorp_C_Tier1": "PharmaCorp C (Tier 1 Partner)",
        "PharmaCorp_D_Tier2": "PharmaCorp D (Tier 2 Partner)",
        "EU_Logistics": "EU Logistics",
        "BioTherapy_Raw": "BioTherapy Precursor",
        "API_Generic_Raw": "Generic API Raw Material",
        "Viral_Vector_Raw": "BioTherapy Precursor",
    }
    if entity_name in entity_display_map: return entity_display_map[entity_name]
    formatted = entity_name.replace("_", " ").title()
    for old, new in {'Nj': 'NJ', 'Nc': 'NC', 'Usa': 'USA', 'Eu': 'EU'}.items():
        formatted = formatted.replace(old, new)
    return formatted

def format_location_name(location_name: str) -> str:
    """Format location node names for display"""
    if not location_name: return "Unknown"
    location_display_map = {
        "Mock_Town_NJ_USA": "Mock Town, NJ",
        "North_Cove_NC_USA": "North Cove, NC",
        "Rocky_Mount_NC_USA": "Rocky Mount, NC",
        "Mumbai_Zone_A": "Mumbai, India",
        "Rotterdam_Port_EU": "Rotterdam, EU",
    }
    if location_name in location_display_map:
        return location_display_map[location_name]
    return location_name.replace("_", " ").title()

def format_product_name(product_name: str) -> str:
    if not product_name: return "Unknown"
    # Map to display names
    product_display_map = {
        "Product_X_BioTherapy": "Product X BioTherapy",
        "Product_Y_Sterile": "Product Y Sterile",
        "Product_Z_Commodity": "Product Z Commodity"
    }
    if product_name in product_display_map:
        return product_display_map[product_name]
    return product_name.replace("_", " ").title()

def metric_card(label, value, delta=None, delta_color="normal"):
    delta_html = ""
    if delta:
        color = "#2ca02c" if delta_color == "normal" else "#d62728"
        if delta_color == "inverse": color = "#d62728"
        delta_html = f"<span style='font-size: 0.8rem; color: {color};'>{delta}</span>"
    
    st.markdown(f"""
    <div style="border: 1px solid #e6e6e6; border-radius: 5px; padding: 10px; margin-bottom: 10px; background-color: #ffffff;">
        <div style="font-size: 0.8rem; color: #666;">{label}</div>
        <div style="font-size: 1.1rem; font-weight: 600; line-height: 1.2; margin-top: 4px;">{value}</div>
        <div style="margin-top: 4px;">{delta_html}</div>
    </div>
    """, unsafe_allow_html=True)

def plot_sankey(state):
    details = state['risk_calculations'].get('details', {})
    if not details: return go.Figure().update_layout(title="No Impact Detected")
    
    supplier = state['detected_entity']
    event = state['detected_event']
    
    def product_sort_key(name):
        if '_X_' in name: return 0
        if '_Y_' in name: return 1
        return 2
    
    product_list = sorted(details.keys(), key=product_sort_key)
    label_list = [event, supplier] + product_list + ["Financial Loss"]
    label_map = {name: i for i, name in enumerate(label_list)}
    
    sources, targets, values, colors = [], [], [], []
    
    # Event -> Supplier
    sources.append(label_map[event]); targets.append(label_map[supplier]); values.append(10); colors.append("lightgrey")
    
    for prod in product_list:
        sources.append(label_map[supplier]); targets.append(label_map[prod]); values.append(5)
        is_risk = details[prod]['days_uncovered_avg'] > 0
        colors.append("rgba(255, 50, 50, 0.8)" if is_risk else "rgba(50, 200, 50, 0.4)")
        if is_risk:
            sources.append(label_map[prod]); targets.append(label_map["Financial Loss"])
            values.append(max(1, details[prod]['loss_p50'] / 100000))
            colors.append("rgba(200, 0, 0, 0.8)")

    wrapped_labels = []
    for label in label_list:
        if label == supplier: wrapped_labels.append(format_entity_name(label))
        elif label in product_list: wrapped_labels.append(format_product_name(label))
        else: wrapped_labels.append(label)
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=20, thickness=20, line=dict(color="black", width=0.5), label=wrapped_labels, hovertemplate='%{label}<extra></extra>'),
        link=dict(source=sources, target=targets, value=values, color=colors))])
    fig.update_layout(title="<b>Live Risk Contagion Path</b>", height=400, margin=dict(l=10,r=10,t=40,b=10))
    return fig

def plot_risk_ranges(state):
    details = state['risk_calculations'].get('details', {})
    if not details: return go.Figure()
    
    def product_sort_key(name):
        if '_X_' in name: return 0
        if '_Y_' in name: return 1
        return 2
    
    prods = sorted(details.keys(), key=product_sort_key)
    prod_labels = [format_product_name(p) for p in prods]
    p50 = [details[p]['loss_p50'] for p in prods]
    p5 = [details[p]['loss_p5'] for p in prods]
    p95 = [details[p]['loss_p95'] for p in prods]
    
    fig = go.Figure()
    
    # Vertical chart: products on x-axis, loss on y-axis
    # Add vertical lines (range bars) from P5 to P95
    for i, p in enumerate(prods):
        fig.add_trace(go.Scatter(
            x=[prod_labels[i], prod_labels[i]], 
            y=[p5[i], p95[i]], 
            mode='lines', 
            line=dict(color='black', width=3), 
            showlegend=False, 
            hoverinfo='skip'
        ))
    
    # Add markers: Worst Case (P95) at top, Expected (P50) in middle, Best Case (P5) at bottom
    # Order matters for legend: add in reverse order so Worst Case appears at top of legend
    fig.add_trace(go.Scatter(
        x=prod_labels, 
        y=p95, 
        mode='markers', 
        marker=dict(symbol='triangle-down', size=12, color='black'), 
        name="Worst Case (P95)"
    ))
    fig.add_trace(go.Scatter(
        x=prod_labels, 
        y=p50, 
        mode='markers', 
        marker=dict(size=14, color='indianred'), 
        name="Expected (P50)"
    ))
    fig.add_trace(go.Scatter(
        x=prod_labels, 
        y=p5, 
        mode='markers', 
        marker=dict(symbol='triangle-up', size=12, color='black'), 
        name="Best Case (P5)"
    ))
    
    fig.update_layout(
        title=dict(text="<b>Probabilistic Forecast (95% CI)</b>", x=0, xanchor='left'),  # Left-aligned title
        xaxis_title="Product",
        yaxis_title="USD Loss",
        height=350, 
        margin=dict(l=10, r=120, t=40, b=10),  # Increased right margin for vertical legend
        legend=dict(
            orientation="v",  # Vertical orientation
            x=1.02,  # Position on the right
            y=1,  # Top of the plot
            xanchor='left',  # Anchor to left edge of legend
            yanchor='top'  # Anchor to top
        )
    )
    return fig

def render_network_graph(graph, impacted_products=None, source_node=None):
    # Layout Logic
    for node, data in graph.nodes(data=True):
        ntype = data.get('type', 'Unknown')
        if ntype == 'Location': graph.nodes[node]['layer'] = 0
        elif any(x in ntype for x in ['Partner', 'Supplier', 'Internal', 'Logistics']): graph.nodes[node]['layer'] = 1
        elif 'Ingredient' in ntype: graph.nodes[node]['layer'] = 2
        elif 'Product' in ntype: graph.nodes[node]['layer'] = 3
        else: graph.nodes[node]['layer'] = 4
    
    pos = nx.multipartite_layout(graph, subset_key='layer', scale=2)
    
    # Path Highlighting Logic
    highlighted_edges = set()
    highlighted_nodes = set()
    root_location = None
    
    if source_node:
        highlighted_nodes.add(source_node)
        # 1. Location -> Supplier
        predecessors = list(graph.predecessors(source_node))
        for pred in predecessors:
            if graph.nodes[pred].get('type') == 'Location':
                highlighted_edges.add((pred, source_node))
                root_location = pred
                highlighted_nodes.add(pred)
                break
        
        # 2. Supplier -> Products (Shortest Path)
        if impacted_products:
            for prod in impacted_products:
                try:
                    path = nx.shortest_path(graph, source=source_node, target=prod)
                    for i in range(len(path)-1): 
                        highlighted_edges.add((path[i], path[i+1]))
                        highlighted_nodes.add(path[i])
                        highlighted_nodes.add(path[i+1])
                except: pass

    # Build Traces
    edge_x, edge_y, highlight_x, highlight_y = [], [], [], []
    highlight_hover_x, highlight_hover_y, highlight_hover_text = [], [], []  # Hover for highlighted edges
    mid_x, mid_y, mid_text = [], [], []  # For Hover on non-highlighted edges

    # Determine if we're in "active scenario" mode (case selected)
    is_active_scenario = source_node is not None

    for edge in graph.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        data = graph.get_edge_data(edge[0], edge[1])
        lead = data.get('lead_time_days', 0)
        
        # Determine if edge is active (part of disruption path)
        is_active = edge in highlighted_edges
        
        # Clean names for tooltip
        # Format names based on node type
        src_type = graph.nodes[edge[0]].get('type', '')
        tgt_type = graph.nodes[edge[1]].get('type', '')
        src_name = format_location_name(edge[0]) if 'Location' in src_type else format_entity_name(edge[0])
        tgt_name = format_location_name(edge[1]) if 'Location' in tgt_type else format_entity_name(edge[1])
        
        # Contextual tooltip: show IMPACT PATH for active edges
        status_text = "⚠️ <b>IMPACT PATH</b>" if is_active else "Standard Flow"
        
        # Contextual Labeling: Specific text for Location edges
        source_type = graph.nodes[edge[0]].get('type', 'Unknown')
        if source_type == 'Location':
            # Location -> Supplier edges: explain why 0 days
            time_info = "<b>Status:</b> Site Located Here<br><b>Lead Time:</b> 0 Days (Static)"
        else:
            # Other edges: show lead time with bold formatting
            time_info = f"<b>Lead Time:</b> {lead} Days"
        
        tooltip_text = f"{status_text}<br>{src_name} → {tgt_name}<br>{time_info}"

        # Visuals
        if is_active:
            # Highlighted path (red, thick) - only when scenario is active
            highlight_x.extend([x0, x1, None]); highlight_y.extend([y0, y1, None])
            # Add multiple hover markers along the edge for better interaction (avoid overlap issues)
            # Use 3 points: 25%, 50%, 75% along the edge
            for frac in [0.25, 0.5, 0.75]:
                mx = x0 + (x1 - x0) * frac
                my = y0 + (y1 - y0) * frac
                highlight_hover_x.append(mx)
                highlight_hover_y.append(my)
                highlight_hover_text.append(tooltip_text)
        else:
            # Non-highlighted edges - ALWAYS add hover markers for ALL edges (except product-product)
            source_type = graph.nodes[edge[0]].get('type', '')
            target_type = graph.nodes[edge[1]].get('type', '')
            # Filter product-product edges to reduce clutter
            if not ('Product' in source_type and 'Product' in target_type):
                # Always show the edge line
                edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
                # Add multiple hover markers along the edge for better interaction (avoid overlap issues)
                # Use 3 points: 25%, 50%, 75% along the edge
                for frac in [0.25, 0.5, 0.75]:
                    mx = x0 + (x1 - x0) * frac
                    my = y0 + (y1 - y0) * frac
                    mid_x.append(mx)
                    mid_y.append(my)
                    mid_text.append(tooltip_text)

    # Edge styling based on scenario state
    if is_active_scenario:
        # Faint Background Edges (non-impacted)
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#eee'), hoverinfo='none', mode='lines')
    else:
        # Normal Edges (all visible, no scenario selected)
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#ccc'), hoverinfo='none', mode='lines')
    
    # Active Path Edges (Red) - only shown when scenario is active
    highlight_trace = go.Scatter(x=highlight_x, y=highlight_y, line=dict(width=3, color='red'), hoverinfo='none', mode='lines')
    
    # Separate hover trace for highlighted edges (on top, larger size for easy interaction)
    # Fully transparent markers - invisible but provide hover interaction
    highlight_hover_trace = go.Scatter(
        x=highlight_hover_x, y=highlight_hover_y, mode='markers', text=highlight_hover_text, hoverinfo='text',
        marker=dict(size=40, color='rgba(0,0,0,0)', line=dict(width=0)), showlegend=False,  # Fully transparent, large for easy hover
        hovertemplate='%{text}<extra></extra>'
    )
    
    # Hover markers for non-highlighted edges (ALWAYS create, even if empty, to avoid errors)
    # Fully transparent markers - invisible but provide hover interaction
    edge_hover_trace = go.Scatter(
        x=mid_x if mid_x else [None], y=mid_y if mid_y else [None], mode='markers', text=mid_text if mid_text else [''], hoverinfo='text',
        marker=dict(size=40, color='rgba(0,0,0,0)', line=dict(width=0)), showlegend=False,  # Fully transparent, large for easy hover
        hovertemplate='%{text}<extra></extra>'
    )
    
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    color_map = {'Location': '#1f77b4', 'Supplier': '#2ca02c', 'Product': '#ff7f0e', 'Ingredient': '#9467bd'}

    for node in graph.nodes():
        x, y = pos[node]; node_x.append(x); node_y.append(y)
        data = graph.nodes[node]; ntype = data.get('type', 'Unknown')
        
        # Color Logic: Grey out if not in path (only when scenario is active)
        if not source_node:  # No scenario selected: all nodes colorful
            is_active = True
        else:
            # Scenario active: only highlighted nodes are colorful
            is_active = node in highlighted_nodes
            
        base_c = '#gray'
        if 'Location' in ntype: base_c = color_map['Location']
        elif any(x in ntype for x in ['Partner', 'Supplier', 'Internal', 'Logistics']): base_c = color_map['Supplier']
        elif 'Product' in ntype: base_c = color_map['Product']
        elif 'Ingredient' in ntype: base_c = color_map['Ingredient']
        
        final_c = base_c if is_active else '#f0f0f0'  # Fade out
        if node == source_node or node == root_location: final_c = 'red'  # Root cause
        
        node_color.append(final_c)
        
        # Format node name based on type
        if 'Location' in ntype:
            node_display = format_location_name(node)
        else:
            node_display = format_entity_name(node)
        hover_info = f"<b>{node_display}</b><br>{ntype}"
        if 'revenue_annual' in data: hover_info += f"<br>💰 Rev: ${data['revenue_annual']:,.0f}"
        if 'inventory_weeks' in data: hover_info += f"<br>📦 Inv: {data['inventory_weeks']} wks"
        node_text.append(hover_info)
        size = 15
        if 'Product' in ntype: size = 15 + (data.get('revenue_annual', 0) / 100_000_000)
        node_size.append(min(size, 40))
    
    # Use a single line style for all markers (Plotly doesn't support per-marker line styles)
    # Active nodes will be distinguished by their red color, inactive by grey color
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', textposition="top center",
        text=[(format_location_name(n) if 'Location' in graph.nodes[n].get('type', '') else format_entity_name(n)) if n in highlighted_nodes or not source_node else "" for n in graph.nodes()],  # Only label active nodes
        textfont=dict(size=9, color='#333'),
        hoverinfo='text', hovertext=node_text,
        marker=dict(showscale=False, color=node_color, size=node_size, line=dict(color='white', width=2))
    )
    
    # Order matters: hover traces should be on top for better interaction
    # Put hover traces last so they're on top and clickable
    fig = go.Figure(data=[edge_trace, highlight_trace, highlight_hover_trace, edge_hover_trace, node_trace],
                    layout=go.Layout(
                        title='<b>Global Supply Chain Digital Twin</b>', showlegend=False,
                        hovermode='closest', margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), height=500))
    return fig

def plot_workflow_diagram():
    """
    Displays the multi-agent workflow diagram and agent descriptions side by side.
    """
    st.markdown("### 📊 Workflow Diagram")
    st.caption("Multi-agent workflow with conditional routing")
    
    # Create two columns for side-by-side layout
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        # Try to load SVG first (preferred for high quality), then PNG
        svg_path = os.path.join(os.path.dirname(__file__), "workflow_diagram.svg")
        png_path = os.path.join(os.path.dirname(__file__), "workflow_diagram.png")
        
        if os.path.exists(svg_path):
            try:
                # Streamlit can display SVG directly
                st.image(svg_path, caption="Resilio Multi-Agent Workflow", use_container_width=False)
            except Exception as e:
                st.warning(f"Could not load workflow diagram SVG: {e}")
                # Fall back to PNG if SVG fails
                if os.path.exists(png_path):
                    try:
                        from PIL import Image
                        img = Image.open(png_path)
                        st.image(img, caption="Resilio Multi-Agent Workflow", use_container_width=False)
                    except Exception as e2:
                        st.warning(f"Could not load PNG either: {e2}")
        elif os.path.exists(png_path):
            try:
                from PIL import Image
                img = Image.open(png_path)
                st.image(img, caption="Resilio Multi-Agent Workflow", use_container_width=False)
            except Exception as e:
                st.warning(f"Could not load workflow diagram image: {e}")
        else:
            st.info("💡 **To add the workflow diagram:** Save your workflow diagram as `workflow_diagram.svg` or `workflow_diagram.png` in the `ui/` folder")
            st.info("Workflow Architecture: START → Sentinel → Detective → Quantifier → Strategist → Auditor → (Approved → END | Retry → Sentinel)")
    
    with col2:
        # Show detailed description
        st.markdown("#### 📋 Agent Descriptions")
        st.markdown("""
        **1. 📡 Sentinel Agent** - Detect & Verify
        - Scans news input for supply chain disruptions
        - Uses LLM with Tavily (web search) and NASA EONET (geospatial verification)
        - Maps events to entities in the knowledge graph
        - Extracts: entity, event type, severity
        
        **2. 🕵️ Detective Agent** - Trace Impact
        - Traverses the knowledge graph using Breadth-First Search (BFS) to find impacted products
        - Explores connections level-by-level from the disrupted supplier to downstream products
        - Detects hidden dependencies (e.g., Saline → CAR-T)
        - Returns list of impacted products
        
        **3. 📊 Quantifier Agent** - Calculate Risk
        - Runs Monte Carlo simulation (1000 iterations)
        - Calculates financial risk ranges (P5, Expected, P95)
        - Computes inventory gap days
        - Returns probabilistic risk report
        
        **4. 🎯 Strategist Agent** - Recommend Action
        - Analyzes risk magnitude and event type
        - Generates recommended actions
        - Provides context-specific guidance
        
        **5. ⚖️ Auditor Agent** - Validate & Approve
        - Validates entity grounding (hallucination check)
        - Verifies math integrity
        - Approves or blocks results for presentation
        """)

def main_control_tower():
    st.set_page_config(page_title="Resilio Control Tower", layout="wide")
    st.markdown("## 🛡️ RESILIO: Supply Chain Control Tower")
    if USE_REAL_LLM: st.caption("🟢 **ONLINE:** Connected to Gemini + Tavily + NASA.")
    else: st.caption("🔒 **ZERO-DEPENDENCY MODE:** Running deterministic mock engine.")
    st.markdown("---")
    
    col_graph, col_controls = st.columns([2, 1])
    with col_controls:
        st.header("⚡ Scenario Injection")
        scenario = st.radio(
            "Select Case Study:",
            [
                "Custom Input...",
                "🧬 Internal: BioTherapy Logistics",
                "💧 Partner B: IV Fluid Crisis",
                "🌪️ Partner C: Tornado Hit",
                "🔥 Partner D: Factory Fire"
            ]
        )
        
        if scenario == "Custom Input...":
            news_input = st.text_area("Headline:", height=100)
            
            # Simulation Guide for Zero-Dependency Mode
            if not USE_REAL_LLM:
                with st.expander("ℹ️ Simulation Guide: Valid Inputs", expanded=False):
                    st.markdown("""
                    **The Zero-Dependency Brain recognizes these key nodes:**
                    
                    * **Locations:** North Carolina, Rocky Mount, North Cove, New Jersey, Mock Town, Mumbai, Rotterdam
                    * **Partners:** PharmaCorp A, B, C, D, EU Logistics
                    * **Disruptions:** Fire, Tornado, Hurricane, Strike, Floods, Logistics
                    
                    **Example inputs:**
                    - "Severe flooding impacts facility in North Carolina."
                    - "Fire reported at facility in Mumbai."
                    - "Tornado strikes Rocky Mount, NC facility."
                    - "Port strike in Rotterdam halts exports."
                    - "Logistics disruption: Cryogenic delivery truck for BioTherapy delayed."
                    """)
        elif "Internal" in scenario: news_input = "Logistics disruption: Cryogenic delivery truck for BioTherapy delayed."
        elif "Partner B" in scenario: news_input = "Hurricane Helene floods North Cove, NC facility. Critical IV Fluid shortage."
        elif "Partner C" in scenario: news_input = "EF3 Tornado strikes Rocky Mount, NC facility. Warehouse roof torn off."
        elif "Partner D" in scenario: news_input = "Fire reported at facility in Mumbai."
        
        run_btn = st.button("▶️ RUN AGENT", type="primary")

    if 'result' not in st.session_state: st.session_state['result'] = None
    if run_btn:
        with st.spinner("🤖 Sentinel Agent mapping global graph..."):
            try:
                app = build_workflow()
                st.session_state['result'] = app.invoke({"input_news": news_input})
            except Exception as e: st.error(f"Error: {e}")
    
    result = st.session_state.get('result')
    
    with col_graph:
        detected_node = result.get('detected_entity') if result else None
        rc_temp = result.get('risk_calculations', {}) if result else {}
        impacted_prods = list(rc_temp.get('details', {}).keys()) if rc_temp else []
        with st.expander("🌍 Global Knowledge Graph (Digital Twin)", expanded=True):
            st.plotly_chart(render_network_graph(KG, impacted_prods, detected_node), use_container_width=True)
        
        # Add workflow diagram below knowledge graph (always visible)
        with st.expander("🔄 Multi-Agent Workflow", expanded=False):
            plot_workflow_diagram()

    if not result: return
    audit = result.get('audit_report')
    if audit and hasattr(audit, 'is_safe_to_present') and not audit.is_safe_to_present: st.error("🛑 **BLOCKED BY AUDITOR**"); return
    
    rc = result.get('risk_calculations', {})
    
    st.markdown("### 🚨 Live Risk Assessment")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    total_p5 = rc.get('total_p5', 0); total_p95 = rc.get('total_p95', 0)
    details = rc.get('details', {})
    
    if details:
        dis_p5 = max([d.get('disruption_p5', 0) for d in details.values()])
        dis_p95 = max([d.get('disruption_p95', 0) for d in details.values()])
        gap_p5 = max([d.get('gap_p5', 0) for d in details.values()])
        gap_p95 = max([d.get('gap_p95', 0) for d in details.values()])
        avg_inv = np.mean([d.get('inventory_days', 0) for d in details.values()])
    else:
        dis_p5=0; dis_p95=0; gap_p5=0; gap_p95=0; avg_inv=0

    with k1: metric_card("💥 Event", result.get('detected_event', 'Unknown'))
    with k2: metric_card("📍 Entity", format_entity_name(result.get('detected_entity')))
    with k3: metric_card("💰 Revenue Risk (95% CI)", f"${total_p5/1e6:.1f}M - ${total_p95/1e6:.1f}M", delta="Probabilistic Forecast", delta_color="inverse")
    with k4: metric_card("⏱️ Disruption Duration", f"{dis_p5:.1f} - {dis_p95:.1f} Days", delta=f"Vs. {avg_inv:.0f} Days Inventory", delta_color="normal")
    with k5: metric_card("⏳ Net Gap", f"{gap_p5:.1f} - {gap_p95:.1f} Days", delta="Uncovered" if gap_p95 > 0 else "Fully Covered", delta_color="inverse" if gap_p95 > 0 else "normal")

    st.plotly_chart(plot_sankey(result), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(plot_risk_ranges(result), use_container_width=True)
    with c2: 
        st.success(f"🤖 **STRATEGIST:** {result.get('recommended_action')}", icon="🛡️")
        st.caption("⚖️ **AUDITOR VALIDATION LOG**")
        col_a, col_b = st.columns(2)
        col_a.info(f"Hallucination: {'PASS' if audit.hallucination_check else 'FAIL'}")
        col_b.info(f"Math Integrity: {'PASS' if audit.math_check else 'FAIL'}")

if __name__ == "__main__":
    main_control_tower()