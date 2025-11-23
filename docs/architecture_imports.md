# InstaSchool Import Architecture

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  main.py    │  │ UI Components│  │  Batch Service   │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │              │
└─────────┼─────────────────┼────────────────────┼──────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     Services Layer                           │
│  ┌──────────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ CurriculumService│  │ CacheService  │  │RetryService │  │
│  └────────┬─────────┘  └───────┬───────┘  └──────┬──────┘  │
│           │                     │                  │         │
└───────────┼─────────────────────┼──────────────────┼─────────┘
            │                     │                  │
            ▼                     │                  │
┌─────────────────────────────────┼──────────────────┼─────────┐
│               Implementation Layer                 │         │
│  ┌───────────────────────────────▼──────────────────▼──────┐ │
│  │            src/agent_framework.py                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │Orchestrator  │  │ ContentAgent │  │ MediaAgent  │  │ │
│  │  │    Agent     │  │              │  │             │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  │           (All inherit from BaseAgent)                 │ │
│  └──────────────────────────┬──────────────────────────────┘ │
│                             │                                │
└─────────────────────────────┼────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Foundation Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              src/core/types.py                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │             BaseAgent                          │  │   │
│  │  │  - _call_model()                              │  │   │
│  │  │  - _call_model_cached()                       │  │   │
│  │  │  - Caching support                            │  │   │
│  │  │  - Retry logic                                │  │   │
│  │  │  - Logging support                            │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Import Rules by Layer

### Foundation Layer (`src/core/`)
**CAN import from:**
- Standard library only
- Conditional imports from services (for optional features)

**CANNOT import from:**
- Application layer
- Services layer (unconditionally)
- Implementation layer

**Example:**
```python
# ✓ GOOD
from typing import Dict, Any
try:
    from services.cache_service import SmartCache  # Conditional OK
except ImportError:
    pass

# ✗ BAD
from src.agent_framework import ContentAgent
from services.cache_service import SmartCache  # Unconditional import
```

### Implementation Layer (`src/agent_framework.py`)
**CAN import from:**
- Foundation layer (`src/core/`)
- Standard library
- Services layer (conditional)

**CANNOT import from:**
- Application layer

**Example:**
```python
# ✓ GOOD
from src.core.types import BaseAgent
from typing import List, Dict

# ✓ ACCEPTABLE (conditional)
try:
    from services.retry_service import RetryHandler
except ImportError:
    pass

# ✗ BAD
from services.curriculum_service import CurriculumService  # Unnecessary
```

### Services Layer (`services/`)
**CAN import from:**
- Foundation layer (`src/core/`)
- Implementation layer (`src/agent_framework.py`)
- Other services
- Standard library

**CANNOT import from:**
- Application layer

**Example:**
```python
# ✓ GOOD
from src.agent_framework import OrchestratorAgent
from src.core.types import BaseAgent
from services.cache_service import SmartCache

# ✗ BAD
from main import some_function  # Never import from main
```

### Application Layer (`main.py`, UI components)
**CAN import from:**
- All other layers
- Services
- Implementation
- Foundation

**Example:**
```python
# ✓ GOOD - Can import from anywhere
from src.agent_framework import OrchestratorAgent
from services.curriculum_service import CurriculumService
from src.core.types import BaseAgent
```

## Dependency Flow

```
Application Layer
    ↓ (uses)
Services Layer
    ↓ (uses)
Implementation Layer
    ↓ (inherits/uses)
Foundation Layer
```

**Key Principle:** Dependencies flow downward only. Lower layers never depend on upper layers.

## Benefits of This Architecture

1. **No Circular Dependencies**: Impossible by design
2. **Clear Separation**: Each layer has a specific purpose
3. **Easy Testing**: Each layer can be tested independently
4. **Scalable**: New features fit naturally into existing structure
5. **Maintainable**: Clear rules about where code belongs

## Adding New Code

### New Agent Class
**Location:** `src/agent_framework.py`
```python
from src.core.types import BaseAgent

class MyNewAgent(BaseAgent):
    def __init__(self, client, model, config):
        super().__init__(client, model)
        # Your code here
```

### New Service
**Location:** `services/my_service.py`
```python
from src.agent_framework import OrchestratorAgent
from src.core.types import BaseAgent  # If needed

class MyService:
    def __init__(self, agent: OrchestratorAgent):
        # Your code here
```

### New Core Type
**Location:** `src/core/types.py`
```python
class MyBaseType:
    """Minimal dependencies only"""
    pass
```

### New UI Component
**Location:** `src/ui_components.py` or `main.py`
```python
from services.curriculum_service import CurriculumService
from src.agent_framework import ContentAgent

# Can import from anywhere
```

## Testing the Architecture

Verify no circular dependencies:
```bash
python3 -c "
from src.core.types import BaseAgent
from src.agent_framework import OrchestratorAgent
from services.curriculum_service import CurriculumService
print('✓ No circular dependencies')
"
```

Run full test suite:
```bash
python3 -m pytest tests/ -v
```
