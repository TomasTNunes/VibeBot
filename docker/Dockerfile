# Use an official Python runtime as the base image.
FROM python:3.12.2-slim

# Set the working directory inside the container
WORKDIR /app

# Install gosu (alternative to su-exec)
RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ .

# Add script to switch user and run it
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Run the application
CMD ["python", "main.py"]
