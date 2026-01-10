#!/usr/bin/env Rscript
# Hygeia-Graph: LASSO Feature Selection Runner (glmnet)
# Performs cross-validated LASSO to filter relevant predictors for a target variable.

if (!requireNamespace("glmnet", quietly=TRUE)) stop("Package glmnet required")
if (!requireNamespace("jsonlite", quietly=TRUE)) stop("Package jsonlite required")

args <- commandArgs(trailingOnly = TRUE)

# --- Argument Parsing Helper ---
parse_args <- function(args) {
    options <- list(
        data = NULL,
        target = NULL,
        out_dir = NULL,
        family = "auto",
        alpha = 1.0,
        nfolds = 5,
        lambda_rule = "lambda.1se",
        max_features = 30,
        standardize = TRUE,
        seed = 1,
        quiet = FALSE
    )
    
    i <- 1
    while (i <= length(args)) {
        arg <- args[i]
        val <- NULL
        if (i < length(args)) val <- args[i+1]
        
        if (arg == "--data") { options$data <- val; i <- i+2 }
        else if (arg == "--target") { options$target <- val; i <- i+2 }
        else if (arg == "--out_dir") { options$out_dir <- val; i <- i+2 }
        else if (arg == "--family") { options$family <- val; i <- i+2 }
        else if (arg == "--alpha") { options$alpha <- as.numeric(val); i <- i+2 }
        else if (arg == "--nfolds") { options$nfolds <- as.integer(val); i <- i+2 }
        else if (arg == "--lambda_rule") { options$lambda_rule <- val; i <- i+2 }
        else if (arg == "--max_features") { options$max_features <- as.integer(val); i <- i+2 }
        else if (arg == "--standardize") { options$standardize <- as.integer(val) == 1; i <- i+2 }
        else if (arg == "--seed") { options$seed <- as.integer(val); i <- i+2 }
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

# --- JSON Meta Writer ---
write_meta <- function(status, message=NULL, details=NULL, cv_info=NULL, selected_info=NULL) {
    meta <- list(
        computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
        status = status,
        settings = list(
            target = opts$target,
            family_used = details$family,
            alpha = opts$alpha,
            nfolds = opts$nfolds,
            lambda_rule = opts$lambda_rule,
            max_features = opts$max_features,
            standardize = opts$standardize,
            seed = opts$seed
        ),
        cv = cv_info,
        selected = selected_info,
        messages = list(),
        engine = list(
            r_version = R.version.string,
            package_versions = list(
                glmnet = as.character(packageVersion("glmnet")),
                jsonlite = as.character(packageVersion("jsonlite"))
            )
        )
    )
    
    if (!is.null(message)) {
        meta$messages[[1]] <- list(
            level = "error",
            code = if (!is.null(details$code)) details$code else "RUNTIME_ERROR",
            message = message
        )
    }
    
    jsonite_json <- jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE)
    write(jsonite_json, file = file.path(opts$out_dir, "lasso_meta.json"))
}

# 1. Validation & Setup
if (is.null(opts$data) || is.null(opts$target) || is.null(opts$out_dir)) {
    stop("Missing required arguments: --data, --target, --out_dir")
}

if (!dir.exists(opts$out_dir)) dir.create(opts$out_dir, recursive = TRUE)

tryCatch({
    # 2. Load Data
    df <- read.csv(opts$data, stringsAsFactors = FALSE, check.names = FALSE)
    
    if (!opts$target %in% colnames(df)) {
        stop(sprintf("Target column '%s' not found in dataset.", opts$target))
    }
    
    # Check Missing
    # Naive check: complete.cases on everything (or just used columns?)
    # Since we use all columns except target as features, we check everything.
    if (any(is.na(df)) || any(df == "")) {
        write_meta("failed", "Missing values detected. Imputation not supported.", details=list(code="MISSING_DATA_ABORT"))
        quit(save="no", status=0)
    }
    
    # 3. Prepare X and y
    y_raw <- df[[opts$target]]
    predictors_df <- df[, setdiff(colnames(df), opts$target), drop=FALSE]
    predictor_names <- colnames(predictors_df)
    
    # Detect Family
    family <- opts$family
    if (family == "auto") {
        if (is.numeric(y_raw) && length(unique(y_raw)) > 5) {
            family <- "gaussian"
        } else if (length(unique(y_raw)) == 2) {
            family <- "binomial"
        } else {
            family <- "multinomial"
        }
    }
    log_info(sprintf("Using family: %s", family))
    
    # Prepare Design Matrix (One-Hot Encoding)
    # Convert character cols to factor explicitely for model.matrix
    for (col in predictor_names) {
        if (is.character(predictors_df[[col]])) {
            predictors_df[[col]] <- as.factor(predictors_df[[col]])
        }
    }
    
    # Create model matrix (auto dummy/one-hot)
    # remove intercept (-1) as glmnet handles it
    X_mat <- model.matrix(~ . -1, data = predictors_df)
    
    # Prepare Y
    if (family == "gaussian") {
        y_vec <- as.numeric(y_raw)
    } else {
        y_vec <- as.factor(y_raw)
    }
    
    # 4. Run cv.glmnet
    set.seed(opts$seed)
    log_info(sprintf("Running cv.glmnet (alpha=%s, nfolds=%d)...", opts$alpha, opts$nfolds))
    
    fit <- glmnet::cv.glmnet(
        x = X_mat,
        y = y_vec,
        family = family,
        alpha = opts$alpha,
        nfolds = opts$nfolds,
        standardize = opts$standardize,
        type.measure = "default" # deviance/auc depending on family
    )
    
    # 5. Extract Coefs
    lambda_choice <- if (opts$lambda_rule == "lambda.min") fit$lambda.min else fit$lambda.1se
    log_info(sprintf("Selected lambda: %f (%s)", lambda_choice, opts$lambda_rule))
    
    # Extract
    # For multinomial, coef returns a list (one mat per class).
    # We consolidate: if a feature has non-zero coef for ANY class, it counts.
    
    raw_coefs <- coef(fit, s = lambda_choice)
    
    # Helper to get variable importance map (features -> max abs coef)
    # returns named vector: feature_name -> max_abs_coef
    get_imp_vec <- function(cf) {
        # cf is sparse matrix. convert to matrix or extract indices
        # row 1 is Intercept usually, skip it?
        # glmnet cols are predictors.
        # as.matrix might be heavy if huge, but usually fine for "wide" data here.
        # Actually coef returns n_features+1 x 1 matrix (sparse)
        
        m <- as.matrix(cf)
        # Remove (Intercept) if present
        if ("(Intercept)" %in% rownames(m)) {
            m <- m[rownames(m) != "(Intercept)", , drop=FALSE]
        }
        return(abs(m[,1]))
    }
    
    feature_importance_dummy <- NULL
    
    if (family == "multinomial") {
        # raw_coefs is a list
        # Sum absolute coefs across classes or take Max? Max is safer for "selection"
        # We need a unified list of all dummies
        all_dummies <- rownames(coef(fit, s = lambda_choice)[[1]])
        all_dummies <- setdiff(all_dummies, "(Intercept)")
        
        vals <- numeric(length(all_dummies))
        names(vals) <- all_dummies
        
        for (class_res in raw_coefs) {
            cls_imp <- get_imp_vec(class_res)
            # update max
            # cls_imp might be partial if sparse? No, matrix conversion handles it.
            # align
            for (d in names(cls_imp)) {
                vals[d] <- max(vals[d], cls_imp[d])
            }
        }
        feature_importance_dummy <- vals
    } else {
        feature_importance_dummy <- get_imp_vec(raw_coefs)
    }
    
    # 6. Map Dummies Back to Original Columns
    # Strategy: iterate original columns. Find dummies that start with colname.
    # Warning: heuristic. If ColA="Age", ColB="AgeGroup", prefix matching "Age" matches both.
    # Better: check exact match or exact match + known separator? model.matrix uses "ColNameLevel".
    # Since we know the original column list `predictor_names`, we can iterate them longest to shortest
    # or handle overlaps.
    
    # But wait, model.matrix behaves predictably.
    # Numeric cols: name matches exactly.
    # Factor cols: name is ColName + Level.
    
    # Let's build a map: OriginalCol -> Importance (Max of its dummies)
    
    final_scores <- numeric(length(predictor_names))
    names(final_scores) <- predictor_names
    
    dummy_names <- names(feature_importance_dummy)
    
    for (col in predictor_names) {
        # Check type
        is_num <- is.numeric(predictors_df[[col]])
        
        relevant_dummies <- c()
        if (is_num) {
            # Exact match
            if (col %in% dummy_names) relevant_dummies <- c(col)
        } else {
            # Prefix match
            # "ColName" is prefix. Dummies are "ColNameLevelA", "ColNameLevelB"
            # We must be careful about "ColName" vs "ColName2"
            # Since model.matrix concats, "A" + "lev" -> "Alev".
            # We can rely on `assign` attribute of model matrix if we saved it?
            # attr(X_mat, "assign") maps col index to term index.
            # term.labels from terms() maps term index to variable name.
            
            # Reconstruct terms info more robustly
            # X_mat was built from predictors_df.
            # attr(X_mat, "assign") gives integer IDs.
            # attr(X_mat, "contrasts") etc.
            
            # Actually, assign is perfect.
            # 1. Get assignments
            assign_idx <- attr(X_mat, "assign")
            # 2. Get term labels (variable names)
            # We need the formula used: ~ . -1
            # Or just usage of column names in order?
            # Assign usually maps 1-based index to the input variable index in order of columns?
            # Let's verify:
            # If predictors are A, B, C. assign will be 1, 1, 1 (if A has 3 levels), 2, 3...
            # Yes. `assign` corresponds to the column index in `predictors_df`.
            
            # map dummy index (in X_mat) to original col index (in predictors_df)
            # feature_importance_dummy is named by X_mat colnames.
            # But we might have filtered 0s.
            pass
        }
    }
    
    # Robust Mapping using 'assign'
    # feature_importance_dummy contains ALL terms (even 0 ones? No, we extracted from coefs).
    # Coefs return sparse structure for all columns in X_mat.
    # So we can iterate 1:ncol(X_mat)
    
    assign_map <- attr(X_mat, "assign") # vector of length ncol(X_mat)
    # assign_map values correspond to index in predictor_names
    
    # CAUTION: model.matrix drop unused levels?
    # Yes. But the mapping holds for the generated matrix.
    
    cols_in_matrix <- colnames(X_mat)
    
    # Re-extract coefficients aligning with X_mat columns
    # feature_importance_dummy computed above is named vector.
    # Ensure alignment
    
    for (j in seq_along(cols_in_matrix)) {
        d_name <- cols_in_matrix[j]
        orig_idx <- assign_map[j] 
        orig_name <- predictor_names[orig_idx]
        
        imp <- feature_importance_dummy[d_name]
        if (is.na(imp)) imp <- 0
        
        # Max pool
        if (imp > final_scores[orig_name]) {
            final_scores[orig_name] <- imp
        }
    }
    
    # 7. Filter & Sort
    # Filter out 0 importance
    selected_scores <- final_scores[final_scores > 0]
    
    # Sort descending
    selected_scores <- sort(selected_scores, decreasing = TRUE)
    
    # Apply Limit
    n_limit <- opts$max_features
    if (length(selected_scores) > n_limit) {
        selected_scores <- selected_scores[1:n_limit]
    }
    
    selected_cols <- names(selected_scores)
    
    # 8. Write Results
    
    # A. Coefficients CSV
    # Original_Col, Importance
    coef_df <- data.frame(
        original_column = names(selected_scores),
        importance = as.numeric(selected_scores),
        stringsAsFactors = FALSE
    )
    write.csv(coef_df, file.path(opts$out_dir, "lasso_coefficients.csv"), row.names = FALSE)
    
    # B. Filtered Data
    # Include Target and Selected Cols
    out_cols <- c(opts$target, selected_cols)
    filtered_df <- df[, out_cols, drop=FALSE]
    write.csv(filtered_df, file.path(opts$out_dir, "filtered_data.csv"), row.names = FALSE)
    
    # C. Meta
    write_meta(
        status = "success",
        details = list(family = family),
        cv_info = list(
            lambda_min = fit$lambda.min,
            lambda_1se = fit$lambda.1se,
            lambda_used = lambda_choice
        ),
        selected_info = list(
            n_selected = length(selected_cols),
            columns = selected_cols
        )
    )
    
    log_info(sprintf("Success. Selected %d features.", length(selected_cols)))

}, error = function(e) {
    log_error(e$message)
    write_meta("failed", message = e$message, details = list(code = "RUNTIME_ERROR", family="unknown"))
    quit(save="no", status=1)
})
