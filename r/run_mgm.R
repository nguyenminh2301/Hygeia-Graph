#!/usr/bin/env Rscript
# Hygeia-Graph: MGM Runner with EBIC
# Executes Mixed Graphical Model estimation and produces results.json

# Load required libraries
suppressPackageStartupMessages({
  library(mgm)
  library(jsonlite)
  library(digest)
})

# === Argument Parsing ===
args <- commandArgs(trailingOnly = TRUE)

# Parse arguments
data_path <- NULL
schema_path <- NULL
spec_path <- NULL
out_path <- NULL
quiet <- FALSE
debug <- TRUE

i <- 1
while (i <= length(args)) {
  if (args[i] == "--data" && i < length(args)) {
    data_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--schema" && i < length(args)) {
    schema_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--spec" && i < length(args)) {
    spec_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--out" && i < length(args)) {
    out_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--quiet") {
    quiet <- TRUE
    i <- i + 1
  } else if (args[i] == "--debug") {
    if (i < length(args) && tolower(args[i + 1]) == "false") {
      debug <- FALSE
      i <- i + 2
    } else {
      i <- i + 1
    }
  } else {
    i <- i + 1
  }
}

# Validate required arguments
if (is.null(data_path) || is.null(schema_path) || is.null(spec_path) || is.null(out_path)) {
  cat("ERROR: Missing required arguments\n", file = stderr())
  cat("Usage: Rscript run_mgm.R --data <csv> --schema <json> --spec <json> --out <json> [--quiet] [--debug false]\n", file = stderr())
  quit(status = 1)
}

# === Helper Functions ===

# Compute SHA256 hash of file
compute_file_hash <- function(path) {
  if (file.exists(path)) {
    return(digest(file = path, algo = "sha256"))
  }
  return(NULL)
}

# Create results structure
create_results <- function(status = "failed", messages = list()) {
  list(
    result_version = "0.1.0",
    analysis_id = NULL,  # Will be filled
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    status = status,
    engine = list(
      name = "R.mgm",
      r_version = R.version.string,
      package_versions = list(
        mgm = as.character(packageVersion("mgm")),
        jsonlite = as.character(packageVersion("jsonlite")),
        digest = as.character(packageVersion("digest"))
      )
    ),
    input = list(),
    messages = messages,
    nodes = list(),
    edges = list()
  )
}

# Add message to results
add_message <- function(results, level, code, message, details = NULL) {
  msg <- list(level = level, code = code, message = message)
  if (!is.null(details)) {
    msg$details <- details
  }
  results$messages[[length(results$messages) + 1]] <- msg
  return(results)
}

# Write results.json
write_results <- function(results, path) {
  # Ensure output directory exists
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  
  # Write JSON
  write_json(results, path, pretty = TRUE, auto_unbox = TRUE, null = "null")
  
  if (!quiet) {
    n_edges <- length(results$edges)
    cat(sprintf("WROTE: %s (status=%s, edges=%d)\n", path, results$status, n_edges))
  }
}

# === Main Execution Pipeline ===

start_time <- proc.time()
results <- create_results()

tryCatch({
  
  # === Load Schema and Spec JSONs ===
  if (!quiet) cat("Loading schema and spec...\n")
  
  schema <- fromJSON(schema_path, simplifyVector = FALSE)
  spec <- fromJSON(spec_path, simplifyVector = FALSE)
  
  # Set analysis_id
  if (!is.null(spec$analysis_id)) {
    results$analysis_id <- spec$analysis_id
  } else if (!is.null(schema$analysis_id)) {
    results$analysis_id <- schema$analysis_id
  } else {
    results$analysis_id <- uuid::UUIDgenerate()
  }
  
  # Add input hashes
  results$input$schema_sha256 <- compute_file_hash(schema_path)
  results$input$spec_sha256 <- compute_file_hash(spec_path)
  results$input$data_sha256 <- compute_file_hash(data_path)
  results$input$schema_ref <- "schema.json"
  
  # === Load Data CSV ===
  if (!quiet) cat("Loading data...\n")
  
  df <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)
  
  # === Validate Columns ===
  schema_cols <- sapply(schema$variables, function(v) v$column)
  missing_cols <- setdiff(schema_cols, colnames(df))
  
  if (length(missing_cols) > 0) {
    results <- add_message(
      results, "error", "COLUMN_NOT_FOUND",
      sprintf("Missing columns in data: %s", paste(missing_cols, collapse = ", "))
    )
    write_results(results, out_path)
    quit(status = 0)
  }
  
  #=== Check Missing Data (warn_and_abort policy) ===
  if (!quiet) cat("Checking for missing data...\n")
  
  has_missing <- FALSE
  for (v in schema$variables) {
    col <- v$column
    col_data <- df[[col]]
    
    # Check for NA
    if (any(is.na(col_data))) {
      has_missing <- TRUE
      break
    }
    
    # Check for empty strings in categorical
    if (!is.null(v$mgm_type) && v$mgm_type == "c") {
      if (any(col_data == "" | is.null(col_data))) {
        has_missing <- TRUE
        break
      }
    }
  }
  
  if (has_missing) {
    # Build nodes from schema for failed response
    results$nodes <- lapply(schema$variables, function(v) {
      node <- list(
        id = v$id,
        column = v$column,
        mgm_type = v$mgm_type,
        measurement_level = v$measurement_level,
        level = v$level
      )
      if (!is.null(v$label)) node$label <- v$label
      if (!is.null(v$domain_group)) node$domain_group <- v$domain_group
      node
    })
    
    results <- add_message(
      results, "error", "MISSING_DATA_ABORT",
      "Missing values detected. Hygeia-Graph does not impute; please preprocess externally (e.g., MICE) and re-run."
    )
    write_results(results, out_path)
    quit(status = 0)
  }
  
  # === Encode Data to Numeric Matrix ===
  if (!quiet) cat("Encoding data for MGM...\n")
  
  encoded_df <- data.frame(matrix(ncol = 0, nrow = nrow(df)))
  type_vec <- character(length(schema$variables))
  level_vec <- integer(length(schema$variables))
  
  for (i in seq_along(schema$variables)) {
    v <- schema$variables[[i]]
    col <- v$column
    mgm_type <- v$mgm_type
    level <- v$level
    
    x <- df[[col]]
    
    if (mgm_type == "g") {
      # Gaussian: numeric conversion
      x_num <- suppressWarnings(as.numeric(x))
      if (any(is.na(x_num))) {
        results <- add_message(
          results, "error", "NON_NUMERIC_GAUSSIAN",
          sprintf("Cannot convert column '%s' to numeric for Gaussian variable", col)
        )
        write_results(results, out_path)
        quit(status = 0)
      }
      encoded_df[[v$id]] <- x_num
      type_vec[i] <- "g"
      level_vec[i] <- 1
      
    } else if (mgm_type == "p") {
      # Poisson: validate non-negative integers
      x_num <- suppressWarnings(as.numeric(x))
      if (any(!is.finite(x_num)) || any(x_num < 0) || any(abs(x_num - round(x_num)) > 1e-9)) {
        results <- add_message(
          results, "error", "INVALID_COUNT_DATA",
          sprintf("Column '%s' contains invalid count data (must be non-negative integers)", col)
        )
        write_results(results, out_path)
        quit(status = 0)
      }
      encoded_df[[v$id]] <- x_num
      type_vec[i] <- "p"
      level_vec[i] <- 1
      
    } else if (mgm_type == "c") {
      # Categorical: map to integer codes
      if (!is.null(v$categories) && length(v$categories) > 0) {
        # Use schema categories
        categories <- unlist(v$categories)
        codes <- match(as.character(x), categories)
        if (any(is.na(codes))) {
          results <- add_message(
            results, "error", "CATEGORY_MAPPING_FAILED",
            sprintf("Cannot map column '%s' values to schema categories", col)
          )
          write_results(results, out_path)
          quit(status = 0)
        }
        if (length(categories) != level) {
          results <- add_message(
            results, "error", "LEVEL_MISMATCH_SCHEMA",
            sprintf("Column '%s': schema categories count != level", col)
          )
          write_results(results, out_path)
          quit(status = 0)
        }
      } else {
        # Infer from data
        if (is.numeric(x)) {
          uniq <- sort(unique(x))
        } else {
          uniq <- sort(unique(as.character(x)))
        }
        
        if (length(uniq) != level) {
          results <- add_message(
            results, "error", "LEVEL_MISMATCH_DATA",
            sprintf("Column '%s': data unique count (%d) != level (%d)", col, length(uniq), level)
          )
          write_results(results, out_path)
          quit(status = 0)
        }
        
        codes <- match(x, uniq)
      }
      
      encoded_df[[v$id]] <- codes
      type_vec[i] <- "c"
      level_vec[i] <- level
    }
  }
  
  # Convert to matrix
  data_mat <- as.matrix(encoded_df)
  
  # Final validation
  if (!is.matrix(data_mat) || any(is.na(data_mat)) || any(!is.finite(data_mat))) {
    results <- add_message(
      results, "error", "ENCODING_FAILED",
      "Data encoding produced invalid matrix"
    )
    write_results(results, out_path)
    quit(status = 0)
  }
  
  # === Extract MGM Parameters from Spec ===
  if (!quiet) cat("Configuring MGM parameters...\n")
  
  mgm_params <- spec$mgm
  reg_params <- mgm_params$regularization
  
  # Enforce constraints
  if (mgm_params$k != 2) {
    results <- add_message(results, "error", "UNSUPPORTED_K", "Only k=2 (pairwise) is supported")
    write_results(results, out_path)
    quit(status = 0)
  }
  
  if (reg_params$lambda_selection != "EBIC") {
    results <- add_message(results, "error", "INVALID_LAMBDA_SELECTION", "Lambda selection must be EBIC")
    write_results(results, out_path)
    quit(status = 0)
  }
  
  # Set random seed if provided
  if (!is.null(spec$random_seed)) {
    set.seed(spec$random_seed)
  }
  
  # === Execute MGM ===
  if (!quiet) cat("Running MGM with EBIC...\n")
  
  fit <- mgm::mgm(
    data = data_mat,
    type = type_vec,
    level = level_vec,
    k = 2,
    lambdaSel = "EBIC",
    lambdaGam = reg_params$ebic_gamma,
    alphaSeq = reg_params$alpha,
    ruleReg = mgm_params$rule_reg,
    overparameterize = mgm_params$overparameterize,
    scale = mgm_params$scale_gaussian,
    signInfo = mgm_params$sign_info,
    threshold = "none",
    pbar = FALSE,
    warnings = TRUE
  )
  
  # === Extract Pairwise Parameters ===
  if (!quiet) cat("Extracting pairwise interactions...\n")
  
  edges <- list()
  
  if (!is.null(fit$interactions$indicator) && length(fit$interactions$indicator) > 0) {
    indicator <- fit$interactions$indicator[[1]]  # k=2 interactions
    weights <- fit$interactions$weights[[1]]
    
    if (is.matrix(indicator) && nrow(indicator) > 0) {
      for (r in 1:nrow(indicator)) {
        i <- indicator[r, 1]
        j <- indicator[r, 2]
        
        # Extract parameter block
        block <- weights[[r]]
        raw <- as.numeric(unlist(block, use.names = FALSE))
        raw <- raw[!is.na(raw)]  # Remove any NA
        
        if (length(raw) == 0) {
          next  # Skip empty blocks
        }
        
        # Compute block summary
        block_summary <- list(
          n_params = length(raw),
          l2_norm = sqrt(sum(raw^2)),
          mean = mean(raw),
          max = max(raw),
          min = min(raw),
          max_abs = max(abs(raw))
        )
        
        # === Edge Mapping ===
        edge_mapping <- spec$edge_mapping
        aggregator <- edge_mapping$aggregator
        sign_strategy <- edge_mapping$sign_strategy
        zero_tol <- edge_mapping$zero_tolerance
        
        # Compute aggregated weight
        weight <- switch(
          aggregator,
          "l2_norm" = block_summary$l2_norm,
          "mean" = block_summary$mean,
          "max_abs" = block_summary$max_abs,
          "max" = block_summary$max,
          "mean_abs" = mean(abs(raw)),
          "sum_abs" = sum(abs(raw)),
          block_summary$max_abs  # default
        )
        
        # Compute sign
        if (abs(weight) <= zero_tol) {
          sign <- "zero"
          weight <- 0
        } else if (sign_strategy == "none") {
          sign <- "unsigned"
        } else if (sign_strategy == "mean") {
          s <- sign(mean(raw))
          sign <- if (s > 0) "positive" else if (s < 0) "negative" else "unsigned"
        } else if (sign_strategy == "dominant") {
          idx <- which.max(abs(raw))
          s <- sign(raw[idx])
          sign <- if (s > 0) "positive" else if (s < 0) "negative" else "unsigned"
        } else {
          sign <- "unsigned"
        }
        
        # Get variable IDs
        source_id <- schema$variables[[i]]$id
        target_id <- schema$variables[[j]]$id
        
        # Ensure lexicographic ordering
        if (source_id > target_id) {
          temp <- source_id
          source_id <- target_id
          target_id <- temp
        }
        
        # Build edge
        edge <- list(
          source = source_id,
          target = target_id,
          weight = weight,
          sign = sign,
          block_summary = block_summary
        )
        
        if (debug) {
          edge$raw_block <- raw
        }
        
        edges[[length(edges) + 1]] <- edge
      }
    }
  }
  
  # === Build Nodes ===
  nodes <- lapply(schema$variables, function(v) {
    node <- list(
      id = v$id,
      column = v$column,
      mgm_type = v$mgm_type,
      measurement_level = v$measurement_level,
      level = v$level
    )
    if (!is.null(v$label)) node$label <- v$label
    if (!is.null(v$domain_group)) node$domain_group <- v$domain_group
    node
  })
  
  # === Update Results ===
  results$status <- "success"
  results$nodes <- nodes
  results$edges <- edges
  
  # Add optional metadata
  results$mgm_fit <- list(
    lambda_selection = "EBIC",
    ebic_gamma = reg_params$ebic_gamma,
    alpha = reg_params$alpha,
    rule_reg = mgm_params$rule_reg,
    overparameterize = mgm_params$overparameterize,
    k = 2
  )
  
  results$edge_mapping_used <- edge_mapping
  
  results$data_summary <- list(
    row_count = nrow(df),
    column_count = ncol(df),
    missing_rate = 0  # We already aborted if missing
  )
  
  # Compute runtime
  elapsed <- (proc.time() - start_time)[["elapsed"]]
  results$runtime <- list(seconds = elapsed)
  
  if (!quiet) cat(sprintf("MGM completed successfully. Found %d edges.\n", length(edges)))
  
}, error = function(e) {
  results <<- add_message(
    results, "error", "RUNTIME_ERROR",
    conditionMessage(e)
  )
})

# === Write Results ===
write_results(results, out_path)

# Exit with success (we wrote results.json)
quit(status = 0)
