import os
import json
import hashlib
import time
from functools import wraps
from config import active_config as config

# Create cache directory if it doesn't exist
os.makedirs(config.CACHE_DIR, exist_ok=True)

def cache_result(func):
    """
    Decorator to cache function results
    
    The cache is based on function name and arguments
    Results expire after 1 hour by default
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip caching if first arg is self (for methods)
        cache_key_args = args
        if len(args) > 0 and hasattr(args[0], '__class__'):
            cache_key_args = (args[0].__class__.__name__,) + args[1:]
        
        # Create a unique key from function name and arguments
        key = hashlib.md5(
            f"{func.__name__}:{str(cache_key_args)}:{str(kwargs)}".encode()
        ).hexdigest()
        
        cache_file = os.path.join(config.CACHE_DIR, f"{key}.json")
        
        # Check if cached result exists and is recent
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 3600:  # Cache valid for 1 hour
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    # If cache file is corrupted, continue to execute function
                    pass
        
        # Call the function and cache the result
        result = func(*args, **kwargs)
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f)
        except (IOError, TypeError) as e:
            # Log but continue if caching fails
            print(f"Caching failed for {func.__name__}: {e}")
        
        return result
    
    return wrapper