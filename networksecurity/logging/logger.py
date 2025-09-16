import logging
import os
from datetime import datetime

# 1. Create the log file name
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

# 2. Define the path for the "logs" directory
logs_path = os.path.join(os.getcwd(), "logs")

# 3. Create the directory, if it doesn't exist
os.makedirs(logs_path, exist_ok=True)

# 4. Define the full path for the log file
LOG_FILE_PATH = os.path.join(logs_path, LOG_FILE)

# 5. Configure the logger
logging.basicConfig(
    filename=LOG_FILE_PATH,
    # The typo is corrected here from 'levename' to 'levelname'
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- Example Usage ---
# After setting up the config, you can now log messages
if __name__ == "__main__":
    logging.info("Logging has started!")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")