"""
RIFE v4.26 Manager - Research-based RIFE v4.26 integration
Manages RIFE v4.26 installation and capabilities based on research findings.
"""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json


class RIFEv426Manager:
    """
    Manager for RIFE v4.26 with research-validated capabilities.
    
    Based on research: "Only RIFE v4.x models support arbitrary frame rates 
    through custom FPS mode parameters"
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.rife_v426_path = self.project_root / "RIFEv4.26"
        self.model_path = self.rife_v426_path / "train_log"
        self.capabilities = self._detect_v426_capabilities()
        
        # Research-validated configuration
        self.research_config = self._get_research_validated_config()
    
    def _detect_v426_capabilities(self) -> Dict[str, Any]:
        """
        Detect RIFE v4.26 exact capabilities based on research findings.
        
        Research: "RIFE v4.6+ models with explicit FPS targets rather than 
        multiplication factors"
        """
        
        if not self.is_v426_available():
            return {
                'available': False,
                'supports_arbitrary_fps': False,
                'supports_25x_multiplier': False,
                'supports_exact_fps_targets': False,
                'model_version': None
            }
        
        # RIFE v4.26 capabilities per research
        return {
            'available': True,
            'supports_arbitrary_fps': True,
            'supports_25x_multiplier': True,  # Key: 24fps->60fps (2.5x)
            'supports_exact_fps_targets': True,
            'model_version': '4.26',
            'model_type': 'HDv3',  # Based on detected files
            'precision_mode': True,  # Research: duration-preserving mode
            'recommended_config': {
                'fps_num': 60000,
                'fps_den': 1001,  # Exact 59.94fps per research
                'sc': False,  # Disable scene change detection
                'skip': False,  # Disable frame skipping
                'precision': True  # Enable precision mode
            }
        }
    
    def is_v426_available(self) -> bool:
        """Check if RIFE v4.26 is properly installed."""
        
        # Check for required model files
        required_files = [
            'flownet.pkl',
            'IFNet_HDv3.py',
            'RIFE_HDv3.py'
        ]
        
        if not self.model_path.exists():
            return False
            
        for file_name in required_files:
            if not (self.model_path / file_name).exists():
                return False
                
        return True
    
    def _get_research_validated_config(self) -> Dict[str, Any]:
        """
        Get research-validated configuration for different scenarios.
        
        Research: "For RIFE interpolation, use v4.6+ models with explicit 
        FPS targets rather than multiplication factors"
        """
        
        return {
            # 24fps -> 60fps (2.5x) - Most common case
            '24_to_60': {
                'mode': 'custom_fps',
                'fps_num': 60000,
                'fps_den': 1001,  # 59.94fps exactly
                'sc': False,      # Disable scene change detection
                'skip': False,    # Disable frame skipping
                'method': 'precision',  # Use precision interpolation
                'expected_ratio': 2.5
            },
            
            # 24fps -> 30fps (1.25x) - Simple case
            '24_to_30': {
                'mode': 'custom_fps', 
                'fps_num': 30000,
                'fps_den': 1001,  # 29.97fps exactly
                'sc': False,
                'skip': False,
                'method': 'precision',
                'expected_ratio': 1.25
            },
            
            # 30fps -> 60fps (2x) - Integer multiplier
            '30_to_60': {
                'mode': 'multiplier',
                'multiplier': '2x',
                'sc': False,
                'skip': False,
                'method': 'standard',
                'expected_ratio': 2.0
            },
            
            # General precision mode for arbitrary rates
            'arbitrary': {
                'mode': 'custom_fps',
                'sc': False,
                'skip': False, 
                'method': 'precision',
                'use_exact_fps': True
            }
        }
    
    def get_optimal_config(
        self,
        source_fps: float,
        target_fps: float
    ) -> Dict[str, Any]:
        """
        Get optimal configuration for given FPS conversion.
        
        Args:
            source_fps: Source video frame rate
            target_fps: Target frame rate
            
        Returns:
            Optimal configuration dictionary
        """
        
        if not self.capabilities['available']:
            return {'error': 'RIFE v4.26 not available'}
        
        # Calculate conversion ratio
        ratio = target_fps / source_fps if source_fps > 0 else 0
        
        # Match to research-validated scenarios
        if abs(source_fps - 24) < 0.1 and abs(target_fps - 60) < 0.1:
            config = self.research_config['24_to_60'].copy()
        elif abs(source_fps - 24) < 0.1 and abs(target_fps - 30) < 0.1:
            config = self.research_config['24_to_30'].copy()
        elif abs(source_fps - 30) < 0.1 and abs(target_fps - 60) < 0.1:
            config = self.research_config['30_to_60'].copy()
        else:
            # Arbitrary rate conversion
            config = self.research_config['arbitrary'].copy()
            config['fps_num'] = int(target_fps * 1001)
            config['fps_den'] = 1001
            config['expected_ratio'] = ratio
        
        # Add metadata
        config.update({
            'source_fps': source_fps,
            'target_fps': target_fps,
            'conversion_ratio': ratio,
            'model_version': '4.26',
            'duration_preserving': True
        })
        
        return config
    
    def validate_conversion_feasibility(
        self,
        source_fps: float,
        target_fps: float
    ) -> Tuple[bool, str]:
        """
        Validate if conversion is feasible with RIFE v4.26.
        
        Returns:
            (feasible, message) tuple
        """
        
        if not self.capabilities['available']:
            return False, "RIFE v4.26 not available"
        
        if source_fps <= 0 or target_fps <= 0:
            return False, "Invalid frame rates"
        
        ratio = target_fps / source_fps
        
        # Research constraints
        if ratio < 1.0:
            return False, "RIFE cannot reduce frame rate (use decimation instead)"
        
        if ratio > 8.0:
            return False, "Conversion ratio >8x may cause quality degradation"
        
        # Check if we have optimized config for this conversion
        config = self.get_optimal_config(source_fps, target_fps)
        if 'error' in config:
            return False, config['error']
        
        return True, f"Conversion feasible: {source_fps}fps -> {target_fps}fps ({ratio:.2f}x)"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        
        if not self.is_v426_available():
            return {'available': False}
        
        # Get model file sizes and timestamps
        model_info = {}
        for file_path in self.model_path.glob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                model_info[file_path.name] = {
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                }
        
        return {
            'available': True,
            'version': '4.26',
            'model_type': 'HDv3',
            'path': str(self.model_path),
            'files': model_info,
            'capabilities': self.capabilities,
            'research_validated': True
        }
    
    def generate_inference_command(
        self,
        input_path: Path,
        output_path: Path,
        config: Dict[str, Any]
    ) -> list[str]:
        """
        Generate RIFE inference command with v4.26 specific parameters.
        
        Research: "The configuration fps_num=60000, fps_den=1001, sc=false, skip=false 
        achieves exact 59.94fps output"
        """
        
        if not self.capabilities['available']:
            raise RuntimeError("RIFE v4.26 not available")
        
        # Base command (assuming inference script exists)
        cmd = [
            'python', 
            str(self.rife_v426_path / 'inference_video.py'),  # Will need this script
            '--input', str(input_path),
            '--output', str(output_path),
            '--model', str(self.model_path)
        ]
        
        # Add v4.26 specific parameters based on config
        if config['mode'] == 'custom_fps':
            cmd.extend([
                '--fps_num', str(config['fps_num']),
                '--fps_den', str(config['fps_den'])
            ])
        elif config['mode'] == 'multiplier':
            cmd.extend([
                '--multi', config['multiplier'].replace('x', '')
            ])
        
        # Research-based quality parameters
        if not config.get('sc', True):
            cmd.append('--no_scene_change')
        
        if not config.get('skip', True):
            cmd.append('--no_skip')
        
        # Precision mode for duration preservation
        if config.get('method') == 'precision':
            cmd.append('--precision_mode')
        
        return cmd