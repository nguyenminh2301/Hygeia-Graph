#!/usr/bin/env Rscript
# Hygeia-Graph: Idempotent R package installer
# Installs required CRAN packages for MGM execution

cat("=== Hygeia-Graph R Package Installer ===\n\n")

# Set CRAN mirror (avoid interactive prompts)
options(repos = c(CRAN = "https://cloud.r-project.org"))

# Required packages
required_packages <- c("mgm", "jsonlite", "digest", "uuid")

cat("Checking and installing required packages...\n")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat(sprintf("Installing %s...\n", pkg))
    install.packages(pkg, quiet = FALSE)
  } else {
    cat(sprintf("%s is already installed\n", pkg))
  }
}

cat("\n=== Installed Package Versions ===\n")

for (pkg in required_packages) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    version <- packageVersion(pkg)
    cat(sprintf("  %s: %s\n", pkg, version))
  } else {
    cat(sprintf("  %s: FAILED TO INSTALL\n", pkg))
  }
}

cat("\n=== R Environment ===\n")
cat(sprintf("R version: %s\n", R.version.string))
cat("\nInstallation complete!\n")
