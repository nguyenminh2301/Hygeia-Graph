# Troubleshooting

This guide addresses common issues when installing and running Hygeia-Graph.

## Installation Issues

### ModuleNotFoundError: No module named 'hygeia_graph'

**Cause**: The package is not installed in the Python environment.

**Solution**:
```bash
pip install -e .
```

This installs the package in development mode from the `src/` directory.

---

### Rscript not found / 'Rscript' is not recognized

**Cause**: R is not installed or not on the system PATH.

**Solutions**:

1. **Install R**: Download from https://cran.r-project.org/

2. **Add R to PATH**:
   - **Windows**: Add `C:\Program Files\R\R-4.x.x\bin` to PATH
   - **macOS/Linux**: R installer typically adds to PATH automatically

3. **Verify installation**:
   ```bash
   Rscript --version
   ```

---

### R package installation fails

**Cause**: Required R packages (mgm, jsonlite, digest, uuid) are not installed.

**Solution**:
```bash
Rscript r/install.R
```

If this fails, install manually in R:
```r
install.packages(c("mgm", "jsonlite", "digest", "uuid"), repos = "https://cran.r-project.org")
```

**Common sub-issues**:
- **Network error**: Check internet connection and CRAN mirror
- **Compilation error**: Install Rtools (Windows) or Xcode CLI (macOS)

---

### pip install fails with build errors

**Cause**: Missing build tools or old pip version.

**Solutions**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install build tools (if needed)
pip install setuptools wheel
```

---

## Runtime Issues

### Missing values abort (MISSING_DATA_ABORT)

**Cause**: The dataset contains missing values (NA, empty strings).

**Message**:
```
MISSING_DATA_ABORT: Dataset contains 5 variables with missing values
```

**Solution**: Hygeia-Graph does not impute missing data. You must:
1. Remove rows with missing values
2. Or impute using external tools (e.g., MICE in R, sklearn.impute in Python)

**Best practice**: Check for missing values before uploading:
```python
import pandas as pd
df = pd.read_csv("data.csv")
print(df.isna().sum())  # Should be all zeros
```

---

### CATEGORY_MAPPING_FAILED

**Cause**: A categorical value in the data doesn't match the schema's category list.

**Example**:
```
Schema defines: ["Yes", "No"]
Data contains: ["Y", "N"]  # Different values!
```

**Solution**:
1. Re-run schema inference to detect actual categories
2. Or edit the schema to match data values exactly

---

### LEVEL_MISMATCH_DATA

**Cause**: The number of unique categories in data differs from schema's `level`.

**Example**:
```
Schema: level = 3
Data has: ["A", "B"]  # Only 2 unique values
```

**Solution**:
1. Verify the schema `level` matches unique category count
2. Re-infer schema from data if needed

---

### JSON validation errors

**Cause**: Schema or model spec JSON is malformed or missing required fields.

**Diagnosis**:
```bash
python -m hygeia_graph.validate schema path/to/schema.json
python -m hygeia_graph.validate model_spec path/to/model_spec.json
```

**Common issues**:
- Missing `spec_version` or `schema_version`
- Invalid `mgm_type` (must be g/c/p)
- `level` doesn't match `categories` length

---

### R subprocess timeout

**Cause**: MGM computation taking too long for large datasets.

**Solutions**:
1. Increase timeout in advanced options (default: 300s)
2. Reduce dataset size (fewer rows/variables)
3. Use higher EBIC gamma (sparser, faster model)

---

### Empty network (no edges)

**Cause**: Regularization too strong or weak associations.

**Solutions**:
1. Lower EBIC gamma (e.g., 0.25) for less sparsity
2. Lower elastic net alpha for less L1 penalty
3. Verify data has actual correlations

---

## Deployment Issues

### Streamlit Cloud: R package installation fails

**Cause**: Streamlit Cloud's R environment may have issues with CRAN packages.

**Solution**: Use Docker deployment instead:
```bash
docker build -t hygeia-graph .
docker run -p 8501:8501 hygeia-graph
```

---

### Docker build fails

**Common issues**:

1. **Disk space**: Docker needs ~2GB for R packages
   ```bash
   docker system prune  # Clean up
   ```

2. **Network errors**: CRAN mirror unreachable
   - Retry the build
   - Use a different CRAN mirror in `r/install.R`

3. **Build timeout**: Increase Docker's resources

---

### Port already in use

**Cause**: Another process is using port 8501.

**Solutions**:
```bash
# Use different port
streamlit run app.py --server.port 8502

# Or for Docker
docker run -p 8502:8502 -e PORT=8502 hygeia-graph
```

---

## Getting Help

If you encounter an issue not listed here:

1. **Check the logs**: Error messages often indicate the cause
2. **Run diagnostics**:
   ```bash
   python -c "import hygeia_graph; print(hygeia_graph.__version__)"
   Rscript --version
   Rscript -e "library(mgm); packageVersion('mgm')"
   ```
3. **Open an issue**: https://github.com/nguyenminh2301/Hygeia-Graph/issues

Include:
- Python/R versions
- Error message (full traceback)
- Steps to reproduce
- Sample data (if possible, anonymized)
