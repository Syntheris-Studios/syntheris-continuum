"""
RIFE (Real-Time Intermediate Flow Estimation) backend implementation.
Provides high-quality video frame interpolation using deep learning.
"""

from __future__ import annotations
import sys
import subprocess
import shutil
import time
import os
from pathlib import Path
from typing import Generator, Tuple, Optional, Dict, Any
from .base import InterpBackend
from .rife_v426_manager import RIFEv426Manager
from .rife_v426_config import RIFEv426Configurator


class RIFEBackend(InterpBackend):
    """RIFE interpolation backend with complete functionality."""
    
    name = "rife"
    version = "4.26"
    
    def __init__(self, rife_script: Optional[Path] = None, model_dir: Optional[Path] = None):
        """
        Initialize RIFE backend with v4.26 support.
        
        Args:
            rife_script: Path to RIFE inference script
            model_dir: Path to RIFE model directory
        """
        # Initialize both managers for research-validated processing
        self.v426_manager = RIFEv426Manager()
        self.v426_configurator = RIFEv426Configurator()
        
        # Find RIFE installation - prioritize v4.26 if available
        app_dir = Path(__file__).resolve().parents[2]
        
        if self.v426_configurator.is_v426_available():
            # Use RIFE v4.26 for exact FPS targeting and precision interpolation
            self.rife_dir = self.v426_configurator.working_dir
            self.rife_script = self.rife_dir / 'inference_video.py'
            self.model_dir = self.rife_dir / 'train_log'
            self.version = "4.26"
            self.precision_mode = True
            self.supports_exact_fps = True
            self.supports_2_5x_multiplier = True  # Key feature for 24fps->60fps
            print(f"[RIFE] Using v4.26 with exact FPS targeting: {self.rife_dir}")
        else:
            # Fallback to existing RIFE installation
            rife_dir = app_dir / 'Practical-RIFE'
            
            # Use patched script if available, fallback to original
            patched_script = rife_dir / 'inference_video_patched.py'
            original_script = rife_dir / 'inference_video.py'
            
            if rife_script:
                self.rife_script = rife_script
            elif patched_script.exists():
                self.rife_script = patched_script
            elif original_script.exists():
                self.rife_script = original_script
            else:
                self.rife_script = None
                
            self.rife_dir = rife_dir
            self.version = "HDv3"
            self.precision_mode = False
            self.supports_exact_fps = False
            self.supports_2_5x_multiplier = False
            print(f"[RIFE] Using legacy HDv3: {self.rife_dir}")
            
        # Store RIFE directory for working directory
        
        # Model directory (only set if not already set by v4.26 path above)
        if model_dir:
            self.model_dir = model_dir
        elif not hasattr(self, 'model_dir') or self.model_dir is None:
            # Use self.rife_dir instead of local rife_dir variable
            train_log = self.rife_dir / 'train_log'
            if train_log.exists() and (train_log / 'flownet.pkl').exists():
                self.model_dir = train_log
            elif (self.rife_dir / 'flownet.pkl').exists():
                self.model_dir = self.rife_dir
            else:
                self.model_dir = None
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if RIFE is properly installed and configured."""
        
        if not self.rife_script or not self.rife_script.exists():
            return False, f"RIFE script not found: {self.rife_script}"
        
        if not self.model_dir:
            return False, "RIFE model directory not found"
        
        model_file = self.model_dir / 'flownet.pkl'
        if not model_file.exists():
            return False, f"RIFE model not found: {model_file}"
        
        # Check for required dependencies
        try:
            import torch
            if not torch.cuda.is_available():
                return True, "RIFE available (CPU mode - will be slow)"
        except ImportError:
            return False, "PyTorch not installed"
        
        return True, "RIFE backend ready"
    
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
        Process video with RIFE interpolation using research-validated approach.
        
        Research: "For RIFE interpolation, use v4.6+ models with explicit FPS targets 
        rather than multiplication factors"
        """
        
        # Validate input
        valid, message = self.validate_input(input_path)
        if not valid:
            raise ValueError(message)
        
        # Ensure absolute paths
        input_abs = input_path.resolve()
        output_abs = output_path.resolve()
        
        # Ensure output directory exists
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        
        # Store target_fps for ATFI access
        self.last_target_fps = target_fps
        
        # Use RIFE v4.26 precision processing if available
        if self.supports_exact_fps and self.v426_configurator.is_v426_available():
            yield "Using RIFE v4.26 with exact FPS targeting for duration-preserving interpolation"
            yield from self._process_with_v426_enhanced(input_abs, output_abs, mode, multiplier, target_fps, scale)
        else:
            yield f"Using legacy RIFE {self.version} processing"
            yield from self._process_with_legacy(input_abs, output_abs, mode, multiplier, target_fps, scale, uhd_mode)
    
    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        mode: str,
        multiplier: Optional[str],
        target_fps: Optional[float],
        scale: float,
        uhd_mode: str
    ) -> list[str]:
        """Build RIFE command line arguments with duration preservation."""
        
        # CRITICAL: Get input duration BEFORE RIFE processing to prevent corruption
        input_duration = self._get_video_duration(input_path)
        print(f"[RIFE] V4.3.0 DURATION PRESERVATION: Input {input_duration:.6f}s")
        
        # Use just the script filename since we set working directory
        cmd = [
            sys.executable,
            self.rife_script.name,  # Use the actual script name (patched or original)
            '--video', str(input_path),
            '--output', str(output_path),
            '--model', str(self.model_dir.relative_to(self.rife_dir))  # Relative to RIFE dir
        ]
        
        # Use multiplier mode to avoid SSIM early termination issues
        if mode == 'custom_fps' and target_fps:
            # Calculate appropriate multiplier
            import cv2
            try:
                cap = cv2.VideoCapture(str(input_path))
                source_fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                
                if source_fps > 0:
                    ratio = target_fps / source_fps
                    if ratio <= 1.5:
                        mult = '2'
                    elif ratio <= 3.0:
                        mult = '2'  # 24fps->60fps gets 2x = 48fps
                    elif ratio <= 6.0:
                        mult = '4'
                    else:
                        mult = '8'
                else:
                    mult = '2'
            except:
                mult = '2'
            
            cmd.extend(['--multi', mult])
        else:
            # Direct multiplier mode
            mult = multiplier.replace('x', '') if multiplier else '2'
            if mult not in {'2', '4', '8'}:
                mult = '2'
            cmd.extend(['--multi', mult])
        
        # Scale parameter
        if scale in [0.25, 0.5, 2.0, 4.0]:
            cmd.extend(['--scale', str(scale)])
        
        # UHD mode
        if self._should_enable_uhd(input_path, uhd_mode):
            cmd.append('--UHD')
        
        return cmd
    
    def _should_enable_uhd(self, video_path: Path, uhd_mode: str) -> bool:
        """Determine if UHD mode should be enabled."""
        
        if uhd_mode == 'off':
            return False
        if uhd_mode == 'on':
            return True
        
        # Auto mode - check resolution
        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # Enable UHD for 4K or higher
            return width >= 3840 or height >= 2160
        except:
            return False
    
    def _check_alternative_outputs(
        self,
        input_path: Path,
        expected_output: Path
    ) -> list[Path]:
        """
        Check for alternative output file naming patterns that RIFE commonly creates.
        """
        
        output_dir = expected_output.parent
        if not output_dir.exists():
            return []
        
        alternatives = []
        
        # Pattern 1: RIFE's standard naming with multiplier (input_2X_60fps.mp4)
        input_stem = input_path.stem
        for multiplier in ['2X', '4X', '8X']:
            # Check for input_2X_60fps.mp4 pattern
            for fps in ['24fps', '30fps', '48fps', '60fps', '120fps']:
                pattern = output_dir / f"{input_stem}_{multiplier}_{fps}.mp4"
                if pattern.exists():
                    alternatives.append(pattern)
        
        # Pattern 2: Check for files with the expected base name but with multiplier
        expected_stem = expected_output.stem  # e.g., "segment_001_60fps"
        if '_' in expected_stem:
            # Extract base name (e.g., "segment_001" from "segment_001_60fps")
            base_parts = expected_stem.split('_')
            if len(base_parts) >= 2:
                base_name = '_'.join(base_parts[:-1])  # Everything except last part
                for multiplier in ['2X', '4X', '8X']:
                    for fps in ['24fps', '30fps', '48fps', '60fps', '120fps']:
                        pattern = output_dir / f"{base_name}_{multiplier}_{fps}.mp4"
                        if pattern.exists() and pattern not in alternatives:
                            alternatives.append(pattern)
        
        # Pattern 3: Check for any MP4 files with multiplier indicators
        for file in output_dir.glob("*.mp4"):
            if file == expected_output:
                continue
            # Look for multiplier patterns in filename
            if any(mult in file.stem for mult in ['2X', '4X', '8X', '_2x_', '_4x_', '_8x_']):
                if file not in alternatives:
                    alternatives.append(file)
        
        # Pattern 4: Check for files that match the input stem + multiplier patterns
        for file in output_dir.glob(f"{input_stem}*.mp4"):
            if file != expected_output and file not in alternatives:
                # Check if it looks like a RIFE output
                if any(indicator in file.stem.lower() for indicator in ['x_', 'fps', 'interpolat']):
                    alternatives.append(file)
        
        # Sort by most likely match (prefer files with FPS indicators)
        def score_alternative(file: Path) -> int:
            score = 0
            stem = file.stem.lower()
            # Prefer files with fps indicators
            if 'fps' in stem:
                score += 10
            # Prefer files with multiplier indicators
            if any(mult in stem for mult in ['2x', '4x', '8x']):
                score += 5
            # Prefer larger files (likely complete)
            try:
                size = file.stat().st_size
                if size > 1024 * 1024:  # > 1MB
                    score += 3
            except:
                pass
            return score
        
        alternatives.sort(key=score_alternative, reverse=True)
        return alternatives
    
    def get_capabilities(self) -> dict:
        """Get RIFE backend capabilities."""
        
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                device_name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            else:
                device_name = "CPU"
                vram = 0
        except:
            cuda_available = False
            device_name = "Unknown"
            vram = 0
        
        return {
            'name': self.name,
            'version': self.version,
            'cuda_available': cuda_available,
            'device': device_name,
            'vram_gb': vram,
            'supported_multipliers': ['2x', '4x', '8x'],
            'max_resolution': '8K' if vram >= 8 else '4K' if vram >= 4 else '1080p',
            'features': [
                'Motion-adaptive interpolation',
                'Scene-cut detection',
                'Multi-scale processing',
                'Temporal consistency'
            ]
        }
    
    def estimate_processing_time(
        self,
        input_path: Path,
        mode: str,
        multiplier: Optional[str] = None,
        target_fps: Optional[float] = None
    ) -> float:
        """Estimate RIFE processing time."""
        
        # Get video duration and resolution
        try:
            import cv2
            cap = cv2.VideoCapture(str(input_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            duration = frame_count / fps if fps > 0 else 0
            pixels = width * height
            
            # Base rate: seconds per second of video
            # Depends on resolution and GPU
            if pixels > 3840 * 2160:  # 4K+
                base_rate = 10.0
            elif pixels > 1920 * 1080:  # 1080p+
                base_rate = 5.0
            else:
                base_rate = 2.0
            
            # Adjust for multiplier
            if mode == 'multiplier':
                mult = int(multiplier.replace('x', '')) if multiplier else 2
                rate = base_rate * (mult / 2)
            else:
                rate = base_rate * 2
            
            return duration * rate
            
        except:
            # Fallback to file size estimate
            return super().estimate_processing_time(input_path, mode, multiplier, target_fps)
    
    def _process_with_v426(
        self,
        input_path: Path,
        output_path: Path,
        mode: str,
        multiplier: Optional[str],
        target_fps: Optional[float],
        scale: float
    ) -> Generator[str, None, None]:
        """
        Process with RIFE v4.26 using research-validated precision approach.
        
        Research: "Configuration fps_num=60000, fps_den=1001, sc=false, skip=false 
        achieves exact 59.94fps output"
        """
        
        # Get source FPS for optimal configuration
        import cv2
        try:
            cap = cv2.VideoCapture(str(input_path))
            source_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
        except:
            source_fps = 24.0  # Default assumption
        
        # Determine target FPS
        if mode == 'custom_fps' and target_fps:
            final_target_fps = target_fps
        elif mode == 'multiplier':
            mult_value = int(multiplier.replace('x', '')) if multiplier else 2
            final_target_fps = source_fps * mult_value
        else:
            final_target_fps = 60.0  # Default
        
        # Get research-validated configuration
        config = self.v426_manager.get_optimal_config(source_fps, final_target_fps)
        
        if 'error' in config:
            raise RuntimeError(f"RIFE v4.26 configuration error: {config['error']}")
        
        yield f"Research-validated config: {source_fps}fps -> {final_target_fps}fps ({config['conversion_ratio']:.2f}x)"
        yield f"Using precision mode: {config['method']}"
        
        # For now, use the legacy processing with optimized parameters
        # TODO: Implement actual v4.26 inference script
        yield "Note: Using optimized legacy processing (v4.26 inference script needed)"
        
        # Use legacy method with v4.26-optimized parameters
        yield from self._process_with_legacy(
            input_path, output_path, 'custom_fps', None, final_target_fps, scale, 'auto'
        )
    
    def _process_with_v426_enhanced(
        self,
        input_path: Path,
        output_path: Path,
        mode: str,
        multiplier: Optional[str],
        target_fps: Optional[float],
        scale: float
    ) -> Generator[str, None, None]:
        """
        Enhanced RIFE v4.26 processing with exact FPS targeting and duration validation.
        
        Research: "Use RIFE v4.26 with exact FPS parameters for 2.5x multiplier support"
        """
        
        # Get source FPS and duration for validation
        import cv2
        try:
            cap = cv2.VideoCapture(str(input_path))
            source_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
        except:
            source_fps = 24.0  # Default assumption

        input_duration = self._get_video_duration(input_path)
        
        # Determine target FPS
        if mode == 'custom_fps' and target_fps:
            final_target_fps = target_fps
        elif mode == 'multiplier':
            mult_value = int(multiplier.replace('x', '')) if multiplier else 2
            final_target_fps = source_fps * mult_value
        else:
            final_target_fps = 60.0  # Default
        
        # Get optimal v4.26 configuration
        config = self.v426_configurator.get_optimal_config(source_fps, final_target_fps)
        
        if 'error' in config:
            raise RuntimeError(f"RIFE v4.26 configuration error: {config['error']}")
        
        yield f"Source: {source_fps}fps -> Target: {final_target_fps}fps ({config['conversion_ratio']:.2f}x)"
        yield f"Using config: {config.get('description', 'Arbitrary FPS conversion')}"
        yield f"Input duration: {input_duration:.3f}s"
        
        # Validate conversion feasibility
        feasible, message = self.v426_configurator.validate_conversion(source_fps, final_target_fps)
        if not feasible:
            raise RuntimeError(f"Conversion not feasible: {message}")
        
        yield f"Validation: {message}"
        
        # Build v4.26 command
        cmd = self.v426_configurator.build_command(input_path, output_path, config)
        
        yield f"Working directory: {self.rife_dir}"
        yield f"Command: {' '.join(cmd)}"
        
        # Execute with proper working directory and progress monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(self.rife_dir)  # Critical: Set working directory to RIFE v4.26
        )
        
        last_progress_time = time.time()
        timeout_seconds = 600  # 10 minutes
        recent_output = []
        
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    recent_output.append(line)
                    if len(recent_output) > 20:  # Keep last 20 lines
                        recent_output.pop(0)
                    
                    # Yield progress updates
                    if '%|' in line or 'it/s' in line:
                        yield f"Progress: {line}"
                    elif 'Error' in line or 'error' in line:
                        yield f"WARNING: {line}"
                    
                    # Check for timeout
                    if time.time() - last_progress_time > timeout_seconds:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        raise RuntimeError(f"RIFE v4.26 timeout after {timeout_seconds} seconds")
                    
                    last_progress_time = time.time()
        
        # Wait for completion
        return_code = process.wait()
        
        if return_code != 0:
            error_output = '\n'.join(recent_output[-10:]) if recent_output else 'No output captured'
            raise RuntimeError(f"RIFE v4.26 failed with exit code {return_code}. Last output:\n{error_output}")
        
        # V4.3.0: CRITICAL DURATION VALIDATION - Fix RIFE non-deterministic corruption
        if output_path.exists():
            input_duration = self._get_video_duration(input_path)
            output_duration = self._get_video_duration(output_path)
            duration_drift_ms = abs(output_duration - input_duration) * 1000
            
            yield f"[RIFE] Duration validation: {input_duration:.6f}s -> {output_duration:.6f}s (drift: {duration_drift_ms:.1f}ms)"
            
            if duration_drift_ms > 5:  # More than 5ms drift is unacceptable
                yield f"[RIFE] CRITICAL: Non-deterministic duration corruption detected - applying fix"
                self._apply_rife_duration_fix(output_path, input_duration, output_duration)
                
                # Verify fix worked
                corrected_duration = self._get_video_duration(output_path)
                final_drift_ms = abs(corrected_duration - input_duration) * 1000
                yield f"[RIFE] Fix result: {corrected_duration:.6f}s (final drift: {final_drift_ms:.1f}ms)"
            else:
                yield f"[RIFE] SUCCESS: Duration preserved within tolerance"
        
        # Check for alternative outputs and duration validation
        if not output_path.exists():
            yield "Expected output not found - checking for alternative naming patterns..."
            alternatives = self._check_alternative_outputs(input_path, output_path)
            
            if alternatives:
                alternative_file = alternatives[0]
                yield f"Using alternative output: {alternative_file.name}"
                shutil.move(str(alternative_file), str(output_path))
            else:
                raise RuntimeError(f"RIFE v4.26 completed but no output found")
        
        # Verify output is valid and validate duration
        if output_path.stat().st_size == 0:
            raise RuntimeError("RIFE v4.26 created empty output file")
        
        # Duration validation with research-validated approach
        output_duration = self._get_video_duration(output_path)
        duration_diff_ms = abs(output_duration - input_duration) * 1000
        
        if duration_diff_ms > 100:  # Research tolerance: <100ms
            yield f"WARNING: Duration mismatch: {duration_diff_ms:.1f}ms difference (input: {input_duration:.3f}s, output: {output_duration:.3f}s)"
        else:
            yield f"SUCCESS: Duration preserved within tolerance: {duration_diff_ms:.1f}ms difference"
        
        yield "RIFE v4.26 processing complete with exact FPS targeting!"
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        import cv2
        try:
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            if fps > 0 and frame_count > 0:
                return frame_count / fps
        except:
            pass
        
        # Fallback to ffprobe
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0
    
    def _process_with_legacy(
        self,
        input_path: Path,
        output_path: Path,
        mode: str,
        multiplier: Optional[str],
        target_fps: Optional[float],
        scale: float,
        uhd_mode: str
    ) -> Generator[str, None, None]:
        """Process with legacy RIFE implementation."""
        
        # Build command - use relative script name since we'll set working directory
        cmd = self._build_command(
            input_path, output_path, mode, multiplier, 
            target_fps, scale, uhd_mode
        )
        
        yield f"Starting legacy RIFE processing..."
        yield f"Working directory: {self.rife_dir}"
        yield f"Command: {' '.join(cmd)}"
        
        # RIFE expects to run from its own directory to find models and dependencies
        
        # V4.2.1 FIX: Enhanced subprocess handling for large files to prevent pipe buffer overflow
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(self.rife_dir),  # Critical: Set working directory to RIFE
            bufsize=1,  # Line buffered to prevent pipe overflow
            universal_newlines=True
        )
        
        last_progress_time = time.time()
        timeout_seconds = 600  # 10 minutes
        recent_output = []  # Track output for error reporting
        
        # V4.2.1 FIX: Enhanced output processing to prevent buffer overflow
        output_lines_processed = 0
        max_output_lines = 10000  # Prevent memory exhaustion from massive output
        
        if process.stdout:
            try:
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if line:
                        output_lines_processed += 1
                        
                        # Prevent memory exhaustion from massive output
                        if output_lines_processed > max_output_lines:
                            recent_output = recent_output[-10:]  # Keep only last 10 lines
                            output_lines_processed = 10
                        
                        recent_output.append(line)
                        if len(recent_output) > 50:  # Increased buffer for large files
                            recent_output.pop(0)
                        
                        # Yield progress updates (less frequently for large files)
                        if output_lines_processed % 10 == 0:  # Every 10th line
                            if '%|' in line or 'it/s' in line:
                                yield line
                            elif 'Error' in line or 'error' in line:
                                yield f"WARNING: {line}"
                        
                        # Check for timeout
                        if time.time() - last_progress_time > timeout_seconds:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                            raise RuntimeError(f"RIFE timeout after {timeout_seconds} seconds")
                        
                        last_progress_time = time.time()
            except Exception as e:
                # V4.2.1 FIX: Handle pipe-related exceptions gracefully
                yield f"WARNING: Output processing issue: {str(e)} - process may still complete"
                # Don't raise, let process complete
        
        # Wait for completion
        return_code = process.wait()
        
        if return_code != 0:
            error_output = '\n'.join(recent_output[-10:]) if recent_output else 'No output captured'
            raise RuntimeError(f"RIFE failed with exit code {return_code}. Last output:\n{error_output}")
        
        # V4.3.0: CRITICAL DURATION VALIDATION - Fix RIFE non-deterministic corruption
        if output_path.exists():
            input_duration = self._get_video_duration(input_path)
            output_duration = self._get_video_duration(output_path)
            duration_drift_ms = abs(output_duration - input_duration) * 1000
            
            yield f"[RIFE] Duration validation: {input_duration:.6f}s -> {output_duration:.6f}s (drift: {duration_drift_ms:.1f}ms)"
            
            if duration_drift_ms > 5:  # More than 5ms drift is unacceptable
                yield f"[RIFE] CRITICAL: Non-deterministic duration corruption detected - applying fix"
                self._apply_rife_duration_fix(output_path, input_duration, output_duration)
                
                # Verify fix worked
                corrected_duration = self._get_video_duration(output_path)
                final_drift_ms = abs(corrected_duration - input_duration) * 1000
                yield f"[RIFE] Fix result: {corrected_duration:.6f}s (final drift: {final_drift_ms:.1f}ms)"
            else:
                yield f"[RIFE] SUCCESS: Duration preserved within tolerance"
        
        # Check for alternative outputs BEFORE throwing error
        if not output_path.exists():
            yield "Expected output not found - checking for alternative naming patterns..."
            
            # Debug: Show what files exist in the directory
            output_dir = output_path.parent
            if output_dir.exists():
                existing_files = list(output_dir.glob("*"))
                yield f"Debug: Output directory contains {len(existing_files)} files:"
                for f in existing_files:
                    if f.is_file():
                        yield f"  - {f.name} ({f.stat().st_size} bytes)"
                
                # Check for alternative naming patterns
                alternatives = self._check_alternative_outputs(input_path, output_path)
                yield f"Debug: Found {len(alternatives)} alternative outputs: {[f.name for f in alternatives]}"
                
                if alternatives:
                    # Move the first alternative to expected location
                    alternative_file = alternatives[0]
                    yield f"Using alternative output: {alternative_file.name}"
                    shutil.move(str(alternative_file), str(output_path))
                    yield f"Renamed {alternative_file.name} -> {output_path.name}"
                else:
                    # No alternatives found - this is a real failure
                    raise RuntimeError(f"RIFE completed but no output found in: {output_dir}")
            else:
                raise RuntimeError(f"RIFE output directory not found: {output_dir}")
        
        # Verify output is valid
        if output_path.stat().st_size == 0:
            file_size = output_path.stat().st_size if output_path.exists() else 0
            raise RuntimeError(f"RIFE created empty output file (size: {file_size} bytes)")
    
    def _apply_rife_duration_fix(self, video_path: Path, target_duration: float, current_duration: float):
        """
        Apply zero-tolerance duration fix to RIFE output.
        Fixes RIFE's non-deterministic duration corruption.
        """
        
        # Calculate exact padding needed
        padding_needed = target_duration - current_duration
        
        print(f"[RIFE FIX] Applying duration correction: {padding_needed*1000:.1f}ms")
        
        # Create temp file for correction
        temp_corrected = video_path.with_suffix('.rife_fixed.mp4')
        
        if padding_needed > 0:
            # RIFE truncated - add padding using tpad filter
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin',
                '-i', str(video_path),
                '-vf', f'tpad=stop_mode=clone:stop_duration={padding_needed:.6f}',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '18',
                str(temp_corrected)
            ]
        else:
            # RIFE extended - trim to exact duration
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin',
                '-i', str(video_path),
                '-t', str(target_duration),
                '-c:v', 'libx264',
                '-preset', 'fast', 
                '-crf', '18',
                str(temp_corrected)
            ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0 and temp_corrected.exists():
            # Replace original with corrected
            video_path.unlink()
            temp_corrected.rename(video_path)
            print(f"[RIFE FIX] SUCCESS: Duration corrected to {target_duration:.6f}s")
        else:
            print(f"[RIFE FIX] FAILED: {result.stderr.decode('utf-8', errors='replace') if result.stderr else 'Unknown error'}")
            temp_corrected.unlink(missing_ok=True)