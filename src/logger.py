import os
import logging
from logging.handlers import RotatingFileHandler

# Define the log file path
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.log')

# Configure logging
logger = logging.getLogger() # Get the root logger
logger.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Create a StreamHandler for terminal output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Create a FileHandler for file output
file_handler = RotatingFileHandler(log_file_path, maxBytes=1*1024*1024*1024, backupCount=1)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)