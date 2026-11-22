"""
Abstract base class for interpolation backends.
Defines the interface that all interpolation backends must implement.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Tuple, Optional, Any


class InterpBackend(ABC):
    """Abstract base class for video interpolation backends."""
    
    name: str = "base"
    version: Optional[str] = None
    
    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """
        Check if this backend is available and properly configured.
        
        Returns:
            Tuple of (is_available, message)
        """
        pass
    
    @abstractmethod
    def process(
        self,
        input_path: Path,
        output_path: Path,
        *,
        mode: str = 'multiplier',
        multiplier: Optional[str] = '2x',
        target_fps: Optional[float] = None,
        scale: float = 1.0,
        uhd_mode: str = 'auto',
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Process a video with interpolation.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            mode: Processing mode ('multiplier' or 'custom_fps')
            multiplier: Frame multiplier (e.g., '2x', '4x')
            target_fps: Target frame rate for custom_fps mode
            scale: Resolution scale factor
            uhd_mode: UHD processing mode ('auto', 'on', 'off')
            **kwargs: Additional backend-specific parameters
            
        Yields:
            Progress/status messages
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> dict:
        """
        Get backend capabilities and limitations.
        
        Returns:
            Dictionary describing backend capabilities
        """
        pass
    
    def validate_input(self, input_path: Path) -> Tuple[bool, str]:
        """
        Validate input video file.
        
        Args:
            input_path: Path to input video
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not input_path.exists():
            return False, f"Input file not found: {input_path}"
        
        if input_path.stat().st_size == 0:
            return False, "Input file is empty"
        
        # Check file extension
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}
        if input_path.suffix.lower() not in valid_extensions:
            return False, f"Unsupported file format: {input_path.suffix}"
        
        return True, "OK"
    
    def estimate_processing_time(
        self,
        input_path: Path,
        mode: str,
        multiplier: Optional[str] = None,
        target_fps: Optional[float] = None
    ) -> float:
        """
        Estimate processing time in seconds.
        
        Args:
            input_path: Input video path
            mode: Processing mode
            multiplier: Frame multiplier
            target_fps: Target FPS
            
        Returns:
            Estimated time in seconds
        """
        # Default estimation based on file size
        # Subclasses can override with more accurate estimates
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        
        # Rough estimate: 1 MB/second for 2x, slower for higher multipliers
        base_rate = 1.0  # MB/second
        
        if mode == 'multiplier':
            mult = int(multiplier.replace('x', '')) if multiplier else 2
            rate = base_rate / mult
        else:
            # Custom FPS mode, estimate based on target
            rate = base_rate / 2 if target_fps and target_fps > 60 else base_rate
        
        return file_size_mb / rate
    
    def get_optimal_settings(
        self,
        input_path: Path,
        available_vram: Optional[float] = None
    ) -> dict:
        """
        Get optimal processing settings for the input.
        
        Args:
            input_path: Input video path
            available_vram: Available VRAM in MB
            
        Returns:
            Dictionary of recommended settings
        """
        # Default recommendations
        # Subclasses can override with backend-specific logic
        
        settings = {
            'scale': 1.0,
            'uhd_mode': 'auto',
            'batch_size': 1
        }
        
        # Adjust based on available VRAM
        if available_vram:
            if available_vram < 4096:  # Less than 4GB
                settings['scale'] = 0.5
                settings['uhd_mode'] = 'off'
            elif available_vram < 8192:  # Less than 8GB
                settings['scale'] = 0.75
                settings['uhd_mode'] = 'auto'
            else:  # 8GB or more
                settings['scale'] = 1.0
                settings['uhd_mode'] = 'on'
        
        return settings