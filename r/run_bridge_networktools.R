#!/usr/bin/env Rscript
# Hygeia-Graph: Bridge Centrality (networktools)
# Computes canonical bridge metrics using networktools::bridge()

if (!requireNamespace("qgraph", quietly=TRUE)) stop("Package qgraph required")
if (!requireNamespace("networktools", quietly=TRUE)) stop("Package networktools required")
if (!requireNamespace("jsonlite", quietly=TRUE)) stop("Package jsonlite required")

args <- commandArgs(trailingOnly = TRUE)

# --- Argument Parsing ---
parse_args <- function(args) {
    options <- list(
        results = NULL,
        derived = NULL,
        out_path = NULL,
        threshold = 0.0,
        use_abs_filter = TRUE,
        top_edges = NULL,
        quiet = FALSE
    )
    
    i <- 1
    while (i <= length(args)) {
        arg <- args[i]
        val <- NULL
        if (i < length(args)) val <- args[i+1]
        
        if (arg == "--results") { options$results <- val; i <- i+2 }
        else if (arg == "--derived") { options$derived <- val; i <- i+2 }
        else if (arg == "--out_path") { options$out_path <- val; i <- i+2 }
        else if (arg == "--threshold") { options$threshold <- as.numeric(val); i <- i+2 }
        else if (arg == "--use_abs_filter") { options$use_abs_filter <- as.integer(val) == 1; i <- i+2 }
        else if (arg == "--top_edges") { options$top_edges <- as.integer(val); i <- i+2 }
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
if (is.null(opts$results) || is.null(opts$out_path)) {
    stop("Missing required arguments: --results, --out_path")
}

tryCatch({
    # 1. Load Results
    res_json <- jsonlite::fromJSON(opts$results)
    
    if (is.null(res_json$status) || res_json$status != "success") {
        output <- list(
            status = "failed",
            message = "Results JSON input indicates failure.",
            code = "RESULTS_NOT_SUCCESS"
        )
        write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
        quit(save="no", status=0)
    }
    
    analysis_id <- if (!is.null(res_json$analysis_id)) res_json$analysis_id else "unknown"
    
    # 2. Load Derived (for communities)
    derived_json <- NULL
    communities_vec <- NULL
    
    if (!is.null(opts$derived) && file.exists(opts$derived)) {
        try({
            derived_json <- jsonlite::fromJSON(opts$derived)
        }, silent = TRUE)
    }
    
    # 3. Extract communities or fallback to domain_group
    nodes_df <- res_json$nodes
    n_nodes <- nrow(nodes_df)
    node_ids <- nodes_df$id
    
    # Try communities from derived
    if (!is.null(derived_json) && !is.null(derived_json$communities)) {
        mem_list <- derived_json$communities$membership
        if (length(mem_list) > 0) {
            comm_vals <- character(n_nodes)
            for (i in seq_len(n_nodes)) {
                nid <- node_ids[i]
                if (!is.null(mem_list[[nid]])) {
                    comm_vals[i] <- as.character(mem_list[[nid]])
                } else {
                    comm_vals[i] <- "Unknown"
                }
            }
            communities_vec <- comm_vals
            log_info("Using communities from derived_metrics.")
        }
    }
    
    # Fallback to domain_group
    if (is.null(communities_vec)) {
        domain_vec <- nodes_df$domain_group
        if (!is.null(domain_vec) && any(!is.na(domain_vec) & domain_vec != "")) {
            communities_vec <- domain_vec
            log_info("Using domain_group as communities fallback.")
        }
    }
    
    # If still no communities, we cannot compute bridge
    if (is.null(communities_vec) || length(unique(communities_vec)) < 2) {
        output <- list(
            status = "failed",
            analysis_id = analysis_id,
            message = "Bridge requires at least 2 groups (communities or domain_group).",
            code = "NO_GROUPS"
        )
        write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
        quit(save="no", status=0)
    }
    
    # 4. Build Adjacency Matrix
    edges_df <- res_json$edges
    
    W <- matrix(0, nrow=n_nodes, ncol=n_nodes)
    rownames(W) <- colnames(W) <- node_ids
    
    if (length(edges_df) > 0 && nrow(edges_df) > 0) {
        edges_df$abs_w <- abs(edges_df$weight)
        edges_df <- edges_df[order(-edges_df$abs_w), ]
        
        # Filter threshold
        mask <- if (opts$use_abs_filter) edges_df$abs_w >= opts$threshold else edges_df$weight >= opts$threshold
        edges_df <- edges_df[mask, ]
        
        # Top edges cap
        if (!is.null(opts$top_edges) && opts$top_edges > 0 && nrow(edges_df) > opts$top_edges) {
            edges_df <- edges_df[1:opts$top_edges, ]
        }
        
        # Populate W
        node_idx_map <- setNames(seq_len(n_nodes), node_ids)
        
        for (k in seq_len(nrow(edges_df))) {
            u <- edges_df$source[k]
            v <- edges_df$target[k]
            w <- edges_df$weight[k]
            
            i <- node_idx_map[u]
            j <- node_idx_map[v]
            
            if (!is.na(i) && !is.na(j)) {
                W[i, j] <- w
                W[j, i] <- w
            }
        }
    }
    
    if (sum(abs(W)) == 0) {
        output <- list(
            status = "failed",
            analysis_id = analysis_id,
            message = "No edges after filtering.",
            code = "NO_EDGES"
        )
        write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
        quit(save="no", status=0)
    }
    
    # 5. Create qgraph object and compute bridge
    log_info("Building qgraph object...")
    q_graph <- qgraph::qgraph(W, DoNotPlot = TRUE)
    
    log_info("Computing bridge centrality...")
    bridge_result <- networktools::bridge(
        q_graph,
        communities = communities_vec,
        useCommunities = "all"
    )
    
    # 6. Extract metrics
    # bridge_result is a list with: 
    # $`Bridge Strength`, $`Bridge Betweenness`, $`Bridge Closeness`, $`Bridge Expected Influence (1-step)`, etc.
    
    bridge_strength <- NULL
    bridge_ei <- NULL
    bridge_betweenness <- NULL
    bridge_closeness <- NULL
    
    if (!is.null(bridge_result$`Bridge Strength`)) {
        bridge_strength <- as.list(setNames(bridge_result$`Bridge Strength`, node_ids))
    }
    if (!is.null(bridge_result$`Bridge Expected Influence (1-step)`)) {
        bridge_ei <- as.list(setNames(bridge_result$`Bridge Expected Influence (1-step)`, node_ids))
    }
    if (!is.null(bridge_result$`Bridge Betweenness`)) {
        bridge_betweenness <- as.list(setNames(bridge_result$`Bridge Betweenness`, node_ids))
    }
    if (!is.null(bridge_result$`Bridge Closeness`)) {
        bridge_closeness <- as.list(setNames(bridge_result$`Bridge Closeness`, node_ids))
    }
    
    # 7. Output
    output <- list(
        status = "success",
        analysis_id = analysis_id,
        computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
        method = "networktools::bridge",
        n_communities = length(unique(communities_vec)),
        community_source = if (!is.null(derived_json) && !is.null(derived_json$communities)) "derived" else "domain_group",
        metrics = list(
            bridge_strength = bridge_strength,
            bridge_expected_influence = bridge_ei,
            bridge_betweenness = bridge_betweenness,
            bridge_closeness = bridge_closeness
        ),
        engine = list(
            r_version = R.version.string,
            networktools_version = as.character(packageVersion("networktools")),
            qgraph_version = as.character(packageVersion("qgraph"))
        )
    )
    
    write(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = TRUE), opts$out_path)
    log_info("Bridge computation complete.")

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
