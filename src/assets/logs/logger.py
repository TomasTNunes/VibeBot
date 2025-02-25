import os
import logging
from logging.handlers import RotatingFileHandler

# Define the log file path
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.log')

############################################################################################################
######################################### CONFIGURE ROOT LOGGER ############################################
############################################################################################################

# Configure logging for Root Logger (all loggers)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a formatter
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Create a custom variable with the logger name inside brackets, padded to 22 spaces
        record.name_in_brackets = f"[{record.name}]"
        return super().format(record)
formatter = CustomFormatter('%(asctime)s %(levelname)-8s %(name_in_brackets)-21s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Create a StreamHandler for terminal output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Create a FileHandler for file output
file_handler = RotatingFileHandler(log_file_path, maxBytes=1*1024*1024*1024, backupCount=1)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

############################################################################################################
############################################ CREATE LOGGERS ################################################
############################################################################################################

# Create a logger for main.py (Server Side)
main_logger = logging.getLogger('vibebot')
main_logger.propagate = True # use Root Handlers

# Create a logger for cogs.music.py (Server Side)
music_logger = logging.getLogger('vibebot.music')
music_logger.propagate = True # use Root Handlers
