"""
Content Caching Service
Intelligent caching to reduce API costs by avoiding regeneration of identical content
"""

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Import file locking utilities
try:
    import fcntl
    FILE_LOCKING_AVAILABLE = True
except ImportError:
    FILE_LOCKING_AVAILABLE = False
    print("Warning: fcntl not available, file locking disabled on this platform")


class ContentCache:
    """Handles caching of generated content to reduce API costs"""
    
    def __init__(self, cache_dir: str = "cache", max_age_days: int = 30):
        """Initialize cache with directory and maximum age
        
        Args:
            cache_dir: Directory to store cache files
            max_age_days: Maximum age of cached content in days
        """
        self.cache_dir = Path(cache_dir)
        self.max_age_days = max_age_days
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different content types
        (self.cache_dir / "content").mkdir(exist_ok=True)
        (self.cache_dir / "images").mkdir(exist_ok=True)
        (self.cache_dir / "charts").mkdir(exist_ok=True)
        (self.cache_dir / "quizzes").mkdir(exist_ok=True)
        (self.cache_dir / "summaries").mkdir(exist_ok=True)
        (self.cache_dir / "resources").mkdir(exist_ok=True)
        (self.cache_dir / "outlines").mkdir(exist_ok=True)
        
    def _generate_cache_key(self, content_type: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key based on content type and parameters
        
        Args:
            content_type: Type of content (content, image, chart, etc.)
            params: Parameters used for generation
            
        Returns:
            Unique cache key string
        """
        # Create a stable string representation of parameters with safe serialization
        try:
            param_str = self._safe_json_dumps(params)
        except (TypeError, ValueError) as e:
            # Fallback to string representation for non-serializable objects
            param_str = str(sorted(params.items()))
            print(f"Warning: Using fallback serialization for cache key: {e}")
        
        # Generate hash
        hash_obj = hashlib.md5(f"{content_type}_{param_str}".encode())
        return hash_obj.hexdigest()
        
    def _safe_json_dumps(self, obj: Any) -> str:
        """Safely serialize object to JSON string
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON string representation
        """
        def json_serializer(obj):
            """Custom JSON serializer for non-standard types"""
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif callable(obj):
                return f"<function:{getattr(obj, '__name__', 'anonymous')}>"
            elif hasattr(obj, '__class__'):
                return f"<{obj.__class__.__name__}:{str(obj)}>"
            else:
                return str(obj)
        
        return json.dumps(obj, sort_keys=True, default=json_serializer)
        
    def _get_cache_file_path(self, content_type: str, cache_key: str) -> Path:
        """Get the full path for a cache file
        
        Args:
            content_type: Type of content
            cache_key: Unique cache key
            
        Returns:
            Path to cache file
        """
        return self.cache_dir / content_type / f"{cache_key}.json"
        
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file is still valid (not expired)
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            True if cache is valid, False if expired
        """
        if not cache_file.exists():
            return False
            
        # Check file age
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(days=self.max_age_days)
        
        return file_time > expiry_time
    
    def _safe_touch_file(self, cache_file: Path) -> None:
        """Safely update file access time
        
        Args:
            cache_file: Path to cache file
        """
        try:
            cache_file.touch()
        except (OSError, PermissionError):
            # Ignore if we can't update access time
            pass
        
    def get_cached_content(self, content_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached content if available and valid
        
        Args:
            content_type: Type of content to retrieve
            params: Parameters used for generation
            
        Returns:
            Cached content if available, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(content_type, params)
            cache_file = self._get_cache_file_path(content_type, cache_key)
            
            if not self._is_cache_valid(cache_file):
                return None
                
            # Use file locking to prevent race conditions
            with open(cache_file, 'r', encoding='utf-8') as f:
                if FILE_LOCKING_AVAILABLE:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                        cached_data = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
                else:
                    cached_data = json.load(f)
                
            # Update access time safely
            self._safe_touch_file(cache_file)
            
            print(f"Cache hit for {content_type}: {cache_key[:8]}...")
            return cached_data.get('content')
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Cache data corruption for {content_type}: {e}")
            return None
        except Exception as e:
            print(f"Error reading cache for {content_type}: {e}")
            return None
            
    def cache_content(self, content_type: str, params: Dict[str, Any], content: Any) -> bool:
        """Cache generated content
        
        Args:
            content_type: Type of content being cached
            params: Parameters used for generation
            content: The generated content to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(content_type, params)
            cache_file = self._get_cache_file_path(content_type, cache_key)
            
            cache_data = {
                'content': content,
                'params': params,
                'created_at': datetime.now().isoformat(),
                'content_type': content_type,
                'cache_key': cache_key
            }
            
            # Use file locking for writing to prevent race conditions
            with open(cache_file, 'w', encoding='utf-8') as f:
                if FILE_LOCKING_AVAILABLE:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                        json.dump(cache_data, f, indent=2, default=str)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
                else:
                    json.dump(cache_data, f, indent=2, default=str)
                
            print(f"Cached {content_type}: {cache_key[:8]}...")
            return True
            
        except Exception as e:
            print(f"Error caching {content_type}: {e}")
            return False
            
    def clear_cache(self, content_type: Optional[str] = None) -> int:
        """Clear cached content
        
        Args:
            content_type: Specific content type to clear, or None for all
            
        Returns:
            Number of files cleared
        """
        cleared_count = 0
        
        try:
            if content_type:
                # Clear specific content type
                cache_dir = self.cache_dir / content_type
                if cache_dir.exists():
                    for cache_file in cache_dir.glob("*.json"):
                        cache_file.unlink()
                        cleared_count += 1
            else:
                # Clear all content types
                for subdir in self.cache_dir.iterdir():
                    if subdir.is_dir():
                        for cache_file in subdir.glob("*.json"):
                            cache_file.unlink()
                            cleared_count += 1
                            
            print(f"Cleared {cleared_count} cache files")
            return cleared_count
            
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return 0
            
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache files
        
        Returns:
            Number of expired files removed
        """
        removed_count = 0
        
        try:
            for subdir in self.cache_dir.iterdir():
                if subdir.is_dir():
                    for cache_file in subdir.glob("*.json"):
                        if not self._is_cache_valid(cache_file):
                            cache_file.unlink()
                            removed_count += 1
                            
            print(f"Removed {removed_count} expired cache files")
            return removed_count
            
        except Exception as e:
            print(f"Error during cache cleanup: {e}")
            return 0
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'by_type': {},
            'oldest_file': None,
            'newest_file': None
        }
        
        try:
            oldest_time = None
            newest_time = None
            
            for subdir in self.cache_dir.iterdir():
                if subdir.is_dir():
                    type_stats = {
                        'count': 0,
                        'size_mb': 0
                    }
                    
                    for cache_file in subdir.glob("*.json"):
                        file_stat = cache_file.stat()
                        file_time = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        type_stats['count'] += 1
                        type_stats['size_mb'] += file_stat.st_size / (1024 * 1024)
                        
                        stats['total_files'] += 1
                        stats['total_size_mb'] += file_stat.st_size / (1024 * 1024)
                        
                        if oldest_time is None or file_time < oldest_time:
                            oldest_time = file_time
                            stats['oldest_file'] = str(cache_file)
                            
                        if newest_time is None or file_time > newest_time:
                            newest_time = file_time
                            stats['newest_file'] = str(cache_file)
                    
                    if type_stats['count'] > 0:
                        stats['by_type'][subdir.name] = type_stats
                        
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            for type_name in stats['by_type']:
                stats['by_type'][type_name]['size_mb'] = round(stats['by_type'][type_name]['size_mb'], 2)
                
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            
        return stats


class SmartCache:
    """Smart caching with content similarity detection"""
    
    def __init__(self, cache_dir: str = "cache"):
        """Initialize smart cache
        
        Args:
            cache_dir: Directory for cache storage
        """
        self.content_cache = ContentCache(cache_dir)
        
    def get_content_similarity_key(self, params: Dict[str, Any]) -> str:
        """Generate a similarity key that ignores minor parameter differences
        
        Args:
            params: Content generation parameters
            
        Returns:
            Similarity key for approximate matching
        """
        # Extract core parameters that affect content similarity
        core_params = {
            'topic': str(params.get('topic', '')).lower().strip(),
            'subject': str(params.get('subject', '')).lower().strip(), 
            'grade': str(params.get('grade', '')).lower().strip(),
            'style': str(params.get('style', '')).lower().strip(),
            'language': str(params.get('language', 'english')).lower().strip()
        }
        
        # Remove empty values and normalize
        core_params = {k: v for k, v in core_params.items() if v}
        
        try:
            return json.dumps(core_params, sort_keys=True)
        except (TypeError, ValueError):
            # Fallback for non-serializable objects
            return str(sorted(core_params.items()))
        
    def get_similar_content(self, content_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get content with similar parameters if exact match not found
        
        Args:
            content_type: Type of content
            params: Generation parameters
            
        Returns:
            Similar cached content if found, None otherwise
        """
        # First try exact match
        exact_content = self.content_cache.get_cached_content(content_type, params)
        if exact_content:
            return exact_content
            
        # If no exact match, look for similar content
        similarity_key = self.get_content_similarity_key(params)
        
        try:
            cache_dir = self.content_cache.cache_dir / content_type
            if not cache_dir.exists():
                return None
                
            # Check all cached files for similar parameters
            for cache_file in cache_dir.glob("*.json"):
                if not self.content_cache._is_cache_valid(cache_file):
                    continue
                    
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        
                        cached_params = cached_data.get('params', {})
                        cached_similarity_key = self.get_content_similarity_key(cached_params)
                        
                        if cached_similarity_key == similarity_key:
                            print(f"Found similar cached content for {content_type}")
                            # Update access time
                            cache_file.touch()
                            return cached_data.get('content')
                        
                except Exception as e:
                    print(f"Error checking similarity for {cache_file}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching for similar content: {e}")
            
        return None