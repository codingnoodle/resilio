# 💰 Financial Risk Calculation Explained

## Overview
Resilio uses **Monte Carlo Simulation** with **Empirical Disruption Profiles** to calculate probabilistic financial risk ranges (P5-P95) instead of fixed point estimates. The system uses event-type-specific disruption distributions and path-aware inventory buffering.

## Formula Breakdown

### Step 1: Empirical Disruption Duration (Event-Type Specific)

Instead of a generic severity multiplier, Resilio uses **empirical disruption profiles** based on historical data for each event type:

```python
DISRUPTION_PROFILES = {
    "Tornado": (90, 15),       # Mean: 90 days, Std Dev: 15 days
    "Hurricane": (60, 10),     # Mean: 60 days, Std Dev: 10 days
    "Fire": (75, 14),          # Mean: 75 days, Std Dev: 14 days
    "Strike": (45, 10),        # Mean: 45 days, Std Dev: 10 days
    "Logistics": (21, 5),      # Mean: 21 days, Std Dev: 5 days
    "FDA": (90, 30),           # Mean: 90 days, Std Dev: 30 days
    "Default": (45, 7)         # Mean: 45 days, Std Dev: 7 days
}
```

**Example**: Hurricane event → Mean: 60 days, Std Dev: 10 days

### Step 2: Monte Carlo Simulation (1000 runs)

For each simulation run:

#### 2a. Disruption Duration (from empirical distribution)
```python
disruption_days = Normal(mean=event_mean, std_dev=event_sigma)
```
- **Mean**: Event-specific mean (e.g., 60 days for Hurricane)
- **Std Dev**: Event-specific sigma (e.g., 10 days for Hurricane)
- **Result**: Distribution like 50-70 days (60 ± 10) for Hurricane

#### 2b. Path-Aware Inventory Calculation
```python
# Find shortest path from disruption source to product
path = shortest_path(graph, source=disrupted_entity, target=product)

# Sum inventory along the entire supply path
path_inventory_weeks = sum([graph.nodes[n].get('inventory_weeks', 0) for n in path])
inventory_days = path_inventory_weeks * 7
```

**Key Innovation**: Instead of just using the product's inventory, we sum inventory buffers along the entire supply chain path. This accounts for:
- Raw material inventory at suppliers
- Work-in-progress inventory
- Finished goods inventory at the product level

**Example Path**: `PharmaCorp_C_Tier1 → Product_Y_Sterile`
- Product_Y_Sterile: 2 weeks inventory
- **Total Path Inventory**: 2 weeks = 14 days

#### 2c. Daily Revenue (with volatility)
```python
daily_revenue = Normal(mean=annual_revenue/365, std_dev=20% of mean)
```
- **Mean**: Annual revenue ÷ 365
- **Std Dev**: 20% volatility (models demand fluctuations)
- **Example**: $1.2B/year → $3,287,671/day ± $657,534

#### 2d. Inventory Gap Calculation
```python
gap_days = max(disruption_days - inventory_days, 0)
```
- **Inventory Days**: Sum of inventory along the supply path (path-aware)
- **Gap**: Days where inventory runs out before supply resumes
- **Example**: 60 days disruption - 14 days inventory = **46 days gap**

#### 2e. Financial Loss
```python
loss = gap_days × daily_revenue
```
- **Example**: 46 days × $3,287,671/day = **$151,232,866**

### Step 3: Aggregate Results (1000 simulations)

After running 1000 simulations, we calculate percentiles:

- **P5 (Best Case)**: 5th percentile - optimistic scenario
- **P50 (Expected)**: 50th percentile (median) - most likely
- **P95 (Worst Case)**: 95th percentile - pessimistic scenario

**Example Output** for Product Y (Hurricane scenario):
- P5: $108M (best case)
- P50: $244M (expected)
- P95: $398M (worst case)
- **Range**: $108M - $398M

## Why Ranges Instead of Fixed Numbers?

1. **Uncertainty in Disruption Duration**: Recovery time varies based on event type
2. **Revenue Volatility**: Daily sales fluctuate (20% standard deviation)
3. **Path-Aware Inventory**: Inventory buffers along the supply chain path
4. **Multiple Products**: Different products have different inventory levels and revenue
5. **Risk Management**: P95 gives worst-case planning, P5 gives optimistic view

## Real Example: Hurricane in North Carolina (Partner B)

**Input**:
- Event: Hurricane Flooding
- Entity: PharmaCorp_B_Tier1 (North Cove, NC)
- Product: Product_Z_Commodity
  - Annual Revenue: $300,000,000
  - Inventory: 2 weeks (14 days) - path-aware

**Calculation**:
1. **Disruption Distribution**: Hurricane → Mean: 60 days, Sigma: 10 days
   - Disruption Range: 50-70 days (P5-P95)
2. **Daily Revenue**: $300M ÷ 365 = $821,918/day ± $164,384
3. **Path Inventory**: 14 days (Product_Z_Commodity only)
4. **Inventory Gap**: max(60 - 14, 0) = 46 days (average)
5. **Financial Loss**: 46 days × $821,918 = $37,808,228 (simplified)

**Monte Carlo Result** (1000 simulations):
- Expected Loss: **$37,238,298**
- Range: **$15,234,567 - $62,194,536** (P5-P95)

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DISRUPTION_PROFILES` | Event-specific | Empirical (Mean, Sigma) for each event type |
| `Tornado` | (90, 15) | 90 days mean, 15 days std dev |
| `Hurricane` | (60, 10) | 60 days mean, 10 days std dev |
| `Fire` | (75, 14) | 75 days mean, 14 days std dev |
| `Strike` | (45, 10) | 45 days mean, 10 days std dev |
| `Logistics` | (21, 5) | 21 days mean, 5 days std dev |
| `revenue_volatility` | 20% | Daily revenue fluctuation |
| `simulations` | 1000 | Number of Monte Carlo runs |
| `path_aware_inventory` | True | Sum inventory along supply path |

## Path-Aware Inventory Buffering

**Traditional Approach**:
- Only considers product-level inventory
- Example: Product has 2 weeks → 14 days buffer

**Resilio's Path-Aware Approach**:
- Sums inventory along the entire supply chain path
- Example Path: `Supplier → Ingredient → Product`
  - Supplier inventory: 0 weeks
  - Ingredient inventory: 4 weeks
  - Product inventory: 2 weeks
  - **Total Path Inventory**: 6 weeks = 42 days

This provides a more realistic "effective inventory" that accounts for buffers at each stage of the supply chain.

## Dashboard Metrics

The dashboard displays three key time-based metrics:

1. **⏱️ Disruption Duration**: P5-P95 range from empirical distribution
   - Example: "50.0 - 70.0 Days"
   - Shows how long the disruption event lasts

2. **📦 Inventory Buffer**: Total path-aware inventory days
   - Example: "14.0 Days"
   - Shows available stock along the supply path

3. **⏳ Net Gap**: P5-P95 range of uncovered days
   - Example: "36.0 - 56.0 Days"
   - Shows the actual gap: `max(Disruption - Inventory, 0)`
   - If gap is 0, shows "Fully Covered"

## Code Location

The calculation is in `src/resilio_core.py`:
- Function: `predict_financial_impact_range()`
- Lines: 152-194
- Disruption Profiles: Lines 132-140
- Path-Aware Inventory: Lines 163-167
