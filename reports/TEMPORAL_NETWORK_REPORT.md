# Temporal Network Dynamics Module Report

## Overview
Implemented a new **Temporal Network Dynamics** module allowing users to estimate:
1.  **Temporal Network (PDC)**: Lag-1 predictive relationships (Directed).
2.  **Contemporaneous Network (PCC)**: Residual associations (Undirected).

Uses the R `graphicalVAR` package with LASSO regularization.

## Key Features
-   **Dual Network View**: Separate tabs for Temporal and Contemporaneous networks.
-   **Guardrails**:
    -   Validates long-format data (Time + optional ID).
    -   Checks for equal time intervals.
    -   Enforces minimum data length (<20 rows blocked).
    -   **Advanced Unlock**: Allows bypassing strict checks (e.g., >20% missing) with explicit user consent.
-   **Imputation**: Options for Linear Interpolation (`zoo::na.approx`) or Kalman (`imputeTS`, advanced).
-   **Privacy**: Temporary R files deleted immediately. Outputs only stored in memory until ZIP download.

## Implementation Details
1.  **R Backend**:
    -   `r/run_temporal_var.R`: CLI wrapper for `graphicalVAR`. Checks inputs and performs optional detrending/imputation.
2.  **Python Validation**:
    -   `src/hygeia_graph/temporal_validation.py`: Strictly validates structure before calling R.
3.  **UI**:
    -   New page "Temporal Networks (VAR)" in "Advanced" section.
    -   Localized strings in English and Vietnamese.

## Verification
### Automated Tests
-   `tests/test_temporal_validation_unit.py` (PASSED): Covers input validation, interval checking, and missing data logic.
-   `tests/test_temporal_integration_optional.py` (SKIPPED): Skipped if `graphicalVAR` missing, validates end-to-end flow.

### Manual QA Steps (Hugging Face / Local)
1.  **Load Data**: Upload a long-format CSV (e.g., columns: `time`, `id`, `var1`, `var2`).
2.  **Navigate**: Go to "Temporal Networks (VAR)".
3.  **Setup**: Select `time`, `id` (optional), and numeric variables.
4.  **Run**: Click "Run Temporal Analysis".
5.  **Output**: Verify both "Temporal (Directed)" and "Contemporaneous (Undirected)" tabs populate with graphs and tables.
6.  **Export**: Download ZIP and verify contents (`PDC.csv`, `PCC.csv`).

## Limitations
-   **Causality**: Estimates are predictive (Granger), not necessarily causal.
-   **Missing Data**: `graphicalVAR` does not handle NAs internally; imputation is required if any NAs exist.
-   **Performance**: R subprocess overhead exists (~2-5s startup).
