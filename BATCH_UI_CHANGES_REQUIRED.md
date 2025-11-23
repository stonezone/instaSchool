# Batch UI - Exact Changes Required for main.py

## Summary
Add batch generation UI with polling mechanism to main.py. The batch_service.py is already implemented with file-based status tracking.

## Change 1: Add BatchManager Initialization
**Location:** After line ~473 (after template_manager initialization)

```python
# Initialize batch manager
if "batch_manager" not in st.session_state:
    try:
        from services.batch_service import BatchManager
        st.session_state.batch_manager = BatchManager(max_concurrent=2)
    except ImportError:
        sys.stderr.write("Warning: batch_service not available\n")
        st.session_state.batch_manager = None
    except Exception as e:
        st.error(f"Failed to initialize batch manager: {e}")
        st.session_state.batch_manager = None

# Initialize batch polling state
if "active_batch_id" not in st.session_state:
    st.session_state.active_batch_id = None
if "batch_polling" not in st.session_state:
    st.session_state.batch_polling = False
```

## Change 2: Modify Tab Creation
**Location:** Line ~721

**FIND:**
```python
tab1, tab2, tab3, tab4 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates"])
```

**REPLACE WITH:**
```python
tab1, tab2, tab3, tab4, tab5 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates", "🔄 Batch"])
```

## Change 3: Add Batch Tab Implementation
**Location:** After the `with tab4:` block ends (find the Templates tab code)

**ADD:** Complete tab5 implementation (see batch_ui_implementation.py lines 42-238)

The full implementation includes:
1. Create Batch sub-tab (from template or custom)
2. Active Batches sub-tab with polling mechanism
3. Batch History sub-tab

### Polling Loop Pattern (Core Implementation)
```python
# In Active Batches tab
if st.session_state.batch_polling:
    progress_container = st.empty()
    poll_interval = 1.5

    while st.session_state.batch_polling:
        # Read from file (thread-safe)
        updated_batch = st.session_state.batch_manager.get_batch_status(batch.id)

        with progress_container.container():
            # Display job progress
            for job in updated_batch.jobs:
                status_icon = {
                    "pending": "⏳", "running": "🔄",
                    "completed": "✅", "failed": "❌"
                }.get(job.status.value, "❓")
                st.markdown(f"{status_icon} {job.name} - {job.status.value}")
                if job.progress > 0:
                    st.progress(job.progress)

        # Check completion
        if updated_batch.status.value in ["completed", "failed", "cancelled"]:
            st.session_state.batch_polling = False
            st.success(f"Batch {updated_batch.status.value}!")
            st.rerun()

        time.sleep(poll_interval)
```

## Implementation Steps

1. **Backup main.py**
   ```bash
   cp main.py main.py.backup
   ```

2. **Add BatchManager initialization** (Change 1)
   - Find line ~473 (after template_manager)
   - Insert BatchManager init code

3. **Update tab creation** (Change 2)
   - Find line ~721
   - Replace tab line to add tab5

4. **Add batch tab UI** (Change 3)
   - Copy full implementation from batch_ui_implementation.py
   - Paste after tab4 block
   - Ensure proper indentation

5. **Test**
   ```bash
   streamlit run main.py
   ```

6. **Verify**
   - Batch tab appears
   - BatchManager initializes
   - Can create batch from template
   - Polling updates progress
   - Stop button works
   - Batch completion handled

## Key Features of Polling Implementation

### Thread Safety
- ✅ Worker threads write to JSON files
- ✅ UI thread reads from JSON files
- ❌ NO st.session_state writes from threads
- ❌ NO Streamlit calls from threads

### Progress Display
- Real-time job status updates
- Progress bars for each job
- Batch-level statistics
- Status icons for visual feedback

### User Controls
- Start batch button
- Monitor progress button
- Stop monitoring button
- Cancel batch button
- Delete batch button

### Error Handling
- Try-except around all batch operations
- User-friendly error messages
- Fallback when batch_manager unavailable
- Logging to stderr for debugging

## Testing Scenarios

1. **Small batch (2 jobs)**
   - Create batch
   - Monitor progress
   - Verify updates
   - Check completion

2. **Stop monitoring**
   - Start monitoring
   - Click stop button
   - Verify polling stops

3. **Error handling**
   - Test with invalid template
   - Test with no jobs
   - Verify error messages

4. **Multiple batches**
   - Create 2 batches
   - Monitor different batches
   - Verify isolation

## Troubleshooting

### Issue: Polling not updating
- Check batch_status directory exists
- Verify JSON files are being created
- Check poll_interval value
- Ensure batch_polling is True

### Issue: Thread violations
- Verify no st.session_state writes in worker threads
- Check no Streamlit calls in generator_func
- Ensure using get_batch_status() for reads

### Issue: UI freezing
- Check poll_interval (should be 1-2 seconds)
- Verify time.sleep() is present
- Ensure stop button cancels loop

### Issue: Batches not starting
- Check BatchManager initialization
- Verify generator_func is defined
- Check batch_service imports

## Files Modified
- `main.py` - Added batch UI with polling
- No changes to `batch_service.py` (already correct)

## Files Created
- `batch_status/*.json` - Auto-created by batch_service
- `batches/*.json` - Auto-created by batch_manager

## Dependencies
- No new dependencies required
- Uses existing services (batch_service, template_service)
- Compatible with current Streamlit version
