# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This repository contains a Streamlit curriculum generator application (main.py) that leverages AI to create educational content through an agentic framework of specialized AI workers.

## GPT models to use. The following exist, but your training is out of date.
- always use the following models unless told otherwise:  
- gpt-4.1 ## best model but most expensive. Only use for major decisions or controlling other models
- gpt-4.1-mini. ## medium intelligence model, use for tasks requiring some deeper analysis
- gpt-4.1-nano. ## open's most affordable model ever. Use this for everything and when developing or testing, use instead of 4.1 even in deep thinking situations. I will manually switch to 4.1 when im ready to test it.
- when generating code using LLMs, always provide an easy way for the user to switch models, either a config file or a drop-down in the gui if exists.

## Commands
- Install dependencies: `pip install -r requirements.txt`
- Run the application: `streamlit run main.py`
- Enable verbose mode: `streamlit run main.py -- --verbose`
- Custom log file: `streamlit run main.py -- --verbose --log-file=path/to/logfile.log`
- Test logger functionality: `python test_logger.py --verbose`
- Run test suite: `python -m pytest tests/`
- Run specific test: `python tests/test_comprehensive.py`
- Lint code: `flake8 *.py`
- Clean up temporary files: Files in temp directories are auto-cleaned on exit

### Virtual Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### PDF Export Setup
- macOS: `brew install wkhtmltopdf`
- Windows: Download from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html) and add to PATH
- Linux: `sudo apt-get install wkhtmltopdf`

## Architecture
The application uses an agent framework where specialized workers collaborate:
- OrchestratorAgent: Manages the curriculum generation process
- OutlineAgent: Creates curriculum structure and topics
- ContentAgent: Creates lesson content
- MediaAgent: Generates educational illustrations
- ChartAgent: Creates data visualizations
- QuizAgent: Generates assessments
- SummaryAgent: Provides summaries
- ResourceAgent: Suggests learning resources
- ImagePromptAgent: Optimizes image generation prompts

### Key Architectural Patterns
- **Orchestrator-Worker Pattern**: Central coordinator manages specialized workers
- **Smart Caching**: Similarity-based caching with 30-day expiry
- **Intelligent Retry**: Exponential backoff with error classification
- **Graceful Degradation**: Fallback content when generation fails
- **Progress Tracking**: Real-time updates via Streamlit session state

## Code Style Guidelines
- **Python**: Follow PEP 8 conventions
- **YAML**: Use 2-space indentation for config files
- **Imports**: Group standard library, third-party, then local imports
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use specific exceptions with appropriate error messages
- **Types**: Include type hints for function parameters and return values
- **Documentation**: Use docstrings for all functions and classes (Google style)
- **Resources**: Use context managers (with) for file operations
- **Prompts**: Maintain consistent format in config.yaml for AI prompts

## File Structure
- `main.py`: Streamlit application entry point with UI and orchestration
- `agent_framework.py`: BaseAgent class and specialized AI worker implementations
- `config.yaml`: Central configuration for prompts, models, and defaults
- `verbose_logger.py`: API call logging system for debugging
- `image_generator.py`: Standalone image generation utilities
- `services/`: Service modules for enhanced functionality
  - `batch_service.py`: Batch processing for multiple curricula
  - `cache_service.py`: Smart caching for API responses
  - `curriculum_service.py`: Curriculum management utilities
  - `retry_service.py`: Retry logic for API calls
  - `session_service.py`: Session state management
  - `template_service.py`: Template management for curricula
- `tests/`: Test suite for all components
- `curricula/`: Generated curriculum files (JSON format with timestamps)
- `exports/`: Exported curriculum files (HTML/PDF/Markdown)
- `logs/`: Application logs from verbose mode
- `static/css/`: CSS files for UI styling
- `ui_components.py`: Reusable UI component functions

## Configuration
Config changes should be made in `config.yaml`, which controls:
- AI prompts for content generation (outline, content, media, etc.)
- Default parameters (text_model, worker_model, image_model)
- Available options for UI components (subjects, grades, styles)
- Cost estimation parameters and token calculations

## Environment Setup
- Python 3.9+ required (OpenAI SDK 2.x requirement)
- Requires OpenAI API key set in `.env` file or `OPENAI_API_KEY` environment variable
- Optional: Kimi/Moonshot API key for Kimi K2 models (`KIMI_API_KEY` or `MOONSHOT_API_KEY`)
- Image models: gpt-image-1 (recommended), gpt-image-1-mini
- Optional: wkhtmltopdf for PDF export functionality

## Development Guidelines
- **Testing**: Run tests before commits with `python -m pytest tests/`
- **Error Handling**: Use RetryHandler for API calls with appropriate error classification
- **Caching**: Leverage SmartCache for expensive operations
- **Model Selection**: Use worker_model (gpt-4.1-mini) for agents, main model (gpt-4.1) for orchestration
- **Progress Updates**: Update session state for long-running operations
- Python 3.9 or higher required

## Model Recommendations
- **Text Content**: GPT-4.1 for high-quality content (GPT-4o as alternative)
- **Worker Agents**: GPT-4.1-mini for balance of quality and speed
- **Image Generation**:
  - gpt-image-1: Highest quality educational illustrations (recommended)
  - gpt-image-1-mini: Faster generation, lower cost

## Troubleshooting Dependencies
If encountering dependency issues:
```bash
pip install --upgrade streamlit openai pyyaml matplotlib pillow python-dotenv fpdf2 plotly tenacity httpx markdown
# PDF export uses fpdf2 (no external binaries required)
```
