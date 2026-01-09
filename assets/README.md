# Example Dataset

This directory contains example data and pre-generated artifacts for demonstrating Hygeia-Graph.

## Files

### example_data.csv
Synthetic clinical dataset with 150 patients and 6 variables:

| Column | Type | MGM Type | Description |
|--------|------|----------|-------------|
| Age | Float | Gaussian (g) | Patient age in years |
| CRP | Float | Gaussian (g) | C-Reactive Protein level (mg/L) |
| Gender | String | Categorical (c) | Patient gender (M/F) |
| CancerStage | String | Categorical (c) | Cancer stage (I/II/III/IV, ordinal) |
| HospitalDays | Integer | Poisson (p) | Days hospitalized |
| SymptomCount | Integer | Poisson (p) | Number of symptoms reported |

**Properties**:
- 150 rows (patients)
- No missing values
- Mixed variable types suitable for MGM analysis
- Includes correlations between variables (e.g., CancerStage → HospitalDays → SymptomCount)

### example_schema.json
Pre-generated schema defining variable types and metadata. Validates against `contracts/schema.schema.json`.

**Domain Groups**:
- Demographics: Age, Gender
- Biomarkers: CRP
- Diagnosis: CancerStage
- Utilization: HospitalDays
- Symptoms: SymptomCount

### example_model_spec.json
Pre-generated model specification with recommended defaults. Validates against `contracts/model_spec.schema.json`.

**Key Settings**:
- `lambda_selection`: "EBIC" (locked)
- `ebic_gamma`: 0.5
- `alpha`: 0.5 (elastic net mixing)
- `missing_policy.action`: "warn_and_abort" (locked)
- `aggregator`: "max_abs"
- `sign_strategy`: "dominant"

## Usage

1. **In Streamlit App**: Upload `example_data.csv` to test the full pipeline
2. **Direct Validation**:
   ```bash
   python -m hygeia_graph.validate schema assets/example_schema.json
   python -m hygeia_graph.validate model_spec assets/example_model_spec.json
   ```

## Generating Results

To generate `results.json` from this example:

1. Start the app: `streamlit run app.py`
2. Upload `example_data.csv`
3. Review inferred variable types
4. Click "Run MGM"
5. Download `results.json`

> **Note**: Requires R with the `mgm` package installed.
