"""
Pipeline Fortification Module for Syntheris Video Processor
Implements intelligent retry logic, resource management, and bulletproof error handling
Target: 99.5%+ success rate through adaptive processing strategies
"""

from __future__ import annotations
import subprocess
import json
import time
import gc
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Generator
from dataclasses import dataclass
from enum import Enum
import logging


class ProcessingMode(Enum):
    """Processing quality modes for resource management"""
    ULTRA = "ultra"  # Full resolution, maximum quality
    HIGH = "high"    # 90% resolution, high quality
    MEDIUM = "medium"  # 75% resolution, balanced
    LOW = "low"      # 60% resolution, resource-constrained
    SAFE = "safe"    # 50% resolution, failsafe mode


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    initial_delay: float = 2.0
    backoff_factor: float = 2.0
    resolution_scale_factor: float = 0.85  # Scale down by 15% per retry
    memory_cleanup_between_retries: bool = True
    fallback_to_alternative_backend: bool = True


@dataclass
class ResourceLimits:
    """Dynamic resource allocation limits"""
    max_vram_usage_percent: float = 80.0
    max_resolution: Tuple[int, int] = (3840, 2160)  # 4K max
    max_segment_duration: float = 10.0  # seconds
    min_free_disk_gb: float = 5.0
    process_timeout: int = 1800  # 30 minutes


class PipelineFortification:
    """
    Main fortification class implementing bulletproof video processing pipeline
    with intelligent retry logic and resource management
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.retry_config = RetryConfig()
        self.resource_limits = ResourceLimits()
        self.performance_metrics: Dict[str, Any] = {}
        self.failure_context: List[Dict[str, Any]] = []
        
    def _setup_logger(self) -> logging.Logger:
        """Setup comprehensive logging system"""
        logger = logging.getLogger("PipelineFortification")
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler for detailed logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"fortification_{int(time.time())}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def process_with_retry(
        self,
        process_func: callable,
        input_path: Path,
        output_path: Path,
        **kwargs
    ) -> Generator[str, None, Path]:
        """
        Process with intelligent retry logic and progressive resource scaling
        
        Args:
            process_func: Processing function to execute
            input_path: Input video path
            output_path: Output video path
            **kwargs: Additional processing parameters
            
        Yields:
            Progress messages
            
        Returns:
            Path to processed output
        """
        
        mode = ProcessingMode.ULTRA
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries):
            try:
                yield f"Processing attempt {attempt + 1}/{self.retry_config.max_retries} in {mode.value} mode"
                
                # Pre-processing validation
                validation_result = self.validate_preprocessing(input_path, mode)
                if not validation_result['valid']:
                    yield f"Validation failed: {validation_result['message']}"
                    mode = self._downgrade_mode(mode)
                    continue
                
                # Adjust parameters based on mode
                adjusted_kwargs = self._adjust_parameters_for_mode(kwargs, mode)
                
                # Execute processing
                start_time = time.time()
                result = yield from self._execute_with_monitoring(
                    process_func,
                    input_path,
                    output_path,
                    **adjusted_kwargs
                )
                
                # Record success metrics
                self.performance_metrics[f"attempt_{attempt}"] = {
                    'mode': mode.value,
                    'duration': time.time() - start_time,
                    'success': True
                }
                
                yield f"Successfully processed in {mode.value} mode"
                return result
                
            except Exception as e:
                last_exception = e
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                
                # Capture failure context
                self.failure_context.append({
                    'attempt': attempt + 1,
                    'mode': mode.value,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                
                # Analyze failure and determine strategy
                strategy = self._analyze_failure(e)
                
                if attempt < self.retry_config.max_retries - 1:
                    # Clean up resources
                    if self.retry_config.memory_cleanup_between_retries:
                        yield "Cleaning up resources..."
                        self._cleanup_resources()
                    
                    # Apply retry strategy
                    if strategy == 'downgrade':
                        mode = self._downgrade_mode(mode)
                        yield f"Downgrading to {mode.value} mode for next attempt"
                    
                    # Exponential backoff
                    delay = self.retry_config.initial_delay * (
                        self.retry_config.backoff_factor ** attempt
                    )
                    yield f"Waiting {delay:.1f} seconds before retry..."
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    if self.retry_config.fallback_to_alternative_backend:
                        yield "Attempting fallback processing..."
                        try:
                            yield from self._fallback_processing(
                                input_path,
                                output_path,
                                **kwargs
                            )
                            return
                        except Exception as fallback_error:
                            self.logger.error(f"Fallback also failed: {fallback_error}")
        
        # All attempts exhausted
        raise RuntimeError(
            f"Processing failed after {self.retry_config.max_retries} attempts. "
            f"Last error: {last_exception}"
        )
    
    def validate_preprocessing(
        self,
        input_path: Path,
        mode: ProcessingMode
    ) -> Dict[str, Any]:
        """
        Validate input video and system resources before processing
        
        Returns:
            Dictionary with validation results
        """
        
        result = {
            'valid': True,
            'message': 'Validation passed',
            'details': {}
        }
        
        # Check input file
        if not input_path.exists():
            result['valid'] = False
            result['message'] = f"Input file not found: {input_path}"
            return result
        
        # Check file integrity
        integrity = self._check_video_integrity(input_path)
        if not integrity['valid']:
            result['valid'] = False
            result['message'] = integrity['message']
            result['details']['integrity'] = integrity
            return result
        
        # Check GPU memory if using CUDA
        if self._is_cuda_available():
            vram_check = self._check_vram_availability(mode)
            if not vram_check['sufficient']:
                result['valid'] = False
                result['message'] = f"Insufficient VRAM: {vram_check['message']}"
                result['details']['vram'] = vram_check
                return result
        
        # Check disk space
        disk_check = self._check_disk_space()
        if not disk_check['sufficient']:
            result['valid'] = False
            result['message'] = f"Insufficient disk space: {disk_check['message']}"
            result['details']['disk'] = disk_check
            return result
        
        result['details'] = {
            'integrity': integrity,
            'vram': vram_check if self._is_cuda_available() else {'sufficient': True},
            'disk': disk_check
        }
        
        return result
    
    def _check_video_integrity(self, video_path: Path) -> Dict[str, Any]:
        """Check video file integrity using FFprobe"""
        
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name,r_frame_rate',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'valid': False,
                    'message': f"FFprobe failed: {result.stderr}"
                }
            
            data = json.loads(result.stdout)
            if not data.get('streams'):
                return {
                    'valid': False,
                    'message': "No video streams found"
                }
            
            stream = data['streams'][0]
            
            # Check for corrupted frames
            frame_check_cmd = [
                'ffmpeg', '-v', 'error',
                '-i', str(video_path),
                '-f', 'null', '-'
            ]
            
            frame_result = subprocess.run(
                frame_check_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            has_errors = 'error' in frame_result.stderr.lower()
            
            return {
                'valid': not has_errors,
                'message': 'Video integrity check passed' if not has_errors else 'Corrupted frames detected',
                'width': stream.get('width', 0),
                'height': stream.get('height', 0),
                'duration': stream.get('duration', 0),
                'codec': stream.get('codec_name', 'unknown'),
                'fps': stream.get('r_frame_rate', '0/1')
            }
            
        except subprocess.TimeoutExpired:
            return {
                'valid': False,
                'message': "Video integrity check timed out"
            }
        except Exception as e:
            return {
                'valid': False,
                'message': f"Integrity check failed: {str(e)}"
            }
    
    def _check_vram_availability(self, mode: ProcessingMode) -> Dict[str, Any]:
        """Check GPU VRAM availability"""
        
        try:
            import torch
            
            if not torch.cuda.is_available():
                return {
                    'sufficient': True,
                    'message': 'CUDA not available, using CPU'
                }
            
            # Get VRAM info
            total_vram = torch.cuda.get_device_properties(0).total_memory
            reserved_vram = torch.cuda.memory_reserved(0)
            allocated_vram = torch.cuda.memory_allocated(0)
            free_vram = total_vram - reserved_vram
            
            # Estimate required VRAM based on mode
            required_vram_gb = {
                ProcessingMode.ULTRA: 8.0,
                ProcessingMode.HIGH: 6.0,
                ProcessingMode.MEDIUM: 4.0,
                ProcessingMode.LOW: 2.0,
                ProcessingMode.SAFE: 1.0
            }
            
            required = required_vram_gb.get(mode, 4.0) * (1024 ** 3)
            
            sufficient = free_vram >= required
            
            return {
                'sufficient': sufficient,
                'message': f"Free VRAM: {free_vram / (1024**3):.2f}GB, Required: {required / (1024**3):.2f}GB",
                'total_gb': total_vram / (1024**3),
                'free_gb': free_vram / (1024**3),
                'required_gb': required / (1024**3)
            }
            
        except ImportError:
            return {
                'sufficient': True,
                'message': 'PyTorch not available for VRAM check'
            }
        except Exception as e:
            self.logger.warning(f"VRAM check failed: {e}")
            return {
                'sufficient': True,
                'message': f"VRAM check failed: {e}"
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        
        try:
            import shutil
            
            stat = shutil.disk_usage(Path.cwd())
            free_gb = stat.free / (1024 ** 3)
            
            sufficient = free_gb >= self.resource_limits.min_free_disk_gb
            
            return {
                'sufficient': sufficient,
                'message': f"Free disk: {free_gb:.2f}GB",
                'free_gb': free_gb,
                'total_gb': stat.total / (1024 ** 3)
            }
            
        except Exception as e:
            self.logger.warning(f"Disk space check failed: {e}")
            return {
                'sufficient': True,
                'message': f"Disk check failed: {e}"
            }
    
    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _adjust_parameters_for_mode(
        self,
        params: Dict[str, Any],
        mode: ProcessingMode
    ) -> Dict[str, Any]:
        """Adjust processing parameters based on mode"""
        
        adjusted = params.copy()
        
        # Resolution scaling based on mode
        scale_factors = {
            ProcessingMode.ULTRA: 1.0,
            ProcessingMode.HIGH: 0.9,
            ProcessingMode.MEDIUM: 0.75,
            ProcessingMode.LOW: 0.6,
            ProcessingMode.SAFE: 0.5
        }
        
        adjusted['scale'] = scale_factors.get(mode, 1.0)
        
        # UHD mode adjustment
        if mode in [ProcessingMode.LOW, ProcessingMode.SAFE]:
            adjusted['uhd_mode'] = 'off'
        
        # Multiplier adjustment for RIFE
        if mode == ProcessingMode.SAFE:
            adjusted['multiplier'] = '2x'  # Minimum interpolation
        
        return adjusted
    
    def _execute_with_monitoring(
        self,
        process_func: callable,
        input_path: Path,
        output_path: Path,
        **kwargs
    ) -> Generator[str, None, Path]:
        """Execute processing with resource monitoring"""
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Execute the processing function
            result = yield from process_func(input_path, output_path, **kwargs)
            
            # Record performance metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            self.performance_metrics['last_execution'] = {
                'duration': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'parameters': kwargs
            }
            
            return result
            
        except Exception as e:
            # Capture detailed error context
            self.logger.error(f"Execution failed: {e}", exc_info=True)
            raise
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def _cleanup_resources(self):
        """Clean up resources between retries"""
        
        # Force garbage collection
        gc.collect()
        
        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass
        
        # Clean temp directories
        temp_dirs = [
            Path(tempfile.gettempdir()) / "syntheris_temp",
            Path.cwd() / "temp"
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                try:
                    # Remove old temp files (older than 1 hour)
                    cutoff_time = time.time() - 3600
                    for item in temp_dir.iterdir():
                        if item.is_file() and item.stat().st_mtime < cutoff_time:
                            item.unlink()
                except Exception as e:
                    self.logger.warning(f"Temp cleanup failed: {e}")
    
    def _analyze_failure(self, exception: Exception) -> str:
        """
        Analyze failure and determine retry strategy
        
        Returns:
            Strategy: 'downgrade', 'retry', or 'abort'
        """
        
        error_str = str(exception).lower()
        
        # GPU memory errors - downgrade resolution
        if any(keyword in error_str for keyword in [
            'cuda out of memory',
            'gpu memory',
            'vram',
            '3221226505'  # Windows GPU crash code
        ]):
            return 'downgrade'
        
        # Corrupted frame errors - retry with cleanup
        if any(keyword in error_str for keyword in [
            'corrupted',
            'invalid frame',
            'decode error'
        ]):
            return 'retry'
        
        # Exit code 1 - general failure, try downgrade
        if 'exit code 1' in error_str:
            return 'downgrade'
        
        # Default to downgrade for unknown errors
        return 'downgrade'
    
    def _downgrade_mode(self, current_mode: ProcessingMode) -> ProcessingMode:
        """Downgrade processing mode for retry"""
        
        mode_order = [
            ProcessingMode.ULTRA,
            ProcessingMode.HIGH,
            ProcessingMode.MEDIUM,
            ProcessingMode.LOW,
            ProcessingMode.SAFE
        ]
        
        try:
            current_idx = mode_order.index(current_mode)
            next_idx = min(current_idx + 1, len(mode_order) - 1)
            return mode_order[next_idx]
        except ValueError:
            return ProcessingMode.SAFE
    
    def _fallback_processing(
        self,
        input_path: Path,
        output_path: Path,
        **kwargs
    ) -> Generator[str, None, Path]:
        """Fallback processing with minimal resources"""
        
        yield "Executing fallback processing with minimal resources..."
        
        # Use basic FFmpeg interpolation as fallback
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-filter:v', 'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.resource_limits.process_timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Fallback processing failed: {result.stderr}")
            
            yield "Fallback processing completed successfully"
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Fallback processing timed out")


class EnhancedConcatenation:
    """Enhanced concatenation with robust validation and fallbacks"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("EnhancedConcatenation")
    
    def concatenate_with_validation(
        self,
        segment_paths: List[Path],
        output_path: Path,
        crossfade: bool = False,
        crossfade_duration: float = 0.1
    ) -> Path:
        """
        Concatenate segments with validation and fallback methods
        
        Args:
            segment_paths: List of segment paths
            output_path: Output video path
            crossfade: Apply crossfade between segments
            crossfade_duration: Crossfade duration in seconds
            
        Returns:
            Path to concatenated video
        """
        
        if not segment_paths:
            raise ValueError("No segments to concatenate")
        
        # Validate all segments first
        valid_segments = []
        for segment in segment_paths:
            if self._validate_segment(segment):
                valid_segments.append(segment)
            else:
                self.logger.warning(f"Skipping invalid segment: {segment}")
        
        if not valid_segments:
            raise ValueError("No valid segments to concatenate")
        
        if len(valid_segments) == 1:
            # Single segment, just copy
            shutil.copy2(valid_segments[0], output_path)
            return output_path
        
        # Try primary concatenation method
        try:
            return self._concat_primary(valid_segments, output_path, crossfade, crossfade_duration)
        except Exception as e:
            self.logger.warning(f"Primary concatenation failed: {e}")
            
            # Try fallback method
            try:
                return self._concat_fallback(valid_segments, output_path)
            except Exception as e2:
                self.logger.error(f"Fallback concatenation also failed: {e2}")
                
                # Last resort - re-encode everything
                return self._concat_reencode(valid_segments, output_path)
    
    def _validate_segment(self, segment_path: Path) -> bool:
        """Validate a video segment"""
        
        if not segment_path.exists():
            return False
        
        if segment_path.stat().st_size == 0:
            return False
        
        # Check with FFprobe
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(segment_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False
            
            data = json.loads(result.stdout)
            return bool(data.get('streams'))
            
        except Exception:
            return False
    
    def _concat_primary(
        self,
        segments: List[Path],
        output_path: Path,
        crossfade: bool,
        crossfade_duration: float
    ) -> Path:
        """Primary concatenation method with concat demuxer"""
        
        # Create concat list with UTF-8 encoding
        concat_list = output_path.parent / 'concat.txt'
        
        with open(concat_list, 'w', encoding='utf-8') as f:
            for segment in segments:
                # Properly escape paths
                escaped_path = str(segment).replace('\\', '/').replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        try:
            if crossfade and len(segments) > 1:
                # Build crossfade filter
                filter_complex = self._build_crossfade_filter(len(segments), crossfade_duration)
                
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_list),
                    '-filter_complex', filter_complex,
                    '-map', '[v]',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '18',
                    str(output_path)
                ]
            else:
                # Simple concatenation
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_list),
                    '-c', 'copy',
                    str(output_path)
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
            
            return output_path
            
        finally:
            concat_list.unlink(missing_ok=True)
    
    def _concat_fallback(self, segments: List[Path], output_path: Path) -> Path:
        """Fallback concatenation using filter_complex"""
        
        # Build input arguments
        inputs = []
        for segment in segments:
            inputs.extend(['-i', str(segment)])
        
        # Build filter for concatenation
        filter_parts = []
        for i in range(len(segments)):
            filter_parts.append(f"[{i}:v:0]")
        
        filter_str = ''.join(filter_parts) + f"concat=n={len(segments)}:v=1:a=0[v]"
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin'
        ] + inputs + [
            '-filter_complex', filter_str,
            '-map', '[v]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Fallback concat failed: {result.stderr}")
        
        return output_path
    
    def _concat_reencode(self, segments: List[Path], output_path: Path) -> Path:
        """Last resort - re-encode all segments to ensure compatibility"""
        
        self.logger.info("Using re-encode concatenation as last resort")
        
        # Re-encode all segments to ensure compatibility
        temp_dir = output_path.parent / f"reencode_{int(time.time())}"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            reencoded_segments = []
            
            for i, segment in enumerate(segments):
                reencoded = temp_dir / f"segment_{i:03d}.mp4"
                
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-i', str(segment),
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '18',
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',  # Force consistent framerate
                    str(reencoded)
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                reencoded_segments.append(reencoded)
            
            # Now concatenate the re-encoded segments
            return self._concat_primary(reencoded_segments, output_path, False, 0)
            
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _build_crossfade_filter(self, segment_count: int, duration: float) -> str:
        """Build crossfade filter for segments"""
        
        if segment_count < 2:
            return "[0:v]"
        
        filter_parts = []
        
        for i in range(segment_count - 1):
            if i == 0:
                filter_parts.append(
                    f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset=0[v1]"
                )
            else:
                filter_parts.append(
                    f"[v{i}][{i+1}:v]xfade=transition=fade:duration={duration}:offset=0[v{i+1}]"
                )
        
        # Join with semicolons and add final output
        filter_str = ';'.join(filter_parts)
        if segment_count > 2:
            filter_str += f";[v{segment_count-1}]"
        else:
            filter_str += ";[v1]"
        
        return filter_str