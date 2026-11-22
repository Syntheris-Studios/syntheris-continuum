"""
File handling utilities for video processing
"""

import tempfile
import uuid
from pathlib import Path
from typing import Union, Optional, List
import shutil

def resolve_video_path(video_file) -> Optional[str]:
    """
    Resolve video file path from various input types
    Handles Gradio file objects, strings, and dictionaries
    """
    if video_file is None:
        return None
        
    # Handle Gradio file object
    if hasattr(video_file, 'name'):
        return video_file.name
        
    # Handle string path
    if isinstance(video_file, str):
        return video_file
        
    # Handle dictionary with path/name keys
    if isinstance(video_file, dict):
        return video_file.get('path') or video_file.get('name')
        
    return None

def extract_batch_file_paths(batch_files) -> List[str]:
    """
    Extract file paths from batch file input
    Handles various formats from gr.Files component
    """
    if not batch_files:
        return []
        
    paths = []
    
    # Handle list of files
    if isinstance(batch_files, list):
        for file_obj in batch_files:
            path = resolve_video_path(file_obj)
            if path:
                paths.append(path)
    else:
        # Handle single file
        path = resolve_video_path(batch_files)
        if path:
            paths.append(path)
            
    return paths


def ensure_temp_dir(base_dir: Optional[Path] = None) -> Path:
    """
    Ensure temporary directory exists and return path.
    
    Args:
        base_dir: Base directory for temp folder
        
    Returns:
        Path to temp directory
    """
    if base_dir:
        temp_dir = base_dir / "temp"
    else:
        temp_dir = Path.cwd() / "temp"
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def cleanup_temp_files(temp_dir: Path) -> None:
    """
    Clean up temporary files and directories.
    
    Args:
        temp_dir: Directory to clean up
    """
    if temp_dir.exists() and temp_dir.is_dir():
        try:
            shutil.rmtree(temp_dir)
        except (OSError, PermissionError):
            # If we can't remove the directory, at least try to clean files
            try:
                for file in temp_dir.rglob('*'):
                    if file.is_file():
                        file.unlink(missing_ok=True)
            except (OSError, PermissionError):
                pass

def create_temp_file(suffix: str = ".mp4", prefix: str = "syntheris_") -> Path:
    """Create a temporary file with proper cleanup handling"""
    from ..core.config import TEMP_DIR
    TEMP_DIR.mkdir(exist_ok=True)
    
    # Create unique filename
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{prefix}{unique_id}{suffix}"
    
    return TEMP_DIR / filename

def create_temp_dir(prefix: str = "syntheris_job_") -> Path:
    """Create a temporary directory for processing"""
    from ..core.config import TEMP_DIR
    TEMP_DIR.mkdir(exist_ok=True)
    
    unique_id = str(uuid.uuid4())[:8]
    dirname = f"{prefix}{unique_id}"
    
    temp_dir = TEMP_DIR / dirname
    temp_dir.mkdir(exist_ok=True)
    
    return temp_dir

def cleanup_temp_files(*file_paths: Union[str, Path]):
    """Clean up temporary files safely"""
    for file_path in file_paths:
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors

def ensure_output_filename(input_path: str, suffix: str = "_processed", extension: str = None) -> Path:
    """Generate output filename based on input"""
    from ..core.config import OUTPUT_DIR
    
    input_file = Path(input_path)
    stem = input_file.stem
    ext = extension or input_file.suffix
    
    output_filename = f"{stem}{suffix}{ext}"
    return OUTPUT_DIR / output_filename

def get_safe_filename(filename: str) -> str:
    """Convert filename to safe format for filesystem"""
    import re
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces with underscores
    return safe_name

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def validate_video_file(file_path: Union[str, Path]) -> bool:
    """Validate that file is a supported video format"""
    supported_extensions = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v'}
    
    try:
        path = Path(file_path)
        return (path.exists() and 
                path.is_file() and 
                path.suffix.lower() in supported_extensions and
                path.stat().st_size > 0)
    except Exception:
        return False