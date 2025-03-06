#!/bin/bash

# This script installs pre-commit hooks, and only needs to be ran once at the start.
# After cloning/forking the repository and installing Python requirements from requirements.txt,
# make sure you have the project's Python environment activated before running this script.
pre-commit install --install-hooks