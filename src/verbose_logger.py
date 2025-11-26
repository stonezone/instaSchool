"""
Verbose Logger Module for InstaSchool Curriculum Generator
Provides functionality to log API calls, responses and other debug information
"""

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path

class VerboseLogger:
    """Logger class to handle verbose output and file logging"""
    
    def __init__(self, verbose=False, log_file=None):
        """Initialize the logger
        
        Args:
            verbose (bool): Whether to print verbose output to console
            log_file (str): Path to log file. If None, creates one in logs directory
        """
        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)
        
        # Generate log filename with timestamp if not provided
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"logs/instaschool_{timestamp}.log"
        
        # Configure logger
        self.logger = logging.getLogger('instaschool')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # File handler (always active)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
        
        # Console handler (only in verbose mode)
        self.verbose = verbose
        if verbose:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(logging.Formatter(
                '\033[92m%(asctime)s\033[0m - \033[94m%(levelname)s\033[0m - %(message)s'
            ))
            self.logger.addHandler(console_handler)
        
        self.log_file = log_file
        self.logger.info(f"Logging initialized. Log file: {log_file}")
        
        # Print a prominent banner if verbose mode is enabled
        if verbose:
            print("\n" + "="*80)
            print("\033[1m\033[96m VERBOSE MODE ENABLED \033[0m")
            print(" All API requests and responses will be displayed in the terminal")
            print(f" Log file: {log_file}")
            print("="*80 + "\n")
            self.logger.info("Verbose mode enabled - API calls will be displayed in terminal")
    
    def log_api_request(self, model, endpoint, params):
        """Log an API request
        
        Args:
            model (str): The AI model being used
            endpoint (str): The API endpoint being called
            params (dict): The parameters being sent to the API
        """
        # Create a sanitized copy of params for logging
        safe_params = params.copy() if isinstance(params, dict) else {"raw_params": str(params)}
        
        # Remove potentially sensitive data
        if isinstance(safe_params, dict):
            if 'api_key' in safe_params:
                safe_params['api_key'] = '***API_KEY_REDACTED***'
            if 'headers' in safe_params and isinstance(safe_params['headers'], dict):
                if 'Authorization' in safe_params['headers']:
                    safe_params['headers']['Authorization'] = '***AUTH_REDACTED***'
                if 'api-key' in safe_params['headers']:
                    safe_params['headers']['api-key'] = '***API_KEY_REDACTED***'
        
        # Format the request for logging
        try:
            params_str = json.dumps(safe_params, indent=2)
        except (TypeError, ValueError):
            params_str = str(safe_params)
        
        log_msg = f"API REQUEST: {model} - {endpoint}\n{params_str}"
        self.logger.debug(log_msg)
        
        # For console output in verbose mode, make it stand out
        if self.verbose:
            print("\n" + "="*80)
            print(f"\033[1m\033[96m>>> OUTGOING REQUEST: {model} - {endpoint}\033[0m")
            print("-"*80)
            print(params_str)
            print("="*80 + "\n")
    
    def log_api_response(self, model, response, status=None):
        """Log an API response
        
        Args:
            model (str): The AI model that was used
            response: The response from the API
            status (int, optional): HTTP status code if available
        """
        # Format response for logging
        try:
            if hasattr(response, '__dict__'):
                # Use __dict__ for OpenAI response objects
                response_dict = response.__dict__
                # Handle nested objects
                for key, value in response_dict.items():
                    if hasattr(value, '__dict__'):
                        response_dict[key] = value.__dict__
                response_str = json.dumps(response_dict, indent=2, default=str)
            else:
                response_str = json.dumps(response, indent=2, default=str)
        except (TypeError, ValueError):
            response_str = str(response)
        
        # Status text
        status_text = f" (Status: {status})" if status else ""
        log_msg = f"API RESPONSE: {model}{status_text}\n{response_str}"
        self.logger.debug(log_msg)
        
        # For console output in verbose mode, make it stand out
        if self.verbose:
            print("\n" + "="*80)
            print(f"\033[1m\033[92m<<< INCOMING RESPONSE: {model}{status_text}\033[0m")
            print("-"*80)
            print(response_str)
            print("="*80 + "\n")
    
    def log_error(self, error, model=None, context=None, include_traceback=False):
        """Log an error with optional traceback

        Args:
            error: The error that occurred
            model (str, optional): The AI model being used when the error occurred
            context (str, optional): Additional context about the error
            include_traceback (bool): If True, include full traceback in log file
        """
        import traceback as tb
        model_info = f" ({model})" if model else ""
        context_info = f" - Context: {context}" if context else ""

        log_msg = f"ERROR{model_info}: {str(error)}{context_info}"
        self.logger.error(log_msg)

        # Log full traceback to file if requested
        if include_traceback:
            self.logger.error(f"Traceback:\n{tb.format_exc()}")

        # For console output in verbose mode, make it stand out
        if self.verbose:
            print(f"\033[91mERROR{model_info}: {str(error)}{context_info}\033[0m")
            if include_traceback:
                print(f"\033[91m{tb.format_exc()}\033[0m")
    
    def log_info(self, message):
        """Log an informational message
        
        Args:
            message (str): The message to log
        """
        self.logger.info(message)
    
    def log_warning(self, message):
        """Log a warning message
        
        Args:
            message (str): The warning message to log
        """
        self.logger.warning(message)
        
    def log_debug(self, message):
        """Log a debug message
        
        Args:
            message (str): The debug message to log
        """
        self.logger.debug(message)

    def get_log_file_path(self):
        """Get the path to the current log file
        
        Returns:
            str: Path to the log file
        """
        return self.log_file


# Global logger instance - will be initialized by main application
logger = None

def init_logger(verbose=False, log_file=None):
    """Initialize the global logger instance
    
    Args:
        verbose (bool): Whether to enable verbose mode
        log_file (str, optional): Path to log file
    
    Returns:
        VerboseLogger: The logger instance
    """
    global logger
    logger = VerboseLogger(verbose=verbose, log_file=log_file)
    return logger

def get_logger():
    """Get the global logger instance
    
    Returns:
        VerboseLogger: The logger instance
    """
    global logger
    if logger is None:
        # Initialize with defaults if not already initialized
        logger = init_logger()
    return logger

def check_log_file(log_file_path):
    """Check if the log file exists and is writable
    
    Args:
        log_file_path (str): Path to the log file
        
    Returns:
        bool: True if the log file is writable, False otherwise
        str: Error message if there was an error, None otherwise
    """
    if not log_file_path:
        return False, "No log file path provided"
    
    try:
        # Check if the directory exists
        log_dir = os.path.dirname(log_file_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                print(f"Created log directory: {log_dir}")
            except Exception as e:
                return False, f"Could not create log directory: {e}"
        
        # Check if the file is writable by attempting to open it
        with open(log_file_path, 'a') as f:
            f.write("")
        
        return True, None
    except Exception as e:
        return False, f"Error checking log file: {e}"