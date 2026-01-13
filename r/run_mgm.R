#!/usr/bin/env Rscript
# Hygeia-Graph: MGM Runner with EBIC
# Executes Mixed Graphical Model estimation and produces results.json

# Load required libraries
suppressPackageStartupMessages({
  library(mgm)
  library(jsonlite)
  library(digest)
  library(igraph)
})

# === Argument Parsing ===
args <- commandArgs(trailingOnly = TRUE)

# Parse arguments
data_path <- NULL
schema_path <- NULL
spec_path <- NULL
out_path <- NULL
posthoc_path <- NULL
model_out_path <- NULL  # NEW: Path to save mgm fit RDS for intervention v2
community_algo <- "spinglass_neg"
spins <- NULL
predictability <- FALSE
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
  } else if (args[i] == "--posthoc_out" && i < length(args)) {
    posthoc_path <- args[i + 1]
    predictability <- TRUE  # Enable predictability by default if posthoc requested
    i <- i + 2
  } else if (args[i] == "--model_out" && i < length(args)) {
    model_out_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--community_algo" && i < length(args)) {
    community_algo <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--spins" && i < length(args)) {
    spins <- as.integer(args[i + 1])
    i <- i + 2
  } else if (args[i] == "--predictability" && i < length(args)) {
    val <- as.integer(args[i + 1])
    predictability <- (val == 1)
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
  
  # === Build Nodes (Populate early to ensure valid JSON on failure) ===
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
    # Nodes are already built above
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
  
  # === Save Model RDS if requested (for intervention v2) ===
  if (!is.null(model_out_path)) {
    if (!quiet) cat(sprintf("Saving model RDS to %s...\n", model_out_path))
    dir.create(dirname(model_out_path), recursive = TRUE, showWarnings = FALSE)
    saveRDS(fit, model_out_path)
  }
  
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
  
  # === Update Results ===
  results$status <- "success"
  # nodes already populated
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

# === R Posthoc Analysis (Optional) ===
if (!is.null(posthoc_path)) {
  if (!quiet) cat("Computing posthoc metrics...\n")
  
  posthoc_res <- list(
    analysis_id = results$analysis_id,
    computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    predictability = list(enabled = FALSE, by_node = list(), metric_by_node = list(), details = list()),
    communities = list(enabled = FALSE, membership = list(), n_communities = 0, params = list()),
    messages = list()
  )
  
  # Helper to add posthoc message
  add_ph_message <- function(ph, level, code, message, details = NULL) {
    msg <- list(level = level, code = code, message = message)
    if (!is.null(details)) msg$details <- details
    ph$messages[[length(ph$messages) + 1]] <- msg
    return(ph)
  }
  
  # 1. Predictability
  if (predictability) {
    if (!quiet) cat("  Predictability (R2/CC/nCC)...\n")
    tryCatch({
      # errorCon="R2", errorCat=c("CC", "nCC")
      # predict.mgm returns list with 'errors' and 'predicted'
      pred_obj <- mgm::predict.mgm(fit, data = data_mat, errorCon = c("R2"), errorCat = c("CC", "nCC", "CCmarg"))
      
      # Extract errors dataframe
      # Columns usually: Variable, Error, Type
      errors_df <- pred_obj$errors
      
      by_node <- list()
      metric_by_node <- list()
      det_R2 <- list()
      det_CC <- list()
      det_nCC <- list()
      det_CCmarg <- list()
      
      # Iterate over schema variables to map back to IDs
      # The errors_df is indexed by column number 1..p matching fit call
      
      for (i in 1:nrow(errors_df)) {
        # mgm usually returns a matrix/df where first col is numeric index?
        # Actually predict.mgm result 'errors' is a matrix with rows = variables
        # Row names might be present?
        # Let's rely on index i matching variables[[i]]
        
        v_id <- schema$variables[[i]]$id
        v_type <- schema$variables[[i]]$mgm_type
        
        # errors_df columns: R2, CC, nCC, CCmarg  (if requested)
        # Note: predict.mgm returns a matrix. Columns are named.
        row_vals <- errors_df[i, , drop = FALSE]
        
        val_primary <- NULL
        metric_name <- NULL
        
        if (v_type %in% c("g", "p")) {
          if ("R2" %in% colnames(row_vals)) {
            val <- as.numeric(row_vals[1, "R2"])
            det_R2[[v_id]] <- val
            val_primary <- val
            metric_name <- "R2"
          }
        } else if (v_type == "c") {
          # Capture details
          if ("CC" %in% colnames(row_vals)) det_CC[[v_id]] <- as.numeric(row_vals[1, "CC"])
          if ("nCC" %in% colnames(row_vals)) det_nCC[[v_id]] <- as.numeric(row_vals[1, "nCC"])
          if ("CCmarg" %in% colnames(row_vals)) det_CCmarg[[v_id]] <- as.numeric(row_vals[1, "CCmarg"])
          
          # Primary: nCC
          if (!is.null(det_nCC[[v_id]])) {
             val_primary <- det_nCC[[v_id]]
             metric_name <- "nCC"
             
             # Warning if negative
             if (val_primary < 0) {
               posthoc_res <- add_ph_message(posthoc_res, "warning", "NEGATIVE_NCC", 
                                             sprintf("Node %s has negative nCC", v_id))
             }
          }
        }
        
        if (!is.null(val_primary)) {
          by_node[[v_id]] <- val_primary
          metric_by_node[[v_id]] <- metric_name
        }
      }
      
      posthoc_res$predictability$enabled <- TRUE
      posthoc_res$predictability$by_node <- by_node
      posthoc_res$predictability$metric_by_node <- metric_by_node
      posthoc_res$predictability$details <- list(
        R2 = det_R2, CC = det_CC, nCC = det_nCC, CCmarg = det_CCmarg
      )
      
    }, error = function(e) {
      posthoc_res <<- add_ph_message(posthoc_res, "error", "PREDICTABILITY_FAILED", conditionMessage(e))
    })
  }
  
  # 2. Communities
  if (!quiet) cat("  Community detection...\n")
  tryCatch({
    # Build graph in igraph
    # We reuse 'edges' list from results, but need a proper igraph object
    # Or cleaner: using the computed 'edges' list is safer as it matches results exactly
    
    # Vertices
    v_ids <- sapply(results$nodes, function(x) x$id)
    g <- make_empty_graph(n = length(v_ids), directed = FALSE)
    V(g)$name <- v_ids
    
    # Edges
    # 'edges' contains source/target/weight/sign (computed above)
    # We should use ALL edges that MGM found (results$edges)
    
    edge_src <- character()
    edge_tgt <- character()
    edge_w_signed <- numeric()
    edge_w_abs <- numeric()
    
    for (e in results$edges) {
       edge_src <- c(edge_src, e$source)
       edge_tgt <- c(edge_tgt, e$target)
       edge_w_signed <- c(edge_w_signed, e$weight)
       edge_w_abs <- c(edge_w_abs, abs(e$weight))
    }
    
    if (length(edge_src) > 0) {
      g <- add_edges(g, rbind(edge_src, edge_tgt))
      E(g)$weight <- edge_w_signed      # default weight attribute
      E(g)$weight_signed <- edge_w_signed
      E(g)$weight_abs <- edge_w_abs
    }
    
    comm <- NULL
    algo_used <- community_algo
    
    if (length(E(g)) == 0) {
       # No edges -> each node is its own community
       comm_membership <- 1:length(v_ids)
       algo_used <- "none (no edges)"
    } else {
      if (community_algo == "spinglass_neg") {
        # Spinglass with neg weights
        s_val <- if (!is.null(spins)) spins else max(10, ceiling(sqrt(length(v_ids))))
        
        # Try spinglass
        out <- tryCatch({
          set.seed(if(!is.null(spec$random_seed)) spec$random_seed else 123)
          cluster_spinglass(g, weights = E(g)$weight_signed, implementation = "neg", 
                            spins = s_val, gamma = 1.0, gamma.minus = 1.0)
        }, error = function(e) { e })
        
        if (inherits(out, "error")) {
          posthoc_res <- add_ph_message(posthoc_res, "warning", "SPINGLASS_FAILED", 
                                        paste("Spinglass failed, falling back to Walktrap:", conditionMessage(out)))
          algo_used <- "walktrap (fallback)"
          comm <- cluster_walktrap(g, weights = E(g)$weight_abs)
        } else {
          comm <- out
        }
        
      } else {
        # Default / Walktrap
        algo_used <- "walktrap"
        comm <- cluster_walktrap(g, weights = E(g)$weight_abs)
      }
      
      comm_membership <- if (!is.null(comm)) membership(comm) else 1:length(v_ids)
    }
    
    # Build membership map
    mem_map <- list()
    for (i in seq_along(v_ids)) {
      mem_map[[v_ids[i]]] <- as.character(comm_membership[i])
    }
    
    posthoc_res$communities$enabled <- TRUE
    posthoc_res$communities$algorithm <- algo_used
    posthoc_res$communities$membership <- mem_map
    posthoc_res$communities$n_communities <- length(unique(comm_membership))
    posthoc_res$communities$params <- list(spins = spins, seed = spec$random_seed)
    
  }, error = function(e) {
    posthoc_res <<- add_ph_message(posthoc_res, "error", "COMMUNITIES_FAILED", conditionMessage(e))
  })
  
  # Write r_posthoc.json
  dir.create(dirname(posthoc_path), recursive = TRUE, showWarnings = FALSE)
  write_json(posthoc_res, posthoc_path, pretty = TRUE, auto_unbox = TRUE, null = "null")
  if (!quiet) cat(sprintf("WROTE: %s\n", posthoc_path))
}

