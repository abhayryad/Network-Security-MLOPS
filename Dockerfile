# Use the specified lightweight base image
FROM python:3.10-slim-buster

# Set the working directory
WORKDIR /app

# --- Python Dependencies (Cached Layer) ---
# Copy requirements file first. This layer is only rebuilt if requirements.txt changes.
COPY requirements.txt .

# Install Python dependencies using --no-cache-dir to avoid storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# --- Application Code ---
# Copy the rest of the application code. This layer is only rebuilt if the app code changes.
COPY . .

# Define the command to run the application
CMD ["python3", "app.py"]