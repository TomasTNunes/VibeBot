import os
import logging
from logging.handlers import RotatingFileHandler

# Define the log file path
log_directory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/')

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
file_handler = RotatingFileHandler(os.path.join(log_directory_path, 'bot.log'), maxBytes=1*1024*1024*1024, backupCount=1)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

############################################################################################################
############################################ CREATE LOGGERS ################################################
############################################################################################################

# Create a logger for main.py
main_logger = logging.getLogger('vibebot')
main_logger.propagate = True # use Root Handlers

# Create a logger for cogs.music.py
music_logger = logging.getLogger('vibebot.music')
music_logger.propagate = True # use Root Handlers

# Create a logger for music data in cogs.music.py
music_data_logger = logging.getLogger('vibebot.music.music_data')
music_data_logger.propagate = False # don't use Root Handlers
music_data_log_path = os.path.join(log_directory_path, 'music_data.log')
music_data_file_handler = RotatingFileHandler(music_data_log_path, maxBytes=1*1024*1024*1024, backupCount=1)
music_data_formatter = CustomFormatter('%(asctime)s %(levelname)-8s %(name_in_brackets)-27s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
music_data_file_handler.setFormatter(music_data_formatter)
music_data_logger.addHandler(music_data_file_handler)

# Create a logger for debugging
debug_logger = logging.getLogger('vibebot.debug')
debug_logger.propagate = False # don't use Root Handlers
debug_log_path = os.path.join(log_directory_path, 'debug.log')
debug_file_handler = RotatingFileHandler(debug_log_path, maxBytes=1*1024*1024*1024, backupCount=1)
debug_formatter = CustomFormatter('%(asctime)s %(levelname)-8s %(name_in_brackets)-21s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
debug_file_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_file_handler)
