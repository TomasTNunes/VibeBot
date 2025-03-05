#!/bin/bash

# Download latest version of Lavalink.jar. This script should be ran from project root (./scripts/download_lavalink.sh)
# Delete existing Lavalink.jar
rm -rf lavalink/Lavalink.jar

# Fetch the latest release information from the GitHub API
response=$(curl -s https://api.github.com/repos/lavalink-devs/Lavalink/releases/latest)

# Extract the browser_download_url for the Lavalink.jar asset
# Using grep, sed, and awk to parse the JSON response
download_url=$(echo "$response" | grep -o '"browser_download_url": "[^"]*' | grep 'Lavalink.jar' | sed 's/"browser_download_url": "//')

# Check if the download URL was successfully extracted
if [[ -z "$download_url" ]]; then
  echo "Error: Could not find the download URL for Lavalink.jar"
  exit 1
fi

# Download the file
echo "Downloading Lavalink.jar from: $download_url"
curl -L -o lavalink/Lavalink.jar "$download_url"

# Check if the download was successful
if [[ $? -eq 0 ]]; then
  echo "Download completed successfully: Lavalink.jar"
else
  echo "Error: Failed to download Lavalink.jar"
  exit 1
fi