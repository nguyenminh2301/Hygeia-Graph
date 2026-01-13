# Hygeia-Graph Test Report

**Date:** 2026-01-14 00:38:26

**Python:** 3.13.6
**R:** 4.3.3

---

## Test Results Summary


| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Data Loading | 9 | 0 | 0 |
| Schema Generation | 12 | 0 | 0 |
| Model Specification | 9 | 0 | 0 |
| MGM Execution | 0 | 0 | 3 |
| Descriptives | 0 | 3 | 0 |
| Localization | 2 | 0 | 0 |
| **Total** | **32** | **3** | **3** |


## Detailed Results


### Data Loading


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| File exists (easy) | ✅ PASSED | 0.00s | Found G:\My Drive\Minh-ca nhan\Github\Hygeia-Graph\assets\example_easy.csv |
| Load CSV (easy) | ✅ PASSED | 0.00s | 140 rows, 6 cols |
| Row count (easy) | ✅ PASSED | 0.00s | 140 rows |
| File exists (medium) | ✅ PASSED | 0.00s | Found G:\My Drive\Minh-ca nhan\Github\Hygeia-Graph\assets\example_medium.csv |
| Load CSV (medium) | ✅ PASSED | 0.00s | 280 rows, 12 cols |
| Row count (medium) | ✅ PASSED | 0.00s | 280 rows |
| File exists (hard) | ✅ PASSED | 0.00s | Found G:\My Drive\Minh-ca nhan\Github\Hygeia-Graph\assets\example_hard.csv |
| Load CSV (hard) | ✅ PASSED | 0.00s | 600 rows, 32 cols |
| Row count (hard) | ✅ PASSED | 0.00s | 600 rows |


### Schema Generation


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| Infer variables (easy) | ✅ PASSED | 0.00s | 6 variables inferred |
| Build schema (easy) | ✅ PASSED | 0.00s | 6 variables |
| Schema validation (easy) | ✅ PASSED | 0.00s | Valid JSON Schema |
| Variable types (easy) | ✅ PASSED | 0.00s | g: 3, c: 2, p: 1 |
| Infer variables (medium) | ✅ PASSED | 0.00s | 12 variables inferred |
| Build schema (medium) | ✅ PASSED | 0.00s | 12 variables |
| Schema validation (medium) | ✅ PASSED | 0.00s | Valid JSON Schema |
| Variable types (medium) | ✅ PASSED | 0.00s | g: 7, c: 4, p: 1 |
| Infer variables (hard) | ✅ PASSED | 0.00s | 32 variables inferred |
| Build schema (hard) | ✅ PASSED | 0.00s | 32 variables |
| Schema validation (hard) | ✅ PASSED | 0.00s | Valid JSON Schema |
| Variable types (hard) | ✅ PASSED | 0.00s | g: 18, c: 11, p: 3 |


### Model Specification


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| Default settings (easy) | ✅ PASSED | 0.00s | EBIC gamma=0.5 |
| Build model spec (easy) | ✅ PASSED | 0.00s | Analysis ID: 1b72dd22... |
| Model spec validation (easy) | ✅ PASSED | 0.00s | Valid JSON Schema |
| Default settings (medium) | ✅ PASSED | 0.00s | EBIC gamma=0.5 |
| Build model spec (medium) | ✅ PASSED | 0.00s | Analysis ID: 4b44c74a... |
| Model spec validation (medium) | ✅ PASSED | 0.00s | Valid JSON Schema |
| Default settings (hard) | ✅ PASSED | 0.00s | EBIC gamma=0.5 |
| Build model spec (hard) | ✅ PASSED | 0.00s | Analysis ID: 3a6dd087... |
| Model spec validation (hard) | ✅ PASSED | 0.00s | Valid JSON Schema |


### MGM Execution


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| MGM execution (easy) | ⏭️ SKIPPED | 0.00s | Validation failed for schema:
  /: Additional properties are not allowed ('centrality', 'edge_mapping', 'engine', 'input', 'mgm', 'missing_policy', 'random_seed', 'spec_version', 'visualization' were unexpected)
  /: 'schema_version' is a required property
  /: 'dataset' is a required property
  /: 'variables' is a required property |
| MGM execution (medium) | ⏭️ SKIPPED | 0.00s | Validation failed for schema:
  /: Additional properties are not allowed ('centrality', 'edge_mapping', 'engine', 'input', 'mgm', 'missing_policy', 'random_seed', 'spec_version', 'visualization' were unexpected)
  /: 'schema_version' is a required property
  /: 'dataset' is a required property
  /: 'variables' is a required property |
| MGM execution (hard) | ⏭️ SKIPPED | 0.00s | Validation failed for schema:
  /: Additional properties are not allowed ('centrality', 'edge_mapping', 'engine', 'input', 'mgm', 'missing_policy', 'random_seed', 'spec_version', 'visualization' were unexpected)
  /: 'schema_version' is a required property
  /: 'dataset' is a required property
  /: 'variables' is a required property |


### Descriptives


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| Descriptive stats (easy) | ❌ FAILED | 0.00s | 'measurement_level' |
| Descriptive stats (medium) | ❌ FAILED | 0.00s | 'measurement_level' |
| Descriptive stats (hard) | ❌ FAILED | 0.00s | 'measurement_level' |


### Localization


| Test | Status | Duration | Details |
|------|--------|----------|---------|
| English localization | ✅ PASSED | 0.00s | intro_title: Welcome to Hygeia-Graph... |
| Vietnamese localization | ✅ PASSED | 0.00s | intro_title: Welcome to Hygeia-Graph... |

