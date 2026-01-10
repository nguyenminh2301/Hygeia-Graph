#!/usr/bin/env Rscript
# Hygeia-Graph: Bootnet Analysis Runner (Robustness)
# Handles nonparametric bootstrapping (edge weights) and case-dropping (centrality stability)

# 0. Dependencies
if (!requireNamespace("bootnet", quietly=TRUE)) stop("Package bootnet required")
if (!requireNamespace("mgm", quietly=TRUE)) stop("Package mgm required")
if (!requireNamespace("jsonlite", quietly=TRUE)) stop("Package jsonlite required")

args <- commandArgs(trailingOnly = TRUE)

# --- Argument Parsing Helper ---
parse_args <- function(args) {
    options <- list(
        data = NULL,
        schema = NULL,
        spec = NULL,
        out_dir = NULL,
        n_boots_np = 200,
        n_boots_case = 200,
        n_cores = 1,
        caseMin = 0.05,
        caseMax = 0.75,
        caseN = 10,
        cor_level = 0.7,
        quiet = FALSE
    )
    
    i <- 1
    while (i <= length(args)) {
        arg <- args[i]
        val <- NULL
        if (i < length(args)) val <- args[i+1]
        
        if (arg == "--data") { options$data <- val; i <- i+2 }
        else if (arg == "--schema") { options$schema <- val; i <- i+2 }
        else if (arg == "--spec") { options$spec <- val; i <- i+2 }
        else if (arg == "--out_dir") { options$out_dir <- val; i <- i+2 }
        else if (arg == "--n_boots_np") { options$n_boots_np <- as.integer(val); i <- i+2 }
        else if (arg == "--n_boots_case") { options$n_boots_case <- as.integer(val); i <- i+2 }
        else if (arg == "--n_cores") { options$n_cores <- as.integer(val); i <- i+2 }
        else if (arg == "--caseMin") { options$caseMin <- as.numeric(val); i <- i+2 }
        else if (arg == "--caseMax") { options$caseMax <- as.numeric(val); i <- i+2 }
        else if (arg == "--caseN") { options$caseN <- as.integer(val); i <- i+2 }
        else if (arg == "--cor_level") { options$cor_level <- as.numeric(val); i <- i+2 }
        else if (arg == "--quiet") { options$quiet <- TRUE; i <- i+1 }
        else { i <- i+1 }
    }
    return(options)
}

opts <- parse_args(args)
cols_to_use <- NULL # Will be populated based on schema order

# --- Logging ---
log_info <- function(msg) {
    if (!opts$quiet) cat(sprintf("[INFO] %s\n", msg))
}

log_error <- function(msg) {
    cat(sprintf("[ERROR] %s\n", msg), file=stderr())
}

# --- JSON Meta Writer (for atomic/safe output) ---
write_meta <- function(status, message=NULL, cs=list(strength=NULL, expectedInfluence=NULL)) {
    meta <- list(
        analysis_id = if (!is.null(spec$analysis_id)) spec$analysis_id else "unknown",
        computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
        status = status,
        settings = list(
            n_boots_np = opts$n_boots_np,
            n_boots_case = opts$n_boots_case,
            n_cores = opts$n_cores,
            caseMin = opts$caseMin,
            caseMax = opts$caseMax,
            caseN = opts$caseN,
            cor_level = opts$cor_level,
            tuning_ebic_gamma = if (!is.null(spec$mgm$regularization$ebic_gamma)) spec$mgm$regularization$ebic_gamma else 0.25,
            criterion = "EBIC"
        ),
        cs_coefficient = cs,
        outputs = list(
            edge_summary_csv = "edge_summary.csv",
            edge_ci_flag_csv = "edge_ci_flag.csv",
            centrality_stability_csv = "centrality_stability_csv.csv"
        ),
        messages = list(),
        engine = list(
            r_version = R.version.string,
            package_versions = list(
                bootnet = as.character(packageVersion("bootnet")),
                mgm = as.character(packageVersion("mgm"))
            )
        )
    )
    
    if (!is.null(message)) {
        meta$messages[[1]] <- list(
            level = "error",
            code = "BOOTNET_ERROR",
            message = message
        )
    }
    
    jsonite_json <- jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE)
    write(jsonite_json, file = file.path(opts$out_dir, "bootnet_meta.json"))
}

# 1. Input Validation
if (is.null(opts$data) || is.null(opts$schema) || is.null(opts$spec) || is.null(opts$out_dir)) {
    stop("Missing required arguments: --data, --schema, --spec, --out_dir")
}

# Load schema/spec first to handle meta
tryCatch({
    schema <- jsonlite::fromJSON(opts$schema)
    spec <- jsonlite::fromJSON(opts$spec)
}, error = function(e) {
    stop(paste("Failed to load JSON inputs:", e$message))
})

# Create output dir
if (!dir.exists(opts$out_dir)) dir.create(opts$out_dir, recursive = TRUE)

tryCatch({
    # 2. Load Data & Validate
    df_raw <- read.csv(opts$data, stringsAsFactors = FALSE)
    
    # Missing Check
    if (any(is.na(df_raw))) {
        msg <- "Missing values detected in data. Bootnet requires complete data."
        write_meta(status="failed", message=msg)
        quit(save="no", status=0) 
    }
    
    # 3. Prepare Variables
    vars <- schema$variables
    n_vars <- length(vars)
    
    # Use 'column' to select/order cols, 'id' for tracking
    df_model <- df_raw[, vars$column, drop=FALSE]
    colnames(df_model) <- vars$id
    
    type_vec <- character(n_vars)
    level_vec <- numeric(n_vars)
    
    for (i in 1:n_vars) {
        v <- vars[i,]
        col_id <- v$id
        mgm_type <- v$mgm_type
        
        # Types: g->g, p->p, c->c
        # But bootnet/mgm needs correct R types:
        # g -> numeric
        # p -> integer
        # c -> factor/ordered
        
        if (mgm_type == "g") {
            df_model[[col_id]] <- as.numeric(df_model[[col_id]])
            type_vec[i] <- "g"
            level_vec[i] <- 1
        } else if (mgm_type == "p") {
            df_model[[col_id]] <- as.integer(df_model[[col_id]])
            type_vec[i] <- "p"
            level_vec[i] <- 1
        } else if (mgm_type == "c") {
            ms_level <- v$measurement_level
            # Check categories
            cats <- NULL
            if ("categories" %in% names(v) && !is.null(v$categories[[1]])) {
                cats <- unlist(v$categories)
            } else {
                cats <- sort(unique(df_model[[col_id]]))
            }
            
            is_ordered <- (ms_level == "ordinal")
            df_model[[col_id]] <- factor(df_model[[col_id]], levels = cats, ordered = is_ordered)
            
            type_vec[i] <- "c"
            level_vec[i] <- length(cats)
        }
    }
    
    # Set seed if available
    seed_val <- spec$random_seed
    if (!is.null(seed_val)) set.seed(seed_val)
    
    tuning <- if (!is.null(spec$mgm$regularization$ebic_gamma)) spec$mgm$regularization$ebic_gamma else 0.25
    
    log_info("Estimating base network...")
    
    # 4. Estimate Base Network
    # We use bootnet::estimateNetwork with default="mgm" to ensure compatibility with bootnet functions
    # Passes args to mgm::mgm
    est <- bootnet::estimateNetwork(
        data = df_model,
        default = "mgm",
        type = type_vec,
        level = level_vec,
        tuning = tuning,
        criterion = "EBIC",
        ruleReg = if (!is.null(spec$mgm$rule_reg)) spec$mgm$rule_reg else "AND",
        binarySign = TRUE, # Recommended for EI
        verbose = FALSE
    )
    
    # 5A. Nonparametric Bootstrap
    log_info(sprintf("Running Nonparametric Bootstrap (%d boots)...", opts$n_boots_np))
    
    # Ensure memory handling
    boots_np <- bootnet::bootnet(
        est,
        nBoots = opts$n_boots_np,
        nCores = opts$n_cores,
        type = "nonparametric",
        statistics = c("edge", "strength", "expectedInfluence"),
        memorysaver = TRUE,
        verbose = !opts$quiet
    )
    
    # Summaries
    zt <- spec$edge_mapping$zero_tolerance
    if (is.null(zt)) zt <- 1e-5
    
    # We use summary() method which returns a data frame
    edge_sum <- summary(boots_np, statistics = "edge")
    
    # Write full edge summary
    write.csv(edge_sum, file.path(opts$out_dir, "edge_summary.csv"), row.names=FALSE)
    
    # Compute Edge CI Flags (Crosses 0?)
    # Cols: node1, node2, sample, mean, q2.5, q97.5 (and prop0 if available)
    # Check bounds
    edge_sum$crosses0 <- (edge_sum$q2.5 <= 0 & edge_sum$q97.5 >= 0)
    
    # Select cols for flags
    cols_flag <- c("node1", "node2", "sample", "q2.5", "q97.5", "prop0", "crosses0")
    cols_flag <- intersect(cols_flag, names(edge_sum))
    write.csv(edge_sum[, cols_flag], file.path(opts$out_dir, "edge_ci_flag.csv"), row.names=FALSE)
    
    # 5B. Case-Dropping Bootstrap
    log_info(sprintf("Running Case-Dropping Bootstrap (%d boots)...", opts$n_boots_case))
    
    boots_case <- bootnet::bootnet(
        est,
        nBoots = opts$n_boots_case,
        nCores = opts$n_cores,
        type = "case",
        caseMin = opts$caseMin,
        caseMax = opts$caseMax,
        caseN = opts$caseN,
        statistics = c("strength", "expectedInfluence"),
        memorysaver = TRUE,
        verbose = !opts$quiet
    )
    
    # Centrality Stability CSV
    # summary() with perNode=FALSE gives average correlation per case drop level
    stab_sum <- summary(boots_case, statistics = c("strength", "expectedInfluence"), perNode = FALSE)
    write.csv(stab_sum, file.path(opts$out_dir, "centrality_stability.csv"), row.names=FALSE)
    
    # CS Coefficient
    # corStability returns numeric vector usually
    # statistics default is c("strength","closeness","betweenness") for some versions, ensure input
    cs_vec <- bootnet::corStability(
        boots_case, 
        cor = opts$cor_level, 
        statistics = c("strength", "expectedInfluence"),
        verbose = FALSE
    )
    
    # cs_vec is named numeric vector
    cs_out <- list(
        strength = if ("strength" %in% names(cs_vec)) cs_vec[["strength"]] else NULL,
        expectedInfluence = if ("expectedInfluence" %in% names(cs_vec)) cs_vec[["expectedInfluence"]] else NULL
    )
    
    log_info("Bootstrapping complete.")
    write_meta(status="success", cs=cs_out)

}, error = function(e) {
    log_error(e$message)
    write_meta(status="failed", message=e$message)
    quit(save="no", status=1)
})
