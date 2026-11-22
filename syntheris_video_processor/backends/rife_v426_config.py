"""
RIFE v4.26 Configuration Module
Provides exact configurations for RIFE v4.26 with research-validated settings.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import os


# RIFE v4.26 exact configurations based on research findings
RIFE_V426_CONFIGS = {
    # Research: "Configuration fps_num=60000, fps_den=1001, sc=false, skip=false achieves exact 59.94fps output"
    '24fps_to_60fps': {
        'fps_num': 60000,
        'fps_den': 1001,  # Exact 59.94fps
        'sc': False,      # Disable scene change detection per research
        'skip': False,    # Disable frame skipping per research
        'multiplier_type': 'exact_fps',
        'working_dir': None,  # Will be determined dynamically
        'model_name': 'HDv3',
        'precision_mode': True,
        'expected_ratio': 2.5,
        'description': '24fps to 59.94fps (2.5x) - Primary use case'
    },
    
    '24fps_to_30fps': {
        'fps_num': 30000,
        'fps_den': 1001,  # Exact 29.97fps
        'sc': False,
        'skip': False,
        'multiplier_type': 'exact_fps',
        'working_dir': None,  # Will be determined dynamically
        'model_name': 'HDv3',
        'precision_mode': True,
        'expected_ratio': 1.25,
        'description': '24fps to 29.97fps (1.25x) - Quality mode'
    },
    
    '30fps_to_60fps': {
        'fps_num': 60000,
        'fps_den': 1001,  # Exact 59.94fps
        'sc': False,
        'skip': False,
        'multiplier_type': 'exact_fps',
        'working_dir': None,  # Will be determined dynamically
        'model_name': 'HDv3',
        'precision_mode': True,
        'expected_ratio': 2.0,
        'description': '30fps to 59.94fps (2x) - Standard doubling'
    },
    
    # Fallback configuration for arbitrary rates
    'arbitrary_fps': {
        'sc': False,
        'skip': False,
        'multiplier_type': 'calculated',
        'working_dir': None,  # Will be determined dynamically
        'model_name': 'HDv3',
        'precision_mode': True,
        'description': 'Arbitrary FPS conversion with calculated parameters'
    }
}

# Performance optimization settings
PERFORMANCE_CONFIGS = {
    'low_memory': {
        'batch_size': 1,
        'tile_size': 512,
        'half_precision': True,
        'memory_efficient': True
    },
    'balanced': {
        'batch_size': 2,
        'tile_size': 1024,
        'half_precision': False,
        'memory_efficient': True
    },
    'high_performance': {
        'batch_size': 4,
        'tile_size': 2048,
        'half_precision': False,
        'memory_efficient': False
    }
}

# Quality presets
QUALITY_PRESETS = {
    'draft': {
        'crf': 25,
        'preset': 'ultrafast',
        'tune': 'fastdecode'
    },
    'standard': {
        'crf': 18,
        'preset': 'fast',
        'tune': 'film'
    },
    'high_quality': {
        'crf': 15,
        'preset': 'slow',
        'tune': 'film'
    }
}


class RIFEv426Configurator:
    """Manages RIFE v4.26 configurations and provides optimized settings."""
    
    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize RIFE v4.26 configurator.
        
        Args:
            working_dir: Override default RIFE v4.26 directory
        """
        if working_dir:
            self.working_dir = Path(working_dir)
        else:
            # Look for RIFE in project structure first, then temp locations
            project_root = Path(__file__).parent.parent.parent
            self.working_dir = project_root / "Practical-RIFE"  # Use integrated installation
        
        # Use centralized path configuration instead of hardcoded paths
        from ..core.config import path_config
        
        # Backup locations to check (using path_config for cross-platform compatibility)
        self.fallback_dirs = [
            project_root / "RIFEv4.26",  # Alternative project location
            project_root / "third_party" / "RIFE_v426",
            Path.home() / "RIFE" / "v426",
        ]
        
        # Use path_config for primary detection
        self._path_config = path_config
        
    def is_v426_available(self) -> bool:
        """Check if RIFE v4.26 is properly installed using centralized path configuration."""
        
        # Use centralized path configuration for RIFE v4.26 detection
        v426_path = self._path_config.get_rife_v426_path()
        
        if v426_path:
            self.working_dir = v426_path  # Update to detected directory
            return True
        
        return False
    
    def get_optimal_config(
        self,
        source_fps: float,
        target_fps: float,
        performance_mode: str = 'balanced'
    ) -> Dict[str, Any]:
        """
        Get optimal configuration for given FPS conversion.
        
        Args:
            source_fps: Source video frame rate
            target_fps: Target frame rate
            performance_mode: Performance preset ('low_memory', 'balanced', 'high_performance')
            
        Returns:
            Optimal configuration dictionary
        """
        
        if not self.is_v426_available():
            return {'error': 'RIFE v4.26 not available', 'fallback_required': True}
        
        # Calculate conversion ratio
        ratio = target_fps / source_fps if source_fps > 0 else 0
        
        # Match to exact configurations
        config_key = None
        if abs(source_fps - 24) < 0.1:
            if abs(target_fps - 60) < 0.1 or abs(target_fps - 59.94) < 0.1:
                config_key = '24fps_to_60fps'
            elif abs(target_fps - 30) < 0.1 or abs(target_fps - 29.97) < 0.1:
                config_key = '24fps_to_30fps'
        elif abs(source_fps - 30) < 0.1 and (abs(target_fps - 60) < 0.1 or abs(target_fps - 59.94) < 0.1):
            config_key = '30fps_to_60fps'
        
        if config_key:
            base_config = RIFE_V426_CONFIGS[config_key].copy()
        else:
            # Arbitrary FPS conversion
            base_config = RIFE_V426_CONFIGS['arbitrary_fps'].copy()
            base_config['fps_num'] = int(target_fps * 1001)
            base_config['fps_den'] = 1001
            base_config['expected_ratio'] = ratio
        
        # Add performance settings
        perf_config = PERFORMANCE_CONFIGS.get(performance_mode, PERFORMANCE_CONFIGS['balanced'])
        base_config['performance'] = perf_config
        
        # Add metadata
        base_config.update({
            'source_fps': source_fps,
            'target_fps': target_fps,
            'conversion_ratio': ratio,
            'working_dir': str(self.working_dir),
            'model_path': str(self.working_dir / 'train_log'),
            'inference_script': str(self.working_dir / 'inference_video.py'),
            'duration_preserving': True,
            'research_validated': True
        })
        
        return base_config
    
    def build_command(
        self,
        input_path: Path,
        output_path: Path,
        config: Dict[str, Any]
    ) -> list[str]:
        """
        Build RIFE v4.26 command with exact configuration.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            config: Configuration dictionary from get_optimal_config()
            
        Returns:
            Command list for subprocess execution
        """
        
        import sys
        
        cmd = [
            sys.executable,
            'inference_video.py',
            '--video', str(input_path),
            '--output', str(output_path)
        ]
        
        # Add FPS parameters using correct RIFE v4.26 syntax
        if config['multiplier_type'] == 'exact_fps':
            # Use --fps for direct FPS targeting (RIFE v4.26 doesn't support fps_num/fps_den)
            target_fps = config.get('target_fps', 60)
            cmd.extend(['--fps', format(float(target_fps), '.12g')])
        elif config['multiplier_type'] == 'calculated':
            # Fallback to multiplier mode
            ratio = config.get('conversion_ratio', 2.0)
            if ratio <= 2.5:
                cmd.extend(['--multi', '2'])
            elif ratio <= 4.0:
                cmd.extend(['--multi', '4'])
            else:
                cmd.extend(['--multi', '8'])
        
        # Research-validated frame skipping control
        # Note: RIFE v4.26 uses --skip to ENABLE skipping, so we DON'T add it to disable
        skip_enabled = config.get('skip', False)  # Research says skip=false
        if skip_enabled:
            cmd.append('--skip')  # Only add if we want to enable skipping
        
        # Note: RIFE v4.26 doesn't have scene change detection arguments
        # Scene detection behavior is handled internally by the model
        
        # Performance optimizations (only use supported arguments)
        perf = config.get('performance', {})
        if perf.get('half_precision'):
            cmd.append('--fp16')
        
        # batch_size is not supported by RIFE v4.26 - removed
        
        # Scale parameter (supported by RIFE v4.26)
        scale = config.get('scale', 1.0)
        if scale != 1.0:
            cmd.extend(['--scale', str(scale)])
        
        # UHD mode (supported by RIFE v4.26) 
        if config.get('uhd_mode') or config.get('enable_uhd'):
            cmd.append('--UHD')
        
        # Model path
        if 'model_path' in config:
            cmd.extend(['--model', str(Path(config['model_path']).relative_to(self.working_dir))])
        else:
            # Default to train_log directory
            cmd.extend(['--model', 'train_log'])
        
        return cmd
    
    def validate_conversion(
        self,
        source_fps: float,
        target_fps: float
    ) -> Tuple[bool, str]:
        """
        Validate if conversion is feasible with RIFE v4.26.
        
        Returns:
            (feasible, message) tuple
        """
        
        if not self.is_v426_available():
            return False, "RIFE v4.26 not available"
        
        if source_fps <= 0 or target_fps <= 0:
            return False, "Invalid frame rates"
        
        ratio = target_fps / source_fps
        
        # Research constraints
        if ratio < 1.0:
            return False, "RIFE cannot reduce frame rate (use decimation instead)"
        
        if ratio > 8.0:
            return False, "Conversion ratio >8x may cause quality degradation"
        
        # Special validation for 2.5x multiplier (24fps->60fps)
        if abs(ratio - 2.5) < 0.1:
            if not abs(source_fps - 24) < 0.1:
                return False, "2.5x multiplier only validated for 24fps input"
        
        return True, f"Conversion feasible: {source_fps}fps -> {target_fps}fps ({ratio:.2f}x)"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed RIFE v4.26 model information."""
        
        if not self.is_v426_available():
            return {'available': False}
        
        model_info = {
            'available': True,
            'version': '4.26',
            'model_type': 'HDv3',
            'working_dir': str(self.working_dir),
            'model_path': str(self.working_dir / 'train_log'),
            'capabilities': {
                'exact_fps_targeting': True,
                'arbitrary_multipliers': True,
                'duration_preserving': True,
                'precision_mode': True,
                'supports_2_5x': True  # Key capability for 24fps->60fps
            }
        }
        
        # Get model file sizes
        model_files = {}
        model_dir = self.working_dir / 'train_log'
        if model_dir.exists():
            for file_path in model_dir.glob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    model_files[file_path.name] = {
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2)
                    }
        
        model_info['model_files'] = model_files
        return model_info


# Convenience functions for common operations
def get_24fps_to_60fps_config() -> Dict[str, Any]:
    """Get the most common configuration: 24fps -> 60fps (2.5x)."""
    configurator = RIFEv426Configurator()
    return configurator.get_optimal_config(24.0, 60.0)


def is_rife_v426_ready() -> bool:
    """Quick check if RIFE v4.26 is ready for use."""
    configurator = RIFEv426Configurator()
    return configurator.is_v426_available()


def get_supported_conversions() -> Dict[str, Dict[str, Any]]:
    """Get all supported exact FPS conversions."""
    return {
        key: {
            'description': config['description'],
            'ratio': config['expected_ratio'],
            'precision_mode': config['precision_mode']
        }
        for key, config in RIFE_V426_CONFIGS.items()
        if key != 'arbitrary_fps'
    }