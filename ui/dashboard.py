import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import sys
import os
import re

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.resilio_core import build_workflow, KG

def plot_sankey(state):
    """
    Renders flow based on the ACTUAL graph traversal in state.
    """
    details = state['risk_calculations'].get('details', {})
    if not details: 
        # Return empty figure if no risk found
        return go.Figure().update_layout(title="No Impact Detected")
    
    # 1. Build Nodes List
    # We need: Event -> Supplier -> Product -> Loss
    # We know the Supplier from state['detected_entity']
    supplier = state['detected_entity']
    event = state['detected_event']
    
    label_list = [event, supplier]
    product_list = list(details.keys())
    label_list.extend(product_list)
    label_list.append("Financial Loss")
    
    # Create map of label -> index
    label_map = {name: i for i, name in enumerate(label_list)}
    
    sources, targets, values, colors = [], [], [], []
    
    # Link 1: Event -> Supplier
    sources.append(label_map[event])
    targets.append(label_map[supplier])
    values.append(10)  # Fixed visual width
    colors.append("lightgrey")
    
    # Link 2: Supplier -> Products
    for prod in product_list:
        sources.append(label_map[supplier])
        targets.append(label_map[prod])
        values.append(5)
        
        # Color red if inventory gap exists
        is_risk = details[prod]['days_uncovered_avg'] > 0
        colors.append("rgba(255, 50, 50, 0.8)" if is_risk else "rgba(50, 200, 50, 0.4)")
        
        # Link 3: Product -> Loss (only if risky)
        if is_risk:
            sources.append(label_map[prod])
            targets.append(label_map["Financial Loss"])
            # Scale the line width by loss amount
            values.append(max(1, details[prod]['loss_p50'] / 100000))
            colors.append("rgba(200, 0, 0, 0.8)")

    # Replace underscores with spaces for better readability in diagram
    wrapped_labels = [label.replace('_', ' ') if '_' in label else label for label in label_list]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,  # Increased padding for longer names
            thickness=25,  # Slightly thicker for better visibility
            line=dict(color="black", width=0.5), 
            label=wrapped_labels,  # Use labels with spaces instead of underscores
            hovertemplate='%{label}<extra></extra>'  # Show full name on hover
        ),
        link=dict(source=sources, target=targets, value=values, color=colors)
    )])
    # Increase height and font size for better label visibility
    fig.update_layout(
        title="<b>Live Risk Contagion Path</b>", 
        height=450,  # Increased height for better label visibility
        font=dict(size=11)
    )
    return fig

def plot_risk_ranges(state):
    details = state['risk_calculations'].get('details', {})
    if not details: return go.Figure()
    
    prods = list(details.keys())
    p50 = [details[p]['loss_p50'] for p in prods]
    p95 = [details[p]['loss_p95'] for p in prods]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=prods, y=p50, name="Expected Loss", marker_color='indianred'))
    fig.add_trace(go.Scatter(x=prods, y=p95, mode='markers', marker=dict(symbol='line-ns-open', size=10, color='black'), name="Worst Case (P95)"))
    fig.update_layout(title="<b>Probabilistic Forecast (95% CI)</b>", yaxis_title="USD Loss", height=300)
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
            
            # Provide Mermaid code for reference if user wants to regenerate the image
            with st.expander("📋 Mermaid Code (for regenerating PNG at mermaid.live)"):
                st.code("""graph TD
    Start((START)) --> Sentinel[📡 Sentinel]
    Sentinel --> Detective[🕵️ Detective]
    Detective --> Quantifier[🧮 Quantifier]
    Quantifier --> Strategist[🧠 Strategist]
    Strategist --> Auditor{⚖️ Auditor}
    Auditor -- "✅ Approved" --> End((END))
    Auditor -- "❌ Rejected" --> Sentinel
    
    style Auditor fill:#ffcccc
    style Sentinel fill:#ccffcc""", language="text")
    
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
    st.markdown("---")
    
    # Add workflow diagram section at the top
    with st.expander("🔄 View Multi-Agent Workflow", expanded=False):
        plot_workflow_diagram()

    # 1. SCENARIO SELECTOR
    with st.sidebar:
        st.header("⚡ Scenario Injection")
        scenario = st.radio(
            "Inject Live Event:",
            [
                "Custom Input...",
                "🔥 Fire at PharmaCorp (India)",
                "🌀 Hurricane in North Carolina (USA)",
                "🚢 Port Strike in Rotterdam (EU)",
                "🛑 FDA Warning for PharmaCorp"
            ]
        )
        
        if scenario == "Custom Input...":
            news_input = st.text_area("Enter News Headline:", height=100)
        elif "Fire" in scenario:
            news_input = "BREAKING: Large fire reported at PharmaCorp facility in Mumbai industrial zone."
        elif "Hurricane" in scenario:
            news_input = "Hurricane Helene projected to hit North Carolina logistics hubs in USA."
        elif "Rotterdam" in scenario:
            news_input = "Labor union announces strike at Rotterdam Port in Netherlands, halting pharma exports."
        else:
            news_input = "FDA issues warning letter to PharmaCorp India regarding quality control."
            
        run_btn = st.button("▶️ RUN AGENT", type="primary")

    # 2. EXECUTION
    if 'result' not in st.session_state:
        st.session_state['result'] = None

    if run_btn:
        with st.spinner("🤖 Sentinel Agent mapping global graph..."):
            # Always rebuild workflow to avoid caching issues
            app = build_workflow()
            # Increase recursion limit and handle errors
            try:
                # Use configurable recursion limit, but workflow should always terminate
                result = app.invoke(
                    {"input_news": news_input},
                    config={"recursion_limit": 15}  # Increased for complex scenarios
                )
                # Validate result before storing
                if result and isinstance(result, dict):
                    st.session_state['result'] = result
                    st.session_state['last_result'] = result  # Store for fallback
                else:
                    st.error("❌ Workflow returned invalid result")
                    st.session_state['result'] = st.session_state.get('last_result', None)
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ Error during analysis: {error_msg}")
                # If recursion error, show helpful message
                if "Recursion limit" in error_msg:
                    st.warning("⚠️ Workflow encountered an unexpected loop. This may indicate a configuration issue.")
                    st.info("💡 Try a different input or check the console for details.")
                # Use last successful result as fallback
                st.session_state['result'] = st.session_state.get('last_result', None)
                # Show traceback in expander for debugging
                with st.expander("🔍 Debug Details"):
                    import traceback
                    st.code(traceback.format_exc())

    # 3. RENDER
    result = st.session_state.get('result')
    
    if not result:
        st.info("👈 Select a scenario and click RUN to start.")
        return

    # AUDITOR CHECK
    audit = result.get('audit_report')
    if audit and hasattr(audit, 'is_safe_to_present') and not audit.is_safe_to_present:
        st.error("🛑 **BLOCKED BY AUDITOR:** Event could not be grounded to Knowledge Graph.")
        return

    # KPIS - Get risk calculations with error handling
    rc = result.get('risk_calculations', {})
    if not rc or not isinstance(rc, dict):
        # Show partial results even if risk calculations are missing
        st.warning("⚠️ No risk calculations available. Entity: {}, Products: {}".format(
            result.get('detected_entity', 'Unknown'), result.get('impacted_products', [])))
        # Still show what we have
        k1, k2 = st.columns(2)
        k1.metric("💥 Event", result.get('detected_event', 'Unknown'))
        with k2:
            st.markdown("**📍 Entity**")
            entity_name = result.get('detected_entity', 'Unknown')
            st.write(entity_name if entity_name else "Unknown")
        # Show debug info
        with st.expander("🔍 Debug: Full Result"):
            st.json(result)
        return
    
    k1, k2, k3, k4 = st.columns(4)
    # Ensure event is not None
    event_name = result.get('detected_event') or 'Unknown'
    if event_name == 'None':
        event_name = 'Unknown'
    k1.metric("💥 Event", event_name)
    # Display entity with full name - use container to prevent truncation
    with k2:
        st.markdown("**📍 Entity**")
        entity_name = result.get('detected_entity') or 'Unknown'
        if entity_name == 'None':
            entity_name = 'Unknown'
        st.write(entity_name)
    
    # Financial Risk with Range (P5-P95) - Convert to float to handle numpy types
    total_p5 = float(rc.get('total_p5', 0) or 0)
    total_expected = float(rc.get('total_expected', 0) or 0)
    total_p95 = float(rc.get('total_p95', 0) or 0)
    
    if total_expected > 0:
        risk_range = f"${total_p5:,.0f} - ${total_p95:,.0f}"
        k3.metric("💰 Financial Risk (Range)", f"${total_expected:,.0f}", delta=f"Range: {risk_range}", delta_color="inverse")
    else:
        k3.metric("💰 Financial Risk", "$0", delta="No impact")
    
    # Inventory Gap with Range
    details = rc.get('details', {})
    if details:
        # Calculate range of days uncovered across all products - Convert to float
        days_list = [float(d.get('days_uncovered_avg', 0) or 0) for d in details.values() if float(d.get('days_uncovered_avg', 0) or 0) > 0]
        if days_list:
            max_gap = max(days_list)
            min_gap = min(days_list) if len(days_list) > 1 else max_gap
            if max_gap > 0:
                gap_range = f"{min_gap:.0f}-{max_gap:.0f}" if min_gap != max_gap else f"{max_gap:.0f}"
                k4.metric("⏳ Inventory Gap (Days)", f"{max_gap:.0f}", delta=f"Range: {gap_range} days", delta_color="inverse")
            else:
                k4.metric("⏳ Inventory Gap", "0 Days", delta="Covered")
        else:
            k4.metric("⏳ Inventory Gap", "0 Days", delta="No gap")
    else:
        k4.metric("⏳ Inventory Gap", "N/A", delta="No data")

    # DETAILED RANGE INFORMATION
    details = rc.get('details', {})
    if details:
        with st.expander("📊 Detailed Risk Breakdown (P5-P95 Ranges)", expanded=False):
            for prod, prod_details in details.items():
                st.markdown(f"**{prod}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    loss_p50 = float(prod_details.get('loss_p50', 0) or 0)
                    loss_p5 = float(prod_details.get('loss_p5', 0) or 0)
                    loss_p95 = float(prod_details.get('loss_p95', 0) or 0)
                    st.metric("Financial Loss Range", 
                             f"${loss_p50:,.0f}",
                             delta=f"${loss_p5:,.0f} - ${loss_p95:,.0f}",
                             delta_color="inverse")
                with col2:
                    disruption_avg = float(prod_details.get('disruption_days_avg', 0) or 0)
                    st.metric("Disruption Duration", f"{disruption_avg:.1f} days", 
                             delta=f"±7 days (Monte Carlo)")
                with col3:
                    gap_avg = float(prod_details.get('days_uncovered_avg', 0) or 0)
                    inv_days = float(prod_details.get('inventory_days', 0) or 0)
                    st.metric("Inventory Gap", f"{gap_avg:.1f} days",
                             delta=f"Out of {inv_days:.0f} days coverage")
                st.markdown("---")

    # VISUALS
    st.plotly_chart(plot_sankey(result), use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(plot_risk_ranges(result), use_container_width=True)
    with c2: 
        st.success(f"🤖 **STRATEGIST:** {result.get('recommended_action')}", icon="🛡️")
        
        # AUDITOR SCORECARD
        st.markdown("---")
        st.caption("⚖️ **AUDITOR VALIDATION LOG**")
        col_a, col_b = st.columns(2)
        col_a.info(f"Hallucination Check: {'PASS' if audit.hallucination_check else 'FAIL'}")
        col_b.info(f"Math Integrity Check: {'PASS' if audit.math_check else 'FAIL'}")

if __name__ == "__main__":
    main_control_tower()
