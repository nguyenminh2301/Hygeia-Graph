#!/usr/bin/env Rscript
# Hygeia-Graph: Intervention Simulation v2 using mgm::predict.mgm
# Compares baseline vs intervention-modified predictions (non-causal)

if (!requireNamespace("mgm", quietly=TRUE)) stop("Package mgm required")
if (!requireNamespace("jsonlite", quietly=TRUE)) stop("Package jsonlite required")

args <- commandArgs(trailingOnly = TRUE)

# --- Argument Parsing ---
parse_args <- function(args) {
    options <- list(
        model_rds = NULL,
        data = NULL,
        schema = NULL,
        out_path = NULL,
        intervene_node = NULL,
        delta = 1.0,
        delta_units = "sd",  # "sd" or "raw"
        quiet = FALSE
    )
    
    i <- 1
    while (i <= length(args)) {
        arg <- args[i]
        val <- NULL
        if (i < length(args)) val <- args[i+1]
        
        if (arg == "--model_rds") { options$model_rds <- val; i <- i+2 }
        else if (arg == "--data") { options$data <- val; i <- i+2 }
        else if (arg == "--schema") { options$schema <- val; i <- i+2 }
        else if (arg == "--out_path") { options$out_path <- val; i <- i+2 }
        else if (arg == "--intervene_node") { options$intervene_node <- val; i <- i+2 }
        else if (arg == "--delta") { options$delta <- as.numeric(val); i <- i+2 }
        else if (arg == "--delta_units") { options$delta_units <- val; i <- i+2 }
        else if (arg == "--quiet") { options$quiet <- TRUE; i <- i+1 }
        else { i <- i+1 }
    }
    return(options)
}

opts <- parse_args(args)

# --- Logging ---
log_info <- function(msg) {
    if (!opts$quiet) cat(sprintf("[INFO] %s\n", msg))
}

log_error <- function(msg) {
    cat(sprintf("[ERROR] %s\n", msg), file=stderr())
}

# --- Validation ---
if (is.null(opts$model_rds) || is.null(opts$data) || is.null(opts$schema) || 
    is.null(opts$out_path) || is.null(opts$intervene_node)) {
    stop("Missing required arguments: --model_rds, --data, --schema, --out_path, --intervene_node")
}

tryCatch({
    # 1. Load model
    log_info("Loading MGM model...")
    fit <- readRDS(opts$model_rds)
    
    # 2. Load data and schema
    log_info("Loading data and schema...")
    df <- read.csv(opts$data, stringsAsFactors = FALSE, check.names = FALSE)
    schema <- jsonlite::fromJSON(opts$schema, simplifyVector = FALSE)
    
    # 3. Build encoding (matching run_mgm.R logic)
    n_vars <- length(schema$variables)
    node_ids <- sapply(schema$variables, function(v) v$id)
    
    # Find intervention node index
    intervene_idx <- which(node_ids == opts$intervene_node)
    if (length(intervene_idx) == 0) {
        output <- list(
            status = "failed",
            message = sprintf("Intervention node '%s' not found.", opts$intervene_node),
            code = "NODE_NOT_FOUND"
        )
        write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
        quit(save="no", status=0)
    }
    intervene_idx <- intervene_idx[1]
    
    # Encode data using same logic as run_mgm
    encoded_df <- list()
    type_vec <- character(n_vars)
    level_vec <- integer(n_vars)
    col_stats <- list()  # Store column statistics
    
    for (i in seq_len(n_vars)) {
        v <- schema$variables[[i]]
        col <- v$column
        x <- df[[col]]
        
        type <- v$mgm_type
        level <- v$level
        
        if (type == "g") {
            # Gaussian
            col_mean <- mean(x, na.rm = TRUE)
            col_sd <- sd(x, na.rm = TRUE)
            if (is.na(col_sd) || col_sd == 0) col_sd <- 1
            
            encoded_df[[v$id]] <- (x - col_mean) / col_sd
            type_vec[i] <- "g"
            level_vec[i] <- 1
            
            col_stats[[v$id]] <- list(
                type = "g",
                mean = col_mean,
                sd = col_sd
            )
        } else if (type == "p") {
            # Poisson (counts)
            col_mean <- mean(x, na.rm = TRUE)
            col_sd <- sd(x, na.rm = TRUE)
            if (is.na(col_sd) || col_sd == 0) col_sd <- 1
            
            encoded_df[[v$id]] <- x
            type_vec[i] <- "p"
            level_vec[i] <- 1
            
            col_stats[[v$id]] <- list(
                type = "p",
                mean = col_mean,
                sd = col_sd
            )
        } else if (type == "c") {
            # Categorical
            uniq <- sort(unique(as.character(x)))
            mode_val <- names(sort(table(x), decreasing = TRUE))[1]
            
            codes <- match(as.character(x), uniq)
            encoded_df[[v$id]] <- codes
            type_vec[i] <- "c"
            level_vec[i] <- level
            
            col_stats[[v$id]] <- list(
                type = "c",
                levels = uniq,
                mode = mode_val,
                mode_code = match(mode_val, uniq)
            )
        }
    }
    
    data_mat <- as.matrix(as.data.frame(encoded_df))
    
    # 4. Build baseline row (mean/mode for each variable)
    log_info("Building baseline state...")
    baseline <- numeric(n_vars)
    names(baseline) <- node_ids
    
    for (i in seq_len(n_vars)) {
        nid <- node_ids[i]
        stats <- col_stats[[nid]]
        
        if (stats$type == "g") {
            baseline[i] <- 0  # Standardized mean
        } else if (stats$type == "p") {
            baseline[i] <- round(stats$mean)
            if (baseline[i] < 0) baseline[i] <- 0
        } else if (stats$type == "c") {
            baseline[i] <- stats$mode_code
        }
    }
    
    baseline_mat <- matrix(baseline, nrow = 1)
    colnames(baseline_mat) <- node_ids
    
    # 5. Predict baseline
    log_info("Computing baseline predictions...")
    pred_base <- predict(fit, data = baseline_mat)
    
    # 6. Modify intervention node
    log_info(sprintf("Applying intervention: %s += %f (%s)", 
                     opts$intervene_node, opts$delta, opts$delta_units))
    
    intervention_mat <- baseline_mat
    int_stats <- col_stats[[opts$intervene_node]]
    
    if (int_stats$type == "g") {
        # For Gaussian: delta in SD or raw units
        if (opts$delta_units == "sd") {
            intervention_mat[1, intervene_idx] <- baseline_mat[1, intervene_idx] + opts$delta
        } else {
            # Raw units -> convert to standardized
            intervention_mat[1, intervene_idx] <- baseline_mat[1, intervene_idx] + (opts$delta / int_stats$sd)
        }
    } else if (int_stats$type == "p") {
        # For Poisson: delta in raw counts
        new_val <- baseline_mat[1, intervene_idx] + opts$delta
        intervention_mat[1, intervene_idx] <- max(0, round(new_val))
    } else if (int_stats$type == "c") {
        # For categorical: delta is the target category code (1-indexed)
        # This is more complex - skip for v1, just use delta as code directly
        intervention_mat[1, intervene_idx] <- max(1, min(int_stats$levels, round(opts$delta)))
    }
    
    # 7. Predict intervention
    log_info("Computing intervention predictions...")
    pred_int <- predict(fit, data = intervention_mat)
    
    # 8. Compute effects (differences)
    log_info("Computing effects...")
    effects <- list()
    
    for (i in seq_len(n_vars)) {
        nid <- node_ids[i]
        stats <- col_stats[[nid]]
        
        if (stats$type == "g" || stats$type == "p") {
            # Continuous/count: difference in predicted values
            base_pred <- pred_base$predicted[1, i]
            int_pred <- pred_int$predicted[1, i]
            
            effect <- int_pred - base_pred
            
            # Convert back to original scale if Gaussian
            if (stats$type == "g") {
                effect_raw <- effect * stats$sd
            } else {
                effect_raw <- effect
            }
            
            effects[[nid]] <- list(
                baseline = base_pred,
                intervention = int_pred,
                effect = effect,
                effect_raw = effect_raw,
                type = stats$type
            )
        } else if (stats$type == "c") {
            # Categorical: difference in probability vectors
            if (!is.null(pred_base$probabilities) && !is.null(pred_base$probabilities[[i]])) {
                base_prob <- pred_base$probabilities[[i]][1, ]
                int_prob <- pred_int$probabilities[[i]][1, ]
                
                prob_diff <- int_prob - base_prob
                max_change <- max(abs(prob_diff))
                
                effects[[nid]] <- list(
                    baseline_probs = as.list(base_prob),
                    intervention_probs = as.list(int_prob),
                    prob_diff = as.list(prob_diff),
                    max_abs_change = max_change,
                    type = stats$type
                )
            } else {
                effects[[nid]] <- list(
                    effect = 0,
                    type = stats$type,
                    note = "Probability not available"
                )
            }
        }
    }
    
    # 9. Build summary (top affected nodes)
    effect_values <- sapply(node_ids, function(nid) {
        e <- effects[[nid]]
        if (!is.null(e$effect)) return(abs(e$effect))
        if (!is.null(e$max_abs_change)) return(e$max_abs_change)
        return(0)
    })
    
    top_n <- min(10, n_vars)
    top_idx <- order(effect_values, decreasing = TRUE)[1:top_n]
    top_nodes <- node_ids[top_idx]
    
    # 10. Output
    output <- list(
        status = "success",
        analysis_id = if (!is.null(schema$analysis_id)) schema$analysis_id else "unknown",
        computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
        method = "mgm::predict.mgm",
        disclaimer = "NON-CAUSAL simulation. Observational associations only.",
        settings = list(
            intervene_node = opts$intervene_node,
            delta = opts$delta,
            delta_units = opts$delta_units
        ),
        baseline_summary = as.list(baseline),
        effects = effects,
        top_affected = as.list(top_nodes),
        engine = list(
            r_version = R.version.string,
            mgm_version = as.character(packageVersion("mgm"))
        )
    )
    
    write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
    log_info("Intervention v2 complete.")

}, error = function(e) {
    log_error(e$message)
    output <- list(
        status = "failed",
        message = e$message,
        code = "RUNTIME_ERROR"
    )
    write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
    quit(save="no", status=1)
})
