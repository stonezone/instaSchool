import streamlit as st
import os
import sys
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
import matplotlib
matplotlib.use('Agg') # Use Agg backend for matplotlib

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
from src.agent_framework import OrchestratorAgent, OutlineAgent, ContentAgent, MediaAgent, ChartAgent, QuizAgent, SummaryAgent, ResourceAgent
from src.image_generator import ImageGenerator
from services.curriculum_service import CurriculumService, CurriculumValidator, CurriculumExporter
from services.session_service import SessionManager, QuizManager, InputValidator

# Import modern UI components
from src.ui_components import ModernUI, ThemeManager, LayoutHelpers

# Setup page config for wider layout
st.set_page_config(page_title="Curriculum Generator", page_icon=":books:", layout="wide")

# Load modern UI design system
ModernUI.load_css()

# Detect if user is on mobile
def is_mobile():
    """Detect if user is on a mobile device using viewport width"""
    # Simplified mobile detection that doesn't rely on the broken component
    # Default to desktop view to avoid layout issues
    return False

# Set global state for mobile detection
if "is_mobile" not in st.session_state:
    mobile_detected = is_mobile()
    st.session_state.is_mobile = mobile_detected

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

# ========== PDF Export Compatibility Check ==========
PDF_CAPABLE = False
WKHTMLTOPDF_PATH = shutil.which("wkhtmltopdf")
if WKHTMLTOPDF_PATH:
    try:
        import pdfkit
        PDF_CAPABLE = True
        # Define config globally for pdfkit path, avoid using 'config' as variable name here to prevent confusion
        pdfkit_wkhtmltopdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    except ImportError:
        st.warning("pdfkit library not installed. PDF export will be disabled. Run: pip install pdfkit")
        PDF_CAPABLE = False
    except Exception as e:
        st.error(f"Error configuring pdfkit: {e}")
        PDF_CAPABLE = False
else:
     st.warning("wkhtmltopdf executable not found in PATH. PDF export will be disabled. Please install it.")

# ========== Load OpenAI Key and Client ==========
try:
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY not set in environment variable or .env file")
        st.stop()

    # Initialize the client based on detected SDK version
    if 'OPENAI_NEW_API' in locals() and OPENAI_NEW_API:
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        # Fallback logic (shouldn't be reached if import checks pass)
        st.error("OpenAI client initialization failed. SDK version issue suspected.")
        st.stop()
except ImportError as e:
    if 'dotenv' in str(e):
        st.warning("python-dotenv not installed, falling back to environment variables.")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            st.error("OPENAI_API_KEY not set in environment variable")
            st.stop()
        if 'OPENAI_NEW_API' in locals() and OPENAI_NEW_API:
            client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            st.error("OpenAI client initialization failed. SDK version issue suspected.")
            st.stop()
    else:
        st.error(f"Import error during OpenAI setup: {e}")
        st.stop()
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    sys.stderr.write(traceback.format_exc() + "\n")
    st.stop()

# ========== Initialize session state and services ==========
# Initialize session manager
if "session_manager" not in st.session_state:
    try:
        st.session_state.session_manager = SessionManager()
    except Exception as e:
        st.error(f"Failed to initialize session manager: {e}")
        st.session_state.session_manager = None

# Curriculum service and template manager will be initialized after config is loaded

if "curriculum" not in st.session_state:
    st.session_state.curriculum = None
if "curriculum_id" not in st.session_state:
    st.session_state.curriculum_id = uuid.uuid4().hex
# Initialize session state using StateManager
StateManager.initialize_state()

# Additional state initialization
if "api_error" not in st.session_state:
    st.session_state.api_error = None
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

# Create directories if they don't exist
Path("curricula").mkdir(exist_ok=True)
Path("exports").mkdir(exist_ok=True)

# ========== Utility Functions for Session Management ==========
def add_to_cleanup(file_path: Optional[str]):
    """Adds a file path to the set of temporary files to be cleaned up on exit."""
    if file_path and os.path.exists(file_path):
        if 'last_tmp_files' not in st.session_state:
            st.session_state['last_tmp_files'] = set()
        st.session_state['last_tmp_files'].add(file_path)

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

# Initialize curriculum service and template manager after config is loaded
if "curriculum_service" not in st.session_state:
    try:
        st.session_state.curriculum_service = CurriculumService(client, config)
    except Exception as e:
        st.error(f"Failed to initialize curriculum service: {e}")
        sys.stderr.write(f"Curriculum service error: {e}\n")
        sys.stderr.write(traceback.format_exc() + "\n")
        st.session_state.curriculum_service = None

# Initialize template manager
if "template_manager" not in st.session_state:
    try:
        from services.template_service import TemplateManager
        st.session_state.template_manager = TemplateManager()
    except ImportError:
        sys.stderr.write("Warning: template_service not available\n")
        st.session_state.template_manager = None
    except Exception as e:
        st.error(f"Failed to initialize template manager: {e}")
        st.session_state.template_manager = None

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
            temp_files = st.session_state.get('last_tmp_files', set())
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
        # Use get() with defaults to avoid KeyError
        current_answers = dict(st.session_state.get('quiz_answers', {}))
        current_feedback = dict(st.session_state.get('quiz_feedback', {}))
        
        # Compare answers
        if case_sensitive:
            is_correct = (user_answer == correct_answer)
        else:
            is_correct = (user_answer.strip().lower() == correct_answer.strip().lower())
        
        current_answers[q_key] = user_answer
        current_feedback[q_key] = is_correct
        
        # Atomic update - only update if both operations succeed
        st.session_state.quiz_answers = current_answers
        st.session_state.quiz_feedback = current_feedback
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

def create_pdf_link(html_content: str, filename: str) -> Optional[str]:
    """Generates a Streamlit download button link for a PDF created from HTML."""
    if not PDF_CAPABLE:
        return None
    
    try:
        # Create a temporary file for the PDF output
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()  # Close the file to allow pdfkit to write to it
        
        # Add the PDF to the list of temp files to be cleaned up
        st.session_state.last_tmp_files.add(temp_pdf.name)
        
        # Generate PDF with pdfkit
        try:
            pdfkit.from_string(
                html_content, 
                temp_pdf.name, 
                configuration=pdfkit_wkhtmltopdf_config,
                options={'quiet': ''}
            )
            
            # Get the PDF data for the download button
            with open(temp_pdf.name, "rb") as file:
                pdf_data = file.read()
            
            # Create a download button
            b64_pdf = base64.b64encode(pdf_data).decode('utf-8')
            href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{filename}" style="display: inline-block; padding: 0.5em 1em; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; cursor: pointer;">📥 Download PDF</a>'
            return href
            
        except Exception as e:
            sys.stderr.write(f"PDF generation error: {e}\n")
            return None
    
    except Exception as e:
        sys.stderr.write(f"Error creating PDF link: {e}\n")
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

# Advanced Settings Section  
with st.sidebar.expander("🤖 **AI Model Settings**", expanded=False):
    # Main model selection (for orchestration)
    text_model = st.selectbox(
        "Main AI Model (Orchestrator)", 
        options=config["defaults"].get("text_models", ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]), 
        index=config["defaults"].get("text_models", ["gpt-4.1"]).index(config["defaults"]["text_model"]) if config["defaults"]["text_model"] in config["defaults"].get("text_models", ["gpt-4.1"]) else 0, 
        help="gpt-4.1: Best but expensive (orchestration), gpt-4.1-mini: Medium (deeper analysis), gpt-4.1-nano: Most affordable (dev/testing)"
    )
    
    # Worker model selection (for content generation)
    worker_model = st.selectbox(
        "Worker AI Model (Content)", 
        options=config["defaults"].get("text_models", ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]), 
        index=config["defaults"].get("text_models", ["gpt-4.1"]).index(config["defaults"]["worker_model"]) if config["defaults"]["worker_model"] in config["defaults"].get("text_models", ["gpt-4.1"]) else 0, 
        help="Model for content generation. Use gpt-4.1-nano for development/testing to save costs."
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
    available_image_models = config["defaults"].get("image_models", ["gpt-imagegen-1", "dall-e-3", "dall-e-2"])
    
    # Debug - log available models to stderr
    sys.stderr.write(f"Available image models in config: {available_image_models}\n")
    
    # Image model selection with explicit options
    image_model = st.selectbox(
        "Image Model", 
        options=available_image_models,
        index=available_image_models.index(config["defaults"].get("image_model", "gpt-image-1")) 
              if config["defaults"].get("image_model", "gpt-image-1") in available_image_models else 0,
        help="Select the model for generating images: gpt-image-1 (your primary model), dall-e-3 (creative), or dall-e-2 (basic)"
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
    st.session_state.image_size = image_size
    
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

# Apply theme-specific styling (handled by design system)
# Mobile detection
is_mobile = st.session_state.get("is_mobile", False)

# Mobile banner disabled
# Always use desktop view for now to ensure proper sidebar behavior
st.session_state.is_mobile = False

# --- Main Area Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates"])

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
        ModernUI.card(
            title="🚀 Quick Start",
            content="""
            **Ready to create your curriculum?**
            
            1. ⚙️ Configure your settings in the sidebar
            2. 📋 Optionally choose a template below  
            3. ✨ Click Generate to create your curriculum
            
            Your settings: **{subject} • {grade} • {style}**
            """.format(subject=subject_str, grade=grade, style=lesson_style),
            icon="🎓"
        )
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
                st.session_state.active_tab = 1
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
                    st.session_state.selected_template_id = selected_template.id
                else:
                    st.session_state.selected_template_id = None
            else:
                st.info("No templates found for the selected subject and grade. You can create custom templates in the Templates tab.")
                st.session_state.selected_template_id = None
    
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
            st.session_state.generating = False
            progress_bar.empty()
            st.warning("Generation cancelled.")
            
    # Only show generate button if not already generating
    elif st.button("🚀 Generate New Curriculum", use_container_width=True, type="primary"):
        # --- Start Generation Process ---
        # Set generating flag to true
        st.session_state.generating = True
        
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
            st.session_state.generation_params = template_params.copy()
            st.session_state.generation_params.update({
                "text_model": text_model,
                "worker_model": worker_model,
                "image_model": image_model,
                "image_size": st.session_state.get("image_size", "1024x1024"),
            })
        else:
            # Use standard parameters
            st.session_state.generation_params = {
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
        
        # We'll clear temp files only if generation is successful
        # Store the current tmp files to clean up later
        current_tmp_files = set(st.session_state.get('last_tmp_files', set()))

        # Reset progress and show modern progress interface
        st.session_state.progress = 0.0
        
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
                st.session_state.generating = False
                st.stop()
        else:
            # Fallback validation
            if not subject_str:
                st.error("Validation error: Please select at least one subject")
                progress_bar.empty()
                st.session_state.generating = False
                st.stop()
            if len(subject_str) > 50:
                st.error("Validation error: Subject string is too long. Please reduce the number of subjects.")
                progress_bar.empty()
                st.session_state.generating = False
                st.stop()

        # Initialize curriculum structure in session state
        st.session_state.curriculum_id = uuid.uuid4().hex
        st.session_state.curriculum = {
            "meta": {
                "id": st.session_state.curriculum_id,
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
        }
        
        # Clear previous dynamic states
        st.session_state.edit_history = {}
        st.session_state.quiz_answers = {}
        st.session_state.quiz_feedback = {}
        st.session_state.edit_mode = False

        try:
            # Use the curriculum service to generate the curriculum
            with st.spinner("Generating curriculum..."):
                # Update progress as we go - Step 1: Planning
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
                    # Generate the curriculum using the service - Step 2: Content
                    StateManager.update_state('progress', 0.3)
                    with progress_container.container():
                        ModernUI.progress_steps(generation_steps, current_step=2)
                        progress_bar.progress(st.session_state.progress, text="Generating outline and content...")
                    
                    # Generate curriculum based on service availability
                    if st.session_state.curriculum_service:
                        # Wrap API call with error handler
                        curriculum = ErrorHandler.safe_api_call(
                            st.session_state.curriculum_service.generate_curriculum,
                            params
                        )
                    else:
                        # Fallback to direct orchestrator call
                        st.warning("Curriculum service not available, using direct generation...")
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
                        st.session_state.generating = False
                
                # Update progress - Step 4: Finalizing
                StateManager.update_state('progress', 0.9)
                with progress_container.container():
                    ModernUI.progress_steps(generation_steps, current_step=4)
                    progress_bar.progress(st.session_state.progress, text="Finalizing curriculum...")
                
                # Check if curriculum was generated successfully
                if curriculum is None:
                    st.error("Failed to generate curriculum. Please check your settings and try again.")
                    StateManager.update_state('generating', False)
                elif curriculum.get("meta", {}).get("cancelled", False):
                    # Display a message that generation was cancelled but show any partial results
                    st.warning("Generation was cancelled. Partial results may be available in the 'View & Edit' tab.")
                    # Still store what we have so far
                    StateManager.update_state('curriculum', curriculum)
                else:
                    # Store in session state
                    StateManager.update_state('curriculum', curriculum)
                    
                    # Generation complete - now clean up old temp files
                    cleanup_tmp_files(current_tmp_files)
                    st.session_state['last_tmp_files'] = set()
                    
                    # Update progress to complete - Step 5: Complete
                    with progress_container.container():
                        ModernUI.progress_steps(generation_steps, current_step=5)
                    st.session_state.progress = 1.0
                    progress_bar.progress(1.0, text="Curriculum generation complete!")
                    st.success("Curriculum generated successfully! View results in the 'View & Edit' tab.")
                    time.sleep(1.5)
                
                # Always clean up the progress interface
                progress_container.empty()
                
                # Reset generating flag
                st.session_state.generating = False
        
        except ValueError as e:
            # Handle validation errors specifically
            st.error(f"Validation error: {e}")
            sys.stderr.write(f"Validation error during curriculum generation: {e}\n")
            progress_container.empty()
            st.session_state.generating = False
        except Exception as e:
            # Handle all other errors
            st.error(f"Unexpected error during curriculum generation: {e}")
            sys.stderr.write(f"Curriculum generation error: {e}\n")
            sys.stderr.write(traceback.format_exc() + "\n")
            progress_container.empty()
            st.session_state.generating = False
            
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

        # Edit Mode Toggle
        edit_mode = st.checkbox("Enable Edit Mode", value=st.session_state.edit_mode, key="edit_mode_toggle")
        st.session_state.edit_mode = edit_mode
        if edit_mode:
            st.info("Edit Mode Enabled: Changes are saved automatically as you type or select options.")

        # Iterate through units
        for i, unit in enumerate(curriculum.get("units", [])):
            unit_key_base = f"unit_{i}" # Base key for widgets in this unit

            # Add an indicator for units without expected media
            unit_title = unit.get('title', f'Untitled')
            
            # Don't display any media warnings in the title
            with st.expander(f"Unit {i+1}: {unit_title}", expanded=(i==0)): # Expand first unit by default
                st.markdown(f"#### Unit {i+1}: {unit_title}")

                # --- Display/Edit Title ---
                if edit_mode:
                    # Use on_change callback for immediate update without rerun
                    def update_title():
                        new_value = st.session_state[f"{unit_key_base}_title"]
                        st.session_state.curriculum["units"][i]["title"] = new_value
                    
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
                                st.session_state.curriculum["units"][i]["selected_image_b64"] = new_selected_b64
                            
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
                         st.session_state.curriculum["units"][i]["content"] = new_content
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
                if chart_dict and isinstance(chart_dict, dict) and chart_dict.get("b64"):
                    suggestion = unit.get("chart_suggestion")
                    if suggestion and isinstance(suggestion, dict):
                        # Show only the title for the chart, not the suggestion text with chart type
                        chart_title = suggestion.get("title", "Chart")
                        # Display chart image using st.image
                        st.image(f"data:image/png;base64,{chart_dict['b64']}", caption=chart_title, width=320)
                    else:
                        # Fallback if no proper suggestion is available
                        st.image(f"data:image/png;base64,{chart_dict['b64']}", caption="Chart", width=320)
                else:
                    if media_richness >= 3:
                        st.markdown("_No chart was generated for this unit._")
                    # Don't show any message if charts aren't expected based on media richness

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
                                        st.session_state.quiz_answers[q_key] = selected
                                        st.session_state.quiz_feedback[q_key] = (selected == correct_answer)
                                    
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
                                        st.session_state.quiz_answers[q_key] = selected
                                        st.session_state.quiz_feedback[q_key] = (selected == correct_answer)
                                    
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
                                        
                                        st.session_state.quiz_answers[q_key] = answer_input
                                        st.session_state.quiz_feedback[q_key] = (user_answer == correct)
                                
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
                            st.session_state.curriculum["units"][i]["summary"] = new_summary
                    else:
                        st.markdown(unit.get("summary", "_No summary available._"))

                # --- Display/Edit Resources ---
                if include_resources:
                    st.markdown("##### Further Resources")
                    if edit_mode:
                        resources_key = f"{unit_key_base}_resources_edit"
                        new_resources = st.text_area("Edit Resources", value=unit.get("resources", ""), key=resources_key, height=100)
                        if new_resources != unit.get("resources", ""):
                            st.session_state.curriculum["units"][i]["resources"] = new_resources
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
                if not PDF_CAPABLE:
                    st.error("PDF export is not available. Please install wkhtmltopdf and pdfkit.")
                else:
                    html_content = generate_html(curriculum, include_images)
                    pdf_filename = f"{base_filename}.pdf"
                    
                    # Create PDF download link
                    pdf_link = create_pdf_link(html_content, pdf_filename)
                    if pdf_link:
                        st.markdown(pdf_link, unsafe_allow_html=True)
                        st.success("PDF generated successfully!")
                    else:
                        st.error("Failed to generate PDF. See console for details.")
        
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
                                st.session_state.selected_template_id = template.id
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

# Initialize agents when needed (done in the agentic_framework.py now)