"""
Media handling utilities for FFmpeg operations.
Provides audio/video manipulation, format conversion, and filtering.
"""

from __future__ import annotations
import subprocess
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


class MediaHandler:
    """Handles media operations like audio extraction, muxing, and format conversion."""
    
    def extract_audio(self, video_path: Path, audio_path: Path) -> Optional[Path]:
        """
        Extract audio track from video.
        
        Args:
            video_path: Source video file
            audio_path: Output audio file path
            
        Returns:
            Path to extracted audio or None if no audio
        """
        
        # Check if video has audio
        if not self.has_audio(video_path):
            return None
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'copy',  # Copy audio codec
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, check=False)
        
        if result.returncode == 0 and audio_path.exists():
            return audio_path
        
        # Fallback to AAC encoding if copy fails
        cmd[6] = 'aac'  # Replace 'copy' with 'aac'
        cmd.extend(['-b:a', '192k'])
        
        result = subprocess.run(cmd, capture_output=True, check=False)
        
        return audio_path if audio_path.exists() else None
    
    def mux_audio(
        self,
        source_video: Path,
        processed_video: Path,
        output_path: Path
    ) -> Path:
        """
        Mux audio from source video into processed video.
        
        Args:
            source_video: Original video with audio
            processed_video: Processed video without audio
            output_path: Output path for muxed video
            
        Returns:
            Path to output video with audio
        """
        
        # Extract audio from source
        temp_audio = output_path.parent / 'temp_audio.aac'
        extracted_audio = self.extract_audio(source_video, temp_audio)
        
        if not extracted_audio:
            # No audio to mux, just copy video
            shutil.copy2(processed_video, output_path)
            return output_path
        
        try:
            # Get pre-mux duration for validation
            pre_mux_duration = self.get_precise_duration(processed_video)
            print(f"[AUDIO MUX] Input video duration: {pre_mux_duration:.3f}s")
            
            # Research-validated audio mux with precision timestamp handling
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin',
                '-i', str(processed_video),
                '-i', str(extracted_audio),
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-copyts',  # Research: Preserve video timestamps
                '-avoid_negative_ts', 'disabled',  # Research: Don't modify timestamps
                '-shortest',  # Research: Use shortest stream to prevent extension
                '-map', '0:v:0',
                '-map', '1:a:0',
                str(output_path)
            ]
            
            # V4.2.1 FIX: Enhanced large file handling with progressive timeout scaling
            file_size_mb = processed_video.stat().st_size / (1024 * 1024)
            timeout_seconds = min(600, max(300, int(file_size_mb * 10)))  # Scale timeout with file size
            
            try:
                print(f"[AUDIO MUX] Processing {file_size_mb:.1f}MB file with {timeout_seconds}s timeout")
                result = subprocess.run(cmd, check=True, capture_output=True, timeout=timeout_seconds)
                print(f"[AUDIO MUX] SUCCESS: Standard mux successful")
            except subprocess.TimeoutExpired:
                print(f"[AUDIO MUX] WARNING: Timeout after {timeout_seconds}s - trying fallback without timestamp preservation")
                # Fallback: Remove complex timestamp options for large files
                cmd_fallback = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-i', str(processed_video),
                    '-i', str(extracted_audio),
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-shortest',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    str(output_path)
                ]
                subprocess.run(cmd_fallback, check=True, capture_output=True, timeout=timeout_seconds)
                print(f"[AUDIO MUX] SUCCESS: Fallback mux successful")
            except subprocess.CalledProcessError as e:
                print(f"[AUDIO MUX] FAIL: FFmpeg error: {e}")
                print(f"[AUDIO MUX] WARNING: Copying video without audio as emergency fallback")
                shutil.copy2(processed_video, output_path)
                return output_path
            
            # Validate post-mux duration with research tolerance
            post_mux_duration = self.get_precise_duration(output_path)
            duration_diff_ms = abs(post_mux_duration - pre_mux_duration) * 1000
            
            print(f"[AUDIO MUX] Output duration: {post_mux_duration:.3f}s")
            print(f"[AUDIO MUX] Duration difference: {duration_diff_ms:.1f}ms")
            
            if duration_diff_ms <= 100:
                print(f"[AUDIO MUX] SUCCESS: Duration preserved within research tolerance")
            else:
                print(f"[AUDIO MUX] WARNING: Duration corruption detected: {duration_diff_ms:.1f}ms exceeds 100ms tolerance")
            
        finally:
            # Clean up temp audio
            temp_audio.unlink(missing_ok=True)
        
        return output_path
    
    def analyze_audio_properties(self, audio_path: Path) -> dict:
        """Analyze audio track properties for optimization."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration:stream=codec_name,bit_rate,sample_rate,channels',
            '-of', 'json', str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            duration = float(data.get('format', {}).get('duration', 0))
            
            audio_stream = {}
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            return {
                'duration': duration,
                'codec': audio_stream.get('codec_name', 'unknown'),
                'bitrate': int(audio_stream.get('bit_rate', 0)) // 1000,  # Convert to kbps
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0))
            }
            
        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
            return {
                'duration': 0,
                'codec': 'unknown',
                'bitrate': 0,
                'sample_rate': 0,
                'channels': 0
            }

    def has_audio(self, video_path: Path) -> bool:
        """Check if video has audio stream."""
        
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    return True
                    
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass
        
        return False
    
    def mux_audio_with_sync(self, source: Path, video: Path, output: Path, 
                            use_shortest: bool = True, audio_codec: str = 'copy',
                            reencode_audio: bool = False) -> None:
        """
        Mux audio with sync preservation and optional re-encoding.
        
        Args:
            source: Original video with audio
            video: Processed video without audio
            output: Output path for muxed video
            use_shortest: Use shortest stream duration
            audio_codec: Audio codec to use
            reencode_audio: Whether to re-encode audio
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(video), 
            '-i', str(source),
            '-c:v', 'copy',
            '-map', '0:v:0', '-map', '1:a:0?'  # Map video from first, audio from second (if exists)
        ]
        
        # Audio codec handling
        if reencode_audio:
            cmd.extend(['-c:a', 'aac', '-b:a', '192k', '-ar', '48000'])
        else:
            cmd.extend(['-c:a', audio_codec])
        
        if use_shortest:
            cmd.extend(['-shortest'])
        
        # Add audio sync flags
        cmd.extend([
            '-async', '1',  # Audio sync compensation
            '-vsync', 'cfr',  # Ensure constant frame rate
            '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
            str(output)
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback to simpler mux if enhanced version fails
            self.mux_audio(source, video, output)
    
    def normalize_cfr(self, video_path: Path, output_path: Path) -> Path:
        """
        Normalize video to constant frame rate and remove duplicates.
        
        Args:
            video_path: Input video path
            output_path: Output video path
            
        Returns:
            Path to normalized video
        """
        
        # Get source FPS
        fps = self.get_video_fps(video_path)
        
        # Build mpdecimate filter for duplicate removal
        filter_complex = f"mpdecimate=hi=6400:lo=1200:frac=0.33,setpts=N/FRAME_RATE/TB"
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(video_path),
            '-filter:v', filter_complex,
            '-r', str(fps),  # Force constant frame rate
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-an',  # No audio during processing
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def get_video_fps(self, video_path: Path) -> float:
        """Get video frame rate."""
        
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    # Parse r_frame_rate (e.g., "30/1" -> 30.0)
                    fps_str = stream.get('r_frame_rate', '30/1')
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        return float(num) / float(den)
                    return float(fps_str)
                    
        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
            pass
        
        return 30.0  # Default fallback
    
    def get_precise_duration(self, video_path: Path) -> float:
        """Get precise video duration using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError):
            pass
        
        return 0.0
    
    def validate_audio_sync_robust(self, video_path: Path) -> dict:
        """Validate audio-video sync with robust error handling."""
        try:
            # Get video and audio stream durations
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'stream=duration,codec_type',
                '-of', 'json',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return {
                    'is_synced': False,
                    'sync_drift_ms': 999999,
                    'error': 'Failed to probe streams'
                }
            
            data = json.loads(result.stdout)
            
            video_duration = 0.0
            audio_duration = 0.0
            has_video = False
            has_audio = False
            
            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type')
                if 'duration' in stream:
                    duration = float(stream['duration'])
                    if codec_type == 'video':
                        video_duration = duration
                        has_video = True
                    elif codec_type == 'audio':
                        audio_duration = duration
                        has_audio = True
            
            # If no audio stream, consider it synced (video-only)
            if not has_audio:
                return {
                    'is_synced': True,
                    'sync_drift_ms': 0,
                    'video_duration': video_duration,
                    'audio_duration': 0,
                    'has_audio': False
                }
            
            # Calculate sync drift
            sync_drift_ms = abs(video_duration - audio_duration) * 1000
            
            return {
                'is_synced': sync_drift_ms <= 40,  # 40ms tolerance
                'sync_drift_ms': sync_drift_ms,
                'video_duration': video_duration,
                'audio_duration': audio_duration,
                'has_audio': True
            }
            
        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError, KeyError) as e:
            return {
                'is_synced': False,
                'sync_drift_ms': 999999,
                'error': str(e)
            }


class FFmpegProcessor:
    """Handles FFmpeg-based video processing operations."""
    
    def apply_deflicker(self, input_path: Path, output_path: Path) -> Path:
        """
        Apply deflicker filter to reduce flicker in video.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            
        Returns:
            Path to deflickered video
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-vf', 'deflicker=mode=pm:size=5',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def convert_to_h264(
        self,
        input_path: Path,
        output_path: Path,
        crf: int = 18
    ) -> Path:
        """
        Convert video to H.264 format.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            crf: Constant Rate Factor (0-51, lower is better quality)
            
        Returns:
            Path to converted video
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', str(crf),
            '-pix_fmt', 'yuv420p',  # Compatibility
            '-c:a', 'aac',
            '-b:a', '192k',
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        fps: Optional[float] = None
    ) -> int:
        """
        Extract frames from video.
        
        Args:
            video_path: Input video path
            output_dir: Directory for extracted frames
            fps: Frame extraction rate (None for all frames)
            
        Returns:
            Number of frames extracted
        """
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            'ffmpeg', '-hide_banner', '-nostdin',
            '-i', str(video_path)
        ]
        
        if fps:
            cmd.extend(['-vf', f'fps={fps}'])
        
        cmd.extend([
            str(output_dir / 'frame_%06d.png')
        ])
        
        subprocess.run(cmd, check=True)
        
        # Count extracted frames
        return len(list(output_dir.glob('frame_*.png')))
    
    def create_video_from_frames(
        self,
        frames_dir: Path,
        output_path: Path,
        fps: float = 30.0,
        pattern: str = 'frame_%06d.png'
    ) -> Path:
        """
        Create video from image sequence.
        
        Args:
            frames_dir: Directory containing frames
            output_path: Output video path
            fps: Output frame rate
            pattern: Frame filename pattern
            
        Returns:
            Path to created video
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-framerate', str(fps),
            '-i', str(frames_dir / pattern),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def apply_pts_reset(self, input_path: Path, output_path: Path, preserve_audio: bool = True) -> Path:
        """
        Apply setpts=PTS-STARTPTS to prevent timestamp accumulation.
        
        Research: "Resetting PTS to start from zero (setpts=PTS-STARTPTS) prevents 
        timestamp accumulation errors"
        
        Args:
            input_path: Input video path
            output_path: Output video path
            preserve_audio: Whether to preserve audio track
            
        Returns:
            Path to processed video
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-vf', 'setpts=PTS-STARTPTS',  # Reset video timestamps
            '-avoid_negative_ts', 'disabled',  # Research: prevent auto-adjustments
            '-copyts',  # Preserve original timestamp precision
        ]
        
        if preserve_audio:
            cmd.extend(['-c:a', 'copy'])  # Copy audio without re-encoding
        else:
            cmd.extend(['-an'])  # No audio
        
        cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '18', str(output_path)])
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def apply_dual_pts_reset(self, input_path: Path, output_path: Path, duration_offset: float = 0.0) -> Path:
        """
        Apply PTS reset with duration offset for concatenation.
        
        Research: "For concatenation, manual PTS adjustment ensures seamless transitions: 
        the second video requires setpts=PTS-STARTPTS+DURATION1/TB"
        
        Args:
            input_path: Input video path
            output_path: Output video path
            duration_offset: Duration offset for chaining (in seconds)
            
        Returns:
            Path to processed video
        """
        
        if duration_offset > 0:
            # Calculate timebase offset (assuming 1/1000 timebase)
            tb_offset = int(duration_offset * 1000)
            setpts_expr = f"PTS-STARTPTS+{tb_offset}/TB"
        else:
            setpts_expr = "PTS-STARTPTS"
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-vf', f'setpts={setpts_expr}',
            '-af', f'asetpts={setpts_expr}',  # Also reset audio timestamps
            '-avoid_negative_ts', 'disabled',
            '-copyts',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def normalize_timestamps(self, input_path: Path, output_path: Path) -> Path:
        """
        Normalize timestamps for consistent timing across pipeline stages.
        
        Research: "Enable precise timing control through -copyts to preserve 
        original timestamps and -avoid_negative_ts disabled"
        
        Args:
            input_path: Input video path
            output_path: Output video path
            
        Returns:
            Path to normalized video
        """
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(input_path),
            '-c', 'copy',  # Stream copy to avoid quality loss
            '-avoid_negative_ts', 'make_zero',  # Normalize negative timestamps
            '-fflags', '+genpts',  # Generate missing PTS values
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return output_path
        except subprocess.CalledProcessError:
            # Fallback: re-encode with timestamp reset
            return self.apply_pts_reset(input_path, output_path)
    
    def validate_audio_sync_robust(self, video_path: Path) -> dict:
        """Production-grade sync validation using PTS analysis."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'packet=pts_time,stream_index', '-select_streams', 'v:0,a:0',
            '-of', 'json', str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            data = json.loads(result.stdout)
            
            video_pts = []
            audio_pts = []
            
            for packet in data.get('packets', []):
                stream_idx = int(packet.get('stream_index', -1))
                pts_time = float(packet.get('pts_time', 0))
                
                if stream_idx == 0:  # Video stream
                    video_pts.append(pts_time)
                elif stream_idx == 1:  # Audio stream
                    audio_pts.append(pts_time)
            
            # Analyze last PTS for each stream - more reliable than duration
            video_end = max(video_pts) if video_pts else 0
            audio_end = max(audio_pts) if audio_pts else 0
            sync_drift_ms = abs(video_end - audio_end) * 1000
            
            return {
                'video_end_pts': video_end,
                'audio_end_pts': audio_end,
                'sync_drift_ms': sync_drift_ms,
                'is_synced': sync_drift_ms <= 40,
                'packet_count': {'video': len(video_pts), 'audio': len(audio_pts)}
            }
            
        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError, subprocess.TimeoutExpired):
            # Fallback to duration-based validation
            return self._fallback_sync_validation(video_path)
    
    def _fallback_sync_validation(self, video_path: Path) -> dict:
        """Fallback sync validation using stream duration."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'stream=duration,codec_type', '-of', 'json', str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            video_duration = 0
            audio_duration = 0
            
            for stream in data.get('streams', []):
                duration = float(stream.get('duration', 0))
                codec_type = stream.get('codec_type')
                
                if codec_type == 'video':
                    video_duration = duration
                elif codec_type == 'audio':
                    audio_duration = duration
            
            sync_drift_ms = abs(video_duration - audio_duration) * 1000
            
            return {
                'video_end_pts': video_duration,
                'audio_end_pts': audio_duration, 
                'sync_drift_ms': sync_drift_ms,
                'is_synced': sync_drift_ms <= 40,
                'fallback_method': True
            }
            
        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
            return {
                'video_end_pts': 0,
                'audio_end_pts': 0,
                'sync_drift_ms': 0,
                'is_synced': False,
                'validation_failed': True
            }

    def get_precise_duration(self, video_path: Path) -> float:
        """
        Get precise duration using research-validated approach.
        
        Research: "Container duration from format metadata often differs from 
        stream duration calculated from frame counts and rates"
        
        Args:
            video_path: Video file path
            
        Returns:
            Duration in seconds (calculated from frame count and rate)
        """
        
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,r_frame_rate',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            if 'streams' in data and data['streams']:
                stream = data['streams'][0]
                
                # Get frame count and rate
                frame_count = int(stream.get('nb_frames', 0))
                fps_str = stream.get('r_frame_rate', '30/1')
                
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den)
                else:
                    fps = float(fps_str)
                
                # Calculate duration from frame math (most reliable per research)
                if fps > 0:
                    return frame_count / fps
                    
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, ValueError):
            pass
        
        # Fallback to format duration
        return self._get_format_duration(video_path)
    
    def _get_format_duration(self, video_path: Path) -> float:
        """Get duration from format metadata (fallback method)."""
        
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError):
            return 0.0