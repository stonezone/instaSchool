#!/usr/bin/env python3
"""
Test script for verbose_logger.py
Demonstrates the usage of the verbose logger and tests its functionality
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(description="Test the verbose logger")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging of API calls")
parser.add_argument("--log-file", type=str, help="Specify a custom log file path")
args = parser.parse_args()

try:
    from src.verbose_logger import init_logger, check_log_file
    
    # Check if a custom log file path was provided, and if it's writable
    if args.log_file:
        is_writable, error_msg = check_log_file(args.log_file)
        if not is_writable:
            print(f"Warning: Could not use specified log file: {error_msg}")
            print("Falling back to default log file location")
            args.log_file = None
    
    # Initialize the logger with verbose mode if requested
    logger = init_logger(verbose=args.verbose, log_file=args.log_file)
    log_file_path = logger.get_log_file_path()
    
    print(f"Logging initialized. Log file: {log_file_path}")
    if args.verbose:
        print(f"Verbose mode enabled. Log output will be displayed in the terminal.")
    
    # Test different log types
    print("\nTesting logger functionality...")
    
    # Test API request logging for text model
    text_model_name = "gpt-4.1"
    endpoint = "chat.completions"
    text_params = {
        "model": text_model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
        "temperature": 0.7
    }
    
    # Test API request logging for image model
    image_model_name = "dall-e-3"
    image_endpoint = "images.generate"
    image_params = {
        "model": image_model_name,
        "prompt": "A beautiful educational illustration of science concepts",
        "n": 1,
        "size": "1024x1024",
        "quality": "standard"
    }
    
    # Log text model request
    logger.log_api_request(model=text_model_name, endpoint=endpoint, params=text_params)
    
    # Log image model request
    logger.log_api_request(model=image_model_name, endpoint=image_endpoint, params=image_params)
    
    # Test API response logging for text model
    text_response = {
        "id": "text-response-id",
        "model": text_model_name,
        "created": datetime.now().timestamp(),
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop",
                "index": 0
            }
        ]
    }
    
    # Test API response logging for image model
    image_response = {
        "created": datetime.now().timestamp(),
        "data": [
            {
                "url": "https://example.com/images/generated-image.png",
                "revised_prompt": "A detailed educational illustration showing scientific concepts with clear visuals and engaging colors"
            }
        ]
    }
    
    # Log responses
    logger.log_api_response(model=text_model_name, response=text_response)
    logger.log_api_response(model=image_model_name, response=image_response)
    
    # Test error logging
    test_error = ValueError("Test error message")
    logger.log_error(error=test_error, model=text_model_name, context="Testing error logging")
    
    # Test info and debug logging
    logger.log_info("This is an informational message")
    logger.log_debug("This is a debug message with detailed information")
    logger.log_warning("This is a warning message")
    
    print(f"\nLogger test completed successfully. Check the log file at: {log_file_path}")
    print("If verbose mode is enabled, you should see the log messages in the terminal above.")
    
except ImportError:
    print("Error: verbose_logger module not found.")
    sys.exit(1)
except Exception as e:
    print(f"Error testing logger: {e}")
    sys.exit(1)