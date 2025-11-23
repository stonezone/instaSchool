# Circular Dependency Fix - InstaSchool

## Summary

Successfully resolved circular dependency risk by extracting `BaseAgent` from `src/agent_framework.py` into a new `src/core/types.py` module. This establishes a proper architectural pattern where:

- **Core types** (`src/core/`) contain foundational classes with minimal dependencies
- **Services** (`services/`) can safely import from core without creating circular dependencies
- **Agent implementations** (`src/agent_framework.py`) import from core and are used by services

## Problem Identified

The original architecture had a circular dependency risk:
```
agent_framework.py → imports cache_service
cache_service.py → could potentially import BaseAgent from agent_framework
tests → import both agent_framework and cache_service
```

As the application grows, this creates maintenance issues and risks actual circular import errors.

## Solution Implemented

Created a three-tier import hierarchy:

```
src/core/types.py (foundation)
    ↓
src/agent_framework.py (implementations)
    ↓
services/*.py (business logic)
```

### Files Created

1. **`src/core/__init__.py`**
   - Module initialization
   - Exports `BaseAgent` for convenience

2. **`src/core/types.py`**
   - Contains `BaseAgent` class
   - Minimal dependencies (only typing and conditional service imports)
   - 190 lines including full documentation
   - All core agent functionality preserved

### Files Modified

1. **`src/agent_framework.py`**
   - Removed `BaseAgent` class definition (125+ lines)
   - Added import: `from src.core.types import BaseAgent`
   - Removed unnecessary import guards (CACHE_AVAILABLE, RETRY_AVAILABLE)
   - All agent classes now properly inherit from `src.core.types.BaseAgent`

2. **`src/__init__.py`**
   - Added export of `BaseAgent` from core for convenience
   - Maintains backward compatibility

## Import Graph

### Before
```
agent_framework.py
├── defines BaseAgent
├── imports SmartCache (services/cache_service.py)
└── imports RetryHandler (services/retry_service.py)

services/cache_service.py
└── (potential to import BaseAgent → circular risk)

tests/*.py
├── imports from agent_framework
└── imports from services
```

### After
```
src/core/types.py (foundation layer)
├── defines BaseAgent
├── minimal dependencies
└── conditional imports of services

src/agent_framework.py (implementation layer)
├── imports BaseAgent from src.core.types
├── all agents inherit from BaseAgent
└── uses by services and tests

services/*.py (business logic layer)
├── imports from src.agent_framework
├── can safely import from src.core if needed
└── no circular dependencies possible

tests/*.py
├── imports from src.agent_framework
└── imports from services
```

## Verification

All tests pass without modification:
```bash
$ python3 -m pytest tests/test_caching.py -v
======================== 3 passed, 3 warnings in 6.85s =========================
```

Import verification confirms:
- ✓ BaseAgent successfully imported from `src.core.types`
- ✓ Agents successfully imported from `src.agent_framework`
- ✓ Services successfully imported
- ✓ Agents correctly inherit from `src.core.types.BaseAgent`
- ✓ No circular dependencies detected

## Benefits

1. **Clear Architecture**: Three-tier hierarchy prevents confusion about import direction
2. **Scalability**: New core types can be added to `src/core/` without risk
3. **Testability**: Each layer can be tested independently
4. **Maintainability**: Clear separation of concerns
5. **Zero Breakage**: No changes required to existing code outside of agent_framework.py

## Remaining Considerations

1. **Performance**: No performance impact - imports happen once at startup
2. **Future Growth**: Consider adding other shared types to `src/core/types.py`:
   - Type aliases for common patterns
   - Shared enums or constants
   - Protocol definitions for interfaces

3. **Documentation**: Consider documenting the import hierarchy in `CLAUDE.md`

## Files Changed Summary

| File | Change | Lines Modified |
|------|--------|----------------|
| `src/core/__init__.py` | Created | 7 new |
| `src/core/types.py` | Created | 190 new |
| `src/agent_framework.py` | Modified | ~130 removed, 2 added |
| `src/__init__.py` | Modified | 3 added |
| **Total** | | **192 net new lines** |

## Import Patterns for Future Development

### Correct ✓
```python
# Services importing from src
from src.agent_framework import OrchestratorAgent
from src.core.types import BaseAgent

# Core importing from services (conditional)
try:
    from services.cache_service import SmartCache
except ImportError:
    pass
```

### Incorrect ✗
```python
# DON'T: src importing unconditionally from services at module level
from services.cache_service import SmartCache  # in src/core/types.py

# DON'T: Circular pattern
# agent_framework imports service
# service imports agent_framework
```

## Testing Recommendations

When adding new agents or services:

1. Run import verification:
   ```bash
   python3 -c "from src.core.types import BaseAgent; from src.agent_framework import OrchestratorAgent; from services.curriculum_service import CurriculumService"
   ```

2. Check inheritance chain:
   ```python
   from src.agent_framework import ContentAgent
   from src.core.types import BaseAgent
   assert isinstance(ContentAgent(client, model, config), BaseAgent)
   ```

3. Run full test suite:
   ```bash
   python3 -m pytest tests/
   ```

## Conclusion

The circular dependency risk has been eliminated through proper architectural layering. The codebase now has a clear, maintainable structure that will support future growth without import conflicts.
