# Methods

This document provides detailed technical information about the statistical methods implemented in Hygeia-Graph, suitable for the Methods section of academic papers.

## Mixed Graphical Model (MGM)

### Model Specification

Hygeia-Graph implements pairwise Mixed Graphical Models (MGM) as described by Haslbeck & Waldorp (2020). The model estimates conditional dependencies between variables of mixed types:

- **Gaussian (g)**: Continuous variables modeled with Gaussian conditional distributions
- **Categorical (c)**: Nominal or ordinal variables modeled with categorical conditional distributions  
- **Poisson (p)**: Count variables modeled with Poisson conditional distributions

The model is restricted to **pairwise interactions (k=2)**, meaning only two-way dependencies are estimated. Higher-order interactions are not modeled.

### Mathematical Framework

For a set of variables X = (X₁, ..., Xₚ), the joint distribution is specified via conditional distributions:

- **Gaussian**: X_s | X_{-s} ~ N(μ_s(X_{-s}), σ²_s)
- **Categorical**: P(X_s = k | X_{-s}) ∝ exp(η_sk(X_{-s}))
- **Poisson**: X_s | X_{-s} ~ Poisson(λ_s(X_{-s}))

The parameters connecting variables form the network edges.

## Regularization and Tuning

### EBIC Selection

Hygeia-Graph uses the **Extended Bayesian Information Criterion (EBIC)** for regularization parameter selection:

```
EBIC = -2 × log-likelihood + k × log(n) + 2 × γ × k × log(p)
```

Where:
- `n`: Number of observations
- `k`: Number of non-zero parameters
- `p`: Number of variables
- `γ` (gamma): Tuning parameter controlling sparsity (default: 0.5)

**Configuration**:
- `ebic_gamma`: Controls the penalty for complexity (0.0–1.0, default 0.5)
  - Higher values → sparser networks
  - Lower values → denser networks

### Elastic Net Regularization

The model uses elastic net regularization combining L1 (Lasso) and L2 (Ridge) penalties:

```
Penalty = α × ||β||₁ + (1-α) × ||β||₂²
```

**Configuration**:
- `alpha`: Elastic net mixing parameter (0.0–1.0, default 0.5)
  - 1.0 = Pure Lasso (sparse)
  - 0.0 = Pure Ridge (dense)
  - 0.5 = Equal mixture

### Neighborhood Regression Rule

The `rule_reg` parameter determines how pairwise dependencies are combined:

- **AND** (default): Edge exists if both nodewise regressions detect it
- **OR**: Edge exists if either nodewise regression detects it

The AND rule produces sparser, more conservative networks.

### Gaussian Scaling

When `scale_gaussian = true`:
- Gaussian variables are standardized (mean=0, sd=1) before model fitting
- Improves numerical stability and interpretability
- Edge weights become standardized coefficients

## Edge Definition and Weight Mapping

### Parameter Blocks

For interactions involving categorical variables, the MGM model estimates parameter *blocks* rather than single values. For example:

- Gaussian × Gaussian: 1 parameter
- Gaussian × Categorical (K levels): K parameters
- Categorical (K₁) × Categorical (K₂): K₁ × K₂ parameters

### Aggregation to Scalar Weight

Hygeia-Graph maps parameter blocks to single scalar edge weights using the `aggregator` function:

| Aggregator | Formula | Description |
|------------|---------|-------------|
| `max_abs` (default) | max(|θ|) | Maximum absolute parameter |
| `l2_norm` | √(Σθ²) | L2 norm of parameter block |
| `mean` | Σθ/n | Mean of parameters |
| `mean_abs` | Σ|θ|/n | Mean absolute value |
| `sum_abs` | Σ|θ| | Sum of absolute values |
| `max` | max(θ) | Maximum (signed) |

**Recommendation**: Use `max_abs` (default) for interpretable edge weights representing the strongest effect.

### Sign Assignment

The `sign_strategy` determines how edge sign is assigned:

| Strategy | Description |
|----------|-------------|
| `dominant` (default) | Sign of parameter with largest |θ| |
| `mean` | Sign of mean(θ) |
| `none` | No sign assigned (unsigned) |

**Interpretation**:
- `positive`: Variables tend to co-occur or vary together
- `negative`: Variables tend to be inversely related
- `zero`: No detectable association

### Zero Tolerance

Parameters with |θ| < `zero_tolerance` (default: 1e-12) are treated as zero.

## Missing Data Policy

Hygeia-Graph enforces a **warn_and_abort** policy for missing data:

1. Data is scanned for missing values (NA, empty strings)
2. If missing values detected:
   - Warning message logged
   - Analysis aborted
   - `results.json` created with `status: "failed"` and error message

**Rationale**: Automatic imputation can introduce bias. Users should handle missing data externally using appropriate methods (e.g., multiple imputation via MICE, maximum likelihood estimation).

**Recommendation**: Preprocess data to remove or impute missing values before loading into Hygeia-Graph.

## Outputs

### results.json Structure

The primary output contains:

```json
{
  "analysis_id": "uuid",
  "status": "success|failed",
  "nodes": [...],
  "edges": [...],
  "messages": [...],
  "engine": {...}
}
```

### Node Attributes

Each node includes:
- `id`: Unique identifier
- `column`: Original column name
- `mgm_type`: Variable type (g/c/p)
- `measurement_level`: Continuous/nominal/ordinal/count
- `level`: Number of categories (1 for continuous/count)

### Edge Attributes

Each edge includes:
- `source`, `target`: Connected node IDs
- `weight`: Aggregated scalar weight
- `sign`: positive/negative/zero/unsigned
- `block_summary`: Statistics of parameter block (n_params, l2_norm, mean, max, min, max_abs)

## Centrality Metrics

Hygeia-Graph computes the following network centrality measures:

### Strength Centrality

Sum of edge weights incident to a node:

```
Strength(i) = Σⱼ |w_ij|
```

Interpretation: Nodes with high strength have strong overall connectivity.

### Betweenness Centrality

Proportion of shortest paths passing through a node:

```
Betweenness(i) = Σ_{s≠i≠t} (σ_st(i) / σ_st)
```

Interpretation: Nodes with high betweenness act as bridges in the network.

### Closeness Centrality

Inverse of average distance to all other nodes:

```
Closeness(i) = (n-1) / Σⱼ d(i,j)
```

For weighted networks, distance is computed as inverse weight.

Interpretation: Nodes with high closeness can efficiently reach all other nodes.

## Software Implementation

- **R Package**: `mgm` (Haslbeck & Waldorp, 2020)
- **Python Interface**: Subprocess bridge with JSON I/O
- **Visualization**: PyVis (vis.js wrapper)
- **Framework**: Streamlit

## References

Haslbeck, J. M. B., & Waldorp, L. J. (2020). mgm: Estimating Time-Varying Mixed Graphical Models in High-Dimensional Data. *Journal of Statistical Software*, 93(8), 1-46. https://doi.org/10.18637/jss.v093.i08

Chen, J., & Chen, Z. (2008). Extended Bayesian information criteria for model selection with large model spaces. *Biometrika*, 95(3), 759-771.
