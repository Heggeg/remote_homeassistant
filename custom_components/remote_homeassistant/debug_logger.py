"""Debug logger that writes to a file in the component directory."""
import os
import datetime
from pathlib import Path

DEBUG_FILE = "remote_ha_debug.log"

def debug_log(message: str, *args):
    """Write debug message to file."""
    try:
        # Get the directory of this file
        component_dir = Path(__file__).parent
        log_file = component_dir / DEBUG_FILE
        
        # Format message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if args:
            message = message % args
        log_line = f"[{timestamp}] {message}\n"
        
        # Append to file
        with open(log_file, "a") as f:
            f.write(log_line)
            
    except Exception as e:
        # Silently fail if we can't write to file
        pass

def clear_debug_log():
    """Clear the debug log file."""
    try:
        component_dir = Path(__file__).parent
        log_file = component_dir / DEBUG_FILE
        if log_file.exists():
            log_file.unlink()
    except:
        pass