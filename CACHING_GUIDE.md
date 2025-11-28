# Streamlit Caching Guide for InstaSchool

## Overview
This guide explains the caching implementation in InstaSchool and how to use cached functions properly.

## What Was Cached

### Configuration Loading
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_config(path="config.yaml") -> Dict[str, Any]:
    # Loads and parses YAML configuration
```

**Usage:**
```python
config = load_config()  # Automatically cached
```

### Service Singletons

All service wrappers use `@st.cache_resource` for persistent object caching:

```python
# OpenAI Client
client = get_openai_client(api_key, org_id=None)

# Curriculum Service
curriculum_service = get_curriculum_service()

# Batch Manager
batch_manager = get_batch_manager()

# Template Manager
template_manager = get_template_manager()

# Database Service (in services/database_service.py)
from services.database_service import get_database_service
db = get_database_service()
```

### Cost Calculations

```python
from src.cost_estimator import calculate_cost, estimate_curriculum_cost

# Both functions are cached with @st.cache_data
cost = calculate_cost("gpt-4.1-nano", input_tokens=1000, output_tokens=500)
estimate = estimate_curriculum_cost("gpt-4.1", "gpt-4.1-nano", num_units=4)
```

## When to Use Each Decorator

### Use `@st.cache_resource` for:
- Database connections
- API clients (OpenAI, etc.)
- Service instances
- Heavy objects that should persist across reruns
- Objects with internal state

**Example:**
```python
@st.cache_resource
def get_api_client():
    return SomeAPIClient()
```

### Use `@st.cache_data` for:
- Pure functions (same input = same output)
- Data transformations
- Calculations
- File parsing/loading
- Any function that returns serializable data

**Example:**
```python
@st.cache_data(ttl=300)  # Optional TTL in seconds
def process_data(input_data):
    return transform(input_data)
```

## Cache Management

### Clearing Cache Programmatically
```python
# Clear specific function cache
load_config.clear()

# Clear all caches
st.cache_data.clear()
st.cache_resource.clear()
```

### User-Initiated Cache Clear
Users can clear cache via Streamlit UI:
1. Click hamburger menu (top right)
2. Settings → Clear cache

## Best Practices

### ✅ DO:
- Cache expensive computations
- Cache service instantiations
- Use TTL for data that may change
- Cache API clients and database connections
- Document what's being cached

### ❌ DON'T:
- Cache functions with side effects
- Cache user-specific data without proper key management
- Over-cache (not everything needs caching)
- Cache without considering memory usage

## Non-Streamlit Context

All cached functions gracefully handle non-Streamlit contexts:

```python
# Works both in Streamlit and standalone scripts
from src.cost_estimator import calculate_cost

cost = calculate_cost("gpt-4.1", 1000, 500)
# Uses caching in Streamlit, regular function call otherwise
```

## Troubleshooting

### Cache Not Working?
1. Check if function is pure (same inputs → same outputs)
2. Verify Streamlit runtime is active
3. Check if cache was manually cleared
4. For `@st.cache_data`, ensure return value is serializable

### Memory Issues?
1. Add TTL to `@st.cache_data` decorators
2. Use `max_entries` parameter to limit cache size
3. Manually clear caches periodically

### Stale Data?
1. Reduce TTL for frequently changing data
2. Add cache clearing logic at appropriate points
3. Use cache invalidation when source data changes

## Implementation Details

### Pattern: Internal Implementation + Cached Wrapper

For maximum flexibility, some functions use this pattern:

```python
# Internal implementation (no caching)
def _calculate_impl(x, y):
    return x + y

# Cached wrapper (Streamlit)
if HAS_STREAMLIT:
    @st.cache_data
    def calculate(x, y):
        return _calculate_impl(x, y)
else:
    # Non-cached fallback
    def calculate(x, y):
        return _calculate_impl(x, y)
```

This allows:
- Caching in Streamlit contexts
- Normal execution in CLI/tests
- Consistent behavior across environments

## Performance Impact

Expected improvements:
- **Config loading**: ~50-100ms saved per rerun
- **Service initialization**: ~100-500ms saved per rerun
- **Cost calculations**: ~1-5ms saved per calculation
- **Overall**: Faster app responsiveness, especially on reruns

## Further Reading

- [Streamlit Caching Documentation](https://docs.streamlit.io/library/advanced-features/caching)
- [Cache Primitives](https://docs.streamlit.io/library/api-reference/performance)
