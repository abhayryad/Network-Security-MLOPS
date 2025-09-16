import sys

from networksecurity.logging import logger
# Assuming you have a custom logger setup like this
# from networksecurity.logging import logger 

class NetworkSecurityException(Exception):
    def __init__(self, error_message: Exception):
        # Call the parent class constructor
        super().__init__(error_message)
        
        # Get exception info directly from the sys module
        _, _, exc_tb = sys.exc_info()
        
        if exc_tb:
            self.lineno = exc_tb.tb_lineno
            self.file_name = exc_tb.tb_frame.f_code.co_filename
        else:
            self.lineno = "N/A"
            self.file_name = "N/A"
        
        self.error_message = error_message

    def __str__(self):
        return f"Error occurred in python script name [{self.file_name}] line number [{self.lineno}] error message [{self.error_message}]"

# --- Example Usage ---
# if __name__ == '__main__':
#     try:
#         # logger.info("Enter the try block") # This is the more common way to log
#         logger.logging.info("Enter the try block")
#         a = 1 / 0
#     except Exception as e:
#         # Raise the custom exception without passing `sys`
#         raise NetworkSecurityException(e)