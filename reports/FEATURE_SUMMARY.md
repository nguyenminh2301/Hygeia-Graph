# Hygeia-Graph — Feature Summary Report

## Overview
**Hygeia-Graph** is a Streamlit-based web application for Mixed Graphical Model (MGM) network analysis in health research. It provides an end-to-end workflow from data upload to network visualization and reporting.

---

## 📂 Data Upload & Format Support

### Supported File Formats
| Format | Extension | Engine |
|--------|-----------|--------|
| CSV | .csv | pandas |
| Excel | .xls, .xlsx | openpyxl/xlrd |
| Text | .txt, .tsv | pandas (auto-detect delimiter) |
| Stata | .dta | pyreadstat |
| SPSS | .sav | pyreadstat |
| SAS | .sas7bdat | pyreadstat |

### Example Datasets
| Dataset | Rows | Columns | Theme |
|---------|------|---------|-------|
| Easy | 140 | 6 | Inflammation & Sleep |
| Medium | 280 | 12 | Metabolic–Mood Comorbidity |
| Hard | 600 | 32 | Multi-domain Stress Test |

**Location:** `assets/example_*.csv`

---

## 📋 Schema & Model Specification

### Schema Builder
- Auto-infer variable types from data
- Manual override: Gaussian (g), Categorical (c), Poisson (p)
- Set measurement levels: continuous, ordinal, nominal, count
- Define variable categories for categorical variables

### Model Specification
- EBIC gamma: Network sparsity control (0.0–1.0)
- Alpha: Elastic-net mixing (1=LASSO, 0=Ridge)
- Rule: AND/OR for edge selection
- Scale Gaussian: Standardize continuous variables

---

## 🔬 MGM Network Analysis

### Mixed Graphical Model (mgm R package)
- Handles mixed variable types (continuous, categorical, count)
- Regularized estimation via glmnet
- EBIC-based model selection

### Output
- Edge weights matrix
- Node positions (optional layout)
- Model diagnostics

---

## 🌐 Network Visualization

### Interactive Network (Pyvis)
- Force-directed layout
- Node coloring by:
  - Variable type (Gaussian/Categorical/Poisson)
  - Domain/community
  - Centrality metrics
- Edge filtering:
  - Threshold slider
  - Top-N edges
  - Absolute weight mode

### Export Options
- PNG screenshot
- HTML interactive (standalone)
- JSON network data

---

## 📊 Derived Metrics

### Centrality Measures
| Metric | Description |
|--------|-------------|
| Strength | Sum of absolute edge weights |
| Betweenness | Shortest path centrality |
| Closeness | Inverse average distance |
| Expected Influence | Signed edge sum |

### Bridge Centrality (networktools)
- Bridge Strength
- Bridge Betweenness
- Bridge Expected Influence

### Community Detection
- Louvain algorithm
- Community assignment per node

### Predictability
- R² for each node (how well predicted by neighbors)
- Displayed as pie chart in network

---

## 🔒 Robustness Analysis (Bootnet)

### Bootstrap Methods
- Nonparametric bootstrap (edge stability)
- Case-dropping bootstrap (network stability)

### Guardrails
| Setting | Safe Max | Hard Max |
|---------|----------|----------|
| Bootstraps | 500 | 2000 |
| Cores | 1 | 2 |

**Advanced unlock:** Checkbox to bypass safe limits.

---

## 📈 Descriptive Statistics

### Variable Classification
- Automatic or schema-based type detection
- Types: continuous, count, nominal, ordinal

### Metrics
| Type | Metrics |
|------|---------|
| Continuous | mean, SD, median, Q1/Q3, IQR, min, max, normality test |
| Count | mean, var, dispersion ratio |
| Categorical | n_levels, top level, entropy, level distribution |

### Normality Tests
- Shapiro-Wilk (n ≤ 5000)
- D'Agostino K² (n > 5000, sampled)

### Exports
- `variable_summary.csv`
- `categorical_levels.csv`
- `descriptives.json`

---

## 📄 LASSO Feature Selection (Preprocessing)

### glmnet Integration
- Automatic family detection (gaussian/binomial/multinomial/poisson)
- Lambda selection: lambda.1se or lambda.min
- Cross-validation folds: 3–20

### Guardrails
| Setting | Safe Max | Hard Max |
|---------|----------|----------|
| CV Folds | 10 | 20 |
| Max Features | 100 | 300 |

### Output
- Selected feature list
- Coefficient table
- Filtered dataset preview

---

## 📊 Longitudinal Flow (V2)

### Pair Detection
- Auto-detect T1/T2 column pairs (suffix-based)
- Manual pair selection

### Sankey Diagram
- Visualize T1 → T2 transitions
- Interactive Plotly figure
- Export: HTML, JSON, CSV

---

## 🎯 Intervention Simulation (V2)

### mgm::predict.mgm
- Load saved MGM model
- Set intervention values
- Compare baseline vs intervention predictions

### Output
- Predicted effects per node
- Non-causal disclaimer included

---

## 🖨️ Publication Pack

### Generated Outputs
- Network plots (basic, predictability, community)
- Centrality tables (CSV)
- Edge weight matrix
- Summary statistics

### Customization
- Threshold, top edges
- Layout algorithm
- Label visibility

---

## 📝 Insights Report

### Auto-generated Report Sections
1. Analysis Overview
2. Network Statistics
3. Top Central Nodes
4. Edge Summary
5. Descriptive Statistics (if computed)

### Export Formats
- Markdown (.md)
- Plain text (.txt)
- JSON payload

---

## 🌐 Multilingual Support (i18n)

### Available Languages
- 🇬🇧 English
- 🇻🇳 Vietnamese

### Coverage
- Navigation labels
- Form fields
- Help text
- Warnings and errors

---

## ⚙️ UX Enhancements

### Data Format Guidance
- Clear requirements shown on upload page
- Detailed explanations in expander

### Guided Navigation
- "Next Step" buttons after each completed stage
- Workflow progress indicator

### Branching Hints
- Recommended defaults for settings
- Captions explaining parameter effects

---

## 🔧 Technical Stack

### Python Dependencies
```
streamlit, pandas, numpy, networkx, pyvis, plotly
jsonschema, scipy, openpyxl, xlrd, pyreadstat
```

### R Dependencies
```
mgm, bootnet, qgraph, networktools, glmnet, jsonlite
```

---

## 📁 Project Structure

```
Hygeia-Graph/
├── app.py                          # Main Streamlit app
├── src/hygeia_graph/
│   ├── ui_pages.py                 # Page renderers
│   ├── descriptives.py             # Descriptive statistics
│   ├── file_loader.py              # Multi-format loader
│   ├── example_datasets.py         # Example data registry
│   ├── heavy_guardrails.py         # Resource guardrails
│   ├── ui_guidance.py              # UX guidance text
│   ├── longitudinal_flow.py        # Sankey diagrams
│   └── ...
├── r/
│   ├── run_mgm.R                   # MGM estimation
│   ├── run_bootnet.R               # Bootstrap analysis
│   ├── run_lasso.R                 # Feature selection
│   └── ...
├── assets/
│   ├── example_easy.csv
│   ├── example_medium.csv
│   └── example_hard.csv
├── tests/                          # Unit tests
└── reports/                        # Feature reports
```

---

*Generated: 2026-01-10*
