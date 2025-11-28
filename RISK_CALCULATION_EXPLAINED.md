# 💰 Financial Risk Calculation Explained

## Overview
Resilio uses **Monte Carlo Simulation** to calculate probabilistic financial risk ranges (P5-P95) instead of fixed point estimates.

## Formula Breakdown

### Step 1: Base Disruption Duration
```
Base Disruption = Event Severity × DEFAULT_DISRUPTION_DAYS (60 days)
```
- **Event Severity**: 0.0 (minor) to 1.0 (critical)
  - Factory Fire: 0.95
  - Hurricane: 0.8
  - Labor Strike: 0.6
  - Regulatory Halt: 1.0

**Example**: Hurricane (0.8) → 0.8 × 60 = **48 days**

### Step 2: Monte Carlo Simulation (1000 runs)

For each simulation run:

#### 2a. Disruption Duration (with uncertainty)
```python
disruption_days = Normal(mean=base_disruption, std_dev=7 days)
```
- **Mean**: Base disruption (e.g., 48 days)
- **Std Dev**: 7 days (models uncertainty in recovery time)
- **Result**: Distribution like 41-55 days (48 ± 7)

#### 2b. Daily Revenue (with volatility)
```python
daily_revenue = Normal(mean=annual_revenue/365, std_dev=20% of mean)
```
- **Mean**: Annual revenue ÷ 365
- **Std Dev**: 20% volatility (models demand fluctuations)
- **Example**: $5M/year → $13,699/day ± $2,740

#### 2c. Inventory Gap Calculation
```python
gap_days = max(disruption_days - inventory_days, 0)
```
- **Inventory Days**: `inventory_weeks × 7`
- **Gap**: Days where inventory runs out before supply resumes
- **Example**: 48 days disruption - 28 days inventory = **20 days gap**

#### 2d. Financial Loss
```python
loss = gap_days × daily_revenue
```
- **Example**: 20 days × $13,699/day = **$273,980**

### Step 3: Aggregate Results (1000 simulations)

After running 1000 simulations, we calculate percentiles:

- **P5 (Best Case)**: 5th percentile - optimistic scenario
- **P50 (Expected)**: 50th percentile (median) - most likely
- **P95 (Worst Case)**: 95th percentile - pessimistic scenario

**Example Output**:
- P5: $108,058 (best case)
- P50: $279,019 (expected)
- P95: $485,899 (worst case)
- **Range**: $108K - $486K

## Why Ranges Instead of Fixed Numbers?

1. **Uncertainty in Disruption Duration**: Recovery time varies
2. **Revenue Volatility**: Daily sales fluctuate
3. **Multiple Products**: Different products have different inventory levels
4. **Risk Management**: P95 gives worst-case planning, P5 gives optimistic view

## Real Example: Hurricane in North Carolina

**Input**:
- Event: Hurricane (severity: 0.8)
- Entity: Apex_Chemicals_USA
- Product: Advil_Max_200mg
  - Annual Revenue: $5,000,000
  - Inventory: 4 weeks (28 days)

**Calculation**:
1. Base Disruption: 0.8 × 60 = 48 days
2. Disruption Range: 48 ± 7 days (41-55 days)
3. Daily Revenue: $13,699 ± $2,740
4. Inventory Gap: max(48 - 28, 0) = 20 days (average)
5. Financial Loss: 20 days × $13,699 = $273,980 (simplified)

**Monte Carlo Result** (1000 simulations):
- Expected Loss: **$279,019**
- Range: **$108,058 - $485,899**

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DEFAULT_DISRUPTION_DAYS` | 60 | Base disruption period |
| `severity` | 0.0-1.0 | Event severity multiplier |
| `disruption_std_dev` | 7 days | Uncertainty in recovery time |
| `revenue_volatility` | 20% | Daily revenue fluctuation |
| `simulations` | 1000 | Number of Monte Carlo runs |

## Code Location

The calculation is in `src/resilio_core.py`:
- Function: `predict_financial_impact_range()`
- Lines: 138-169

