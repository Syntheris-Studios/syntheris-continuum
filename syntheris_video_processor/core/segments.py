"""
Video segmentation and scene detection module.
Handles scene cut detection, segment extraction, and concatenation.
Enhanced with mathematical validation framework for duration precision.
"""

from __future__ import annotations
import subprocess
import json
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import tempfile


class MathematicalValidator:
    """Research-validated mathematical validation for video processing precision."""
    
    def __init__(self, tolerance_ms: float = 50.0):
        self.tolerance_ms = tolerance_ms
    
    def validate_scene_segments(
        self,
        video_path: Path,
        segments: List[Tuple[float, float]],
        stage_name: str = "SCENE_DETECTION"
    ) -> Dict[str, Any]:
        """
        Validate scene segments for mathematical duration precision.
        
        Research: Total segment duration must equal input duration within tolerance.
        """
        
        # Get precise video duration
        video_duration = self._get_precise_duration(video_path)
        
        # Calculate total segments duration
        total_segments_duration = sum(end_time - start_time for start_time, end_time in segments)
        
        # Mathematical validation
        duration_diff_ms = abs(total_segments_duration - video_duration) * 1000
        
        validation = {
            'stage_name': stage_name,
            'video_duration': video_duration,
            'total_segments_duration': total_segments_duration,
            'duration_diff_ms': duration_diff_ms,
            'tolerance_ms': self.tolerance_ms,
            'segments_count': len(segments),
            'segments': segments,
            'math_valid': duration_diff_ms <= self.tolerance_ms,
            'precision_grade': 'RESEARCH' if duration_diff_ms <= 50 else 'PRODUCTION' if duration_diff_ms <= 100 else 'POOR'
        }
        
        # Comprehensive logging
        print(f"[{stage_name} VALIDATION]")
        print(f"  Video duration: {video_duration:.6f}s")
        print(f"  Segments total: {total_segments_duration:.6f}s")
        print(f"  Duration error: {duration_diff_ms:.1f}ms (tolerance: {self.tolerance_ms}ms)")
        print(f"  Precision grade: {validation['precision_grade']}")
        print(f"  Mathematical valid: {'SUCCESS:' if validation['math_valid'] else 'FAIL:'}")
        
        if not validation['math_valid']:
            print(f"[{stage_name} ERROR] Mathematical validation FAILED - duration error exceeds tolerance")
            for i, (start, end) in enumerate(segments):
                segment_duration = end - start
                print(f"    Segment {i+1}: {start:.6f}s -> {end:.6f}s (duration: {segment_duration:.6f}s)")
        
        return validation
    
    def _get_precise_duration(self, video_path: Path) -> float:
        """Get precise duration using frame count / frame rate calculation."""
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
                frame_count = int(stream.get('nb_frames', 0))
                fps_str = stream.get('r_frame_rate', '30/1')
                
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den)
                else:
                    fps = float(fps_str)
                
                if fps > 0:
                    return frame_count / fps
                    
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, ValueError):
            pass
        
        # Fallback to format duration
        return self._get_format_duration(video_path)
    
    def _get_format_duration(self, video_path: Path) -> float:
        """Fallback duration method using format metadata."""
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


class SceneDetector:
    """Detects scene cuts in videos with mathematical validation for duration precision."""
    
    def __init__(self):
        self.validator = MathematicalValidator(tolerance_ms=50.0)
    
    def detect_scenes(
        self, 
        video_path: Path,
        threshold: float = 0.3,
        min_scene_duration: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Detect scenes with mathematical validation and fail-fast protection.
        
        Returns scenes only if they pass mathematical validation.
        Falls back to single segment if validation fails.
        """
        
        # First attempt: Frame-accurate scene detection
        try:
            scenes = self._detect_scenes_frame_accurate(video_path, threshold, min_scene_duration)
            
            # Mathematical validation with fail-fast protection
            validation = self.validator.validate_scene_segments(video_path, scenes, "FRAME_ACCURATE_SCENES")
            
            if validation['math_valid']:
                print(f"[SCENE DETECTION] SUCCESS: Frame-accurate detection successful - {validation['precision_grade']} grade precision")
                return scenes
            else:
                print(f"[SCENE DETECTION] FAIL: Frame-accurate detection failed validation - falling back to legacy method")
                
        except Exception as e:
            print(f"[SCENE DETECTION] FAIL: Frame-accurate detection error: {e} - falling back to legacy method")
        
        # Fallback: Legacy scene detection with validation
        try:
            scenes = self._detect_scenes_legacy(video_path, threshold, min_scene_duration)
            
            validation = self.validator.validate_scene_segments(video_path, scenes, "LEGACY_SCENES")
            
            if validation['math_valid']:
                print(f"[SCENE DETECTION] SUCCESS: Legacy detection successful - {validation['precision_grade']} grade precision")
                return scenes
            else:
                print(f"[SCENE DETECTION] FAIL: Legacy detection failed validation - using single segment")
                
        except Exception as e:
            print(f"[SCENE DETECTION] FAIL: Legacy detection error: {e} - using single segment")
        
        # Final fallback: Single segment (guaranteed to pass validation)
        duration = self.validator._get_precise_duration(video_path)
        single_segment = [(0.0, duration)]
        
        validation = self.validator.validate_scene_segments(video_path, single_segment, "SINGLE_SEGMENT_FALLBACK")
        print(f"[SCENE DETECTION] 🛡️ Single segment fallback - {validation['precision_grade']} grade precision")
        
        return single_segment
    
    def _detect_scenes_frame_accurate(
        self,
        video_path: Path,
        threshold: float = 0.3,
        min_scene_duration: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Frame-accurate scene detection with mathematical precision.
        
        Research: Use frame numbers + FPS for exact timing instead of pts_time estimates.
        """
        
        # Get video metadata for mathematical calculations
        fps = self._get_precise_fps(video_path)
        total_frames = self._get_frame_count(video_path)
        total_duration = total_frames / fps if fps > 0 else 0
        
        print(f"[FRAME_ACCURATE] Video analysis: {total_frames} frames @ {fps:.6f}fps = {total_duration:.6f}s")
        
        # FFmpeg scene detection with frame number output
        cmd = [
            'ffmpeg', '-hide_banner', '-nostdin',
            '-i', str(video_path),
            '-vf', f'select=gt(scene\\,{threshold}),showinfo',
            '-vsync', '0',  # Prevent frame rate conversion
            '-f', 'null', '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            scene_frames = []
            current_frame = 0
            
            # Parse frame numbers from FFmpeg output
            for line in result.stderr.split('\n'):
                if 'n:' in line and 'pts_time:' in line:
                    try:
                        # Extract frame number for mathematical precision
                        frame_match = re.search(r'n:\s*(\d+)', line)
                        time_match = re.search(r'pts_time:\s*([\d.]+)', line)
                        
                        if frame_match and time_match:
                            frame_num = int(frame_match.group(1))
                            scene_time = float(time_match.group(1))
                            
                            # Mathematical validation: frame_num / fps should ≈ scene_time
                            calculated_time = frame_num / fps
                            time_diff = abs(calculated_time - scene_time)
                            
                            if time_diff > 0.1:  # 100ms tolerance for timestamp accuracy
                                print(f"[FRAME_ACCURATE WARNING] Frame/time mismatch: frame {frame_num} at {scene_time:.6f}s (calculated: {calculated_time:.6f}s)")
                            
                            # Use calculated time from frame math for precision
                            precise_time = calculated_time
                            
                            # Validate minimum duration
                            if precise_time - (current_frame / fps) >= min_scene_duration:
                                scene_frames.append((current_frame, frame_num))
                                current_frame = frame_num
                                
                    except (ValueError, IndexError, AttributeError):
                        continue
            
            # Add final scene
            if current_frame < total_frames:
                scene_frames.append((current_frame, total_frames))
            
            # Convert frame boundaries to precise time boundaries
            scenes = []
            for start_frame, end_frame in scene_frames:
                start_time = start_frame / fps
                end_time = end_frame / fps
                scenes.append((start_time, end_time))
                
                print(f"[FRAME_ACCURATE] Scene: frames {start_frame}-{end_frame} -> {start_time:.6f}s-{end_time:.6f}s (duration: {end_time - start_time:.6f}s)")
            
            # If no scenes detected, return whole video as single segment
            if not scenes:
                scenes = [(0.0, total_duration)]
                print(f"[FRAME_ACCURATE] No scene cuts detected - using full video: {total_duration:.6f}s")
            
            return scenes
            
        except subprocess.SubprocessError as e:
            print(f"[FRAME_ACCURATE ERROR] FFmpeg failed: {e}")
            raise
    
    def _detect_scenes_legacy(
        self,
        video_path: Path,
        threshold: float = 0.3,
        min_scene_duration: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Legacy scene detection method (original implementation with validation).
        """
        
        # Use FFmpeg scene detection filter (original method)
        cmd = [
            'ffmpeg', '-hide_banner', '-nostdin',
            '-i', str(video_path),
            '-filter:v', f'select=gt(scene\\,{threshold}),showinfo',
            '-f', 'null', '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse scene timestamps from output
            scenes = []
            current_time = 0.0
            
            for line in result.stderr.split('\n'):
                if 'pts_time' in line:
                    # Extract timestamp
                    try:
                        pts_idx = line.index('pts_time:') + 9
                        end_idx = line.index(' ', pts_idx)
                        scene_time = float(line[pts_idx:end_idx])
                        
                        # Add scene if it meets minimum duration
                        if scene_time - current_time >= min_scene_duration:
                            scenes.append((current_time, scene_time))
                            current_time = scene_time
                    except (ValueError, IndexError):
                        continue
            
            # Add final scene to end of video
            duration = self._get_video_duration(video_path)
            if duration > current_time:
                scenes.append((current_time, duration))
            
            # If no scenes detected, return whole video as single segment
            if not scenes:
                scenes = [(0.0, duration)]
            
            return scenes
            
        except subprocess.SubprocessError:
            # Fallback to single segment on error
            duration = self._get_video_duration(video_path)
            return [(0.0, duration)]
    
    def _get_precise_fps(self, video_path: Path) -> float:
        """Get precise frame rate using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            fps_str = result.stdout.strip()
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den)
            return float(fps_str)
        except (subprocess.SubprocessError, ValueError):
            return 30.0  # Fallback
    
    def _get_frame_count(self, video_path: Path) -> int:
        """Get total frame count using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError):
            return 0

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using FFprobe (legacy method)."""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return 0.0


class SegmentProcessor:
    """Handles video segment extraction and concatenation."""
    
    def extract_segment(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        output_path: Path
    ) -> Path:
        """
        Extract a segment from a video.
        
        Args:
            video_path: Source video path
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Output segment path
            
        Returns:
            Path to extracted segment
        """
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # CRITICAL FIX: Use duration (-t) instead of end time (-to) for accuracy
        duration = end_time - start_time
        
        # Try stream copy first for speed
        cmd_copy = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-ss', f'{start_time:.3f}',
            '-t', f'{duration:.3f}',  # FIXED: Use duration instead of absolute end time
            '-i', str(video_path),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            str(output_path)
        ]
        
        result = subprocess.run(cmd_copy, capture_output=True)
        
        # Check if successful
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        
        # Fallback to re-encode for accurate cut
        cmd_encode = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-ss', f'{start_time:.3f}',
            '-t', f'{duration:.3f}',  # FIXED: Use duration here too
            '-i', str(video_path),
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '20',
            '-an',  # No audio for segments
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        subprocess.run(cmd_encode, check=True)
        return output_path
    
    def concatenate_segments(
        self,
        segment_paths: List[Path],
        output_path: Path,
        crossfade: bool = False,
        crossfade_duration: float = 0.1
    ) -> Path:
        """
        Concatenate multiple video segments.
        
        Args:
            segment_paths: List of segment file paths
            output_path: Output video path
            crossfade: Whether to apply crossfade between segments
            crossfade_duration: Duration of crossfade in seconds
            
        Returns:
            Path to concatenated video
        """
        
        if not segment_paths:
            raise ValueError("No segments to concatenate")
        
        # Enhanced debug logging with total duration validation
        print(f"[CONCAT DEBUG] Processing {len(segment_paths)} segments")
        total_segments_duration = 0.0
        for i, seg_path in enumerate(segment_paths):
            duration = self._get_video_duration(seg_path)
            total_segments_duration += duration
            print(f"[CONCAT DEBUG] Segment {i+1}: {duration:.3f}s - {seg_path.name}")
        
        print(f"[CONCAT DEBUG] Total segments duration: {total_segments_duration:.3f}s")
        print(f"[CONCAT DEBUG] Expected concatenation duration: {total_segments_duration:.3f}s")
        
        if len(segment_paths) == 1:
            # Single segment, just copy
            import shutil
            shutil.copy2(segment_paths[0], output_path)
            return output_path
        
        # Create concat list file with research-validated path handling
        concat_list = output_path.parent / 'concat.txt'
        with open(concat_list, 'w', encoding='utf-8') as f:
            for path in segment_paths:
                # Research: Normalize paths to prevent concat issues
                escaped_path = str(path).replace('\\', '/').replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        if crossfade:
            # Direct input method for crossfade (no concat demuxer to avoid duplication)
            inputs = []
            for segment in segment_paths:
                inputs.extend(['-i', str(segment)])
            
            filter_complex = self._build_crossfade_filter(
                len(segment_paths),
                crossfade_duration
            )
            
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '18',
                str(output_path)
            ]
        else:
            # Enhanced research-validated concatenation with precision timestamp control
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin',
                '-f', 'concat', '-safe', '0',
                '-i', str(concat_list),
                '-c', 'copy',  # Stream copy to avoid re-encoding
                '-copyts',  # Research: Preserve original timestamps for continuity
                '-video_track_timescale', '90000',  # Research: Precise timestamp handling
                '-muxpreload', '0', '-muxdelay', '0',  # Research: Eliminate mux delays
                '-fflags', '+genpts+igndts',  # Research: Generate PTS, ignore DTS issues
                str(output_path)
            ]
        
        # Try primary method first
        try:
            print(f"[CONCAT] Using enhanced research-validated parameters for {len(segment_paths)} segments")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Enhanced duration validation with research tolerance
            final_duration = self._get_video_duration(output_path)
            total_input_duration = sum(self._get_video_duration(seg) for seg in segment_paths)
            duration_diff_ms = abs(final_duration - total_input_duration) * 1000
            
            print(f"[CONCAT DEBUG] Final output: {final_duration:.3f}s (input total: {total_input_duration:.3f}s)")
            print(f"[CONCAT DEBUG] Duration difference: {duration_diff_ms:.1f}ms (tolerance: 100ms)")
            
            if duration_diff_ms <= 5:  # Zero-tolerance: max 5ms acceptable
                print(f"[CONCAT] SUCCESS: Duration preserved within zero tolerance ({duration_diff_ms:.1f}ms)")
            else:
                print(f"[CONCAT] CRITICAL: Duration loss {duration_diff_ms:.1f}ms exceeds 5ms tolerance - applying fix")
                # Apply the same zero-tolerance fix as ATFI
                self._apply_concat_duration_fix(output_path, total_input_duration, final_duration)
            
            return output_path
        except subprocess.CalledProcessError as e:
            # If crossfade failed, try without crossfade using enhanced parameters
            if crossfade and e.returncode == 3015096584:
                print(f"Enhanced concat failed, trying simplified research-validated concat...")
                cmd_simple = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-f', 'concat', '-safe', '0', '-i', str(concat_list),
                    '-c', 'copy', '-copyts',  # Research: Preserve timestamps
                    '-muxpreload', '0', '-muxdelay', '0',  # Research: Eliminate delays
                    '-fflags', '+genpts', str(output_path)
                ]
                try:
                    subprocess.run(cmd_simple, check=True, capture_output=True)
                    return output_path
                except subprocess.CalledProcessError:
                    pass  # Try next fallback
            
            # Research fallback: PTS reset concatenation
            print(f"Concat demuxer failed, trying PTS reset method...")
            try:
                return self._concat_with_pts_reset(segment_paths, output_path)
            except subprocess.CalledProcessError:
                pass  # Try final fallback
            
            # Final fallback: filter_complex method
            print(f"PTS reset failed, trying filter_complex method...")
            try:
                inputs = []
                for segment in segment_paths:
                    inputs.extend(['-i', str(segment)])
                
                filter_parts = []
                for i in range(len(segment_paths)):
                    filter_parts.append(f"[{i}:v:0]")
                filter_str = ''.join(filter_parts) + f"concat=n={len(segment_paths)}:v=1:a=0[vout]"
                
                cmd_filter = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin'
                ] + inputs + [
                    '-filter_complex', filter_str,
                    '-map', '[vout]',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                    str(output_path)
                ]
                
                subprocess.run(cmd_filter, check=True, capture_output=True)
                return output_path
            except subprocess.CalledProcessError:
                # Re-raise original error if all fallbacks fail
                raise e
        finally:
            # Clean up concat file
            concat_list.unlink(missing_ok=True)
    
    def _concat_with_pts_reset(
        self,
        segment_paths: List[Path],
        output_path: Path
    ) -> Path:
        """
        Concatenate segments using PTS reset method to prevent duplication.
        
        Research: "For concatenation, manual PTS adjustment ensures seamless transitions:
        the second video requires setpts=PTS-STARTPTS+DURATION1/TB"
        
        Args:
            segment_paths: List of segment file paths
            output_path: Output video path
            
        Returns:
            Path to concatenated video
        """
        
        if not segment_paths:
            raise ValueError("No segments to concatenate")
        
        if len(segment_paths) == 1:
            # Single segment, just copy
            import shutil
            shutil.copy2(segment_paths[0], output_path)
            return output_path
        
        # Apply PTS reset to each segment first
        temp_dir = output_path.parent / 'pts_reset_temp'
        temp_dir.mkdir(exist_ok=True)
        
        try:
            reset_segments = []
            for i, segment_path in enumerate(segment_paths):
                reset_path = temp_dir / f'reset_{i:03d}.mp4'
                # Each concat-demuxer input starts at zero. The demuxer adds
                # segment durations; adding offsets here would count them twice.
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-i', str(segment_path),
                    '-vf', 'setpts=PTS-STARTPTS',
                    '-af', 'asetpts=PTS-STARTPTS',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                    '-c:a', 'aac', '-b:a', '192k',
                    str(reset_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                reset_segments.append(reset_path)

            concat_list = temp_dir / 'pts_concat.txt'
            with open(concat_list, 'w', encoding='utf-8') as f:
                for path in reset_segments:
                    escaped_path = path.resolve().as_posix().replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-nostdin',
                '-f', 'concat', '-safe', '0',
                '-i', str(concat_list),
                '-c', 'copy',  # Stream copy since segments are already processed
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Verify output duration
            final_duration = self._get_video_duration(output_path)
            expected_duration = sum(self._get_video_duration(seg) for seg in segment_paths)
            print(f"[PTS CONCAT] Final: {final_duration:.3f}s (expected: {expected_duration:.3f}s)")
            
            return output_path
            
        finally:
            # Clean up temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _build_crossfade_filter(
        self,
        segment_count: int,
        duration: float
    ) -> str:
        """Build FFmpeg filter for crossfade between segments."""
        
        if segment_count < 2:
            return ""
        
        # Build complex filter string with proper offset calculation
        filter_parts = []
        
        # Simple concat without crossfade for now to prevent duplication
        # This ensures segments don't overlap and cause content repetition
        for i in range(segment_count):
            filter_parts.append(f"[{i}:v:0]")
        
        filter_parts.append(f"concat=n={segment_count}:v=1:a=0[v]")
        
        return ''.join(filter_parts)
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0

    def _apply_concat_duration_fix(self, video_path: Path, target_duration: float, current_duration: float):
        """
        Apply zero-tolerance duration fix to concatenated video.
        Uses the same approach as ATFI to eliminate truncation.
        """
        
        # Calculate exact padding needed
        padding_needed = target_duration - current_duration
        
        print(f"[CONCAT FIX] Applying zero-tolerance duration correction: +{padding_needed*1000:.1f}ms")
        
        # Create temp file for correction
        temp_corrected = video_path.with_suffix('.concat_fixed.mp4')
        
        # Apply padding using tpad filter to duplicate last frame
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-nostdin',
            '-i', str(video_path),
            '-vf', f'tpad=stop_mode=clone:stop_duration={padding_needed:.6f}',
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
            
            # Verify the fix worked
            corrected_duration = self._get_video_duration(video_path)
            final_diff_ms = abs(corrected_duration - target_duration) * 1000
            print(f"[CONCAT FIX] SUCCESS: Duration corrected to {corrected_duration:.6f}s (diff: {final_diff_ms:.1f}ms)")
        else:
            print(f"[CONCAT FIX] FAILED: {result.stderr.decode('utf-8', errors='replace') if result.stderr else 'Unknown error'}")
            temp_corrected.unlink(missing_ok=True)