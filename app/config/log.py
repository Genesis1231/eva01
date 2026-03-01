import logging
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR) # or logging.ERROR
logger.propagate = False

# Create a console handler and set level to error
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create a file handler and set level to warning
# file_handler = logging.FileHandler('eva.log')
# file_handler.setLevel(logging.ERROR)

# Create a formatter and set it for both handlers
formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
# logger.addHandler(file_handler)
