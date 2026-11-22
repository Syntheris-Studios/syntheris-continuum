"""
Hardware encoding detection and optimization for video processing
"""

import subprocess
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

class HardwareEncoder:
    """
    Detect and utilize hardware video encoders (NVENC, QSV, AMF)
    """
    
    def __init__(self):
        self.encoders = {}
        self.ffmpeg_version = None
        self.detect_capabilities()
    
    def detect_capabilities(self):
        """Detect available hardware encoders and FFmpeg capabilities"""
        self.ffmpeg_version = self._get_ffmpeg_version()
        self.encoders = self._detect_hardware_encoders()
    
    def _get_ffmpeg_version(self) -> Optional[str]:
        """Get FFmpeg version information"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.startswith('ffmpeg version'):
                        return line.split()[2]
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None
    
    def _check_encoder_support(self, encoder_name: str) -> bool:
        """Check if specific encoder is supported by FFmpeg"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return encoder_name in result.stdout
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def _test_encoder_functionality(self, encoder_name: str) -> bool:
        """Test if encoder actually works by encoding a small test video"""
        try:
            # Create a minimal test
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=duration=0.1:size=320x240:rate=1",
                "-c:v", encoder_name, "-f", "null", "-"
            ], capture_output=True, timeout=30)
            
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def _detect_hardware_encoders(self) -> Dict[str, Dict[str, Any]]:
        """Detect all available hardware encoders"""
        encoders = {}
        
        # NVIDIA NVENC Encoders
        nvenc_encoders = {
            "h264_nvenc": {
                "name": "NVIDIA NVENC H.264",
                "codec": "h264",
                "hardware": "nvidia",
                "presets": ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"],
                "max_resolution": "8192x8192",
                "features": ["b_frames", "lookahead", "aq", "2pass"]
            },
            "hevc_nvenc": {
                "name": "NVIDIA NVENC H.265/HEVC",
                "codec": "hevc",
                "hardware": "nvidia",
                "presets": ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"],
                "max_resolution": "8192x8192",
                "features": ["b_frames", "lookahead", "aq", "2pass"]
            }
        }
        
        # Intel QuickSync Encoders
        qsv_encoders = {
            "h264_qsv": {
                "name": "Intel QuickSync H.264",
                "codec": "h264",
                "hardware": "intel",
                "presets": ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-preset", "medium", "-global_quality", "23"],
                "max_resolution": "4096x4096",
                "features": ["lookahead", "2pass"]
            },
            "hevc_qsv": {
                "name": "Intel QuickSync H.265/HEVC", 
                "codec": "hevc",
                "hardware": "intel",
                "presets": ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-preset", "medium", "-global_quality", "23"],
                "max_resolution": "4096x4096",
                "features": ["lookahead", "2pass"]
            }
        }
        
        # AMD AMF Encoders
        amf_encoders = {
            "h264_amf": {
                "name": "AMD AMF H.264",
                "codec": "h264",
                "hardware": "amd",
                "presets": ["speed", "balanced", "quality"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-quality", "balanced", "-rc", "vbr", "-qp_p", "23"],
                "max_resolution": "4096x4096",
                "features": ["preanalysis", "vbaq"]
            },
            "hevc_amf": {
                "name": "AMD AMF H.265/HEVC",
                "codec": "hevc", 
                "hardware": "amd",
                "presets": ["speed", "balanced", "quality"],
                "quality_modes": ["cqp", "vbr", "cbr"],
                "typical_args": ["-quality", "balanced", "-rc", "vbr", "-qp_p", "23"],
                "max_resolution": "4096x4096",
                "features": ["preanalysis", "vbaq"]
            }
        }
        
        all_encoders = {**nvenc_encoders, **qsv_encoders, **amf_encoders}
        
        # Test each encoder
        for encoder_name, encoder_info in all_encoders.items():
            if self._check_encoder_support(encoder_name):
                if self._test_encoder_functionality(encoder_name):
                    encoder_info["available"] = True
                    encoder_info["tested"] = True
                    encoders[encoder_name] = encoder_info
                else:
                    encoder_info["available"] = False
                    encoder_info["tested"] = True
                    encoder_info["error"] = "Encoder exists but failed functionality test"
            else:
                encoder_info["available"] = False
                encoder_info["tested"] = False
                encoder_info["error"] = "Encoder not found in FFmpeg build"
        
        return encoders
    
    def get_available_encoders(self, codec: str = None) -> Dict[str, Dict[str, Any]]:
        """Get list of available encoders, optionally filtered by codec"""
        available = {k: v for k, v in self.encoders.items() if v.get("available", False)}
        
        if codec:
            available = {k: v for k, v in available.items() if v.get("codec") == codec}
        
        return available
    
    def get_optimal_encoder(self, codec: str = "h264", quality: str = "balanced") -> Optional[Dict[str, Any]]:
        """
        Select the best available encoder for given codec and quality
        Priority: NVENC > QSV > AMF > Software fallback
        """
        available = self.get_available_encoders(codec)
        
        if not available:
            return None
        
        # Priority order for hardware vendors
        priority_order = ["nvidia", "intel", "amd"]
        
        for hardware in priority_order:
            for encoder_name, encoder_info in available.items():
                if encoder_info.get("hardware") == hardware:
                    # Customize settings based on quality preference
                    optimized_encoder = encoder_info.copy()
                    optimized_encoder["encoder_name"] = encoder_name
                    optimized_encoder = self._optimize_encoder_settings(optimized_encoder, quality)
                    return optimized_encoder
        
        # If no hardware encoder found, return the first available
        if available:
            encoder_name = list(available.keys())[0]
            encoder_info = available[encoder_name].copy()
            encoder_info["encoder_name"] = encoder_name
            return self._optimize_encoder_settings(encoder_info, quality)
        
        return None
    
    def _optimize_encoder_settings(self, encoder_info: Dict[str, Any], quality: str) -> Dict[str, Any]:
        """Optimize encoder settings based on quality preference"""
        hardware = encoder_info.get("hardware")
        encoder_name = encoder_info.get("encoder_name")
        
        if quality == "fast":
            if hardware == "nvidia":
                encoder_info["optimized_args"] = ["-preset", "p1", "-rc", "cbr", "-b:v", "5000k"]
            elif hardware == "intel":
                encoder_info["optimized_args"] = ["-preset", "veryfast", "-b:v", "5000k"]
            elif hardware == "amd":
                encoder_info["optimized_args"] = ["-quality", "speed", "-rc", "cbr", "-b:v", "5000k"]
                
        elif quality == "balanced":
            if hardware == "nvidia":
                encoder_info["optimized_args"] = ["-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"]
            elif hardware == "intel":
                encoder_info["optimized_args"] = ["-preset", "medium", "-global_quality", "23"]
            elif hardware == "amd":
                encoder_info["optimized_args"] = ["-quality", "balanced", "-rc", "vbr", "-qp_p", "23"]
                
        elif quality == "high":
            if hardware == "nvidia":
                encoder_info["optimized_args"] = ["-preset", "p6", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-aq-strength", "15"]
            elif hardware == "intel":
                encoder_info["optimized_args"] = ["-preset", "slow", "-global_quality", "18", "-look_ahead", "1"]
            elif hardware == "amd":
                encoder_info["optimized_args"] = ["-quality", "quality", "-rc", "vbr", "-qp_p", "18", "-preanalysis", "1"]
                
        elif quality == "lossless":
            if hardware == "nvidia":
                encoder_info["optimized_args"] = ["-preset", "p4", "-rc", "lossless"]
            elif hardware == "intel":
                encoder_info["optimized_args"] = ["-preset", "medium", "-qp", "0"]
            elif hardware == "amd":
                encoder_info["optimized_args"] = ["-quality", "quality", "-qp_p", "0"]
        
        return encoder_info
    
    def build_encode_command(self, 
                           input_path: str, 
                           output_path: str,
                           encoder_info: Dict[str, Any],
                           additional_args: List[str] = None) -> List[str]:
        """Build complete FFmpeg encoding command"""
        encoder_name = encoder_info.get("encoder_name")
        hardware = encoder_info.get("hardware")
        optimized_args = encoder_info.get("optimized_args", [])
        
        cmd = ["ffmpeg", "-y"]
        
        # Hardware acceleration for decoding (if available)
        if hardware == "nvidia":
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        elif hardware == "intel":
            cmd.extend(["-hwaccel", "qsv"])
        elif hardware == "amd":
            cmd.extend(["-hwaccel", "d3d11va"])
        
        # Input
        cmd.extend(["-i", input_path])
        
        # Video encoding
        cmd.extend(["-c:v", encoder_name])
        cmd.extend(optimized_args)
        
        # Additional arguments
        if additional_args:
            cmd.extend(additional_args)
        
        # Output
        cmd.append(output_path)
        
        return cmd
    
    def encode_video(self, 
                    input_path: str, 
                    output_path: str,
                    codec: str = "h264",
                    quality: str = "balanced",
                    additional_args: List[str] = None,
                    progress_callback: Optional[callable] = None) -> bool:
        """
        Encode video using best available hardware encoder
        """
        encoder_info = self.get_optimal_encoder(codec, quality)
        
        if not encoder_info:
            if progress_callback:
                progress_callback("No hardware encoder available, using software fallback")
            return self._software_encode_fallback(input_path, output_path, codec, quality, progress_callback)
        
        cmd = self.build_encode_command(input_path, output_path, encoder_info, additional_args)
        
        if progress_callback:
            progress_callback(f"Encoding with {encoder_info['name']}...")
        
        try:
            # Run encoding with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Monitor progress (simplified - could parse FFmpeg output for detailed progress)
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output and progress_callback:
                    # Parse progress from FFmpeg output (frame=X fps=Y time=Z)
                    if "frame=" in output and "time=" in output:
                        progress_callback(f"Encoding: {output.strip()}")
            
            return_code = process.poll()
            
            if return_code == 0:
                if progress_callback:
                    progress_callback("Hardware encoding completed successfully")
                return True
            else:
                if progress_callback:
                    progress_callback("Hardware encoding failed, trying software fallback")
                return self._software_encode_fallback(input_path, output_path, codec, quality, progress_callback)
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Hardware encoding error: {e}, using software fallback")
            return self._software_encode_fallback(input_path, output_path, codec, quality, progress_callback)
    
    def _software_encode_fallback(self, 
                                 input_path: str, 
                                 output_path: str,
                                 codec: str,
                                 quality: str,
                                 progress_callback: Optional[callable] = None) -> bool:
        """Software encoding fallback when hardware encoding fails"""
        if codec == "h264":
            encoder = "libx264"
        elif codec == "hevc":
            encoder = "libx265"
        else:
            encoder = "libx264"  # Default fallback
        
        # Quality settings for software encoding
        quality_settings = {
            "fast": ["-preset", "ultrafast", "-crf", "28"],
            "balanced": ["-preset", "medium", "-crf", "23"],
            "high": ["-preset", "slow", "-crf", "18"],
            "lossless": ["-preset", "medium", "-crf", "0"]
        }
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", encoder,
            *quality_settings.get(quality, quality_settings["balanced"]),
            output_path
        ]
        
        try:
            if progress_callback:
                progress_callback(f"Software encoding with {encoder}...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                if progress_callback:
                    progress_callback("Software encoding completed successfully")
                return True
            else:
                if progress_callback:
                    progress_callback(f"Software encoding failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            if progress_callback:
                progress_callback("Encoding timed out")
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(f"Software encoding error: {e}")
            return False
    
    def get_encoding_info(self) -> Dict[str, Any]:
        """Get comprehensive encoding capability information"""
        return {
            "ffmpeg_version": self.ffmpeg_version,
            "available_encoders": self.get_available_encoders(),
            "hardware_support": {
                "nvidia": bool([e for e in self.encoders.values() if e.get("hardware") == "nvidia" and e.get("available")]),
                "intel": bool([e for e in self.encoders.values() if e.get("hardware") == "intel" and e.get("available")]),
                "amd": bool([e for e in self.encoders.values() if e.get("hardware") == "amd" and e.get("available")])
            },
            "recommended_encoder": self.get_optimal_encoder("h264", "balanced")
        }
    
    def benchmark_encoders(self, test_video_path: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Benchmark available encoders for performance comparison
        Returns encoding speed and quality metrics
        """
        if not test_video_path:
            # Create a test video if none provided
            test_video_path = self._create_test_video()
        
        results = {}
        available_encoders = self.get_available_encoders()
        
        for encoder_name, encoder_info in available_encoders.items():
            try:
                import time
                start_time = time.time()
                
                temp_output = f"benchmark_output_{encoder_name}.mp4"
                
                cmd = self.build_encode_command(test_video_path, temp_output, encoder_info)
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                
                end_time = time.time()
                encoding_time = end_time - start_time
                
                if result.returncode == 0:
                    # Get output file size
                    output_size = Path(temp_output).stat().st_size if Path(temp_output).exists() else 0
                    
                    results[encoder_name] = {
                        "success": True,
                        "encoding_time": encoding_time,
                        "output_size_mb": output_size / (1024 * 1024),
                        "speed_fps": 30 / encoding_time if encoding_time > 0 else 0,  # Assuming 30fps test video
                        "hardware": encoder_info.get("hardware"),
                        "name": encoder_info.get("name")
                    }
                else:
                    results[encoder_name] = {
                        "success": False,
                        "error": result.stderr.decode() if result.stderr else "Unknown error",
                        "hardware": encoder_info.get("hardware"),
                        "name": encoder_info.get("name")
                    }
                
                # Cleanup
                if Path(temp_output).exists():
                    Path(temp_output).unlink()
                    
            except Exception as e:
                results[encoder_name] = {
                    "success": False,
                    "error": str(e),
                    "hardware": encoder_info.get("hardware"),
                    "name": encoder_info.get("name")
                }
        
        return results
    
    def _create_test_video(self) -> str:
        """Create a small test video for benchmarking"""
        test_path = "benchmark_test_video.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=1920x1080:rate=30",
            "-c:v", "libx264", "-preset", "ultrafast",
            test_path
        ]
        
        subprocess.run(cmd, capture_output=True)
        return test_path