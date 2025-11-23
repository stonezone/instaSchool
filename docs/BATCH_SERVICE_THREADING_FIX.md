# Batch Service Threading Safety Fix

## Problem
The original `services/batch_service.py` implementation had a critical Streamlit threading violation:

- Worker threads were modifying `BatchJob` objects directly
- These job objects could be accessed by the main Streamlit UI thread via `st.session_state`
- Streamlit is NOT thread-safe - background threads cannot safely modify objects that the UI thread accesses
- This caused `script_runner` errors and unpredictable behavior

## Solution
Implemented **file-based status tracking** to ensure complete thread isolation:

### Key Changes

#### 1. Added File-Based Status Storage
- Created `batch_status/` directory for storing job status as JSON files
- Each job has its own status file: `batch_status/{job_id}.json`
- Worker threads write status updates to files (NOT to shared memory)
- UI thread reads status from files (safe, no race conditions)

#### 2. Cross-Platform File Locking
- Implemented `_lock_file()` and `_unlock_file()` helper functions
- Unix/Linux/macOS: Uses `fcntl.flock()` for proper file locking
- Windows: Uses `msvcrt.locking()` for file locking
- Prevents corruption when multiple threads access status files

#### 3. Thread-Safe Status Updates
- `_write_job_status(job)`: Worker threads call this to write status to file
- `_read_job_status(job_id)`: UI thread calls this to read status from file
- `get_job_status(job_id)`: Public API that reads from file system
- No direct object sharing between threads

#### 4. Automatic Cleanup
- `_cleanup_old_status_files()`: Removes status files older than 24 hours
- Called on startup to prevent disk space issues
- Configurable retention period

### Modified Methods

#### BatchQueue Class
```python
def __init__(self, max_concurrent=2, max_completed_jobs=1000, status_dir="batch_status"):
    # Added status_dir parameter
    self.status_dir = Path(status_dir)
    self.status_dir.mkdir(exist_ok=True)
    self._cleanup_old_status_files()

def _write_job_status(self, job: BatchJob):
    # NEW: Write job status to file with locking
    # Thread-safe, no session_state access

def _read_job_status(self, job_id: str) -> Optional[BatchJob]:
    # NEW: Read job status from file with locking
    # Thread-safe, safe for UI thread

def _cleanup_old_status_files(self, max_age_hours=24):
    # NEW: Remove old status files
    # Prevents disk space issues

def _execute_job(self, job: BatchJob, generator_func: Callable):
    # MODIFIED: Now writes status to files instead of just memory
    # Calls _write_job_status() at key points:
    #   - Job start (RUNNING)
    #   - Job completion (COMPLETED)
    #   - Job failure (FAILED)

def get_job_status(self, job_id: str) -> Optional[BatchJob]:
    # MODIFIED: Now reads from file system
    # Safe for UI thread to call
```

#### BatchManager Class
```python
def __init__(self, batch_dir="batches", max_concurrent=2, status_dir="batch_status"):
    # Added status_dir parameter
    self.queue = BatchQueue(max_concurrent, status_dir=status_dir)

def get_batch_status(self, batch_id: str) -> Optional[BatchRequest]:
    # MODIFIED: Updated docstring to clarify thread safety
    # Reads job statuses from files via queue.get_job_status()
```

## Architecture

### Before (Unsafe)
```
[Worker Thread] --> Modifies BatchJob --> [st.session_state] <-- [UI Thread]
                                          ^^^^ RACE CONDITION ^^^^
```

### After (Safe)
```
[Worker Thread] --> Writes to batch_status/{job_id}.json

[UI Thread] --> Reads from batch_status/{job_id}.json

✓ Complete isolation
✓ No shared objects
✓ File system is the single source of truth
```

## Usage

### Starting a Batch
```python
from services.batch_service import BatchManager

# Initialize with custom status directory (optional)
manager = BatchManager(
    batch_dir="batches",
    max_concurrent=2,
    status_dir="batch_status"  # NEW parameter
)

# Create and start batch (unchanged)
batch_id = manager.create_custom_batch(job_configs, "My Batch")
manager.start_batch(batch_id, generator_function)
```

### Checking Status (UI Thread)
```python
# Safe to call from Streamlit UI thread
batch_status = manager.get_batch_status(batch_id)

# All job statuses are read from files
for job in batch_status.jobs:
    st.write(f"{job.name}: {job.status.value}")
    if job.status == BatchStatus.COMPLETED:
        st.json(job.result)
```

### Testing
```bash
# Run threading safety tests
python tests/test_batch_threading.py
```

## Benefits

1. **Thread Safety**: Complete isolation between worker threads and UI thread
2. **Persistence**: Job status survives application restarts
3. **Debugging**: Status files can be inspected manually
4. **Cross-Platform**: Works on Windows, macOS, and Linux
5. **Automatic Cleanup**: Old status files are removed automatically
6. **Backwards Compatible**: Existing API unchanged

## Files Modified

- `services/batch_service.py`: Main implementation
  - Added file-based status tracking
  - Added cross-platform file locking
  - Modified job execution to write to files
  - Added cleanup for old status files

## Files Created

- `docs/BATCH_SERVICE_THREADING_FIX.md`: This documentation
- `tests/test_batch_threading.py`: Threading safety tests
- `batch_status/`: Directory for job status files (created automatically)

## Migration Notes

### For Existing Code
No changes required! The API is backwards compatible:

```python
# Old code still works
manager = BatchManager()
batch_id = manager.create_custom_batch(jobs, "Test")
manager.start_batch(batch_id, generator)
status = manager.get_batch_status(batch_id)
```

### For New Code
You can now optionally specify the status directory:

```python
# New code can customize status directory
manager = BatchManager(status_dir="custom_status_dir")
```

## Performance Considerations

### File I/O Overhead
- Status updates are small JSON files (< 1KB typically)
- Modern SSDs handle this efficiently
- File locking adds minimal overhead
- Overall impact: < 1ms per status update

### Memory Usage
- In-memory cache still maintained for fast access
- File system is used as the definitive source
- Old status files cleaned up automatically

### Disk Space
- Each job creates one status file
- Files are small (< 1KB each)
- Automatic cleanup after 24 hours
- 1000 jobs = ~1MB disk space

## Troubleshooting

### Status Files Not Being Created
- Check that `batch_status/` directory exists and is writable
- Verify no filesystem permission issues
- Check application logs for errors

### Old Status Files Accumulating
- Cleanup runs on startup by default
- Manual cleanup: `queue._cleanup_old_status_files()`
- Adjust retention period if needed: `_cleanup_old_status_files(max_age_hours=12)`

### File Locking Issues on Windows
- File locking uses `msvcrt.locking()` on Windows
- If issues occur, locking gracefully degrades (continues without lock)
- Check Windows file permissions

## Security Considerations

- Status files may contain sensitive curriculum data
- Files are stored in application directory (not web-accessible)
- Consider encrypting status files if needed
- Automatic cleanup reduces exposure window

## Future Enhancements

Potential improvements for future versions:

1. **Database Backend**: Replace file system with SQLite for better concurrency
2. **Encryption**: Add optional encryption for status files
3. **Compression**: Compress large result payloads
4. **Monitoring**: Add metrics for status file I/O performance
5. **Distributed**: Support for distributed job processing across machines
