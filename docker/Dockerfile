# Use an official Python runtime as the base image.
# Slim image to minimize storage size.
FROM python:3.12.2-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ .

# Run the application
CMD ["python", "main.py"]