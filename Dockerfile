# Hygeia-Graph Docker Image
# Plan B deployment for guaranteed R + Python environment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including R
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    build-essential \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -e .

# Install R packages (mgm, jsonlite, digest, uuid)
RUN Rscript r/install.R

# Environment variables
ENV PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["bash", "-lc", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
