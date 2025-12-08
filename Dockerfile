# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for yt_dlp and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy all application files
COPY . .

# Install Python dependencies directly
RUN pip install --no-cache-dir fastapi uvicorn yt_dlp ytmusicapi httpx
RUN pip install -U yt-dlp
# Set environment variable for Cloud Run
ENV PORT 8080

# Expose port
EXPOSE 8080

# Run the FastAPI app
CMD ["sh", "-c", "uvicorn backend:app --host 0.0.0.0 --port $PORT"]