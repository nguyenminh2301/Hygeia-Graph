#!/usr/bin/env Rscript

# run_temporal_var.R - CLI runner for graphicalVAR
# Usage: Rscript r/run_temporal_var.R --data <csv> --time_col <col> --vars <v1,v2> --out_dir <dir> ...

suppressPackageStartupMessages({
  library(graphicalVAR)
  library(jsonlite)
  library(zoo) # For na.approx
})

# 1. Parse Arguments
args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(args) {
  options <- list(
    data = NULL,
    id_col = NULL,
    time_col = NULL,
    vars = NULL,
    out_dir = NULL,
    gamma = 0.5,
    n_lambda = 50,
    scale = TRUE,
    detrend = FALSE,
    impute = "none",
    unequal_ok = FALSE,
    seed = 1,
    quiet = FALSE
  )
  
  i <- 1
  while (i <= length(args)) {
    arg <- args[i]
    val <- args[i+1]
    
    if (arg == "--data") options$data <- val
    else if (arg == "--id_col") options$id_col <- val
    else if (arg == "--time_col") options$time_col <- val
    else if (arg == "--vars") options$vars <- unlist(strsplit(val, ","))
    else if (arg == "--out_dir") options$out_dir <- val
    else if (arg == "--gamma") options$gamma <- as.numeric(val)
    else if (arg == "--n_lambda") options$n_lambda <- as.integer(val)
    else if (arg == "--scale") options$scale <- as.logical(as.integer(val))
    else if (arg == "--detrend") options$detrend <- as.logical(as.integer(val))
    else if (arg == "--impute") options$impute <- val
    else if (arg == "--unequal_ok") options$unequal_ok <- as.logical(as.integer(val))
    else if (arg == "--seed") options$seed <- as.integer(val)
    else if (arg == "--quiet") options$quiet <- TRUE
    
    i <- i + 2
  }
  return(options)
}

opts <- parse_args(args)
set.seed(opts$seed)

# Ensure output directory exists
if (!dir.exists(opts$out_dir)) dir.create(opts$out_dir, recursive = TRUE)
dir.create(file.path(opts$out_dir, "tables"), showWarnings = FALSE)
dir.create(file.path(opts$out_dir, "meta"), showWarnings = FALSE)

meta_path <- file.path(opts$out_dir, "meta", "temporal_meta.json")

# Helper to write failure
write_failure <- function(code, message) {
  err_meta <- list(
    status = "failed",
    error = list(code = code, message = message),
    computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  )
  write(toJSON(err_meta, auto_unbox = TRUE, pretty = TRUE), file = meta_path)
  quit(status = 0) # Exit cleanly so Python can read JSON
}

# 2. Load Data
if (!file.exists(opts$data)) {
  write_failure("FILE_NOT_FOUND", paste("Data file not found:", opts$data))
}

df <- read.csv(opts$data, check.names = FALSE, stringsAsFactors = FALSE)

# Validate Columns
required_cols <- c(opts$time_col, opts$vars)
if (!is.null(opts$id_col) && opts$id_col != "") {
  required_cols <- c(opts$id_col, required_cols)
}

missing_cols <- setdiff(required_cols, names(df))
if (length(missing_cols) > 0) {
  write_failure("MISSING_COLUMNS", paste("Missing columns:", paste(missing_cols, collapse = ", ")))
}

# Sort data
if (!is.null(opts$id_col) && opts$id_col != "") {
  df <- df[order(df[[opts$id_col]], df[[opts$time_col]]), ]
} else {
  df <- df[order(df[[opts$time_col]]), ]
  opts$id_col <- NULL # treat as null if empty/absent
}

# 3. Preprocessing (Imputation & Detrending)
# Extract numeric vars for check
vars_df <- df[, opts$vars, drop = FALSE]
if (!all(sapply(vars_df, is.numeric))) {
  write_failure("NON_NUMERIC", "All analysis variables must be numeric.")
}

# Imputation Logic
apply_imputation <- function(x, method) {
  if (method == "none") {
    return(x) # Let graphicalVAR fail or handle NAs if support exists (it doesn't tolerate NAs well)
  } else if (method == "linear") {
    # zoo::na.approx, rule=2 for leading/trailing NAs (LOCF/NOCB)
    x_imp <- zoo::na.approx(x, na.rm = FALSE) 
    return(zoo::na.fill(x_imp, "extend")) # Fill ends
  } else if (method == "kalman") {
    if (requireNamespace("imputeTS", quietly = TRUE)) {
      return(imputeTS::na_kalman(x))
    } else {
      stop("imputeTS package missing for kalman")
    }
  }
  return(x)
}

# Apply per subject (if ID exists) or global
process_vars <- function(sub_df) {
  v_data <- sub_df[, opts$vars, drop = FALSE]
  
  # Impute
  if (opts$impute != "none") {
    for (v in names(v_data)) {
      v_data[[v]] <- apply_imputation(v_data[[v]], opts$impute)
    }
  }
  
  # Check Remaining NAs
  if (any(is.na(v_data))) {
     # If method was none, this is where we check strictly
     stop("Missing values present after imputation step.")
  }
  
  # Detrend
  if (opts$detrend) {
    time_vec <- sub_df[[opts$time_col]]
    for (v in names(v_data)) {
      # Simple linear detrend
      fit <- lm(v_data[[v]] ~ time_vec)
      v_data[[v]] <- residuals(fit) + mean(v_data[[v]])
    }
  }
  
  return(v_data)
}

# Safety wrapper for processing
data_ready <- tryCatch({
  if (!is.null(opts$id_col)) {
    # Split-Apply-Combine or Loop
    ids <- unique(df[[opts$id_col]])
    processed_list <- list()
    for (pid in ids) {
      sub_mask <- df[[opts$id_col]] == pid
      sub_df <- df[sub_mask, ]
      processed_list[[as.character(pid)]] <- process_vars(sub_df)
    }
    # Re-assemble? 
    # graphicalVAR expects 'vars' and 'idvar' if performing multilevel, but
    # here we are doing "pooled" estimation (v1 scope). 
    # For pooled: stack all processed frames, KEEP id column for graphicalVAR to know breaks.
    
    # Re-bind
    full_processed <- do.call(rbind, processed_list)
    
    # Add ID column back for graphicalVAR input
    # Be careful with order matching
    full_processed[[opts$id_col]] <- rep(ids, sapply(processed_list, nrow)) # Only if order preserved?
    # Better: 
    # process_vars relies on sub_df order. 
    # Let's iterate and bind rows safely.
    
    # Actually, graphicalVAR with idvar argument handles multiple subjects by assuming independence between them.
    # It estimates *one* network (pooled).
    
    # We construct the input DF: needed vars + id col
    final_df <- do.call(rbind, processed_list)
    final_df[[opts$id_col]] <- unlist(lapply(ids, function(i) df[[opts$id_col]][df[[opts$id_col]] == i]))
    final_df
    
  } else {
    # Single subject
    process_vars(df)
  }
}, error = function(e) {
  write_failure("PREPROCESSING_ERROR", as.character(e))
})


# 4. Run graphicalVAR
tryCatch({
  if (!is.null(opts$id_col)) {
    res <- graphicalVAR(
      data = data_ready,
      vars = opts$vars,
      idvar = opts$id_col,
      gamma = opts$gamma,
      nLambda = opts$n_lambda,
      scale = opts$scale,
      verbose = !opts$quiet
    )
  } else {
    res <- graphicalVAR(
      data = data_ready,
      gamma = opts$gamma,
      nLambda = opts$n_lambda,
      scale = opts$scale,
      verbose = !opts$quiet
    )
  }
}, error = function(e) {
  write_failure("ESTIMATION_ERROR", paste("graphicalVAR failed:", e$message))
})

# 5. Extract Results
PDC <- res$PDC # Directed (Temporal)
PCC <- res$PCC # Undirected (Contemporaneous)

# Write Matrices
write.csv(PDC, file.path(opts$out_dir, "tables", "PDC.csv"), row.names = TRUE)
write.csv(PCC, file.path(opts$out_dir, "tables", "PCC.csv"), row.names = TRUE)

# Edge List Extraction
extract_edges <- function(mat, type="PDC") {
  edges <- list()
  nms <- rownames(mat)
  for (i in 1:nrow(mat)) {
    for (j in 1:ncol(mat)) {
      w <- mat[i, j]
      if (w != 0) {
        if (type == "PCC" && i >= j) next # Undirected: output only upper triangle? or both?
        # PyVis usually likes distinct edges. 
        # For undirected PCC, i<j is unique.
        
        src <- nms[i]
        tgt <- nms[j]
        
        if (type == "PDC") {
          # t-1 -> t
          # src is lagged, tgt is current
          # Just record as src->tgt with type 'directed'
          is_directed <- TRUE
        } else {
           is_directed <- FALSE
        }
        
        edges[[length(edges) + 1]] <- list(
          source = src,
          target = tgt,
          weight = w,
          abs_weight = abs(w),
          sign = sign(w),
          type = type
        )
      }
    }
  }
  
  if (length(edges) == 0) return(data.frame())
  do.call(rbind, lapply(edges, as.data.frame))
}

edges_pdc <- extract_edges(PDC, "PDC")
edges_pcc <- extract_edges(PCC, "PCC")

write.csv(edges_pdc, file.path(opts$out_dir, "tables", "temporal_edges.csv"), row.names = FALSE)
write.csv(edges_pcc, file.path(opts$out_dir, "tables", "contemporaneous_edges.csv"), row.names = FALSE)

# 6. Write Meta
meta <- list(
  analysis_id = "temporal_v1", # Placeholder, UI should override if needed by tracking outer ID
  computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  status = "success",
  settings = list(
    gamma = opts$gamma,
    n_lambda = opts$n_lambda,
    detrend = opts$detrend,
    impute = opts$impute
  ),
  outputs = list(
    PDC = "tables/PDC.csv",
    PCC = "tables/PCC.csv",
    temporal_edges = "tables/temporal_edges.csv",
    contemporaneous_edges = "tables/contemporaneous_edges.csv"
  ),
  engine = list(
    r_version = R.version.string,
    package_versions = list(
      graphicalVAR = as.character(packageVersion("graphicalVAR")),
      zoo = as.character(packageVersion("zoo"))
    )
  )
)

write(toJSON(meta, auto_unbox = TRUE, pretty = TRUE), file = meta_path)
