# 🧪 Testing Prompts for Resilio

This document contains example prompts to test different scenarios in the Resilio supply chain risk assessment system.

## 📋 Test Categories

### 1. Natural Disasters (NASA EONET Coverage)

#### Hurricanes & Storms
```
Hurricane Helene projected to hit North Carolina logistics hubs in USA.
```
**Expected**: Should map to `Apex_Chemicals_USA` (Raleigh, NC)

```
Tornado warning issued for Rocky Mount, North Carolina. Pfizer facility at risk.
```
**Expected**: Should map to `Pfizer_Rocky_Mount`

```
Tropical storm approaching the US East Coast, affecting pharmaceutical supply chains.
```
**Expected**: Should map to `Apex_Chemicals_USA` (generic US context)

#### Fires & Wildfires
```
BREAKING: Large fire reported at PharmaCorp facility in Mumbai industrial zone.
```
**Expected**: Should map to `PharmaCorp_India`

```
Wildfire spreading near Rocky Mount, North Carolina. Emergency services responding.
```
**Expected**: Should map to `Pfizer_Rocky_Mount`

```
Massive warehouse fire at pharmaceutical facility in India.
```
**Expected**: Should map to `PharmaCorp_India` (Mumbai)

### 2. Labor & Logistics Disruptions

#### Port Strikes
```
Labor union announces strike at Rotterdam Port in Netherlands, halting pharma exports.
```
**Expected**: Should map to `EuroPharma_Logistics`

```
Port workers in Rotterdam go on strike, disrupting European pharmaceutical supply chain.
```
**Expected**: Should map to `EuroPharma_Logistics`

#### Logistics Failures
```
Logistics failure at EuroPharma distribution center in Rotterdam.
```
**Expected**: Should map to `EuroPharma_Logistics`

### 3. Company-Specific Events

#### Pfizer (Rocky Mount, NC)
```
Pfizer Rocky Mount facility reports production halt due to equipment failure.
```
**Expected**: Should map to `Pfizer_Rocky_Mount`

```
Breaking: EF3 tornado hits Pfizer manufacturing plant in Rocky Mount, North Carolina.
```
**Expected**: Should map to `Pfizer_Rocky_Mount`

#### Janssen (Raritan, NJ)
```
Janssen Raritan facility experiences power outage affecting CAR-T cell therapy production.
```
**Expected**: Should map to `Janssen_Raritan`

```
CAR-T therapy production disrupted at Janssen facility in Raritan, New Jersey.
```
**Expected**: Should map to `Janssen_Raritan`

#### Baxter (North Cove, NC)
```
Baxter North Cove plant reports contamination in IV fluid production line.
```
**Expected**: Should map to `Baxter_North_Cove`

```
Critical shortage: Saline IV bags production halted at Baxter facility in North Cove.
```
**Expected**: Should map to `Baxter_North_Cove` + should detect hidden dependency on CAR-T

#### PharmaCorp (Mumbai, India)
```
PharmaCorp India announces temporary closure of Mumbai manufacturing facility.
```
**Expected**: Should map to `PharmaCorp_India`

```
Fire breaks out at PharmaCorp facility in Mumbai, India. Production suspended.
```
**Expected**: Should map to `PharmaCorp_India`

#### Apex Chemicals (Raleigh, NC)
```
Apex Chemicals USA reports supply chain disruption at North Carolina facility.
```
**Expected**: Should map to `Apex_Chemicals_USA`

```
Hurricane damage reported at Apex Chemicals plant in Raleigh, North Carolina.
```
**Expected**: Should map to `Apex_Chemicals_USA`

### 4. Regulatory & Quality Issues

```
FDA issues warning letter to PharmaCorp India regarding quality control violations.
```
**Expected**: Should map to `PharmaCorp_India`, event type: "Regulatory Halt"

```
Regulatory ban imposed on pharmaceutical exports from India due to quality concerns.
```
**Expected**: Should map to `PharmaCorp_India`

### 5. Hidden Dependency Tests

```
Baxter North Cove facility shuts down due to contamination. IV fluid production halted.
```
**Expected**: 
- Should map to `Baxter_North_Cove`
- Should detect `Saline_IV_Bags` as impacted
- Should detect `Carvykti_Therapy` as impacted (hidden dependency)

```
Critical: Saline IV bag shortage reported. Baxter production line down.
```
**Expected**: Should detect both `Saline_IV_Bags` and `Carvykti_Therapy` as impacted

### 6. Location Ambiguity Tests

```
Hurricane approaching North Carolina. Pharmaceutical facilities at risk.
```
**Expected**: Should map to `Apex_Chemicals_USA` (Raleigh) - NOT Pfizer (Rocky Mount)

```
Natural disaster reported in North Carolina. Multiple pharma facilities affected.
```
**Expected**: Should map to `Apex_Chemicals_USA` (default for generic NC)

```
Fire reported in Mumbai. Industrial zone affected.
```
**Expected**: Should map to `PharmaCorp_India` (Mumbai context)

### 7. Edge Cases & Negative Tests

```
Explosion at Wonka Factory reported. Chocolate production halted.
```
**Expected**: Should return `None` (not in knowledge graph)

```
Supply chain disruption reported in Tokyo, Japan.
```
**Expected**: Should return `None` (location not in knowledge graph)

```
Generic pharmaceutical supply chain issue reported.
```
**Expected**: May return `None` or fallback to generic mapping

### 8. Real-World Historical Events

```
Hurricane Helene makes landfall in North Carolina, affecting pharmaceutical supply chains.
```
**Expected**: Should map to `Apex_Chemicals_USA` (known event mapping)

```
Dana floods hit Spain, disrupting European pharmaceutical logistics.
```
**Expected**: Should map to `EuroPharma_Logistics` (known event mapping)

```
EF3 tornado strikes Pfizer facility in Rocky Mount, North Carolina in July 2023.
```
**Expected**: Should map to `Pfizer_Rocky_Mount` (known event mapping)

### 9. Multi-Entity Scenarios

```
Multiple pharmaceutical facilities in North Carolina report disruptions due to severe weather.
```
**Expected**: Should map to one entity (likely `Apex_Chemicals_USA` as default)

```
Pharmaceutical supply chain crisis: Both Pfizer and Janssen facilities report issues.
```
**Expected**: Should map to one entity (likely first mentioned or most specific)

### 10. Severity Tests

```
Catastrophic: Warehouse completely destroyed by fire at PharmaCorp Mumbai facility.
```
**Expected**: Should have severity ~1.5 (catastrophic)

```
Minor delay reported at Rotterdam port. Temporary logistics issue.
```
**Expected**: Should have severity ~0.2-0.5 (minor to moderate)

## 🎯 Testing Checklist

When testing each prompt, verify:

- [ ] **Entity Mapping**: Correct supplier/company identified
- [ ] **Event Type**: Correct event type extracted (Fire, Hurricane, Strike, etc.)
- [ ] **Severity**: Appropriate severity score (0.0-1.5)
- [ ] **Impacted Products**: Correct products identified downstream
- [ ] **Hidden Dependencies**: Hidden dependencies detected (e.g., Saline → CAR-T)
- [ ] **Financial Risk**: Risk calculations are reasonable
- [ ] **NASA Verification**: If applicable, NASA EONET coordinates used
- [ ] **Verification Log**: Clear explanation of mapping logic

## 📊 Expected Output Format

For each test prompt, you should see:

1. **Detected Entity**: `Supplier_Name`
2. **Detected Event**: `Event Type`
3. **Event Severity**: `0.0-1.5`
4. **Impacted Products**: `[Product1, Product2, ...]`
5. **Risk Calculations**: 
   - Total Expected Loss: `$X`
   - P5-P95 Range: `$Y - $Z`
6. **Verification Log**: Explanation of how entity was mapped

## 🚀 Quick Test Commands

To test in the dashboard:
1. Open the Streamlit dashboard
2. Select "Custom Input..." from the scenario selector
3. Paste one of the test prompts above
4. Click "▶️ RUN AGENT"
5. Verify the results match expected outputs

To test programmatically:
```python
from src.resilio_core import build_workflow

app = build_workflow()
result = app.invoke({"input_news": "Your test prompt here"})
print(result)
```

