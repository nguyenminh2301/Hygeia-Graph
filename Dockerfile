# Hygeia-Graph Docker Image
# Optimized for Hugging Face Spaces (Docker SDK)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including R and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    build-essential \
    gfortran \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -e .

# Install R packages (mgm, jsonlite, digest, uuid)
RUN Rscript r/install.R

# Environment variables for Hugging Face Spaces
ENV PORT=7860
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Expose port
EXPOSE 7860

# Run Streamlit on port 7860 (required for HF Spaces)
CMD ["bash", "-lc", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-7860}"]
