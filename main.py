import os
import sys

# CRITICAL: Set matplotlib backend BEFORE any other imports that might use it
import matplotlib
matplotlib.use('Agg')  # Use Agg backend for matplotlib

import streamlit as st
import json
import time
import uuid
import traceback
import shutil
import tempfile
import atexit
import base64
import markdown
import matplotlib.pyplot as plt
import argparse
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
import requests
from PIL import Image, ImageDraw, ImageFont

# Import new components
from src.state_manager import StateManager
from src.error_handler import ErrorHandler
from utils.regeneration_fix import RegenerationHandler
from src.cost_estimator import estimate_curriculum_cost, get_model_info

# Parse command line arguments
parser = argparse.ArgumentParser(description="Curriculum Generator with Verbose Mode")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging of API calls")
parser.add_argument("--log-file", type=str, help="Specify a custom log file path")
args, unknown = parser.parse_known_args()

# Initialize verbose logger
# Even if verbose mode is not enabled, we still initialize the logger for file logging
try:
    from src.verbose_logger import init_logger, get_logger, check_log_file

    # If a custom log file path was provided, check if it's writable
    if args.log_file:
        is_writable, error_msg = check_log_file(args.log_file)
        if not is_writable:
            # Use stderr instead of stdout to avoid Streamlit capturing it
            sys.stderr.write(f"Warning: Could not use specified log file: {error_msg}\n")
            sys.stderr.write("Falling back to default log file location\n")
            args.log_file = None

    # Initialize the logger with verbose mode if requested
    logger = init_logger(verbose=args.verbose, log_file=args.log_file)
    log_file_path = logger.get_log_file_path()
    
    # Register the logger in the global context
    if args.verbose:
        sys.stderr.write(f"Verbose mode enabled. All API calls will be logged to the terminal and to: {log_file_path}\n")
    else:
        sys.stderr.write(f"Logging to file: {log_file_path}. Use --verbose flag to see API calls in terminal.\n")
        sys.stderr.write(f"Command to enable verbose mode: streamlit run main.py -- --verbose\n")
except ImportError:
    sys.stderr.write("Warning: verbose_logger module not found. Logging disabled.\n")
    args.verbose = False
    logger = None

# Import the agent framework and image generator
from src.agent_framework import OrchestratorAgent, OutlineAgent, ContentAgent, MediaAgent, ChartAgent, QuizAgent, SummaryAgent, ResourceAgent, AudioAgent
from src.image_generator import ImageGenerator
from services.curriculum_service import CurriculumService, CurriculumValidator
from services.export_service import CurriculumExporter
from services.session_service import SessionManager, QuizManager, InputValidator
from services.batch_service import BatchManager
from services.user_service import UserService
from services.analytics_service import AnalyticsService
from services.provider_service import AIProviderService
from version import get_version_display, VERSION

# Import modern UI components
from src.ui_components import ModernUI, ThemeManager, LayoutHelpers, StatusLogger, FamilyDashboard
from services.family_service import get_family_service
from services.report_service import get_report_service
from services.customization_service import get_customization_service, CustomizationService

# Import model detector for dynamic model detection
from src.model_detector import get_available_models, get_fallback_models, get_recommended_models

# Setup page config for wider layout
st.set_page_config(page_title="Curriculum Generator", page_icon=":books:", layout="wide")

# Load modern UI design system
ModernUI.load_css()

# Mobile layout detection
# Note: True JS-based detection requires streamlit-js-eval dependency
# Instead, we provide a manual toggle and use CSS media query hints
def detect_mobile_from_query_params():
    """Check if mobile mode was requested via query params or previous toggle"""
    # Check query params for mobile hint
    try:
        params = st.query_params
        if params.get("mobile") == "1":
            return True
    except Exception:
        pass
    return False

# Set global state for mobile detection
if "is_mobile" not in st.session_state:
    mobile_detected = detect_mobile_from_query_params()
    StateManager.set_state("is_mobile", mobile_detected)

# More robust OpenAI import handling
try:
    import openai
    # Check if we're using OpenAI v1.0.0+ (newer client)
    if hasattr(openai, '__version__') and openai.__version__[0] >= '1':
        try:
            from openai import OpenAI
            client = None  # Will initialize later
            OPENAI_NEW_API = True
            sys.stderr.write(f"Using OpenAI Python SDK v{openai.__version__}\n")
        except ImportError as e:
            st.error(f"Error importing from OpenAI library: {e}")
            st.error("You have OpenAI installed but there was an error importing the client.")
            st.error("Try: pip install --upgrade openai")
            st.stop()
    else:
        # Handle older OpenAI SDK (<1.0.0)
        st.error("You have an older version of the OpenAI library installed.")
        st.error("This application requires OpenAI Python SDK v1.0.0 or higher.")
        st.error("Please run: pip install --upgrade openai")
        st.stop()
except ImportError:
    st.error("OpenAI library not found. Please run: pip install --upgrade openai")
    st.stop()

# Define exception classes that might not exist in all versions
try:
    # For newer OpenAI SDK v1.x
    from openai import APIError, RateLimitError
except ImportError:
    # Fallback definitions for older versions or if specific errors aren't found
    class APIError(Exception): pass
    class RateLimitError(Exception): pass

# ========== Load API Keys and Initialize Client ==========
# Note: This section now supports multi-provider AI services
# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    sys.stderr.write("python-dotenv not installed, using system environment variables only\n")

# Get OpenAI API key for backward compatibility
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize client - will be set by provider service or fallback
client = None
provider_service = None
current_provider = None

# First, we need to load config to initialize provider service
# (Config loading happens later, so we'll do initial client setup after config load)
# For now, check if OpenAI key exists for backward compatibility
if not OPENAI_API_KEY:
    sys.stderr.write("Warning: OPENAI_API_KEY not set. Will attempt to use provider service after config loads.\n")

# ========== Detect Available Models ==========
# Initialize available models in session state
if "available_models" not in st.session_state:
    try:
        # Try to detect models from OpenAI API
        sys.stderr.write("Detecting available OpenAI models...\\n")
        available_models = get_available_models(client)
        
        if 'error' in available_models:
            # Fallback to config if detection fails
            sys.stderr.write(f"Model detection failed: {available_models['error']}\\n")
            sys.stderr.write("Using fallback models from config...\\n")
            StateManager.set_state("available_models", None)
            StateManager.set_state("model_detection_error", available_models['error'])
        else:
            StateManager.set_state("available_models", available_models)
            StateManager.set_state("model_detection_error", None)
            sys.stderr.write(f"Detected {len(available_models['text_models'])} text models and {len(available_models['image_models'])} image models\\n")
    except Exception as e:
        sys.stderr.write(f"Exception during model detection: {e}\\n")
        StateManager.set_state("available_models", None)
        StateManager.set_state("model_detection_error", str(e))

# ========== Initialize session state and services ==========
# Initialize session manager
if "session_manager" not in st.session_state:
    try:
        StateManager.set_state("session_manager", SessionManager())
    except Exception as e:
        st.error(f"Failed to initialize session manager: {e}")
        StateManager.set_state("session_manager", None)

if "curriculum" not in st.session_state:
    StateManager.set_state("curriculum", None)
if "curriculum_id" not in st.session_state:
    StateManager.set_state("curriculum_id", uuid.uuid4().hex)
# Initialize session state using StateManager
StateManager.initialize_state()

# Additional state initialization
if "api_error" not in st.session_state:
    StateManager.set_state("api_error", None)
if "theme" not in st.session_state:
    StateManager.set_state("theme", "Light")

# Create directories if they don't exist
Path("curricula").mkdir(exist_ok=True)
Path("exports").mkdir(exist_ok=True)

# ========== Utility Functions for Session Management ==========
def add_to_cleanup(file_path: Optional[str]):
    """Adds a file path to the set of temporary files to be cleaned up on exit."""
    if file_path and os.path.exists(file_path):
        temp_files = StateManager.get_state("last_tmp_files", set())
        if not isinstance(temp_files, set):
            temp_files = set(temp_files) if temp_files else set()
        temp_files.add(file_path)
        StateManager.set_state("last_tmp_files", temp_files)

def save_base64_to_temp_file(b64_data: str, suffix=".png") -> Optional[str]:
    """Decodes base64 data and saves it to a temporary file, returning the path."""
    if not isinstance(b64_data, str) or not b64_data:
        st.warning("Invalid base64 data provided (empty or not string).")
        return None
    try:
        # Ensure correct padding
        missing_padding = len(b64_data) % 4
        if missing_padding:
            b64_data += '=' * (4 - missing_padding)

        img_bytes = base64.b64decode(b64_data)
        # Use tempfile for secure temporary file creation
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tf:
            tf.write(img_bytes)
            temp_path = tf.name
        add_to_cleanup(temp_path)  # Add to our cleanup list
        return temp_path
    except (base64.binascii.Error, ValueError) as decode_err:
        st.error(f"Error decoding base64 data: {decode_err}")
        return None

def save_session(curriculum: dict, filename: str):
    """Saves the current curriculum state to a JSON file."""
    if not curriculum or not isinstance(curriculum, dict):
        st.error("Cannot save: Invalid curriculum data.")
        return

    save_path = Path("curricula") / Path(filename).name  # Ensure it saves in the curricula dir
    try:
        # Create a deep copy to avoid modifying the live session state
        save_data = json.loads(json.dumps(curriculum))

        # Remove temporary file paths before saving
        for unit in save_data.get("units", []):
            if "images" in unit and isinstance(unit["images"], list):
                for img_dict in unit["images"]:
                    if isinstance(img_dict, dict):
                        img_dict.pop("path", None)  # Remove temp path
            if "chart" in unit and isinstance(unit["chart"], dict):
                unit["chart"].pop("path", None)  # Remove temp path

        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(save_data, f, indent=4)
        st.success(f"Session saved to {save_path}")
    except TypeError as serial_err:
        st.error(f"Data structure error: Cannot serialize curriculum for saving. Details: {serial_err}")
        sys.stderr.write(traceback.format_exc() + "\n")
    except IOError as e:
        st.error(f"Error writing session file {save_path}: {e}")
    except Exception as e:
        st.error(f"Unexpected error saving session: {e}")
        sys.stderr.write(traceback.format_exc() + "\n")

def load_session(filename: str) -> Optional[dict]:
    """Loads a curriculum session from a JSON file."""
    load_path = Path("curricula") / Path(filename).name  # Ensure it loads from the curricula dir
    if not load_path.exists():
        st.error(f"Session file not found: {load_path}")
        return None

    try:
        with open(load_path, "r", encoding='utf-8') as f:
            loaded_curriculum = json.load(f)

        # Basic validation
        if not isinstance(loaded_curriculum, dict) or "meta" not in loaded_curriculum or "units" not in loaded_curriculum:
            st.error(f"Invalid format in session file {load_path}.")
            return None

        # Recreate temporary file paths for images/charts from base64 data
        for unit in loaded_curriculum.get("units", []):
            if "images" in unit and isinstance(unit["images"], list):
                for img_dict in unit["images"]:
                    if isinstance(img_dict, dict) and "b64" in img_dict:
                        path = save_base64_to_temp_file(img_dict["b64"])
                        if path:
                            img_dict["path"] = path  # Add temp path back
            if "chart" in unit and isinstance(unit["chart"], dict) and "b64" in unit["chart"]:
                chart_path = save_base64_to_temp_file(unit["chart"]["b64"])
                if chart_path:
                    unit["chart"]["path"] = chart_path  # Add temp path back
            elif "chart" in unit and isinstance(unit["chart"], dict):
                unit["chart"]["path"] = None  # Ensure path key exists even if no b64

        st.success(f"Session loaded from {load_path}")
        return loaded_curriculum

    except FileNotFoundError:  # Should be caught by exists() check, but belt-and-suspenders
        st.error(f"Session file not found: {load_path}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from {load_path}: {e}")
        return None
    except IOError as e:
        st.error(f"Error reading session file {load_path}: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error loading session: {e}")
        sys.stderr.write(traceback.format_exc() + "\n")
        return None

# ========== Load Config (Robust Version) ==========
def load_config(path="config.yaml") -> Dict[str, Any]:
    config_data = {}
    try:
        with open(path, "r", encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        if not isinstance(config_data, dict):
            st.error(f"Invalid YAML format in {path}. Expected a dictionary (key-value pairs).")
            st.stop()
    except FileNotFoundError:
        st.warning(f"Configuration file '{path}' not found. Using default settings.")
        st.sidebar.info(f"Tip: Create a '{path}' file to customize prompts and defaults.")
    except yaml.YAMLError as e:
        st.error(f"Error parsing configuration file '{path}': {e}. Check YAML syntax.")
        st.stop()
    except Exception as e:
        st.error(f"An unexpected error occurred loading configuration: {e}")
        sys.stderr.write(traceback.format_exc() + "\n")
        st.stop()

    # Ensure primary keys exist
    config_data.setdefault("prompts", {})
    config_data.setdefault("defaults", {})
    config_data.setdefault("info_texts", {})

    # Validate and set defaults for prompts
    prompts = config_data["prompts"]
    required_prompts = ["outline", "content", "image", "chart", "quiz", "summary", "resources"]
    default_prompt_template = "Generate {prompt_type} for topic: {{topic}} for grade {{grade}} {{subject}}. Style: {{style}}. Language: {{language}}. Guidelines: {{extra}}. Output Format: {{format}}" # Added more context and format hint
    for p in required_prompts:
        if p not in prompts or not prompts[p]:
            st.warning(f"Prompt '{p}' missing or empty in config.yaml, using basic fallback.")
            format_hint = "JSON object with key 'topics' containing a list of strings" if p == "outline" else "JSON object with key 'quiz' containing a list of question objects (question, type, options, answer)" if p == "quiz" else "JSON object with keys 'chart_type', 'title', 'data' (with 'labels' and 'values'), 'x_label', 'y_label'" if p == "chart" else "Markdown formatted text"
            prompts[p] = default_prompt_template.format(prompt_type=p, format=format_hint)

    # Validate and set defaults for settings
    defaults = config_data["defaults"]
    defaults.setdefault("subjects", ["Biology", "Chemistry", "Math", "History", "Language Arts"])
    defaults.setdefault("subject", "Biology")
    defaults.setdefault("grades", ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "University"])
    defaults.setdefault("grade", "6")
    defaults.setdefault("styles", ["Standard", "Inquiry-based", "Project-based", "Detailed", "Concise"])
    defaults.setdefault("style", "Standard")
    defaults.setdefault("extra", "")
    defaults.setdefault("media_richness", 3) # 0: Text, 1:Maybe Img, 2:+Img, 3:Maybe Chart, 4:+Chart, 5:+More Img
    defaults.setdefault("languages", ["English", "Spanish", "French", "German", "Chinese"])
    defaults.setdefault("language", "English")
    defaults.setdefault("text_model", "gpt-4.1") # Default to the orchestrator model
    defaults.setdefault("worker_model", "gpt-4.1-mini") # Model for worker agents
    defaults.setdefault("image_model", "gpt-image-1") # Default to gpt-image-1 for better images
    # Set available image models if not defined
    defaults.setdefault("image_models", ["gpt-image-1", "dall-e-3", "dall-e-2"])
    defaults.setdefault("include_quizzes", True)
    defaults.setdefault("include_summary", True)
    defaults.setdefault("include_resources", True)
    defaults.setdefault("include_keypoints", True)
    defaults.setdefault("min_topics", 3)
    defaults.setdefault("max_topics", 5)
    defaults.setdefault("days", 3)

    # Add info about agentic framework if not present
    info_texts = config_data["info_texts"]
    if "agentic_info" not in info_texts:
        info_texts["agentic_info"] = """
        This application uses an agentic framework where multiple AI models work together:
        
        - **Orchestrator**: Plans and coordinates the curriculum
        - **Workers**: Create specific content components
        - **Image Generator**: Creates educational illustrations
        
        Choose the image model that suits your needs:
        - **GPT-Image-1**: Highest quality educational illustrations
        - **DALL-E 3**: Good quality with creative elements
        - **DALL-E 2**: Basic illustrations, faster generation
        """

    return config_data

# Load configuration
config = load_config()

# ========== Initialize AI Provider Service ==========
# Initialize provider service for multi-provider support (OpenAI, Kimi, Ollama)
if 'provider_service' not in st.session_state or 'current_provider' not in st.session_state:
    try:
        # Initialize provider service
        provider_service = AIProviderService(config)
        
        # Get default provider
        current_provider = provider_service.get_default_provider()
        
        # Get client from provider service
        client = provider_service.get_client(current_provider)
        
        # Store in session state
        StateManager.set_state('provider_service', provider_service)
        StateManager.set_state('current_provider', current_provider)
        
        sys.stderr.write(f"✓ Initialized AI provider: {current_provider}\n")
        
    except Exception as e:
        # Fallback to direct OpenAI client if provider service fails
        sys.stderr.write(f"Warning: Provider service initialization failed: {e}\n")
        sys.stderr.write("Falling back to direct OpenAI client...\n")
        
        if not OPENAI_API_KEY:
            st.error("OPENAI_API_KEY not set in environment variable or .env file")
            st.error("Please set your OpenAI API key to use this application.")
            st.stop()
        
        try:
            # Direct OpenAI client initialization as fallback
            if 'OPENAI_NEW_API' in locals() and OPENAI_NEW_API:
                client = OpenAI(api_key=OPENAI_API_KEY)
                StateManager.set_state('provider_service', None)
                StateManager.set_state('current_provider', 'openai')
                sys.stderr.write("✓ Using direct OpenAI client (fallback mode)\n")
            else:
                st.error("OpenAI client initialization failed. SDK version issue suspected.")
                st.stop()
        except Exception as fallback_error:
            st.error(f"Error initializing OpenAI client: {fallback_error}")
            sys.stderr.write(traceback.format_exc() + "\n")
            st.stop()
else:
    # Use existing provider service from session state
    provider_service = StateManager.get_state('provider_service')
    current_provider = StateManager.get_state('current_provider')
    
    # Get client from provider service or use direct client
    if provider_service:
        try:
            client = provider_service.get_client(current_provider)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to get client from provider service: {e}\n")
            # Fallback to direct OpenAI client
            if OPENAI_API_KEY and 'OPENAI_NEW_API' in locals() and OPENAI_NEW_API:
                client = OpenAI(api_key=OPENAI_API_KEY)
            else:
                st.error("Failed to initialize AI client")
                st.stop()

# Ensure we have a valid client
if client is None:
    st.error("Failed to initialize AI client. Please check your API keys and configuration.")
    st.stop()

# Initialize curriculum service and template manager after config is loaded
if "curriculum_service" not in st.session_state:
    try:
        StateManager.set_state("curriculum_service", CurriculumService(client, config))
    except Exception as e:
        st.error(f"Failed to initialize curriculum service: {e}")
        sys.stderr.write(f"Curriculum service error: {e}\n")
        sys.stderr.write(traceback.format_exc() + "\n")
        StateManager.set_state("curriculum_service", None)

# Initialize template manager
if "template_manager" not in st.session_state:
    try:
        from services.template_service import TemplateManager
        StateManager.set_state("template_manager", TemplateManager())
    except ImportError:
        sys.stderr.write("Warning: template_service not available\n")
        StateManager.set_state("template_manager", None)
    except Exception as e:
        st.error(f"Failed to initialize template manager: {e}")
        StateManager.set_state("template_manager", None)

# Initialize batch manager
if "batch_manager" not in st.session_state:
    try:
        StateManager.set_state("batch_manager", BatchManager(max_concurrent=2))
    except Exception as e:
        st.error(f"Failed to initialize batch manager: {e}")
        StateManager.set_state("batch_manager", None)

# Initialize batch state
if "active_batch_id" not in st.session_state:
    StateManager.set_state("active_batch_id", None)
if "batch_polling" not in st.session_state:
    StateManager.set_state("batch_polling", False)

# ====================== Cleanup Function ======================
def cleanup_tmp_files(fileset: set):
    """Delete temporary files when they're no longer needed"""
    for filepath in fileset:
        try:
            Path(filepath).unlink(missing_ok=True) # Delete file if it exists
            sys.stderr.write(f"Deleted tmp file: {filepath}\n")
        except Exception as e:
            sys.stderr.write(f"Error deleting tmp file {filepath}: {e}\n")

# Register cleanup on app exit using session manager
def cleanup_on_exit():
    """Cleanup function for app exit"""
    try:
        if 'session_manager' in st.session_state:
            st.session_state.session_manager.cleanup_temp_files()
        else:
            # Fallback cleanup if session manager not available
            temp_files = StateManager.get_state('last_tmp_files', set())
            for filepath in temp_files:
                try:
                    Path(filepath).unlink(missing_ok=True)
                except Exception as e:
                    sys.stderr.write(f"Error deleting temp file {filepath}: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error during cleanup: {e}\n")

atexit.register(cleanup_on_exit)

# ====================== Utility Functions ======================
def update_quiz_answer(q_key: str, user_answer: str, correct_answer: str, case_sensitive: bool = True) -> bool:
    """Safely update quiz answer in session state to avoid race conditions
    
    Args:
        q_key: Unique question key
        user_answer: User's answer
        correct_answer: Correct answer
        case_sensitive: Whether to use case-sensitive comparison
        
    Returns:
        bool: True if update succeeded, False otherwise
    """
    try:
        # Compare answers
        if case_sensitive:
            is_correct = (user_answer == correct_answer)
        else:
            is_correct = (user_answer.strip().lower() == correct_answer.strip().lower())

        # Atomic update via StateManager
        StateManager.update_quiz_answer(q_key, user_answer, is_correct)
        return True
    except Exception as e:
        st.error(f"Error updating quiz answer: {e}")
        sys.stderr.write(f"Quiz update error: {e}\n")
        return False

def safe_serialize_for_json(obj):
    """Convert objects to serializable types to avoid JSON issues"""
    if isinstance(obj, (datetime, Path)):
        return str(obj)
    if hasattr(obj, 'to_json'):
        return obj.to_json()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    # If couldn't serialize, convert to string
    return str(obj)

def base64_to_file(base64_str: str, file_path: str) -> Optional[str]:
    """Save a base64 string to a file and return the file path"""
    if not base64_str:
        return None
    try:
        img_data = base64.b64decode(base64_str)
        with open(file_path, 'wb') as f:
            f.write(img_data)
        return file_path
    except Exception as e:
        sys.stderr.write(f"Error saving base64 to file: {e}\n")
        return None

# ====================== Agent Classes ======================
# These have been moved to agent_framework.py

# ====================== Initialize Enhanced Image Generator ======================
# Ensure we have a valid default image model
default_image_model = config["defaults"].get("image_model", "gpt-imagegen-1")
# Use stderr to avoid Streamlit capturing this output
sys.stderr.write(f"Using default image model: {default_image_model}\n")
image_generator = ImageGenerator(client, default_image_model)

# ====================== Initialize Orchestrator and Worker Agents ======================
orchestrator = OrchestratorAgent(
    client, 
    model=config["defaults"]["text_model"],
    worker_model=config["defaults"]["worker_model"]
)

# ========================= UI Components =========================
# Mode Selector - Teacher vs Student
st.sidebar.markdown("## 🎓 InstaSchool")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Select Mode",
    ["👨‍🏫 Teacher (Create & Edit)", "🎒 Student (Learn & Practice)"],
    key="app_mode"
)

current_mode = 'teacher' if 'Teacher' in app_mode else 'student'
StateManager.update_state('current_mode', current_mode)

st.sidebar.markdown("---")

# Initialize user service and current user state
if "user_service" not in st.session_state:
    StateManager.set_state("user_service", UserService())
if "current_user" not in st.session_state:
    StateManager.set_state("current_user", None)

# If student mode, show login + student interface and stop
if current_mode == 'student':
    st.sidebar.markdown("### 👤 Student Login")

    user_service: UserService = StateManager.get_state("user_service")
    current_user = StateManager.get_state("current_user", None)

    # Check if we need to show PIN input for existing user
    if not StateManager.has_state('login_needs_pin'):
        StateManager.set_state('login_needs_pin', False)
    if not StateManager.has_state('login_username'):
        StateManager.set_state('login_username', '')

    needs_pin = StateManager.get_state('login_needs_pin', False)
    saved_username = StateManager.get_state('login_username', '')

    if not current_user:
        if needs_pin:
            # User exists and has PIN - show PIN entry
            st.sidebar.info(f"Welcome back, **{saved_username}**!")
            pin = st.sidebar.text_input("Enter PIN", type="password", max_chars=6, key="student_pin")

            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("Login", use_container_width=True):
                    if pin:
                        user, msg = user_service.authenticate(saved_username, pin)
                        if msg == "success":
                            StateManager.set_state("current_user", user)
                            StateManager.set_state('login_needs_pin', False)
                            st.rerun()
                        else:
                            st.sidebar.error("Incorrect PIN. Try again.")
                    else:
                        st.sidebar.warning("Please enter your PIN.")
            with col2:
                if st.button("Cancel", use_container_width=True):
                    StateManager.set_state('login_needs_pin', False)
                    StateManager.set_state('login_username', '')
                    st.rerun()
        else:
            # Show username input
            username = st.sidebar.text_input("Your name", key="student_username")

            # Check if user exists and show appropriate action
            user_exists = user_service.user_exists(username.strip()) if username.strip() else False

            if user_exists:
                has_pin = user_service.user_has_pin(username.strip())
                if has_pin:
                    if st.sidebar.button("Continue →", use_container_width=True):
                        StateManager.set_state('login_needs_pin', True)
                        StateManager.set_state('login_username', username.strip())
                        st.rerun()
                else:
                    if st.sidebar.button("Login", use_container_width=True):
                        user, msg = user_service.authenticate(username.strip())
                        if msg == "success":
                            StateManager.set_state("current_user", user)
                            st.rerun()
            else:
                # New user - show create account options
                if username.strip():
                    st.sidebar.caption("New student? Create your profile:")
                    pin_input = st.sidebar.text_input("Optional PIN (4-6 digits)", type="password", max_chars=6, key="new_user_pin",
                                                      help="Set a PIN to protect your progress")

                    if st.sidebar.button("Create Profile", use_container_width=True):
                        # Validate PIN if provided
                        if pin_input and (len(pin_input) < 4 or not pin_input.isdigit()):
                            st.sidebar.error("PIN must be 4-6 digits")
                        else:
                            user, msg = user_service.create_user(username.strip(), pin_input if pin_input else None)
                            if msg == "created":
                                StateManager.set_state("current_user", user)
                                st.sidebar.success("Profile created!")
                                st.rerun()
                            else:
                                st.sidebar.error(f"Could not create profile: {msg}")

        # Show existing profiles for quick switching
        users = user_service.list_users()
        if users:
            with st.sidebar.expander("📋 Switch Profile", expanded=False):
                for u in users[:5]:  # Limit to 5 profiles
                    label = f"{'🔒' if u['has_pin'] else '👤'} {u['username']}"
                    if st.button(label, key=f"switch_{u['username']}", use_container_width=True):
                        if u['has_pin']:
                            StateManager.set_state('login_needs_pin', True)
                            StateManager.set_state('login_username', u['username'])
                        else:
                            user, _ = user_service.authenticate(u['username'])
                            StateManager.set_state("current_user", user)
                        st.rerun()

    if not current_user:
        st.info("👈 Enter your name in the sidebar to start learning in Student Mode.")
        st.stop()

    # Logged in - show user info and logout
    st.sidebar.success(f"✓ Logged in as **{current_user['username']}**")
    if current_user.get('has_pin'):
        st.sidebar.caption("🔒 PIN protected")
    if st.sidebar.button("Logout", use_container_width=True):
        StateManager.set_state("current_user", None)
        StateManager.set_state('login_needs_pin', False)
        StateManager.set_state('login_username', '')
        st.rerun()

    from src.student_mode.student_ui import render_student_mode
    render_student_mode(config, client)
    st.stop()

# Otherwise continue with teacher mode below...
# Modern Sidebar Configuration
st.sidebar.markdown("## ⚙️ Curriculum Settings")
st.sidebar.markdown("---")

# Basic Settings Section
with st.sidebar.expander("📚 **Basic Settings**", expanded=True):
    # Subject selection (with multiselect)
    selected_subjects = st.multiselect("Subject", config["defaults"]["subjects"], default=[config["defaults"]["subject"]], key="sidebar_subjects")
    if selected_subjects:
        # Validate each subject
        valid_subjects = [s for s in selected_subjects if InputValidator.validate_subject(s)]
        if valid_subjects != selected_subjects:
            st.warning("Some subjects were invalid and removed.")
        subject_str = ", ".join(valid_subjects) if valid_subjects else config["defaults"]["subject"]
    else:
        subject_str = config["defaults"]["subject"]

    # Grade level selection (now using selectbox)
    grade = st.selectbox("Grade Level", config["defaults"]["grades"], index=config["defaults"]["grades"].index(config["defaults"]["grade"]) if config["defaults"]["grade"] in config["defaults"]["grades"] else 0, key="sidebar_grade")

    # Validate grade selection
    if not InputValidator.validate_grade(grade):
        st.error("Invalid grade selection. Using default.")
        grade = config["defaults"]["grade"]

    # Teaching style selection
    lesson_style = st.selectbox("Style", config["defaults"]["styles"], index=config["defaults"]["styles"].index(config["defaults"]["style"]) if config["defaults"]["style"] in config["defaults"]["styles"] else 0, key="sidebar_style")

    # Language selection
    language = st.selectbox("Language", config["defaults"]["languages"], index=config["defaults"]["languages"].index(config["defaults"]["language"]) if config["defaults"]["language"] in config["defaults"]["languages"] else 0, key="sidebar_language")

# AI Provider Selection Section
with st.sidebar.expander("🔌 **AI Provider**", expanded=False):
    # Get provider service from session state
    provider_service = StateManager.get_state("provider_service")
    
    # Get available providers
    available_providers = provider_service.get_available_providers()
    
    # Provider display names
    provider_names = {
        "openai": "OpenAI (Paid)",
        "kimi": "Kimi K2 (Free)",
        "ollama": "Ollama (Local)"
    }
    
    # Get current provider
    current_provider = StateManager.get_state("current_provider", "openai")
    
    # Provider selection dropdown
    selected_provider = st.selectbox(
        "Select AI Provider",
        options=available_providers,
        format_func=lambda x: provider_names.get(x, x),
        index=available_providers.index(current_provider) if current_provider in available_providers else 0,
        help="Choose your AI provider. Kimi K2 is free! OpenAI costs money. Ollama runs locally.",
        key="provider_selector"
    )
    
    # Handle provider change
    if selected_provider != current_provider:
        StateManager.set_state("current_provider", selected_provider)
        # Update the client
        StateManager.set_state("client", provider_service.get_client(selected_provider))
        st.rerun()
    
    # Show provider-specific info
    provider_info = provider_service.get_provider_info(selected_provider)
    if selected_provider == "kimi":
        st.success("✓ Using Kimi K2 (Free tier)")
        st.caption("Free AI with competitive performance")
    elif selected_provider == "ollama":
        st.info("✓ Using local Ollama")
        st.caption("Runs completely offline on your machine")
    elif selected_provider == "openai":
        st.info("✓ Using OpenAI")
        st.caption("Premium AI - charges per API call")

    # Cross-provider orchestration (advanced)
    st.markdown("---")
    st.markdown("**🔀 Cross-Provider Mode**")
    st.caption("Use different providers for different tasks")

    cross_provider_enabled = st.checkbox(
        "Enable cross-provider",
        value=StateManager.get_state("cross_provider_enabled", False),
        key="cross_provider_toggle",
        help="Use Kimi for text and OpenAI for images, etc."
    )
    StateManager.set_state("cross_provider_enabled", cross_provider_enabled)

    if cross_provider_enabled:
        col1, col2 = st.columns(2)
        with col1:
            orchestrator_provider = st.selectbox(
                "Orchestrator",
                options=available_providers,
                format_func=lambda x: provider_names.get(x, x),
                index=available_providers.index(StateManager.get_state("orchestrator_provider", selected_provider)) if StateManager.get_state("orchestrator_provider", selected_provider) in available_providers else 0,
                key="orch_provider"
            )
            StateManager.set_state("orchestrator_provider", orchestrator_provider)
            provider_service.set_task_provider("main", orchestrator_provider)

        with col2:
            worker_provider = st.selectbox(
                "Workers",
                options=available_providers,
                format_func=lambda x: provider_names.get(x, x),
                index=available_providers.index(StateManager.get_state("worker_provider", selected_provider)) if StateManager.get_state("worker_provider", selected_provider) in available_providers else 0,
                key="worker_provider"
            )
            StateManager.set_state("worker_provider", worker_provider)
            provider_service.set_task_provider("worker", worker_provider)

        # Image provider (only OpenAI supports images)
        image_providers = [p for p in available_providers if p == "openai"]
        if image_providers:
            image_provider = st.selectbox(
                "Image Generation",
                options=image_providers,
                format_func=lambda x: provider_names.get(x, x),
                key="image_provider"
            )
            provider_service.set_task_provider("image", image_provider)
        else:
            st.caption("⚠️ Image generation requires OpenAI")

        # Show summary
        st.caption(f"📊 Orchestrator: {orchestrator_provider} | Workers: {worker_provider}")

# Advanced Settings Section  
with st.sidebar.expander("🤖 **AI Model Settings**", expanded=False):
    # Get available models from detection or fallback to config
    if st.session_state.available_models:
        available_text_models = st.session_state.available_models.get('text_models', [])
        available_image_models = st.session_state.available_models.get('image_models', [])
    else:
        # Fallback to config
        fallback_models = get_fallback_models(config)
        available_text_models = fallback_models['text_models']
        available_image_models = fallback_models['image_models']
    
    # Show detection status if there was an error
    if st.session_state.model_detection_error:
        st.warning(f"⚠️ Using fallback models (API detection failed)")
        with st.expander("Detection Error Details"):
            st.code(st.session_state.model_detection_error)
    
    # Main model selection (for orchestration)
    # Get default or first available
    default_text_model = config["defaults"].get("text_model", "gpt-4o")
    if default_text_model not in available_text_models and available_text_models:
        default_text_model = available_text_models[0]
    
    text_model_index = available_text_models.index(default_text_model) if default_text_model in available_text_models else 0
    
    text_model = st.selectbox(
        "Main AI Model (Orchestrator)", 
        options=available_text_models,
        index=text_model_index, 
        help="Select the primary model for planning and coordination. GPT-4 variants recommended for best quality."
    )
    
    # Worker model selection (for content generation)
    default_worker_model = config["defaults"].get("worker_model", "gpt-4o-mini")
    if default_worker_model not in available_text_models and available_text_models:
        # Try to find a mini model
        mini_models = [m for m in available_text_models if 'mini' in m.lower()]
        default_worker_model = mini_models[0] if mini_models else available_text_models[0]
    
    worker_model_index = available_text_models.index(default_worker_model) if default_worker_model in available_text_models else 0
    
    worker_model = st.selectbox(
        "Worker AI Model (Content)", 
        options=available_text_models,
        index=worker_model_index, 
        help="Model for content generation. Use mini models for cost efficiency."
    )
    
    # Show cost estimation (using defaults for now, will update after user selections)
    cost_estimate = estimate_curriculum_cost(
        text_model, worker_model, 
        num_units=4,  # Typical curriculum size
        include_quizzes=config["defaults"]["include_quizzes"],
        include_summary=config["defaults"]["include_summary"],
        include_resources=config["defaults"]["include_resources"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        orch_info = get_model_info(text_model)
        st.caption(f"Orchestrator: {orch_info['relative_cost']}")
    with col2:
        worker_info = get_model_info(worker_model)
        st.caption(f"Worker: {worker_info['relative_cost']}")
    
    st.info(f"💰 Estimated cost: ${cost_estimate['total']:.2f} per curriculum")
    
    if cost_estimate['savings_vs_full']['percent'] > 0:
        st.success(f"💸 Saving {cost_estimate['savings_vs_full']['percent']:.0f}% vs full model!")
    
    # Get available image models from config
    # Image models were already fetched in the available_image_models variable above
    # No need to get from config again - they're already set
    
    # Get default or first available image model
    default_image_model = config["defaults"].get("image_model", "dall-e-3")
    if default_image_model not in available_image_models and available_image_models:
        default_image_model = available_image_models[0]

    image_model_index = available_image_models.index(default_image_model) if default_image_model in available_image_models else 0

    # Debug - log available models to stderr
    sys.stderr.write(f"Available image models: {available_image_models}\n")

    # Image model selection with explicit options
    image_model = st.selectbox(
        "Image Model",
        options=available_image_models,
        index=image_model_index,
        help="Select the model for generating images. DALL-E 3 recommended for best quality."
    )
    
    # Add image size selection based on the chosen model
    col1, col2 = st.columns(2)
    with col1:
        # Dynamically get valid sizes for selected model
        image_sizes = image_generator.get_available_sizes(image_model)
        default_size = image_generator.default_sizes.get(image_model, "1024x1024")
        
        # Size selection dropdown
        image_size = st.selectbox(
            "Image Size", 
            options=image_sizes,
            index=image_sizes.index(default_size) if default_size in image_sizes else 0,
            help="Select the size for generated images. Larger sizes may produce more detailed images."
        )
    
    # Store the selected size in session state for later use
    StateManager.set_state("image_size", image_size)
    
# Content Settings Section
with st.sidebar.expander("📝 **Content Settings**", expanded=False):
    # Media richness slider 
    media_richness = st.slider("Media Richness", min_value=0, max_value=5, value=config["defaults"]["media_richness"], 
                               help="0: Text only, 1: +Maybe image, 2: +Image, 3: +Maybe chart, 4: +Chart, 5: +More images")
    
    st.markdown("**Include Additional Components:**")
    include_quizzes = st.checkbox("Include Quizzes", value=config["defaults"]["include_quizzes"])
    include_summary = st.checkbox("Include Summary", value=config["defaults"]["include_summary"])
    include_resources = st.checkbox("Include Further Resources", value=config["defaults"]["include_resources"])
    include_keypoints = st.checkbox("Include Learning Points", value=config["defaults"]["include_keypoints"])
    
    # Show number of days (informational)
    num_days = st.number_input("Days (Info Only, For Labeling)", min_value=1, max_value=14, value=config["defaults"].get("days", 3), help="Number of days for the curriculum (informational)")

# Information and Help Sections
st.sidebar.markdown("---")

with st.sidebar.expander("💡 **Tips & Help**", expanded=False):
    st.markdown(config["info_texts"].get("tips", "Configure settings, generate, and export your curriculum."))
    
    st.markdown("**Quick Tips:**")
    st.markdown("""
    • Start with basic settings above
    • Use templates for faster setup  
    • Higher media richness = more images/charts
    • Enable components you want included
    """)

with st.sidebar.expander("🤖 **About AI Framework**", expanded=False):
    st.markdown(config["info_texts"].get("agentic_info", "Using an agentic framework for curriculum generation"))

# Theme and preferences
st.sidebar.markdown("---")
st.sidebar.markdown("**Preferences**")
theme = ThemeManager.get_theme_toggle()

# Mobile layout toggle - useful for phones or tablets
mobile_mode = st.sidebar.checkbox(
    "📱 Mobile Layout",
    value=StateManager.get_state("is_mobile", False),
    help="Enable compact layout for smaller screens"
)
StateManager.set_state("is_mobile", mobile_mode)
is_mobile = mobile_mode

# --- Main Area Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates", "🔄 Batch", "📊 Analytics", "👨‍👩‍👧‍👦 Family"])

with tab1:
    # Modern section header
    ModernUI.section_header("Generate New Curriculum", "✨", "generate")
    
    # Dashboard quick stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_curricula = len([f for f in os.listdir("curricula") if f.endswith('.json')]) if os.path.exists("curricula") else 0
        ModernUI.stats_card(str(total_curricula), "Total Curricula", "📚")
    
    with col2:
        # Get current settings summary
        settings_summary = f"{subject_str} • {grade}"
        ModernUI.stats_card(settings_summary, "Current Settings", "⚙️")
    
    with col3:
        # Show selected template or "Custom"
        template_status = "Template" if st.session_state.get('selected_template_id') else "Custom"
        ModernUI.stats_card(template_status, "Generation Mode", "🎯")
    
    st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
    
    # Quick action cards
    if st.session_state.curriculum is None:
        # Show quick start options when no curriculum exists
        with st.container(border=True):
            st.markdown("### 🎓 🚀 Quick Start")
            st.markdown("""
**Ready to create your curriculum?**

1. ⚙️ Configure your settings in the sidebar
2. 📋 Optionally choose a template below
3. ✨ Click Generate to create your curriculum
""")
            st.markdown(f"Your settings: **{subject_str} • {grade} • {lesson_style}**")
    else:
        # Show quick actions when curriculum exists
        col1, col2 = st.columns(2)
        
        with col1:
            if ModernUI.quick_action_button(
                "🔄 Generate New", 
                "Create a fresh curriculum with current settings",
                "🆕",
                "quick_generate_new"
            ):
                StateManager.update_state('curriculum', None)
        
        with col2:
            if ModernUI.quick_action_button(
                "📝 Edit Current", 
                "Continue editing your existing curriculum",
                "✏️",
                "quick_edit_current"
            ):
                # Switch to edit tab
                StateManager.set_state("active_tab", 1)
                st.info("Switch to the 'View & Edit' tab to continue editing!")
    
    # Template selection section
    if st.session_state.template_manager:
        with st.expander("📋 Use Template (Optional)", expanded=False):
            st.markdown("Choose from pre-built curriculum templates to get started faster.")
            
            # Get available templates
            templates = st.session_state.template_manager.list_templates(
                subject_filter=subject_str.split(',')[0].strip() if ',' in subject_str else subject_str,
                grade_filter=grade
            )
            
            if templates:
                template_options = ["None (Custom Generation)"] + [f"{t.name} - {t.description[:50]}..." for t in templates]
                selected_template_idx = st.selectbox(
                    "Choose Template",
                    range(len(template_options)),
                    format_func=lambda x: template_options[x],
                    key="template_selection"
                )
                
                if selected_template_idx > 0:
                    selected_template = templates[selected_template_idx - 1]
                    st.info(f"**{selected_template.name}**\n\n{selected_template.description}")
                    
                    # Show template details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Subjects:** {', '.join(selected_template.subjects)}")
                        st.write(f"**Grades:** {', '.join(selected_template.grades)}")
                    with col2:
                        st.write(f"**Style:** {selected_template.style}")
                        st.write(f"**Used:** {selected_template.usage_count} times")
                    
                    # Store selected template in session state
                    StateManager.set_state("selected_template_id", selected_template.id)
                else:
                    StateManager.set_state("selected_template_id", None)
            else:
                st.info("No templates found for the selected subject and grade. You can create custom templates in the Templates tab.")
                StateManager.set_state("selected_template_id", None)
    
    st.markdown("Configure your curriculum using the sidebar settings, then click generate.")

    # Allow overriding guidelines/focus per generation run
    custom_prompt_input = st.text_area("Optional: Specific Guidelines or Focus for this Generation",
                                       value=config["defaults"]["extra"], key="extra_guidelines",
                                       help="Add specific instructions for the AI for this run.")
    
    # Sanitize the custom prompt
    custom_prompt = InputValidator.sanitize_prompt(custom_prompt_input)

    min_topics = config["defaults"]["min_topics"]
    max_topics = config["defaults"]["max_topics"]
    
    # Cost estimation feature
    with st.expander("💰 Cost Estimation", expanded=False):
        st.markdown("### Estimated Token Usage and Cost")
        st.info("This is an approximate estimate based on your current settings.")
        
        # Prepare estimation parameters
        estimation_params = {
            "media_richness": media_richness,
            "include_quizzes": include_quizzes,
            "include_summary": include_summary,
            "include_resources": include_resources,
            "image_model": image_model,
            "text_model": text_model
        }
        
        # Get cost estimation from service
        if st.session_state.curriculum_service:
            cost_estimate = st.session_state.curriculum_service.estimate_costs(estimation_params)
        else:
            # Fallback to direct cost estimation if service is not available
            min_topics = config["defaults"]["min_topics"]
            max_topics = config["defaults"]["max_topics"]
            topic_count = (min_topics + max_topics) // 2
            
            # Image counts based on media richness
            image_count = 0
            if media_richness >= 2:
                image_count = 1
            if media_richness >= 5:
                image_count = 3
            
            # Get basic cost estimate
            basic_estimate = estimate_curriculum_cost(
                text_model, worker_model, 
                num_units=topic_count,
                include_quizzes=include_quizzes,
                include_summary=include_summary,
                include_resources=include_resources
            )
            
            # Build full cost estimate structure
            cost_estimate = {
                "total_tokens": basic_estimate.get("total_tokens", 0),
                "topic_count": topic_count,
                "image_count": image_count * topic_count,
                "total_cost": basic_estimate.get("total", 0),
                "text_cost": basic_estimate.get("total", 0),  # Simplified - all text cost
                "image_cost": 0,  # Not calculated in basic estimate
                "tokens_breakdown": {
                    "outline": 1000,
                    "content": 4000,
                    "image_prompt": 300,
                    "chart": 1000 if media_richness >= 3 else 0,
                    "quiz": 2000 if include_quizzes else 0,
                    "summary": 1000 if include_summary else 0,
                    "resources": 1000 if include_resources else 0,
                },
                "cost_breakdown": {
                    "main_model": basic_estimate.get("breakdown", {}).get("orchestrator", 0),
                    "worker_model": sum(v for k, v in basic_estimate.get("breakdown", {}).items() if k != "orchestrator"),
                    "images": 0  # Not calculated in basic estimate
                }
            }
        
        # Display metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Est. Total Tokens", f"{cost_estimate['total_tokens']:,.0f}")
            st.metric("Topics", f"{cost_estimate['topic_count']}")
            st.metric("Images", f"{cost_estimate['image_count']}")
        
        with col2:
            st.metric("Est. Total Cost", f"${cost_estimate['total_cost']:.2f}")
            st.metric("Text Cost", f"${cost_estimate['text_cost']:.2f}")
            st.metric("Image Cost", f"${cost_estimate['image_cost']:.2f}")
        
        # Display more details about the calculation
        st.markdown("#### Token Usage Breakdown")
        tokens_breakdown = cost_estimate['tokens_breakdown']
        topic_count = cost_estimate['topic_count']
        
        for component, tokens_per in tokens_breakdown.items():
            if tokens_per > 0:
                st.markdown(f"- **{component.title()}**: {tokens_per * topic_count:,} tokens")
        
        st.markdown("#### Cost Breakdown")
        cost_breakdown = cost_estimate['cost_breakdown']
        st.markdown(f"- **{text_model}** (main model): ${cost_breakdown['main_model']:.2f}")
        st.markdown(f"- **{config['defaults']['worker_model']}** (worker model): ${cost_breakdown['worker_model']:.2f}")
        st.markdown(f"- **{image_model}** (image model): ${cost_breakdown['images']:.2f}")
        
        st.caption("Note: These are rough estimates. Actual usage and costs may vary.")
        
        # Add refresh button for recalculating with current settings
        if st.button("Refresh Estimate", key="refresh_cost_estimate"):
            # Don't use st.rerun() as it stops ongoing generation
            # Instead, just recalculate values here
            pass  # The estimates will be refreshed automatically when this section renders

    # If generation is already in progress, show cancel button
    if st.session_state.generating:
        # Show status and cancel button
        progress_bar = st.progress(st.session_state.progress, text=f"Generating curriculum... {int(st.session_state.progress*100)}% complete")
        
        if st.button("❌ Cancel Generation", use_container_width=True, type="secondary"):
            StateManager.update_state("generating", False)
            progress_bar.empty()
            st.warning("Generation cancelled.")
            
    # Only show generate button if not already generating
    elif st.button("🚀 Generate New Curriculum", use_container_width=True, type="primary"):
        # --- Start Generation Process ---
        # Set generating flag to true
        StateManager.update_state("generating", True)
        
        # Check if using a template
        using_template = hasattr(st.session_state, 'selected_template_id') and st.session_state.selected_template_id
        template_params = {}
        
        if using_template and st.session_state.template_manager:
            try:
                # Apply template to get generation parameters
                template_params = st.session_state.template_manager.apply_template(
                    st.session_state.selected_template_id,
                    subject_str,
                    grade,
                    custom_params={
                        "style": lesson_style,
                        "language": language,
                        "media_richness": media_richness,
                        "custom_prompt": custom_prompt,
                        "include_quizzes": include_quizzes,
                        "include_summary": include_summary,
                        "include_resources": include_resources,
                        "include_keypoints": include_keypoints
                    }
                )
                st.info(f"Using template: {template_params.get('template_name', 'Unknown')}")
            except Exception as e:
                st.error(f"Error applying template: {e}")
                using_template = False
        
        # Store current settings in generation params
        if using_template:
            # Use template parameters as base, override with UI selections
            generation_params = template_params.copy()
            generation_params.update({
                "text_model": text_model,
                "worker_model": worker_model,
                "image_model": image_model,
                "image_size": st.session_state.get("image_size", "1024x1024"),
            })
        else:
            # Use standard parameters
            generation_params = {
                "subject_str": subject_str,
                "grade": grade,
                "lesson_style": lesson_style,
                "media_richness": media_richness,
                "text_model": text_model,
                "worker_model": worker_model,
                "image_model": image_model,
                "image_size": st.session_state.get("image_size", "1024x1024"),
                "language": language,
                "custom_prompt": custom_prompt,
                "include_quizzes": include_quizzes,
                "include_summary": include_summary,
                "include_resources": include_resources,
                "include_keypoints": include_keypoints
            }

        StateManager.update_state("generation_params", generation_params)
        
        # We'll clear temp files only if generation is successful
        # Store the current tmp files to clean up later
        current_tmp_files = set(StateManager.get_state('last_tmp_files', set()))

        # Reset progress and show modern progress interface
        StateManager.update_state("progress", 0.0)
        
        # Modern progress steps
        progress_container = st.empty()
        generation_steps = [
            {"title": "Initialize", "icon": "🚀"},
            {"title": "Plan Structure", "icon": "📋"}, 
            {"title": "Generate Content", "icon": "✍️"},
            {"title": "Create Media", "icon": "🎨"},
            {"title": "Finalize", "icon": "✅"}
        ]
        
        with progress_container.container():
            ModernUI.progress_steps(generation_steps, current_step=0)
            progress_bar = st.progress(0.0, text="Initializing curriculum generation...")

        # Enhanced validation using the validator service
        validation_params = {
            "subject_str": subject_str,
            "grade": grade,
            "image_model": image_model,
            "text_model": text_model,
            "lesson_style": lesson_style,
            "media_richness": media_richness,
            "custom_prompt": custom_prompt
        }
        
        # Check if curriculum service is available
        if st.session_state.curriculum_service:
            is_valid, error_msg = st.session_state.curriculum_service.validate_generation_params(validation_params)
            if not is_valid:
                st.error(f"Validation error: {error_msg}")
                progress_bar.empty()
                StateManager.update_state("generating", False)
                st.stop()
        else:
            # Fallback validation
            if not subject_str:
                st.error("Validation error: Please select at least one subject")
                progress_bar.empty()
                StateManager.update_state("generating", False)
                st.stop()
            if len(subject_str) > 50:
                st.error("Validation error: Subject string is too long. Please reduce the number of subjects.")
                progress_bar.empty()
                StateManager.update_state("generating", False)
                st.stop()

        # Initialize curriculum structure in session state
        curriculum_id = uuid.uuid4().hex
        StateManager.update_state("curriculum_id", curriculum_id)
        StateManager.update_state("curriculum", {
            "meta": {
                "id": curriculum_id,
                "subject": subject_str,
                "grade": grade,
                "style": lesson_style,
                "media_richness": media_richness,
                "text_model": text_model,
                "image_model": image_model,
                "language": language,
                "generated": str(datetime.now().isoformat()),
                "extra": custom_prompt,
                "include_quizzes": include_quizzes,
                "include_summary": include_summary,
                "include_resources": include_resources,
                "include_keypoints": include_keypoints
            },
            "units": []
        })
        
        # Clear previous dynamic states
        StateManager.clear_generation_state()

        try:
            # Use the curriculum service to generate the curriculum
            # Create status logger for detailed real-time feedback
            status_container = st.container()

            with status_container:
                with StatusLogger(title="🚀 Generating Curriculum", expanded=True) as status_log:
                    # Step 1: Initialization
                    status_log.info(f"Subject: {subject_str}")
                    status_log.info(f"Grade Level: {grade}")
                    status_log.info(f"Style: {lesson_style}")
                    status_log.progress("Initializing generation pipeline...")

                    StateManager.update_state('progress', 0.2)
                    with progress_container.container():
                        ModernUI.progress_steps(generation_steps, current_step=1)
                        progress_bar.progress(st.session_state.progress, text="Planning curriculum structure...")

                    # Use stored parameters from when generation started
                    params = st.session_state.generation_params

                    # Check if generation has been cancelled
                    if not st.session_state.generating:
                        progress_container.empty()
                        st.warning("Generation cancelled.")
                        StateManager.update_state('generating', False)
                    else:
                        # Step 2: Content Generation
                        status_log.update_label("📋 Planning Structure")
                        status_log.agent_start("Orchestrator Agent")
                        status_log.progress("Creating curriculum outline...")

                        StateManager.update_state('progress', 0.3)
                        with progress_container.container():
                            ModernUI.progress_steps(generation_steps, current_step=2)
                            progress_bar.progress(st.session_state.progress, text="Generating outline and content...")

                        # Generate curriculum based on service availability
                        if st.session_state.curriculum_service:
                            status_log.agent_start("Content Generation Service")
                            status_log.progress("Generating unit content...")

                            # Wrap API call with error handler
                            curriculum = ErrorHandler.safe_api_call(
                                st.session_state.curriculum_service.generate_curriculum,
                                params
                            )
                            status_log.agent_complete("Content Service")
                        else:
                            # Fallback to direct orchestrator call
                            status_log.warning("Curriculum service not available, using direct generation...")
                            curriculum = orchestrator.create_curriculum(
                                subject_str,
                                grade,
                                lesson_style,
                                language,
                                custom_prompt,
                                config
                            )

                        # Check if generation has been cancelled
                        if not st.session_state.generating:
                            progress_bar.empty()
                            st.warning("Generation cancelled.")
                            StateManager.update_state("generating", False)

                    # Step 4: Finalization
                    status_log.update_label("✨ Finalizing Curriculum")
                    status_log.progress("Assembling final curriculum...")

                    StateManager.update_state('progress', 0.9)
                    with progress_container.container():
                        ModernUI.progress_steps(generation_steps, current_step=4)
                        progress_bar.progress(st.session_state.progress, text="Finalizing curriculum...")

                    # Check if curriculum was generated successfully
                    if curriculum is None:
                        status_log.error("Failed to generate curriculum")
                        raise ValueError("Curriculum generation returned None")
                    elif curriculum.get("meta", {}).get("cancelled", False):
                        # Display a message that generation was cancelled
                        status_log.warning("Generation was cancelled")
                        StateManager.update_state('curriculum', curriculum)
                    else:
                        # Success! Log details
                        units = curriculum.get("units", [])
                        status_log.success(f"Generated {len(units)} units successfully!")
                        status_log.info(f"Curriculum ID: {curriculum.get('meta', {}).get('id', 'N/A')[:8]}...")

                        # Store in session state
                        StateManager.update_state('curriculum', curriculum)

                        # Generation complete - now clean up old temp files
                        cleanup_tmp_files(current_tmp_files)
                        StateManager.set_state('last_tmp_files', set())

            # Update progress to complete - Step 5: Complete
            with progress_container.container():
                ModernUI.progress_steps(generation_steps, current_step=5)
            StateManager.update_state("progress", 1.0)
            progress_bar.progress(1.0, text="Curriculum generation complete!")

            if curriculum and not curriculum.get("meta", {}).get("cancelled", False):
                st.success("Curriculum generated successfully! View results in the 'View & Edit' tab.")
            elif curriculum and curriculum.get("meta", {}).get("cancelled", False):
                st.warning("Generation was cancelled. Partial results may be available in the 'View & Edit' tab.")
            time.sleep(1.5)

            # Always clean up the progress interface
            progress_container.empty()

            # Reset generating flag
            StateManager.update_state("generating", False)
        
        except ValueError as e:
            # Handle validation errors specifically
            st.error(f"Validation error: {e}")
            sys.stderr.write(f"Validation error during curriculum generation: {e}\n")
            progress_container.empty()
            StateManager.update_state("generating", False)
        except Exception as e:
            # Handle all other errors
            st.error(f"Unexpected error during curriculum generation: {e}")
            sys.stderr.write(f"Curriculum generation error: {e}\n")
            sys.stderr.write(traceback.format_exc() + "\n")
            progress_container.empty()
            StateManager.update_state("generating", False)
            
            # Log error details if logger is available
            if logger:
                logger.log_error(error=e, context="Curriculum generation")

with tab2:
    st.markdown("### View & Edit Curriculum")
    if st.session_state.curriculum:
        # Get curriculum data from session state
        curriculum = st.session_state.curriculum
        metadata = curriculum.get("meta", {})

        # Display metadata
        st.markdown(f"#### {metadata.get('subject', 'Subject')} Curriculum - Grade {metadata.get('grade', 'Grade')}")
        st.caption(f"Style: {metadata.get('style', 'Standard')} | Language: {metadata.get('language', 'English')} | Generated: {metadata.get('generated', 'N/A')}")

        # Get curriculum ID for customization
        curriculum_id = metadata.get('id', f"{metadata.get('subject', '')}_{metadata.get('grade', '')}")
        customization_service = get_customization_service()
        customization = customization_service.get_customization(curriculum_id)

        # Parent Controls Expander
        with st.expander("🎛️ Parent Controls", expanded=False):
            st.markdown("##### Content Depth")
            st.caption("Adjust how detailed the content presentation is")

            depth_options = CustomizationService.CONTENT_DEPTHS
            depth_descriptions = CustomizationService.DEPTH_DESCRIPTIONS
            current_depth_idx = depth_options.index(customization.content_depth) if customization.content_depth in depth_options else 1

            selected_depth = st.selectbox(
                "Depth Level",
                options=depth_options,
                index=current_depth_idx,
                format_func=lambda x: f"{x.title()} - {depth_descriptions.get(x, '')}",
                key="curriculum_depth_selector"
            )

            if selected_depth != customization.content_depth:
                customization_service.set_content_depth(curriculum_id, selected_depth)
                st.success(f"Content depth set to: {selected_depth}")

            st.markdown("---")
            st.markdown("##### Supplemental Resources")
            st.caption("Add extra learning materials for this curriculum")

            # Display existing resources
            if customization.supplemental_resources:
                for res_idx, resource in enumerate(customization.supplemental_resources):
                    res_col1, res_col2 = st.columns([4, 1])
                    with res_col1:
                        st.markdown(f"📚 [{resource.get('title', 'Resource')}]({resource.get('url', '#')})")
                        if resource.get('description'):
                            st.caption(resource.get('description'))
                    with res_col2:
                        if st.button("🗑️", key=f"remove_res_{res_idx}"):
                            customization_service.remove_supplemental_resource(curriculum_id, res_idx)
                            st.rerun()

            # Add new resource form
            with st.form(key="add_resource_form"):
                res_title = st.text_input("Resource Title", key="new_res_title")
                res_url = st.text_input("URL", key="new_res_url")
                res_desc = st.text_input("Description (optional)", key="new_res_desc")
                if st.form_submit_button("➕ Add Resource"):
                    if res_title and res_url:
                        customization_service.add_supplemental_resource(curriculum_id, res_title, res_url, res_desc)
                        st.success(f"Added: {res_title}")
                        st.rerun()
                    else:
                        st.warning("Please provide a title and URL")

        # Edit Mode Toggle
        edit_mode = st.checkbox("Enable Edit Mode", value=st.session_state.edit_mode, key="edit_mode_toggle")
        StateManager.set_state("edit_mode", edit_mode)
        if edit_mode:
            st.info("Edit Mode Enabled: Changes are saved automatically as you type or select options.")

        # Iterate through units
        for i, unit in enumerate(curriculum.get("units", [])):
            unit_key_base = f"unit_{i}" # Base key for widgets in this unit

            # Add an indicator for units without expected media
            unit_title = unit.get('title', f'Untitled')
            
            # Don't display any media warnings in the title
            # Check if unit is skipped
            is_skipped = customization_service.is_unit_skipped(curriculum_id, i)
            is_flagged = customization_service.is_unit_flagged(curriculum_id, i)
            unit_note = customization_service.get_unit_note(curriculum_id, i)

            # Build expander title with indicators
            expander_title = f"Unit {i+1}: {unit_title}"
            if is_skipped:
                expander_title = f"⏭️ {expander_title} (Skipped)"
            if is_flagged:
                expander_title = f"🚩 {expander_title}" if not is_skipped else expander_title.replace("⏭️", "🚩⏭️")

            with st.expander(expander_title, expanded=(i==0 and not is_skipped)): # Expand first non-skipped unit
                st.markdown(f"#### Unit {i+1}: {unit_title}")

                # Unit customization controls in a horizontal layout
                ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
                with ctrl_col1:
                    skip_btn_label = "✅ Unskip" if is_skipped else "⏭️ Skip Unit"
                    if st.button(skip_btn_label, key=f"skip_unit_{i}", use_container_width=True):
                        if is_skipped:
                            customization_service.unskip_unit(curriculum_id, i)
                        else:
                            customization_service.skip_unit(curriculum_id, i)
                        st.rerun()

                with ctrl_col2:
                    flag_btn_label = "✅ Unflag" if is_flagged else "🚩 Flag for Review"
                    if st.button(flag_btn_label, key=f"flag_unit_{i}", use_container_width=True):
                        if is_flagged:
                            customization_service.unflag_unit(curriculum_id, i)
                        else:
                            customization_service.flag_unit(curriculum_id, i)
                        st.rerun()

                with ctrl_col3:
                    if st.button("📝 Add Note" if not unit_note else "📝 Edit Note", key=f"note_btn_{i}", use_container_width=True):
                        StateManager.set_state(f"show_note_form_{i}", True)

                # Show note form if toggled
                if StateManager.get_state(f"show_note_form_{i}", False):
                    with st.form(key=f"unit_note_form_{i}"):
                        note_text = st.text_area("Parent Note", value=unit_note or "", key=f"note_input_{i}")
                        note_col1, note_col2 = st.columns(2)
                        with note_col1:
                            if st.form_submit_button("💾 Save Note"):
                                if note_text.strip():
                                    customization_service.add_unit_note(curriculum_id, i, note_text.strip())
                                    st.success("Note saved!")
                                else:
                                    customization_service.remove_unit_note(curriculum_id, i)
                                    st.info("Note removed")
                                StateManager.set_state(f"show_note_form_{i}", False)
                                st.rerun()
                        with note_col2:
                            if st.form_submit_button("❌ Cancel"):
                                StateManager.set_state(f"show_note_form_{i}", False)
                                st.rerun()

                # Display existing note if present
                if unit_note and not StateManager.get_state(f"show_note_form_{i}", False):
                    st.info(f"📝 **Parent Note:** {unit_note}")

                # Show skipped message prominently
                if is_skipped:
                    st.warning("⏭️ This unit is marked as skipped and will be hidden from students.")

                # Show flagged message
                if is_flagged:
                    st.info("🚩 This unit is flagged for parent review before showing to students.")

                st.markdown("---")

                # --- Display Regeneration Status Messages ---
                # Check for regeneration in progress (show spinner)
                if StateManager.get_state(f'regenerating_content_{i}', False):
                    st.spinner(f"Regenerating content for Unit {i+1}...")
                if StateManager.get_state(f'regenerating_images_{i}', False):
                    st.spinner(f"Regenerating images for Unit {i+1}...")
                if StateManager.get_state(f'regenerating_chart_{i}', False):
                    st.spinner(f"Regenerating chart for Unit {i+1}...")
                if StateManager.get_state(f'regenerating_quiz_{i}', False):
                    st.spinner(f"Regenerating quiz for Unit {i+1}...")
                if StateManager.get_state(f'regenerating_summary_{i}', False):
                    st.spinner(f"Regenerating summary for Unit {i+1}...")
                
                # Check for success messages
                if StateManager.get_state(f'content_regenerated_{i}', False):
                    st.success(f"✅ Content regenerated successfully for Unit {i+1}!")
                    StateManager.set_state(f'content_regenerated_{i}', False)
                
                if StateManager.get_state(f'images_regenerated_{i}', False):
                    st.success(f"✅ Images regenerated successfully for Unit {i+1}!")
                    StateManager.set_state(f'images_regenerated_{i}', False)
                
                if StateManager.get_state(f'chart_regenerated_{i}', False):
                    st.success(f"✅ Chart regenerated successfully for Unit {i+1}!")
                    StateManager.set_state(f'chart_regenerated_{i}', False)
                
                if StateManager.get_state(f'quiz_regenerated_{i}', False):
                    st.success(f"✅ Quiz regenerated successfully for Unit {i+1}!")
                    StateManager.set_state(f'quiz_regenerated_{i}', False)
                
                if StateManager.get_state(f'summary_regenerated_{i}', False):
                    st.success(f"✅ Summary regenerated successfully for Unit {i+1}!")
                    StateManager.set_state(f'summary_regenerated_{i}', False)
                
                # Check for error messages
                content_error = StateManager.get_state(f'content_regen_error_{i}', None)
                if content_error:
                    st.error(f"Failed to regenerate content: {content_error}")
                    StateManager.set_state(f'content_regen_error_{i}', None)
                
                images_error = StateManager.get_state(f'images_regen_error_{i}', None)
                if images_error:
                    st.error(f"Failed to regenerate images: {images_error}")
                    StateManager.set_state(f'images_regen_error_{i}', None)
                
                chart_error = StateManager.get_state(f'chart_regen_error_{i}', None)
                if chart_error:
                    st.error(f"Failed to regenerate chart: {chart_error}")
                    StateManager.set_state(f'chart_regen_error_{i}', None)
                
                quiz_error = StateManager.get_state(f'quiz_regen_error_{i}', None)
                if quiz_error:
                    st.error(f"Failed to regenerate quiz: {quiz_error}")
                    StateManager.set_state(f'quiz_regen_error_{i}', None)
                
                summary_error = StateManager.get_state(f'summary_regen_error_{i}', None)
                if summary_error:
                    st.error(f"Failed to regenerate summary: {summary_error}")
                    StateManager.set_state(f'summary_regen_error_{i}', None)
                
                # Check for warnings
                chart_warning = StateManager.get_state(f'chart_regen_warning_{i}', None)
                if chart_warning:
                    st.warning(chart_warning)
                    StateManager.set_state(f'chart_regen_warning_{i}', None)

                # --- Display/Edit Title ---
                if edit_mode:
                    # Use on_change callback for immediate update without rerun
                    def update_title():
                        new_value = st.session_state[f"{unit_key_base}_title"]
                        StateManager.update_curriculum_unit(i, "title", new_value)
                    
                    st.text_input("Unit Title", 
                                 value=unit.get("title", ""), 
                                 key=f"{unit_key_base}_title",
                                 on_change=update_title)

                # --- Image Selection ---
                st.markdown("##### Illustration")
                available_images = unit.get("images", [])
                current_selected_b64 = unit.get("selected_image_b64")
                
                # Create columns for image and options
                # Adjust column layout based on device
                if st.session_state.get("is_mobile", False):
                    # On mobile, stack vertically
                    img_col1 = st.container()
                    img_col2 = st.container()
                else:
                    # On desktop, use columns
                    img_col1, img_col2 = st.columns([2, 1])
                
                with img_col1:
                    if available_images and current_selected_b64:
                        # Display the currently selected image
                        st.image(
                            f"data:image/png;base64,{current_selected_b64}", 
                            caption=f"Illustration: {unit.get('title', 'Untitled')}", 
                            use_container_width=True
                        )
                    else:
                        if media_richness >= 2:
                            st.info("No image selected for this unit.")
                
                with img_col2:
                    # Allow selecting a different image if multiple were generated
                    if available_images and len(available_images) > 1:
                        img_options = {} # dict mapping caption to b64
                        current_selection_caption = None
                        
                        for img_idx, img_data in enumerate(available_images):
                            if img_data and isinstance(img_data, dict) and img_data.get("b64"):
                                 caption = f"Image Option {img_idx + 1}"
                                 img_options[caption] = img_data.get("b64")
                                 
                                 # Find current selection's caption
                                 if img_data.get("b64") == current_selected_b64:
                                     current_selection_caption = caption
                        
                        # If we didn't find the current selection, use the first option
                        if not current_selection_caption and img_options:
                            current_selection_caption = list(img_options.keys())[0]
                        
                        if img_options:
                            st.write("Select different image:")
                            
                            # Use on_change callback for immediate update
                            def update_selected_image():
                                selected_caption = st.session_state[f"{unit_key_base}_img_select"]
                                new_selected_b64 = img_options.get(selected_caption)
                                StateManager.update_curriculum_unit(i, "selected_image_b64", new_selected_b64)
                            
                            selected_caption = st.selectbox(
                                "Choose Illustration", 
                                options=list(img_options.keys()),
                                index=list(img_options.keys()).index(current_selection_caption) if current_selection_caption in img_options else 0,
                                key=f"{unit_key_base}_img_select",
                                on_change=update_selected_image,
                                label_visibility="collapsed",
                                help="Select which generated image to display and export."
                            )
                    
                    # Show image positioning info
                    if available_images and current_selected_b64:
                        st.write("ℹ️ The illustration will be positioned automatically after the introduction for better visual flow.")
                
                # Only show explanatory message if media richness should include images but none were generated
                if not available_images and media_richness >= 2:
                    st.markdown("_No images were generated for this unit. You can regenerate them using the controls at the bottom of this section._")

                # --- Display/Edit Content ---
                st.markdown("##### Lesson Content")
                if edit_mode:
                     # Use a unique key for the text area
                    content_key = f"{unit_key_base}_content_edit"
                    new_content = st.text_area("Edit Content", value=unit.get("content", ""), key=content_key, height=300)
                    # Update session state directly if changed
                    if new_content != unit.get("content", ""):
                         StateManager.update_curriculum_unit(i, "content", new_content)
                         # Edit history management could be added here if needed
                else:
                    # Display content using markdown rendering
                    # Before displaying content, check if we should insert the image after the introduction
                    content = unit.get("content", "_No content available._")
                    
                    # Insert image after introduction if available
                    if available_images and current_selected_b64 and "##" in content:
                        # Find the first section break (##) to place image after intro
                        parts = content.split("##", 1)
                        intro = parts[0]
                        rest = "##" + parts[1] if len(parts) > 1 else ""
                        
                        # Display introduction
                        st.markdown(intro, unsafe_allow_html=False)
                        
                        # Display image between intro and first section
                        st.image(f"data:image/png;base64,{current_selected_b64}", 
                                caption=f"Illustration: {unit.get('title', 'Topic')}", 
                                use_container_width=True)
                        
                        # Display remaining content
                        if rest:
                            st.markdown(rest, unsafe_allow_html=False)
                    else:
                        # Regular display if no image or no clear section breaks
                        st.markdown(content, unsafe_allow_html=False) # Allow markdown, disable HTML

                # --- Display Chart ---
                st.markdown("##### Chart")
                chart_dict = unit.get("chart")
                if chart_dict and isinstance(chart_dict, dict):
                    suggestion = unit.get("chart_suggestion")
                    chart_title = suggestion.get("title", "Chart") if suggestion else "Chart"
                    
                    # Check if this is a Plotly chart or matplotlib chart
                    chart_type = chart_dict.get("chart_type", "matplotlib")
                    
                    if chart_type == "plotly" and chart_dict.get("plotly_config"):
                        # Display interactive Plotly chart
                        try:
                            import plotly.graph_objects as go
                            # Recreate figure from config dict
                            fig = go.Figure(chart_dict["plotly_config"])
                            st.plotly_chart(fig, use_container_width=True)
                        except ImportError:
                            st.warning("Plotly is not installed. Showing static image fallback if available.")
                            # Fallback to matplotlib if plotly not available but b64 exists
                            if chart_dict.get("b64"):
                                st.image(f"data:image/png;base64,{chart_dict['b64']}", caption=chart_title, width=320)
                        except Exception as e:
                            st.error(f"Error displaying Plotly chart: {e}")
                            # Fallback to matplotlib if available
                            if chart_dict.get("b64"):
                                st.image(f"data:image/png;base64,{chart_dict['b64']}", caption=chart_title, width=320)
                    
                    elif chart_dict.get("b64"):
                        # Display matplotlib chart (legacy or fallback)
                        st.image(f"data:image/png;base64,{chart_dict['b64']}", caption=chart_title, width=320)
                    else:
                        # No valid chart data
                        if media_richness >= 3:
                            st.markdown("_No chart was generated for this unit._")
                else:
                    if media_richness >= 3:
                        st.markdown("_No chart was generated for this unit._")

                # --- Audio Narration (TTS) ---
                if config.get("tts", {}).get("enabled", True):
                    st.markdown("##### 🔊 Audio Narration")
                    
                    # Check if audio already exists for this unit
                    audio_data = unit.get("audio")
                    
                    # Create columns for audio player and controls
                    audio_col1, audio_col2 = st.columns([3, 1])
                    
                    with audio_col1:
                        # Display audio player if audio exists
                        if audio_data:
                            audio_path = audio_data.get("path")
                            if audio_path and os.path.exists(audio_path):
                                # Read audio file and display player
                                with open(audio_path, "rb") as audio_file:
                                    audio_bytes = audio_file.read()
                                    st.audio(audio_bytes, format="audio/mp3")
                                
                                # Show audio metadata
                                voice_used = audio_data.get("voice", "unknown")
                                st.caption(f"Voice: {voice_used} | Generated: {audio_data.get('created_at', 'N/A')}")
                            else:
                                st.info("Audio file not found. Generate new audio below.")
                        else:
                            st.info("No audio narration available. Generate audio to listen to this lesson.")
                    
                    with audio_col2:
                        # Voice selection
                        available_voices = config.get("tts", {}).get("available_voices", 
                            ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
                        
                        current_voice = audio_data.get("voice") if audio_data else config.get("tts", {}).get("default_voice", "alloy")
                        
                        selected_voice = st.selectbox(
                            "Voice",
                            available_voices,
                            index=available_voices.index(current_voice) if current_voice in available_voices else 0,
                            key=f"{unit_key_base}_audio_voice"
                        )
                        
                        # Generate/Regenerate button
                        button_label = "🔄 Regenerate Audio" if audio_data else "▶️ Generate Audio"
                        
                        if st.button(button_label, key=f"{unit_key_base}_generate_audio"):
                            # Initialize AudioAgent if not already done
                            if not hasattr(st.session_state, 'audio_agent'):
                                from src.audio_agent import AudioAgent
                                StateManager.set_state("audio_agent", AudioAgent(client, config))
                            
                            # Generate audio
                            with st.spinner(f"Generating audio for Unit {i+1}..."):
                                try:
                                    audio_result = st.session_state.audio_agent.get_audio_for_unit(
                                        unit, 
                                        voice=selected_voice
                                    )
                                    
                                    if audio_result:
                                        # Handle multi-chunk audio
                                        if audio_result.get("type") == "multi_chunk":
                                            st.warning(f"Content is long. Generated {audio_result['total_chunks']} audio segments.")
                                            # For now, use the first chunk
                                            # TODO: Implement multi-chunk playback
                                            audio_result = audio_result["chunks"][0]
                                        
                                        # Store audio info in unit
                                        StateManager.update_curriculum_unit(i, "audio", audio_result)
                                        st.success(f"✅ Audio generated successfully for Unit {i+1}!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to generate audio. Please try again.")
                                
                                except Exception as e:
                                    st.error(f"Audio generation error: {e}")
                                    if logger:
                                        logger.log_error(error=e, context=f"Audio generation for unit {i+1}")

                # --- Display/Edit Quiz ---
                if include_quizzes:
                    st.markdown("##### Quiz")
                    quiz_data = unit.get("quiz", [])
                    
                    if edit_mode:
                        st.info("Quiz editing functionality is not available in this version.")
                    
                    if quiz_data and isinstance(quiz_data, list) and len(quiz_data) > 0:
                        # Display quiz in a nice format
                        for q_idx, q in enumerate(quiz_data):
                            q_text = q.get("question", f"Question {q_idx+1}")
                            q_type = q.get("type", "Unknown")
                            q_options = q.get("options", [])
                            correct_answer = q.get("answer", "")
                            
                            # Create a unique key for this question in this unit
                            q_key = f"{unit_key_base}_q_{q_idx}"
                            
                            st.markdown(f"**{q_idx+1}. {q_text}**")
                            
                            # Track if user has answered this question
                            has_answered = q_key in st.session_state.quiz_feedback
                            
                            # Different display based on question type
                            if q_type == "MCQ" and q_options:
                                # Use horizontal radio buttons for fewer options
                                use_horizontal = len(q_options) <= 4
                                
                                selected = st.radio(
                                    f"Select answer for question {q_idx+1}:",
                                    q_options,
                                    horizontal=use_horizontal,
                                    key=f"{q_key}_radio",
                                    label_visibility="collapsed"
                                )
                                
                                # Check answer button with callback
                                check_col, feedback_col = st.columns([1, 3])
                                with check_col:
                                    def check_mcq_answer():
                                        update_quiz_answer(q_key, selected, correct_answer, case_sensitive=True)
                                    
                                    st.button("Check Answer", 
                                             key=f"{q_key}_check",
                                             on_click=check_mcq_answer,
                                             disabled=has_answered)
                                
                                with feedback_col:
                                    if has_answered:
                                        is_correct = st.session_state.quiz_feedback[q_key]
                                        if is_correct:
                                            st.success("Correct! ✓")
                                        else:
                                            st.error(f"Incorrect. The correct answer is: {correct_answer}")
                            
                            elif q_type == "TF":
                                # Boolean question - True/False
                                selected = st.radio(
                                    f"Select answer for question {q_idx+1}:",
                                    ["True", "False"],
                                    horizontal=True,
                                    key=f"{q_key}_tf",
                                    label_visibility="collapsed"
                                )
                                
                                # Check answer button with callback
                                check_col, feedback_col = st.columns([1, 3])
                                with check_col:
                                    def check_tf_answer():
                                        update_quiz_answer(q_key, selected, correct_answer, case_sensitive=True)
                                    
                                    st.button("Check Answer", 
                                             key=f"{q_key}_check",
                                             on_click=check_tf_answer,
                                             disabled=has_answered)
                                
                                with feedback_col:
                                    if has_answered:
                                        is_correct = st.session_state.quiz_feedback[q_key]
                                        if is_correct:
                                            st.success("Correct! ✓")
                                        else:
                                            st.error(f"Incorrect. The correct answer is: {correct_answer}")
                            
                            elif q_type == "FILL":
                                # Fill in the blank - use form for better UX
                                with st.form(key=f"{q_key}_form"):
                                    answer_input = st.text_input(
                                        f"Answer for question {q_idx+1}:",
                                        key=f"{q_key}_fill",
                                        label_visibility="collapsed",
                                        placeholder="Type your answer here"
                                    )
                                    
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        submitted = st.form_submit_button("Check Answer", disabled=has_answered)
                                    
                                    if submitted:
                                        # Case-insensitive comparison
                                        user_answer = answer_input.strip().lower()
                                        correct = correct_answer.strip().lower()
                                        
                                        update_quiz_answer(q_key, answer_input, correct_answer, case_sensitive=False)
                                
                                # Display feedback outside form
                                if has_answered:
                                    with col2:
                                        is_correct = st.session_state.quiz_feedback[q_key]
                                        if is_correct:
                                            st.success("Correct! ✓")
                                        else:
                                            st.error(f"Incorrect. The correct answer is: {correct_answer}")
                            
                            else:
                                # Fall back for unknown question types
                                st.info(f"Question type '{q_type}' is not interactive.")
                            
                            st.markdown("---")  # Separator between questions
                    else:
                        st.markdown("_No quiz was generated for this unit._")

                # --- Display/Edit Summary ---
                if include_summary:
                    st.markdown("##### Summary")
                    if edit_mode:
                        summary_key = f"{unit_key_base}_summary_edit"
                        new_summary = st.text_area("Edit Summary", value=unit.get("summary", ""), key=summary_key, height=100)
                        if new_summary != unit.get("summary", ""):
                            StateManager.update_curriculum_unit(i, "summary", new_summary)
                    else:
                        st.markdown(unit.get("summary", "_No summary available._"))

                # --- Display/Edit Resources ---
                if include_resources:
                    st.markdown("##### Further Resources")
                    if edit_mode:
                        resources_key = f"{unit_key_base}_resources_edit"
                        new_resources = st.text_area("Edit Resources", value=unit.get("resources", ""), key=resources_key, height=100)
                        if new_resources != unit.get("resources", ""):
                            StateManager.update_curriculum_unit(i, "resources", new_resources)
                    else:
                        # Use unsafe_allow_html=True to correctly render links in resources
                        st.markdown(unit.get("resources", "_No resources available._"), unsafe_allow_html=True)

                # --- Regenerate Components ---
                if st.session_state.curriculum:
                    st.markdown("##### Regenerate Components")
                    # Responsive columns based on device
                    if st.session_state.get("is_mobile", False):
                        # On mobile, stack vertically
                        comp_row1 = st.container()
                        comp_row2 = st.container()
                    else:
                        # On desktop, use two columns
                        comp_row1, comp_row2 = st.columns(2)
                    
                    # Define component flags
                    comp_flags = {
                        "content": True,  # Always available
                        "images": media_richness >= 2,
                        "chart": media_richness >= 3,
                        "quiz": include_quizzes,
                        "summary": include_summary,
                        "resources": include_resources
                    }
                    
                    with comp_row1:
                        # Content regeneration
                        if comp_flags["content"]:
                            button_key = f"{unit_key_base}_regen_content"
                            button_label = "🔄 Regenerate Content"
                            regenerator = RegenerationHandler.create_content_regenerator(
                                client, text_model, config, i, unit, metadata
                            )
                            st.button(button_label, key=button_key, help=f"Regenerate content for this unit", on_click=regenerator)
                                
                        # Image regeneration
                        if comp_flags["images"]:
                            button_key = f"{unit_key_base}_regen_images"
                            button_label = "🔄 Regenerate Images"
                            regenerator = RegenerationHandler.create_image_regenerator(
                                image_generator, config, i, unit, metadata
                            )
                            st.button(button_label, key=button_key, help=f"Regenerate images for this unit", on_click=regenerator)
                    
                    with comp_row2:
                        # Chart regeneration
                        if comp_flags["chart"]:
                            button_key = f"{unit_key_base}_regen_chart"
                            button_label = "🔄 Regenerate Chart"
                            regenerator = RegenerationHandler.create_chart_regenerator(
                                client, text_model, config, i, unit, metadata
                            )
                            st.button(button_label, key=button_key, help=f"Regenerate chart for this unit", on_click=regenerator)
                                
                        # Quiz regeneration
                        if comp_flags["quiz"]:
                            button_key = f"{unit_key_base}_regen_quiz"
                            button_label = "🔄 Regenerate Quiz"
                            regenerator = RegenerationHandler.create_quiz_regenerator(
                                client, text_model, config, i, unit, metadata
                            )
                            st.button(button_label, key=button_key, help=f"Regenerate quiz for this unit", on_click=regenerator)

        # Save current curriculum button
        # Responsive columns based on device
        if st.session_state.get("is_mobile", False):
            # On mobile, stack vertically
            save_col1 = st.container()
            save_col2 = st.container() 
        else:
            # On desktop, use columns
            save_col1, save_col2 = st.columns([1, 3])
        with save_col1:
            if st.button("💾 Save Curriculum", use_container_width=True):
                # Use the session manager for saving with proper error handling
                try:
                    success, message = st.session_state.session_manager.save_curriculum(st.session_state.curriculum)
                    if success:
                        st.success(message)
                    else:
                        st.error(f"Save failed: {message}")
                        
                        # Log error if available
                        if logger:
                            logger.log_error(error=Exception(message), context="Curriculum save")
                except Exception as e:
                    st.error(f"Unexpected error saving curriculum: {e}")
                    sys.stderr.write(f"Save error: {e}\n")
                    sys.stderr.write(traceback.format_exc() + "\n")
                    
                    # Log error if available
                    if logger:
                        logger.log_error(error=e, context="Curriculum save")
        
        with save_col2:
            st.caption("Save your curriculum to a file so you can reload it later or share it.")
    else:
        st.info("No curriculum has been generated yet. Go to the Generate tab to create one.")

with tab3:
    st.markdown("### Export Curriculum")
    
    if st.session_state.curriculum:
        st.markdown("Export your curriculum in various formats for sharing or printing.")
        
        # Get curriculum data
        curriculum = st.session_state.curriculum
        metadata = curriculum.get("meta", {})
        units = curriculum.get("units", [])
        
        # Create base filename
        base_filename = f"{metadata.get('subject', 'Subject')}_{metadata.get('grade', 'Grade')}".replace(' ', '_').replace(',', '')
        
        # Function to convert a curriculum to various formats
        def generate_markdown(curriculum, include_images=True):
            """Generate Markdown representation of curriculum"""
            md_content = f"# {metadata.get('subject', 'Subject')} Curriculum - Grade {metadata.get('grade', 'Grade')}\n\n"
            md_content += f"*Style: {metadata.get('style', 'Standard')} | Language: {metadata.get('language', 'English')}*\n\n"
            
            for i, unit in enumerate(units):
                md_content += f"## Unit {i+1}: {unit.get('title', 'Untitled')}\n\n"
                
                # Get content and check if we should integrate image
                content = unit.get('content', 'No content available.')
                content_has_sections = "##" in content
                
                if include_images and unit.get("selected_image_b64") and content_has_sections:
                    # Split content at first section to insert image between intro and main content
                    parts = content.split("##", 1)
                    intro = parts[0]
                    rest = "##" + parts[1] if len(parts) > 1 else ""
                    
                    # Add introduction
                    md_content += intro + "\n\n"
                    
                    # Add image after introduction
                    md_content += "*![Illustration: " + unit.get('title', 'Topic') + "]*\n\n"
                    
                    # Add remaining content
                    if rest:
                        md_content += rest + "\n\n"
                else:
                    # If no sections, add image at top if available
                    if include_images and unit.get("selected_image_b64"):
                        md_content += "*![Illustration: " + unit.get('title', 'Topic') + "]*\n\n"
                    
                    # Add content normally
                    md_content += f"{content}\n\n"
                
                # Add chart if available
                if include_images and unit.get("chart") and unit.get("chart", {}).get("b64"):
                    chart_title = unit.get("chart_suggestion", {}).get("title", "Chart")
                    md_content += f"### {chart_title}\n\n"
                    md_content += "*[Chart: Data visualization]*\n\n"
                
                # Add quiz if available
                quiz_data = unit.get("quiz", [])
                if quiz_data and isinstance(quiz_data, list) and len(quiz_data) > 0:
                    md_content += "### Quiz\n\n"
                    
                    for q_idx, q in enumerate(quiz_data):
                        q_text = q.get("question", f"Question {q_idx+1}")
                        q_type = q.get("type", "Unknown")
                        q_options = q.get("options", [])
                        correct_answer = q.get("answer", "")
                        
                        md_content += f"**{q_idx+1}. {q_text}**\n\n"
                        
                        if q_type == "MCQ" and q_options:
                            for opt in q_options:
                                md_content += f"- {opt}\n"
                            md_content += f"\n*Answer: {correct_answer}*\n\n"
                        elif q_type == "TF":
                            md_content += f"- True\n- False\n\n*Answer: {correct_answer}*\n\n"
                        elif q_type == "FILL":
                            md_content += f"*Answer: {correct_answer}*\n\n"
                
                # Add summary if available
                if unit.get("summary"):
                    md_content += "### Summary\n\n"
                    md_content += f"{unit.get('summary')}\n\n"
                
                # Add resources if available
                if unit.get("resources"):
                    md_content += "### Further Resources\n\n"
                    md_content += f"{unit.get('resources')}\n\n"
                
                # Add separator between units
                if i < len(units) - 1:
                    md_content += "---\n\n"
            
            return md_content
        
        def generate_html(curriculum, include_images=True):
            """Generate HTML representation of curriculum"""
            # Convert markdown to HTML and add some styling
            md_content = generate_markdown(curriculum, include_images=False)  # Get markdown without image placeholders
            html_content = markdown.markdown(md_content)
            
            # Style the HTML
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{metadata.get('subject', 'Subject')} Curriculum - Grade {metadata.get('grade', 'Grade')}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                    h1, h2, h3, h4 {{
                        color: #2c3e50;
                    }}
                    h1 {{
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        border-bottom: 1px solid #bdc3c7;
                        padding-bottom: 5px;
                        margin-top: 30px;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                        margin: 10px 0;
                        border-radius: 4px;
                    }}
                    .image-container {{
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .quiz-question {{
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 4px;
                        margin: 10px 0;
                    }}
                    .answer {{
                        color: #2980b9;
                        font-weight: bold;
                    }}
                    hr {{
                        border: none;
                        height: 1px;
                        background-color: #ddd;
                        margin: 40px 0;
                    }}
                    .metadata {{
                        color: #7f8c8d;
                        font-style: italic;
                    }}
                </style>
            </head>
            <body>
            """
            
            # Add the converted markdown content
            styled_html += f"<div class='content'>\n"
            
            # Add header
            styled_html += f"<h1>{metadata.get('subject', 'Subject')} Curriculum - Grade {metadata.get('grade', 'Grade')}</h1>\n"
            styled_html += f"<p class='metadata'>Style: {metadata.get('style', 'Standard')} | Language: {metadata.get('language', 'English')}</p>\n"
            
            # Process each unit manually to add images
            for i, unit in enumerate(units):
                styled_html += f"<h2>Unit {i+1}: {unit.get('title', 'Untitled')}</h2>\n"
                
                # Get content and check if we can integrate the image between intro and main content
                content = unit.get('content', 'No content available.')
                content_has_sections = "##" in content
                
                if include_images and unit.get("selected_image_b64") and content_has_sections:
                    # Split content at first section break to insert image after intro
                    parts = content.split("##", 1)
                    intro = parts[0]
                    rest = "##" + parts[1] if len(parts) > 1 else ""
                    
                    # Add introduction
                    intro_html = markdown.markdown(intro)
                    styled_html += f"{intro_html}\n"
                    
                    # Add image after introduction
                    styled_html += f"<div class='image-container'>\n"
                    styled_html += f"<img src='data:image/png;base64,{unit.get('selected_image_b64')}' alt='Unit {i+1} illustration'>\n"
                    styled_html += f"<p><em>Illustration: {unit.get('title', 'Topic')}</em></p>\n"
                    styled_html += f"</div>\n"
                    
                    # Add remaining content
                    if rest:
                        rest_html = markdown.markdown(rest)
                        styled_html += f"{rest_html}\n"
                else:
                    # If no sections or no image, add image at top if available
                    if include_images and unit.get("selected_image_b64"):
                        styled_html += f"<div class='image-container'>\n"
                        styled_html += f"<img src='data:image/png;base64,{unit.get('selected_image_b64')}' alt='Unit {i+1} illustration'>\n"
                        styled_html += f"<p><em>Illustration: {unit.get('title', 'Topic')}</em></p>\n"
                        styled_html += f"</div>\n"
                    
                    # Add content with regular formatting
                    content_html = markdown.markdown(content)
                    styled_html += f"{content_html}\n"
                
                # Add chart if available
                if include_images and unit.get("chart") and unit.get("chart", {}).get("b64"):
                    chart_title = unit.get("chart_suggestion", {}).get("title", "Chart")
                    styled_html += f"<h3>{chart_title}</h3>\n"
                    styled_html += f"<div class='image-container'>\n"
                    styled_html += f"<img src='data:image/png;base64,{unit.get('chart', {}).get('b64')}' alt='{chart_title}'>\n"
                    styled_html += f"</div>\n"
                
                # Add quiz if available
                quiz_data = unit.get("quiz", [])
                if quiz_data and isinstance(quiz_data, list) and len(quiz_data) > 0:
                    styled_html += f"<h3>Quiz</h3>\n"
                    
                    for q_idx, q in enumerate(quiz_data):
                        q_text = q.get("question", f"Question {q_idx+1}")
                        q_type = q.get("type", "Unknown")
                        q_options = q.get("options", [])
                        correct_answer = q.get("answer", "")
                        
                        styled_html += f"<div class='quiz-question'>\n"
                        styled_html += f"<p><strong>{q_idx+1}. {q_text}</strong></p>\n"
                        
                        if q_type == "MCQ" and q_options:
                            styled_html += f"<ul>\n"
                            for opt in q_options:
                                styled_html += f"<li>{opt}</li>\n"
                            styled_html += f"</ul>\n"
                            styled_html += f"<p class='answer'>Answer: {correct_answer}</p>\n"
                        elif q_type == "TF":
                            styled_html += f"<ul>\n<li>True</li>\n<li>False</li>\n</ul>\n"
                            styled_html += f"<p class='answer'>Answer: {correct_answer}</p>\n"
                        elif q_type == "FILL":
                            styled_html += f"<p class='answer'>Answer: {correct_answer}</p>\n"
                        
                        styled_html += f"</div>\n"
                
                # Add summary if available
                if unit.get("summary"):
                    styled_html += f"<h3>Summary</h3>\n"
                    summary_html = markdown.markdown(unit.get('summary', ''))
                    styled_html += f"{summary_html}\n"
                
                # Add resources if available
                if unit.get("resources"):
                    styled_html += f"<h3>Further Resources</h3>\n"
                    resources_html = markdown.markdown(unit.get('resources', ''))
                    styled_html += f"{resources_html}\n"
                
                # Add separator between units
                if i < len(units) - 1:
                    styled_html += f"<hr>\n"
            
            styled_html += "</div>\n</body>\n</html>"
            
            return styled_html
        
        # Export options
        st.markdown("#### Export Options")
        
        include_images = st.checkbox("Include Images in Export", value=True, help="Include generated images in the exported files")
        
        # Responsive columns based on device
        if st.session_state.get("is_mobile", False):
            # On mobile, use a single column
            col1 = st.container()
            col2 = st.container()
            col3 = st.container()
        else:
            # On desktop, use 3 columns
            col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📝 Export as Markdown", use_container_width=True):
                md_content = generate_markdown(curriculum, include_images)
                md_filename = f"{base_filename}.md"
                
                # Write to file
                file_path = os.path.join("exports", md_filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                    
                # Create download link
                b64_md = base64.b64encode(md_content.encode()).decode()
                href = f'<a href="data:file/markdown;base64,{b64_md}" download="{md_filename}" style="display: inline-block; padding: 0.5em 1em; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; cursor: pointer;">📥 Download Markdown</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success(f"Markdown file saved to {file_path}")
        
        with col2:
            if st.button("🌐 Export as HTML", use_container_width=True):
                html_content = generate_html(curriculum, include_images)
                html_filename = f"{base_filename}.html"
                
                # Write to file
                file_path = os.path.join("exports", html_filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                # Create download link
                b64_html = base64.b64encode(html_content.encode()).decode()
                href = f'<a href="data:text/html;base64,{b64_html}" download="{html_filename}" style="display: inline-block; padding: 0.5em 1em; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; cursor: pointer;">📥 Download HTML</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success(f"HTML file saved to {file_path}")
        
        with col3:
            if st.button("📄 Export as PDF", use_container_width=True):
                try:
                    exporter = CurriculumExporter()
                    pdf_data = exporter.generate_pdf(curriculum)

                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_data,
                        file_name=f"{base_filename}.pdf",
                        mime="application/pdf",
                        key="pdf_download_btn",
                    )
                    st.success("PDF ready for download!")
                except Exception as e:
                    st.error(f"Failed to generate PDF: {e}")
                    if logger:
                        logger.log_error(error=e, context="PDF Export")
        
        # Load saved curriculum
        st.markdown("#### Load Saved Curriculum")
        st.markdown("Load a previously saved curriculum file.")
        
        # Get list of saved curricula
        saved_files = sorted(Path("curricula").glob("curriculum_*.json"), key=os.path.getmtime, reverse=True)
        if saved_files:
            file_options = ["Select a file"] + [f.name for f in saved_files]
            selected_file = st.selectbox("Select a saved curriculum", file_options)
            
            if selected_file != "Select a file":
                file_path = os.path.join("curricula", selected_file)
                if st.button("📂 Load Selected Curriculum"):
                    # Use the session manager for loading with proper error handling
                    try:
                        loaded_curriculum, error_msg = st.session_state.session_manager.load_curriculum(selected_file)
                        if loaded_curriculum:
                            # Validate the loaded curriculum
                            is_valid, validation_errors = CurriculumValidator.validate_curriculum(loaded_curriculum)
                            if is_valid:
                                StateManager.update_state('curriculum', loaded_curriculum)
                                st.success(f"Successfully loaded curriculum from {selected_file}")
                            else:
                                st.error("Loaded curriculum failed validation:")
                                for error in validation_errors:
                                    st.error(f"- {error}")
                        else:
                            st.error(f"Failed to load curriculum: {error_msg}")
                            
                            # Log error if available
                            if logger:
                                logger.log_error(error=Exception(error_msg), context="Curriculum load")
                    except Exception as e:
                        st.error(f"Unexpected error loading curriculum: {e}")
                        sys.stderr.write(f"Load error: {e}\n")
                        sys.stderr.write(traceback.format_exc() + "\n")
                        
                        # Log error if available
                        if logger:
                            logger.log_error(error=e, context="Curriculum load")
        else:
            st.info("No saved curricula found.")
            
    else:
        st.info("No curriculum has been generated yet. Go to the Generate tab to create one.")

with tab4:
    st.markdown("### Template Management")
    
    if st.session_state.template_manager:
        # Template tabs
        template_tab1, template_tab2, template_tab3 = st.tabs(["📚 Browse Templates", "➕ Create Template", "📊 Template Stats"])
        
        with template_tab1:
            st.markdown("#### Available Templates")
            
            # Search and filter
            col1, col2, col3 = st.columns(3)
            with col1:
                search_query = st.text_input("Search templates", key="template_search")
            with col2:
                filter_subject = st.selectbox("Filter by Subject", 
                                            ["All"] + config["defaults"]["subjects"], 
                                            key="template_filter_subject")
            with col3:
                filter_grade = st.selectbox("Filter by Grade", 
                                          ["All"] + config["defaults"]["grades"], 
                                          key="template_filter_grade")
            
            # Get templates based on filters
            if search_query:
                templates = st.session_state.template_manager.search_templates(search_query)
            else:
                templates = st.session_state.template_manager.list_templates(
                    subject_filter=filter_subject if filter_subject != "All" else None,
                    grade_filter=filter_grade if filter_grade != "All" else None
                )
            
            if templates:
                for template in templates:
                    with st.expander(f"📋 {template.name}", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Description:** {template.description}")
                            st.write(f"**Subjects:** {', '.join(template.subjects)}")
                            st.write(f"**Grades:** {', '.join(template.grades)}")
                            st.write(f"**Style:** {template.style}")
                            st.write(f"**Language:** {template.language}")
                            if template.tags:
                                st.write(f"**Tags:** {', '.join(template.tags)}")
                        
                        with col2:
                            st.write(f"**Author:** {template.author}")
                            st.write(f"**Used:** {template.usage_count} times")
                            st.write(f"**Created:** {template.created_at[:10]}")
                            
                            # Action buttons
                            if st.button(f"Use Template", key=f"use_{template.id}"):
                                StateManager.set_state("selected_template_id", template.id)
                                st.success(f"Template '{template.name}' selected! Go to the Generate tab to use it.")
                            
                            # Delete button for user templates only
                            if template.id.startswith("user_"):
                                def delete_template():
                                    if st.session_state.template_manager.delete_template(template.id):
                                        st.success(f"Template '{template.name}' deleted!")
                                    else:
                                        st.error("Failed to delete template.")
                                
                                if st.button(f"Delete", key=f"delete_{template.id}", type="secondary", on_click=delete_template):
                                    pass
            else:
                st.info("No templates found matching your criteria.")
        
        with template_tab2:
            st.markdown("#### Create New Template")
            
            if st.session_state.curriculum:
                st.info("Create a template from your current curriculum to reuse its structure.")
                
                # Template creation form
                with st.form("create_template"):
                    template_name = st.text_input("Template Name", placeholder="e.g., My Science Template")
                    template_description = st.text_area("Description", 
                                                       placeholder="Describe what this template is good for...")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        template_tags = st.text_input("Tags (comma-separated)", 
                                                    placeholder="science, elementary, hands-on")
                    with col2:
                        template_public = st.checkbox("Make this template public", 
                                                    help="Public templates can be used by other users")
                    
                    submitted = st.form_submit_button("Create Template")
                    
                    if submitted:
                        if template_name and template_description:
                            try:
                                tags = [tag.strip() for tag in template_tags.split(",") if tag.strip()]
                                template_id = st.session_state.template_manager.create_template(
                                    name=template_name,
                                    description=template_description,
                                    curriculum=st.session_state.curriculum,
                                    tags=tags,
                                    is_public=template_public
                                )
                                st.success(f"Template '{template_name}' created successfully! ID: {template_id}")
                            except Exception as e:
                                st.error(f"Error creating template: {e}")
                        else:
                            st.error("Please provide both name and description.")
            else:
                st.warning("Generate a curriculum first to create a template from it.")
                st.markdown("Templates are created from existing curricula and capture their structure, style, and settings for reuse.")
        
        with template_tab3:
            st.markdown("#### Template Statistics")
            
            try:
                stats = st.session_state.template_manager.get_template_stats()
                
                # Overview metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Templates", stats["total_templates"])
                with col2:
                    st.metric("User Templates", stats["user_templates"])
                with col3:
                    st.metric("System Templates", stats["system_templates"])
                with col4:
                    st.metric("Total Usage", stats["total_usage"])
                
                # Popular templates
                if stats["popular_templates"]:
                    st.markdown("#### Most Popular Templates")
                    for i, template in enumerate(stats["popular_templates"][:3], 1):
                        st.write(f"{i}. **{template.name}** - Used {template.usage_count} times")
                
                # Recent templates
                if stats["recent_templates"]:
                    st.markdown("#### Recently Created")
                    for template in stats["recent_templates"][:3]:
                        st.write(f"• **{template.name}** - {template.created_at[:10]}")
                
                # Subject and grade distribution
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Subjects Covered")
                    for subject in stats["subjects"]:
                        if subject:  # Skip empty subjects
                            st.write(f"• {subject}")
                
                with col2:
                    st.markdown("#### Grade Levels")
                    for grade in sorted(stats["grades"]):
                        if grade:  # Skip empty grades
                            st.write(f"• Grade {grade}")
                            
            except Exception as e:
                st.error(f"Error loading template statistics: {e}")
    else:
        st.error("Template management is not available. Please check your installation.")

with tab5:
    st.markdown("### Batch Curriculum Generation")

    if not st.session_state.batch_manager:
        st.error("Batch generation service is not available. Please check the installation.")
    else:
        # Sub-tabs for different batch operations
        batch_tab1, batch_tab2, batch_tab3 = st.tabs(["➕ Create Batch", "📊 Active Batches", "📜 History"])

        with batch_tab1:
            st.markdown("#### Create New Batch")
            st.markdown("Generate multiple curricula in one batch operation.")

            # Batch creation method selection
            creation_method = st.radio(
                "Creation Method",
                ["From Template", "Custom Combinations"],
                help="Choose how to create your batch jobs"
            )

            if creation_method == "From Template":
                if not st.session_state.template_manager:
                    st.warning("Template manager not available.")
                else:
                    # Template selection
                    templates = st.session_state.template_manager.list_templates()

                    if templates:
                        template_options = {t.name: t.id for t in templates}
                        selected_template_name = st.selectbox(
                            "Select Template",
                            options=list(template_options.keys())
                        )
                        selected_template_id = template_options[selected_template_name]

                        # Subject and grade selection
                        st.markdown("**Select Subjects and Grades**")
                        col1, col2 = st.columns(2)

                        with col1:
                            batch_subjects = st.multiselect(
                                "Subjects",
                                config["defaults"]["subjects"],
                                default=[config["defaults"]["subject"]]
                            )

                        with col2:
                            batch_grades = st.multiselect(
                                "Grades",
                                config["defaults"]["grades"],
                                default=[config["defaults"]["grade"]]
                            )

                        # Show job count
                        total_jobs = len(batch_subjects) * len(batch_grades)
                        st.info(f"This will create **{total_jobs}** curriculum generation jobs.")

                        # Batch name and description
                        batch_name = st.text_input(
                            "Batch Name",
                            value=f"Batch: {selected_template_name}",
                            help="Give your batch a meaningful name"
                        )

                        batch_description = st.text_area(
                            "Description (Optional)",
                            help="Describe this batch generation"
                        )

                        # Cost estimation
                        if total_jobs > 0 and st.session_state.curriculum_service:
                            with st.expander("💰 Cost Estimation", expanded=False):
                                # Estimate cost for one job
                                estimation_params = {
                                    "media_richness": media_richness,
                                    "include_quizzes": include_quizzes,
                                    "include_summary": include_summary,
                                    "include_resources": include_resources,
                                    "image_model": image_model,
                                    "text_model": text_model
                                }
                                single_cost = st.session_state.curriculum_service.estimate_costs(estimation_params)
                                total_cost = single_cost['total_cost'] * total_jobs

                                st.metric("Total Estimated Cost", f"${total_cost:.2f}")
                                st.caption(f"${single_cost['total_cost']:.2f} per curriculum × {total_jobs} jobs")

                        # Create batch button
                        if st.button("🚀 Create Batch", type="primary", disabled=total_jobs == 0):
                            try:
                                # Create batch
                                batch_id = st.session_state.batch_manager.create_batch_from_template(
                                    template_id=selected_template_id,
                                    subjects=batch_subjects,
                                    grades=batch_grades,
                                    template_manager=st.session_state.template_manager,
                                    name=batch_name,
                                    description=batch_description
                                )

                                # Define generator function
                                def generator_func(params):
                                    """Generator function for batch jobs"""
                                    if st.session_state.curriculum_service:
                                        return st.session_state.curriculum_service.generate_curriculum(params)
                                    else:
                                        # Fallback to orchestrator
                                        return orchestrator.create_curriculum(
                                            params.get("subject_str"),
                                            params.get("grade"),
                                            params.get("lesson_style"),
                                            params.get("language"),
                                            params.get("custom_prompt", ""),
                                            config
                                        )

                                # Start batch processing
                                success = st.session_state.batch_manager.start_batch(batch_id, generator_func)

                                if success:
                                    st.success(f"Batch '{batch_name}' created and started!")
                                    StateManager.set_state("active_batch_id", batch_id)
                                    StateManager.set_state("batch_polling", True)
                                    st.rerun()
                                else:
                                    st.error("Failed to start batch processing")

                            except Exception as e:
                                st.error(f"Error creating batch: {e}")
                                sys.stderr.write(f"Batch creation error: {e}\n")
                                sys.stderr.write(traceback.format_exc() + "\n")

                    else:
                        st.info("No templates available. Create templates in the Templates tab first.")

            else:  # Custom Combinations
                st.markdown("**Custom Batch Configuration**")
                st.info("Custom batch creation will be available in a future update.")

        with batch_tab2:
            st.markdown("#### Active Batches")

            # Get active batches
            active_batches = st.session_state.batch_manager.list_batches()
            running_batches = [b for b in active_batches if b.status.value in ["pending", "running"]]

            if not running_batches:
                st.info("No active batches. Create a new batch to get started.")
            else:
                for batch in running_batches:
                    with st.expander(f"📦 {batch.name}", expanded=True):
                        # Batch metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Jobs", batch.total_jobs)
                        with col2:
                            st.metric("Completed", batch.completed_jobs)
                        with col3:
                            st.metric("Failed", batch.failed_jobs)

                        # Progress bar
                        progress = batch.completed_jobs / batch.total_jobs if batch.total_jobs > 0 else 0
                        st.progress(progress, text=f"Progress: {int(progress*100)}%")

                        # Polling mechanism for this batch
                        if st.session_state.active_batch_id == batch.id and st.session_state.batch_polling:
                            # Create polling loop
                            progress_container = st.empty()
                            stop_polling = False

                            # Polling interval
                            poll_interval = 1.5  # seconds

                            # Poll for updates
                            while st.session_state.batch_polling and not stop_polling:
                                # Read status from file (safe for UI thread)
                                updated_batch = st.session_state.batch_manager.get_batch_status(batch.id)

                                if updated_batch:
                                    with progress_container.container():
                                        # Display job statuses
                                        st.markdown("**Job Status:**")
                                        for i, job in enumerate(updated_batch.jobs):
                                            status_icon = {
                                                "pending": "⏳",
                                                "running": "🔄",
                                                "completed": "✅",
                                                "failed": "❌",
                                                "cancelled": "🚫"
                                            }.get(job.status.value, "❓")

                                            st.markdown(f"{status_icon} **{job.name}** - {job.status.value}")
                                            if job.progress > 0:
                                                st.progress(job.progress)

                                    # Check if batch is complete
                                    if updated_batch.status.value in ["completed", "failed", "cancelled"]:
                                        StateManager.set_state("batch_polling", False)
                                        stop_polling = True
                                        st.success(f"Batch {updated_batch.status.value}!")
                                        st.rerun()

                                # Wait before next poll
                                if not stop_polling:
                                    time.sleep(poll_interval)

                            # Stop polling button
                            if st.button("⏸️ Stop Monitoring", key=f"stop_{batch.id}"):
                                StateManager.set_state("batch_polling", False)
                                st.rerun()

                        else:
                            # Show job details without polling
                            st.markdown("**Jobs:**")
                            for job in batch.jobs:
                                status_icon = {
                                    "pending": "⏳",
                                    "running": "🔄",
                                    "completed": "✅",
                                    "failed": "❌",
                                    "cancelled": "🚫"
                                }.get(job.status.value, "❓")
                                st.markdown(f"{status_icon} {job.name} - {job.status.value}")

                            # Monitor button
                            if st.button("👁️ Monitor Progress", key=f"monitor_{batch.id}"):
                                StateManager.set_state("active_batch_id", batch.id)
                                StateManager.set_state("batch_polling", True)
                                st.rerun()

                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🗑️ Cancel Batch", key=f"cancel_{batch.id}"):
                                if st.session_state.batch_manager.cancel_batch(batch.id):
                                    st.success("Batch cancelled")
                                    StateManager.set_state("batch_polling", False)
                                    st.rerun()

                        with col2:
                            if batch.status.value == "completed":
                                if st.button("📥 Download Results", key=f"download_{batch.id}"):
                                    st.info("Download functionality coming soon!")

        with batch_tab3:
            st.markdown("#### Batch History")

            # Get completed/failed batches
            all_batches = st.session_state.batch_manager.list_batches()
            completed_batches = [b for b in all_batches if b.status.value in ["completed", "failed", "cancelled"]]

            if not completed_batches:
                st.info("No completed batches yet.")
            else:
                for batch in completed_batches:
                    with st.expander(f"📦 {batch.name} - {batch.status.value}"):
                        st.markdown(f"**Description:** {batch.description}")
                        st.markdown(f"**Created:** {batch.created_at}")
                        st.markdown(f"**Completed:** {batch.completed_at}")

                        # Stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Jobs", batch.total_jobs)
                        with col2:
                            st.metric("Completed", batch.completed_jobs)
                        with col3:
                            st.metric("Failed", batch.failed_jobs)

                        # View results
                        if batch.status.value == "completed":
                            if st.button("📄 View Results", key=f"view_{batch.id}"):
                                results = st.session_state.batch_manager.get_batch_results(batch.id)
                                st.json(results)

                        # Delete batch
                        if st.button("🗑️ Delete Batch", key=f"delete_{batch.id}"):
                            if st.session_state.batch_manager.delete_batch(batch.id):
                                st.success("Batch deleted")
                                st.rerun()

# =============================================================================
# TAB 6: ANALYTICS DASHBOARD
# =============================================================================
with tab6:
    ModernUI.section_header("Teacher Analytics Dashboard", "📊", "analytics")

    # Initialize analytics service
    if "analytics_service" not in st.session_state:
        st.session_state.analytics_service = AnalyticsService()

    analytics = st.session_state.analytics_service

    # Refresh button
    col_refresh, col_spacer = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # Get analytics summary
    try:
        summary = analytics.get_analytics_summary()

        # Overview metrics
        st.subheader("📈 Overview")
        metric_cols = st.columns(4)

        with metric_cols[0]:
            st.metric("Total Students", summary.total_students)
        with metric_cols[1]:
            st.metric("Active (7 days)", summary.active_students_7d)
        with metric_cols[2]:
            st.metric("Curricula Used", summary.total_curricula)
        with metric_cols[3]:
            st.metric("Total XP Awarded", f"{summary.total_xp_awarded:,}")

        st.markdown("---")

        # Two-column layout for leaderboard and curriculum stats
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🏆 Top Students")
            if summary.top_students:
                for i, student in enumerate(summary.top_students, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "⭐"
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 0.5rem; margin: 0.25rem 0; background: linear-gradient(90deg, rgba(255,215,0,0.1) 0%, transparent 100%); border-radius: 8px;">
                            <strong>{medal} {student.username}</strong><br>
                            <span style="color: #888; font-size: 0.85rem;">
                                Level {student.level} • {student.total_xp:,} XP •
                                {student.curricula_completed}/{student.curricula_started} completed
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No student data yet. Students will appear here after they start learning.")

        with col_right:
            st.subheader("📚 Curriculum Performance")
            if summary.curriculum_stats:
                for cstats in summary.curriculum_stats[:5]:  # Top 5
                    completion_color = "#4CAF50" if cstats.completion_rate > 70 else "#FFC107" if cstats.completion_rate > 40 else "#f44336"
                    struggle_badge = "⚠️" if cstats.struggle_sections else ""

                    st.markdown(f"""
                    <div style="padding: 0.5rem; margin: 0.25rem 0; border-left: 3px solid {completion_color}; padding-left: 1rem;">
                        <strong>{cstats.title}</strong> {struggle_badge}<br>
                        <span style="color: #888; font-size: 0.85rem;">
                            {cstats.total_students} students • {cstats.completion_rate:.1f}% completion
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No curriculum data yet.")

        st.markdown("---")

        # Detailed curriculum analysis
        st.subheader("🔍 Detailed Curriculum Analysis")

        if summary.curriculum_stats:
            curriculum_options = {f"{cs.title} ({cs.curriculum_id[:8]}...)": cs.curriculum_id
                                  for cs in summary.curriculum_stats}

            selected_curriculum_name = st.selectbox(
                "Select a curriculum to analyze:",
                options=list(curriculum_options.keys())
            )

            if selected_curriculum_name:
                selected_id = curriculum_options[selected_curriculum_name]
                details = analytics.get_curriculum_details(selected_id)

                # Section breakdown
                if details['sections']:
                    st.markdown("**Section-by-Section Breakdown:**")

                    for section in details['sections']:
                        struggle_indicator = "🔴 STRUGGLE POINT" if section['is_struggle_point'] else ""
                        bar_width = min(section['completion_rate'], 100)
                        bar_color = "#f44336" if section['is_struggle_point'] else "#4CAF50"

                        st.markdown(f"""
                        <div style="margin: 0.5rem 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span><strong>Section {section['index'] + 1}:</strong> {section['title'][:40]}...</span>
                                <span style="color: #888;">{section['completions']} completions ({section['completion_rate']:.0f}%)</span>
                            </div>
                            <div style="background: #333; border-radius: 4px; height: 8px; margin-top: 4px;">
                                <div style="background: {bar_color}; width: {bar_width}%; height: 100%; border-radius: 4px;"></div>
                            </div>
                            <span style="color: #f44336; font-size: 0.75rem;">{struggle_indicator}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    if details['struggle_sections']:
                        st.warning(f"⚠️ **Struggle Points Detected:** Sections {[s+1 for s in details['struggle_sections']]} have significantly lower completion rates. Consider reviewing the content difficulty or adding more support materials.")
                else:
                    st.info("No section data available for this curriculum.")
        else:
            st.info("Generate some curricula and have students use them to see analytics here.")

    except Exception as e:
        st.error(f"Error loading analytics: {e}")
        if logger:
            logger.log_error(error=e, context="Analytics Dashboard")

# =============================================================================
# TAB 7: FAMILY DASHBOARD
# =============================================================================
with tab7:
    st.markdown("## 👨‍👩‍👧‍👦 Family Dashboard")
    st.markdown("Overview of all children's learning progress")

    try:
        # Get family service
        family_service = get_family_service()

        # Sub-tabs for family features
        family_tab1, family_tab2, family_tab3, family_tab4 = st.tabs(["📊 Overview", "➕ Manage Children", "📄 Reports", "🏆 Certificates"])

        with family_tab1:
            # Get family summary data
            family_data = family_service.get_family_summary()
            FamilyDashboard.render_dashboard(family_data)

        with family_tab2:
            st.markdown("### 👧👦 Manage Children")

            # Show existing children
            children = family_service.get_all_children()
            if children:
                st.markdown("#### Current Profiles")
                for child in children:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        pin_icon = "🔐" if child.get("has_pin") else "🔓"
                        st.markdown(f"**{child.get('username')}** {pin_icon}")
                    with col2:
                        st.markdown(f"⭐ {child.get('total_xp', 0):,} XP")
                    with col3:
                        # View details button
                        if st.button("📊 Details", key=f"details_{child.get('username')}"):
                            user = family_service.db.get_user_by_username(child.get("username"))
                            if user:
                                summary = family_service.get_child_summary(user["id"])
                                st.session_state.selected_child_summary = summary

                st.markdown("---")

            # Show selected child details
            if hasattr(st.session_state, 'selected_child_summary') and st.session_state.selected_child_summary:
                summary = st.session_state.selected_child_summary
                st.markdown(f"#### {summary.get('username')}'s Progress")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🔥 Streak", f"{summary.get('current_streak', 0)} days")
                with col2:
                    st.metric("⭐ Total XP", f"{summary.get('total_xp', 0):,}")
                with col3:
                    st.metric("📚 Due Cards", summary.get("due_cards", 0))

                # Curriculum progress
                curricula = family_service.get_child_curricula_progress(summary.get("user_id"))
                if curricula:
                    st.markdown("##### Curricula Progress")
                    for c in curricula:
                        st.progress(
                            c.get("progress_percent", 0) / 100,
                            text=f"{c.get('title', 'Unknown')} - {c.get('progress_percent', 0)}%"
                        )

                if st.button("Close Details"):
                    st.session_state.selected_child_summary = None
                    st.rerun()

                st.markdown("---")

            # Add new child form
            new_child = FamilyDashboard.render_add_child_form()
            if new_child:
                try:
                    from services.user_service import UserService
                    user_service = UserService()
                    result, status = user_service.create_user(
                        username=new_child["username"],
                        pin=new_child.get("pin")
                    )
                    if status in ["created", "success"]:
                        st.success(f"✅ Created profile for {new_child['username']}")
                        st.rerun()
                    else:
                        st.error(f"Failed to create profile: {status}")
                except Exception as e:
                    st.error(f"Error creating profile: {e}")

        with family_tab3:
            st.markdown("### 📄 Progress Reports")

            # Report type selection
            report_type = st.radio(
                "Report Type",
                ["Family Summary", "Individual Child"],
                horizontal=True
            )

            if report_type == "Individual Child":
                children = family_service.get_all_children()
                if children:
                    child_names = [c.get("username") for c in children]
                    selected_child = st.selectbox("Select Child", child_names)
                else:
                    st.info("No children profiles found.")
                    selected_child = None
            else:
                selected_child = None

            if st.button("📊 Generate Report", use_container_width=True):
                with st.spinner("Generating report..."):
                    if selected_child:
                        user = family_service.db.get_user_by_username(selected_child)
                        if user:
                            report = family_service.generate_weekly_report(user["id"])
                        else:
                            report = None
                    else:
                        report = family_service.generate_weekly_report()

                    if report:
                        st.markdown("#### Report Preview")

                        if report.get("type") == "family":
                            st.markdown(f"**Family Summary** - {report.get('period')}")
                            st.markdown(f"Generated: {report.get('generated_at', '')[:19]}")

                            totals = report.get("totals", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total XP", f"{totals.get('total_xp', 0):,}")
                            with col2:
                                st.metric("Curricula", totals.get("total_curricula", 0))
                            with col3:
                                st.metric("Active Today", totals.get("active_today", 0))

                            for child in report.get("children", []):
                                st.markdown(f"**{child.get('username')}**: Level {child.get('level', 0)}, {child.get('current_streak', 0)} day streak")

                        else:
                            st.markdown(f"**{report.get('user')}** - {report.get('period')}")
                            summary = report.get("summary", {})
                            st.markdown(f"- XP: {summary.get('total_xp', 0):,}")
                            st.markdown(f"- Streak: {summary.get('current_streak', 0)} days")
                            st.markdown(f"- Due Cards: {summary.get('due_cards', 0)}")

                        # Generate PDF report
                        st.markdown("---")
                        st.markdown("#### Download Report")
                        try:
                            report_service = get_report_service()
                            if selected_child:
                                pdf_bytes = report_service.generate_child_report(user["id"])
                                filename = f"{selected_child}_progress_report.pdf"
                            else:
                                pdf_bytes = report_service.generate_family_report()
                                filename = "family_progress_report.pdf"

                            st.download_button(
                                label="📥 Download PDF Report",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")

        with family_tab4:
            st.markdown("### 🏆 Achievement Certificates")
            st.caption("Generate printable certificates to celebrate your children's achievements!")

            from services.certificate_service import get_certificate_service
            cert_service = get_certificate_service()

            cert_type = st.radio(
                "Certificate Type",
                ["Curriculum Completion", "Progress Certificate", "Custom Certificate"],
                horizontal=True
            )

            children = family_service.get_all_children()
            if children:
                child_names = [c.get("username") for c in children]
                selected_child_cert = st.selectbox("Select Child", child_names, key="cert_child")
            else:
                st.info("No children profiles found. Add children first.")
                selected_child_cert = None

            if cert_type == "Curriculum Completion" and selected_child_cert:
                user = family_service.db.get_user_by_username(selected_child_cert)
                if user:
                    curricula = family_service.get_child_curricula_progress(user["id"])
                    completed = [c for c in curricula if c.get("progress_percent", 0) >= 100]

                    if completed:
                        curr_options = [c.get("title", "Unknown") for c in completed]
                        selected_curr = st.selectbox("Select Completed Curriculum", curr_options)

                        if st.button("🎓 Generate Completion Certificate", use_container_width=True):
                            summary = family_service.get_child_summary(user["id"])
                            curr_data = next((c for c in completed if c.get("title") == selected_curr), {})

                            pdf_bytes = cert_service.generate_completion_certificate(
                                student_name=selected_child_cert,
                                curriculum_title=selected_curr,
                                subject=curr_data.get("subject", ""),
                                total_xp=summary.get("total_xp", 0),
                                level=summary.get("level", 0)
                            )

                            st.download_button(
                                label="📥 Download Certificate",
                                data=pdf_bytes,
                                file_name=f"{selected_child_cert}_{selected_curr}_certificate.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.info("No completed curricula yet. Keep learning!")

            elif cert_type == "Progress Certificate" and selected_child_cert:
                user = family_service.db.get_user_by_username(selected_child_cert)
                if user:
                    period = st.text_input("Certificate Period", value=datetime.now().strftime("%B %Y"))
                    summary = family_service.get_child_summary(user["id"])

                    if st.button("📊 Generate Progress Certificate", use_container_width=True):
                        pdf_bytes = cert_service.generate_progress_certificate(
                            student_name=selected_child_cert,
                            period=period,
                            sections_completed=summary.get("total_sections_completed", 0),
                            xp_earned=summary.get("total_xp", 0),
                            streak_days=summary.get("current_streak", 0),
                            quizzes_passed=summary.get("completed_curricula", 0)
                        )

                        st.download_button(
                            label="📥 Download Certificate",
                            data=pdf_bytes,
                            file_name=f"{selected_child_cert}_progress_certificate.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

            elif cert_type == "Custom Certificate" and selected_child_cert:
                st.markdown("#### Create Custom Certificate")
                custom_title = st.text_input("Certificate Title", value="Certificate of Achievement")
                custom_subtitle = st.text_input("Subtitle (optional)", value="")
                custom_text = st.text_area("Main Text", value="For outstanding dedication to learning")
                custom_footer = st.text_input("Footer (optional)", value="")

                if st.button("✨ Generate Custom Certificate", use_container_width=True):
                    pdf_bytes = cert_service.generate_custom_certificate(
                        student_name=selected_child_cert,
                        title=custom_title,
                        main_text=custom_text,
                        subtitle=custom_subtitle,
                        footer_text=custom_footer
                    )

                    st.download_button(
                        label="📥 Download Certificate",
                        data=pdf_bytes,
                        file_name=f"{selected_child_cert}_custom_certificate.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

    except Exception as e:
        st.error(f"Error loading family dashboard: {e}")
        import traceback
        st.code(traceback.format_exc())

# Initialize agents when needed (done in the agentic_framework.py now)

# =============================================================================
# VERSION FOOTER - Always displayed at the bottom of the page
# =============================================================================
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #888; font-size: 0.85rem; padding: 1rem 0;">
        <strong>InstaSchool</strong> {get_version_display()}<br>
        <span style="font-size: 0.75rem;">AI-Powered Curriculum Generator</span>
    </div>
    """,
    unsafe_allow_html=True
)
