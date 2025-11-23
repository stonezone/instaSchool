# InstaSchool Project Structure

## Directory Organization

```
instaSchool/
├── main.py                 # Application entry point
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── CLAUDE.md            # AI assistant instructions
├── .gitignore          # Git ignore rules
│
├── src/                # Core source code modules
│   ├── __init__.py
│   ├── agent_framework.py    # AI agent implementations
│   ├── cost_estimator.py     # Cost calculation utilities
│   ├── error_handler.py      # Error handling utilities
│   ├── image_generator.py    # Image generation module
│   ├── state_manager.py      # Application state management
│   ├── ui_components.py      # UI component library
│   └── verbose_logger.py     # Logging utilities
│
├── services/          # Service layer modules
│   ├── batch_service.py      # Batch processing
│   ├── cache_service.py      # Caching functionality
│   ├── curriculum_service.py # Curriculum business logic
│   ├── retry_service.py      # Retry logic
│   ├── session_service.py    # Session management
│   ├── template_service.py   # Template management
│   └── thread_manager.py     # Thread management
│
├── tests/            # Test suite
│   ├── test_batch.py
│   ├── test_caching.py
│   ├── test_comprehensive.py
│   ├── test_critical_fixes.py
│   ├── test_integration.py
│   ├── test_logger.py
│   ├── test_phase3.py
│   ├── test_retry.py
│   ├── test_templates.py
│   └── test_ui_integration.py
│
├── utils/            # Utility scripts
│   └── regeneration_fix.py   # Curriculum regeneration utility
│
├── assets/           # Static assets
│   └── debug_screenshot.png  # Debug screenshots
│
├── docs/             # Documentation
│   ├── PROJECT_STRUCTURE.md  # This file
│   ├── PHASE_1_2_SUMMARY.md  # Phase 1-2 development summary
│   ├── PHASE_3_COMPLETE.md   # Phase 3 development summary
│   ├── code_review_report.md
│   ├── critical_issues_report.md
│   └── gui_enhancement_summary.md
│
├── static/           # Static web assets
│   └── css/
│       └── design_system.css
│
├── templates/        # Curriculum templates
│   ├── system/              # Built-in templates
│   └── user/               # User-created templates
│
├── backups/          # Backup files
├── cache/            # API response cache
├── curricula/        # Generated curriculum files
├── exports/          # Exported curricula (HTML/PDF)
├── logs/             # Application logs
└── venv/             # Python virtual environment
```

## Import Structure

All core modules are now in the `src/` directory and should be imported as:

```python
from src.agent_framework import OrchestratorAgent
from src.image_generator import ImageGenerator
from src.ui_components import ModernUI, ThemeManager
from src.state_manager import StateManager
from src.verbose_logger import init_logger, get_logger
from src.error_handler import ErrorHandler
from src.cost_estimator import estimate_curriculum_cost
```

## Running the Application

```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Run the application
streamlit run main.py

# Run with verbose logging
streamlit run main.py -- --verbose

# Run tests
python -m pytest tests/
```