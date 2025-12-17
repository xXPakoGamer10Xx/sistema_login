FROM python:3.12-slim

# Install system dependencies
# build-essential for compiling some python packages if needed
# libpango... for reportlab/pdf generation if required (often needed for advanced PDF features, but basic is fine)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Install gunicorn for production serving
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application
COPY . .

# Create necessary directories that might not exist or need specific permissions
RUN mkdir -p instance logs static/uploads/perfiles

# Expose the port the app runs on
EXPOSE 5001

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Run the entrypoint script
CMD ["./entrypoint.sh"]
