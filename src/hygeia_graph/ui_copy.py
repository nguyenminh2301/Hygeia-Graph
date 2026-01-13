"""UI text snippets and copy for Hygeia-Graph."""

# MGM Types explanation
MGM_TYPES_EXPLANATION = """
**MGM node types:**
- **g (Gaussian):** continuous numeric variables (e.g., labs, BMI)
- **c (Categorical):** nominal/ordinal variables (e.g., stage, gender)
- **p (Poisson):** count variables (non-negative integers, e.g., hospital days)

*Tip: Review and correct types before modeling.*
"""

# Privacy notice
PRIVACY_NOTICE = """
🔒 **Privacy:** All temporary files are deleted immediately after each run.
Nothing is stored server-side.
"""

# Clear-all confirmation
CLEAR_ALL_CONFIRM = "✅ Cleared. No data retained in memory."

# Ephemeral files notice
EPHEMERAL_NOTICE = """
ℹ️ Temporary files are deleted automatically after each analysis run.
Use 'Clear all' to remove data from memory.
"""

# Analysis goal descriptions
GOAL_DESCRIPTIONS = {
    "explore": "Build network and explore centrality, communities, and edges.",
    "comparison": "Compare two groups using Network Comparison Test (NCT).",
    "robustness": "Assess network stability via bootstrap analysis (bootnet).",
    "lasso": "Reduce dimensionality with LASSO before network modeling.",
    "publication": "Generate publication-ready figures and tables.",
}

# Next button labels
NEXT_LABELS = {
    "Model Settings": "Next: Model Settings →",
    "Run MGM": "Next: Run MGM →",
    "Explore": "Next: Explore →",
    "Robustness": "Next: Robustness →",
    "Comparison": "Next: Comparison →",
    "Report & Export": "Next: Report & Export →",
    "Preprocessing": "Go to LASSO Preprocessing →",
}

# Status messages
STATUS_SCHEMA_READY = "✅ Schema prepared"
STATUS_SPEC_READY = "✅ Model settings prepared"
STATUS_MGM_SUCCESS = "✅ MGM analysis completed successfully"
STATUS_MGM_FAILED = "❌ MGM analysis failed"
