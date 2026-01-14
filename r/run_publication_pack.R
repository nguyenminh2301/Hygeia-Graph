#!/usr/bin/env Rscript
# Hygeia-Graph: Publication Pack Generator
# Generates static figures (qgraph) and bundles tables.

if (!requireNamespace("qgraph", quietly=TRUE)) stop("Package qgraph required")
if (!requireNamespace("svglite", quietly=TRUE)) stop("Package svglite required")
if (!requireNamespace("jsonlite", quietly=TRUE)) stop("Package jsonlite required")

args <- commandArgs(trailingOnly = TRUE)

# --- Argument Parsing ---
parse_args <- function(args) {
    options <- list(
        results = NULL,
        schema = NULL,
        derived = NULL, # optional
        out_dir = NULL,
        threshold = 0.0,
        use_abs_filter = TRUE,
        top_edges = 500,
        show_labels = TRUE,
        layout = "spring",
        width = 10,
        height = 8,
        quiet = FALSE
    )
    
    i <- 1
    while (i <= length(args)) {
        arg <- args[i]
        val <- NULL
        if (i < length(args)) val <- args[i+1]
        
        if (arg == "--results") { options$results <- val; i <- i+2 }
        else if (arg == "--schema") { options$schema <- val; i <- i+2 }
        else if (arg == "--derived") { options$derived <- val; i <- i+2 }
        else if (arg == "--out_dir") { options$out_dir <- val; i <- i+2 }
        else if (arg == "--threshold") { options$threshold <- as.numeric(val); i <- i+2 }
        else if (arg == "--use_abs_filter") { options$use_abs_filter <- as.integer(val) == 1; i <- i+2 }
        else if (arg == "--top_edges") { options$top_edges <- as.integer(val); i <- i+2 }
        else if (arg == "--show_labels") { options$show_labels <- as.integer(val) == 1; i <- i+2 }
        else if (arg == "--layout") { options$layout <- val; i <- i+2 }
        else if (arg == "--width") { options$width <- as.numeric(val); i <- i+2 }
        else if (arg == "--height") { options$height <- as.numeric(val); i <- i+2 }
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

# --- Metadata Writer ---
write_meta <- function(status, outputs=list(), message=NULL, details=NULL, analysis_id="unknown") {
    meta <- list(
        analysis_id = analysis_id,
        computed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
        status = status,
        settings = list(
            threshold = opts$threshold,
            use_abs_filter = opts$use_abs_filter,
            top_edges = opts$top_edges,
            show_labels = opts$show_labels,
            layout = opts$layout,
            width = opts$width,
            height = opts$height
        ),
        outputs = outputs,
        messages = list(),
        engine = list(
            r_version = R.version.string,
            package_versions = list(
                qgraph = as.character(packageVersion("qgraph")),
                svglite = as.character(packageVersion("svglite")),
                jsonlite = as.character(packageVersion("jsonlite"))
            )
        )
    )
    
    if (!is.null(message)) {
        meta$messages[[1]] <- list(
             level = if (status == "failed") "error" else "warning",
             code = if (!is.null(details$code)) details$code else "RUNTIME_ERROR",
             message = message
        )
    }
    
    dir.create(file.path(opts$out_dir, "meta"), recursive = TRUE, showWarnings = FALSE)
    write(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE), 
          file = file.path(opts$out_dir, "meta", "publication_pack_meta.json"))
}

# 1. Validation & Setup
if (is.null(opts$results) || is.null(opts$schema) || is.null(opts$out_dir)) {
    stop("Missing required arguments: --results, --schema, --out_dir")
}

# Prepare dirs
dir.create(file.path(opts$out_dir, "figures"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(opts$out_dir, "tables"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(opts$out_dir, "meta"), recursive = TRUE, showWarnings = FALSE)

tryCatch({
    # 2. Load JSONs
    res_json <- jsonlite::fromJSON(opts$results)
    
    if (is.null(res_json$status) || res_json$status != "success") {
        write_meta("failed", message="Results JSON input indicates failure.", details=list(code="RESULTS_NOT_SUCCESS"), analysis_id=res_json$analysis_id)
        quit(save="no", status=0) 
    }
    
    analysis_id <- if (!is.null(res_json$analysis_id)) res_json$analysis_id else "unknown"
    
    # Optional Derived
    derived_json <- NULL
    if (!is.null(opts$derived) && file.exists(opts$derived)) {
        try({ derived_json <- jsonlite::fromJSON(opts$derived) }, silent=TRUE)
    }
    
    # 3. Nodes Setup
    nodes_df <- res_json$nodes
    n_nodes <- nrow(nodes_df)
    node_ids <- nodes_df$id
    
    # Color logic
    # Priorities: Community > Domain > Type
    
    # A. Communities
    comm_vec <- NULL
    if (!is.null(derived_json) && !is.null(derived_json$communities)) {
        # Assuming derived_json$communities$membership is a list/named vector
        # jsonlite parsing of dict typically gives a list
        mem_list <- derived_json$communities$membership
        if (length(mem_list) > 0) {
            # Map node_ids to comm IDs
            # Ensure order matches node_ids
            comm_vals <- character(n_nodes)
            for (i in seq_len(n_nodes)) {
                nid <- node_ids[i]
                if (!is.null(mem_list[[nid]])) {
                    comm_vals[i] <- as.character(mem_list[[nid]])
                } else {
                    comm_vals[i] <- "Unknown"
                }
            }
            comm_vec <- comm_vals
        }
    }
    
    # B. Domain Group
    domain_vec <- nodes_df$domain_group
    
    # C. MGM Type
    type_vec <- nodes_df$mgm_type
    
    # Assign Groups
    # If comm exists, use it. Else domain. Else type.
    final_groups <- if (!is.null(comm_vec)) comm_vec else if (!all(is.na(domain_vec)) && any(domain_vec != "")) domain_vec else type_vec
    if (is.null(final_groups)) final_groups <- rep("Default", n_nodes)
    
    # Assign Colors
    # Build a palette
    # Standard qgraph default or custom pastel
    # Let's use qgraph default robustly by passing groups factor
    groups_factor <- as.factor(final_groups)
    
    # Labels
    labels_vec <- if (opts$show_labels) {
        lbls <- nodes_df$label
        if (is.null(lbls)) lbls <- node_ids
        lbls
    } else {
        rep("", n_nodes)
    }
    
    # 4. Filter Edges & Build Matrix
    edges_df <- res_json$edges
    
    # Manual Adjacency Build
    W <- matrix(0, nrow=n_nodes, ncol=n_nodes)
    rownames(W) <- colnames(W) <- node_ids
    
    if (length(edges_df) > 0 && nrow(edges_df) > 0) {
        # Process filtering
        edges_df$abs_w <- abs(edges_df$weight)
        
        # Sort desc
        edges_df <- edges_df[order(-edges_df$abs_w), ]
        
        # Filter threshold
        mask <- if (opts$use_abs_filter) edges_df$abs_w >= opts$threshold else edges_df$weight >= opts$threshold
        edges_df <- edges_df[mask, ]
        
        # Top Edges Cap
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
    
    # Write Adjacency CSV
    write.csv(W, file.path(opts$out_dir, "tables", "adjacency_matrix.csv"))
    
    # 5. Generate Figures
    out_files <- list()
    
    # Function helper for pairs
    save_plot_pair <- function(filename_base, plot_func) {
        # SVG
        svg_path <- file.path(opts$out_dir, "figures", paste0(filename_base, ".svg"))
        svglite::svglite(svg_path, width=opts$width, height=opts$height)
        plot_func()
        dev.off()
        out_files <<- c(out_files, paste0("figures/", filename_base, ".svg"))
        
        # PDF
        pdf_path <- file.path(opts$out_dir, "figures", paste0(filename_base, ".pdf"))
        pdf(pdf_path, width=opts$width, height=opts$height)
        plot_func()
        dev.off()
        out_files <<- c(out_files, paste0("figures/", filename_base, ".pdf"))
    }
    
    # A. Network Plot (qgraph)
    # Using 'groups' for coloring
    
    save_plot_pair("network_qgraph", function() {
        if (sum(abs(W)) == 0) {
            plot(1, type="n", axes=FALSE, xlab="", ylab="")
            text(1, 1, "No edges above threshold")
        } else {
            qgraph::qgraph(
                W,
                layout = if (opts$layout == "circle") "circle" else "spring",
                labels = labels_vec,
                groups = as.list(split(node_ids, groups_factor)), # Groups list mapping
                # qgraph handles colors automatically if groups provided, or pass 'color'
                # Let qgraph decide colors based on groups
                vsize = 6,
                esize = 12, # Scale
                legend = TRUE,
                posCol = "#0000FF", # Blueish
                negCol = "#FF0000", # Redish
                details = TRUE,
                DoNotPlot = FALSE
            )
        }
    })
    
    # A2. Predictability Donut/Pie Network
    # Check if predictability data exists in derived_json
    pred_map <- NULL
    if (!is.null(derived_json) && !is.null(derived_json$node_metrics) && 
        !is.null(derived_json$node_metrics$predictability)) {
        pred_map <- derived_json$node_metrics$predictability
    }
    
    if (!is.null(pred_map) && length(pred_map) > 0 && sum(abs(W)) > 0) {
        save_plot_pair("network_predictability_pie", function() {
            # Build pie list for each node
            # Format: list of vectors c(explained, unexplained)
            pie_list <- lapply(node_ids, function(nid) {
                pred_val <- pred_map[[nid]]
                if (is.null(pred_val) || is.na(pred_val)) {
                    return(c(0, 1))  # No predictability = all unexplained
                }
                # Clamp to [0, 1]
                pred_val <- max(0, min(1, pred_val))
                return(c(pred_val, 1 - pred_val))
            })
            
            # Pie colors: green = explained, gray = unexplained
            pie_colors <- c("#2ecc71", "#ecf0f1")
            
            qgraph::qgraph(
                W,
                layout = if (opts$layout == "circle") "circle" else "spring",
                labels = labels_vec,
                pie = pie_list,
                pieColor = pie_colors,
                vsize = 8,
                esize = 10,
                posCol = "#0000FF",
                negCol = "#FF0000",
                legend = FALSE,
                title = "Predictability (Green = Explained)"
            )
        })
        log_info("Predictability pie network generated.")
    } else {
        log_info("Skipping predictability pie (no data or empty network).")
    }
    
    # A3. Community Hull Network
    # Draw convex hulls around community clusters
    if (!is.null(comm_vec) && length(unique(comm_vec)) > 1 && sum(abs(W)) > 0) {
        save_plot_pair("network_community_hulls", function() {
            # First, get layout coordinates from qgraph
            q_result <- qgraph::qgraph(
                W,
                layout = if (opts$layout == "circle") "circle" else "spring",
                labels = labels_vec,
                vsize = 6,
                esize = 10,
                posCol = "#0000FF",
                negCol = "#FF0000",
                DoNotPlot = TRUE  # Get layout without plotting
            )
            
            coords <- q_result$layout
            
            # Create blank plot first
            plot(coords, type = "n", axes = FALSE, xlab = "", ylab = "",
                 xlim = range(coords[,1]) * 1.2,
                 ylim = range(coords[,2]) * 1.2,
                 main = "Network with Community Hulls")
            
            # Draw hulls for each community
            unique_comms <- unique(comm_vec)
            n_comms <- length(unique_comms)
            
            # Generate colors for communities
            comm_palette <- rainbow(n_comms, alpha = 0.2)
            border_palette <- rainbow(n_comms, alpha = 0.8)
            
            for (k in seq_len(n_comms)) {
                comm_id <- unique_comms[k]
                idx <- which(comm_vec == comm_id)
                
                if (length(idx) >= 3) {
                    # Get coordinates for this community
                    comm_coords <- coords[idx, , drop = FALSE]
                    
                    # Compute convex hull
                    hull_idx <- chull(comm_coords[,1], comm_coords[,2])
                    hull_idx <- c(hull_idx, hull_idx[1])  # Close polygon
                    
                    # Draw hull polygon
                    polygon(
                        comm_coords[hull_idx, 1],
                        comm_coords[hull_idx, 2],
                        col = comm_palette[k],
                        border = border_palette[k],
                        lwd = 2
                    )
                }
            }
            
            # Now draw the network on top
            qgraph::qgraph(
                W,
                layout = coords,  # Use same layout
                labels = labels_vec,
                groups = as.list(split(node_ids, groups_factor)),
                vsize = 6,
                esize = 10,
                posCol = "#0000FF",
                negCol = "#FF0000",
                add = TRUE  # Add to existing plot
            )
            
            # Add legend for communities
            legend("bottomright", 
                   legend = unique_comms, 
                   fill = comm_palette,
                   border = border_palette,
                   title = "Communities",
                   cex = 0.7)
        })
        log_info("Community hulls network generated.")
    } else {
        log_info("Skipping community hulls (no communities or empty network).")
    }
    
    # B. Heatmap
    save_plot_pair("adjacency_heatmap", function() {
        # Base image() needs data rotated?
        # image() draws col 1 at bottom.
        # Use simple mapping. W is symmetric.
        # Diverging palette
        
        # Prepare palette
        limit <- max(abs(W))
        if (limit == 0) limit <- 1
        
        n_cols <- 100
        rbLib <- colorRampPalette(c("red", "white", "blue"))
        cols <- rbLib(n_cols)
        
        # Matrix orientation for image()
        # image(x, y, z)
        # We need to reverse rows to match matrix print order visually if desired, but symmetric is forgiving.
        
        image(1:n_nodes, 1:n_nodes, W,
              col = cols,
              axes = FALSE,
              xlab = "", ylab = "",
              main = "Adjacency Matrix (Signed)",
              zlim = c(-limit, limit))
              
        if (n_nodes <= 40) {
            axis(1, at=1:n_nodes, labels=node_ids, las=2, cex.axis=0.7)
            axis(2, at=1:n_nodes, labels=node_ids, las=2, cex.axis=0.7)
        }
    })
    
    # C. Centrality Plot
    # Prefer derived, else compute local
    strength_vec <- NULL
    inf_vec <- NULL
    
    # Compute from W (The matrix actually plotted)
    # This ensures consistency: "What you see is what you measure" for the specific figure.
    strength_vec <- colSums(abs(W))
    inf_vec <- colSums(W) # Expected influence (sum signed)
    
    # Top N
    top_n <- min(20, n_nodes)
    
    # Sort by Strength
    ord <- order(strength_vec, decreasing = TRUE)[1:top_n]
    
    # Plot Strength
    save_plot_pair("centrality_strength", function() {
        par(mar=c(5, 8, 4, 2)) # margin for labels
        barplot(rev(strength_vec[ord]), horiz=TRUE,
                names.arg=rev(labels_vec[ord]),
                las=1,
                main="Node Strength (Abs)",
                xlab="Sum of Abs Weights",
                col="skyblue")
    })
    
    # Plot Expected Influence
    # Sorted by Abs(Influence) for ranking, but show Signed
    save_plot_pair("centrality_expected_influence", function() {
        abs_inf <- abs(inf_vec)
        ord_inf <- order(abs_inf, decreasing = TRUE)[1:top_n]
        
        vals <- inf_vec[ord_inf]
        cols <- ifelse(vals > 0, "green", "red")
        
        par(mar=c(5, 8, 4, 2))
        barplot(rev(vals), horiz=TRUE,
                names.arg=rev(labels_vec[ord_inf]),
                las=1,
                main="Expected Influence",
                xlab="Sum of Signed Weights",
                col=rev(cols))
    })
    
    # 6. Finish
    write_meta(
        status = "success",
        outputs = list(
            figures = unlist(out_files),
            tables = list("tables/adjacency_matrix.csv")
        ),
        details = list(
            n_nodes = n_nodes,
            n_edges_used = sum(W != 0) / 2
        ),
        analysis_id = analysis_id
    )
    
    log_info("Success.")

}, error = function(e) {
    log_error(e$message)
    write_meta("failed", message = e$message, details = list(code = "RUNTIME_ERROR"))
    quit(save="no", status=1)
})
