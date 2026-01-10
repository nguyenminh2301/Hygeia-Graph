# Next Step: Automated Insights Report

## Summary of Deliverables
Implemented the **Automated Insights Report** generator, which produces a copy-ready Markdown narrative from analysis artifacts.

### Python Modules
- **`src/hygeia_graph/insights_report.py`**:
  - `build_report_payload(...)`: Aggregates results, derived metrics, and robustness outputs into a structured dictionary.
  - `render_report_markdown(...)`: Uses deterministic templates to generate text. Includes required disclaimers (Research Tool Only).
  - `generate_insights_report(...)`: Orchestrator.
- **`src/hygeia_graph/insights_report_utils.py`**:
  - `report_settings_hash`: Ensures reproducible caching of report generation based on settings.

### UI Integration ("Report & Export" Page)
- Added **Report Settings** section:
  - Narrative Style (Paper, Thesis, Concise).
  - Include/Exclude sections (Predictability, Communities, Robustness).
  - Top N Nodes filter.
- **Generate Button**: Creates report and caches it.
- **Preview & Download**:
  - View Markdown.
  - Download `.md`, `.txt`, and `.json` payload.

### Verification

#### Automated Tests
Executed: `pytest tests/test_insights_report_unit.py`
**Result**: Passed.
- Verified payload structure contains required keys.
- Verified markdown contains Disclaimers and Headers.
- Verified deterministic hashing.

#### Manual QA Scenarios
1. **Missing Posthoc**: When `derived_metrics` has no predictability/communities, the report generator gracefully omits those sections/checkboxes.
2. **Missing Robustness**: If `bootnet_meta` is absent, the Robustness section is disabled.
3. **Full Run**: Running MGM + Predictability + Bootstrapping enables all sections. The generated report correctly lists Top 10 nodes, Predictability (R2), and Stability CS-coefficients.

## Usage Guide
1. Finish analysis in **Run MGM** (and optional **Robustness**).
2. Go to **Report & Export**.
3. Select Style (e.g., "Paper").
4. Click **Generate Insights Report**.
5. Copy the "Suggested Paragraph" for your manuscript.
