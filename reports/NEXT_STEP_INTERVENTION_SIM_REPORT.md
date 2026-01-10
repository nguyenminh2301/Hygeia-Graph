# Next Step: Intervention Simulation (Experimental)

## Summary of Deliverables
Implemented an experimental **"Intervention Simulation"** feature to explore network propagation heuristically. This uses the estimated signed adjacency matrix from MGM to simulate how a change in one node (Delta) might affect others via direct and indirect paths.

**Disclaimer**: This is explicitly labeled as "associational propagation" and "not causal inference" throughout the UI and code.

### Python Backend
- **`src/hygeia_graph/intervention_simulation.py`**:
  - `build_signed_adjacency`: Constructs matrix from `results.json` edges.
  - `simulate_intervention`: Computes damped propagation ($Effect = \Delta \cdot A^k \cdot d^{k-1}$).
  - `build_intervention_table`: Formats results into a standardized DataFrame.
- **`src/hygeia_graph/intervention_utils.py`**:
  - `simulation_settings_hash`: Deterministic hashing for caching.

### UI Integration
- **`src/hygeia_graph/ui_pages.py`**:
  - Added `render_simulation_page`.
  - **Inputs**: Node selector (searchable), Delta (SD or Raw), Steps, Damping.
  - **Outputs**:
    - Bar chart (Plotly) showing top increased/decreased nodes.
    - Data table of effects.
    - JSON/CSV download buttons.
- **`app.py`**:
  - Added "Simulation (Experimental)" to navigation.

### Verification

#### Automated Tests
- **`tests/test_intervention_simulation_unit.py`**: **PASSED**.
  - Verified adjacency metrics construction (symmetry).
  - Verified 1-step and 2-step filtered propagation logic.
  - Verified damping application.

#### Manual QA Scenarios to Run
1. **Prerequisite**: Run MGM Analysis on any dataset.
2. **Navigation**: Go to "Simulation (Experimental)".
3. **Execution**:
   - Select a node (e.g., "Age" or a central symptom).
   - Set Delta = 1.0 (SD).
   - Click "Run Simulation".
4. **Validation**:
   - Check if Bar Chart appears.
   - Check if strongest effects are conceptually consistent (e.g., neighbors in the network).
   - Try changing "Steps" to 1 vs 3 and see if more nodes get affected.

## Usage Guide
1. Run **MGM Analysis** first.
2. Navigate to **Simulation**.
3. Select a target node and magnitude of change.
4. Interpret results as "hypothetical propagation" for generating hypotheses, not as predicted outcomes of a clinical trial.
