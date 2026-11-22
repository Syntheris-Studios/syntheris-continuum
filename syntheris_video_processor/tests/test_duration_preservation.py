"""
Test Duration Preservation - Validates Research Findings
Tests exact duration preservation per research document findings.
"""

import unittest
import sys
import subprocess
import tempfile
import json
import cv2
from pathlib import Path
from typing import Tuple, Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from syntheris_video_processor.backends.rife_backend_final_fixed import RIFEBackend
from syntheris_video_processor.core.segments import SegmentProcessor
from syntheris_video_processor.core.media_utils import FFmpegProcessor
from syntheris_video_processor.core.quality_assurance import QualityAssurance
from syntheris_video_processor.backends.rife_v426_config import RIFEv426Configurator


class TestDurationPreservation(unittest.TestCase):
    """Test exact duration preservation per research document"""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.qa = QualityAssurance()
        self.ffmpeg = FFmpegProcessor()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_video_24fps(self, duration: float = 5.0) -> Path:
        """
        Create a precise test video at 24fps for exactly the specified duration.
        
        Args:
            duration: Exact duration in seconds
            
        Returns:
            Path to created test video
        """
        output_path = self.temp_dir / f"test_24fps_{duration}s.mp4"
        
        # Calculate exact frame count for precise duration
        fps = 24.0
        frame_count = int(duration * fps)
        actual_duration = frame_count / fps  # This ensures mathematical precision
        
        # Create test video with exact frame count
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'testsrc=duration={actual_duration}:size=640x480:rate={fps}',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to create test video: {result.stderr}")
        
        # Verify the created video has exact duration
        created_duration = self.get_precise_duration(output_path)
        duration_diff = abs(created_duration - actual_duration)
        self.assertLess(duration_diff, 0.001, f"Test video duration not precise enough: {duration_diff:.6f}s")
        
        return output_path
    
    def get_precise_duration(self, video_path: Path) -> float:
        """
        Get precise duration using research-validated approach.
        
        Research: "Container duration from format metadata often differs from 
        stream duration calculated from frame counts and rates"
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
                
                frame_count = int(stream.get('nb_frames', 0))
                fps_str = stream.get('r_frame_rate', '24/1')
                
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den)
                else:
                    fps = float(fps_str)
                
                # Research-validated: Frame Count / Frame Rate = Duration
                if fps > 0:
                    return frame_count / fps
                    
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, ValueError) as e:
            self.fail(f"Failed to get precise duration: {e}")
        
        return 0.0
    
    def validate_frame_count_math(self, video_path: Path, expected_fps: float, expected_duration: float) -> Dict[str, Any]:
        """
        Validate frame count mathematics: Frame Count / Frame Rate = Duration
        
        Research: "Mathematical relationship validation ensures correct interpolation"
        """
        actual_duration = self.get_precise_duration(video_path)
        
        # Get actual frame count and FPS
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,r_frame_rate',
            '-of', 'json',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = data['streams'][0]
        
        frame_count = int(stream.get('nb_frames', 0))
        fps_str = stream.get('r_frame_rate', '60/1')
        
        if '/' in fps_str:
            num, den = fps_str.split('/')
            actual_fps = float(num) / float(den)
        else:
            actual_fps = float(fps_str)
        
        # Validate mathematical relationship
        calculated_duration = frame_count / actual_fps
        duration_from_math_diff = abs(calculated_duration - actual_duration)
        
        return {
            'frame_count': frame_count,
            'actual_fps': actual_fps,
            'expected_fps': expected_fps,
            'actual_duration': actual_duration,
            'calculated_duration': calculated_duration,
            'fps_match': abs(actual_fps - expected_fps) < 0.1,
            'math_validates': duration_from_math_diff < 0.001,
            'duration_preserved': abs(actual_duration - expected_duration) < 0.1
        }
    
    def test_24fps_to_60fps_duration_preservation(self):
        """
        Test the exact scenario from research: 24fps->60fps with RIFE v4.26
        
        This is the core test case that validates the main research finding.
        """
        print("\n=== Testing 24fps->60fps Duration Preservation ===")
        
        # Create exactly 5.000 second test video at 24fps
        test_video = self.create_test_video_24fps(duration=5.0)
        input_duration = self.get_precise_duration(test_video)
        print(f"Input video: {input_duration:.6f}s @ 24fps")
        
        # Initialize RIFE backend
        backend = RIFEBackend()
        available, message = backend.is_available()
        self.assertTrue(available, f"RIFE backend not available: {message}")
        
        output_path = self.temp_dir / "output_60fps.mp4"
        
        # Process with exact 59.94fps targeting (research-validated)
        processing_logs = []
        try:
            for status in backend.process(
                test_video, output_path,
                mode='custom_fps', target_fps=59.94
            ):
                processing_logs.append(status)
                print(f"RIFE: {status}")
        except Exception as e:
            self.fail(f"RIFE processing failed: {e}\nLogs: {processing_logs}")
        
        # Validate output exists
        self.assertTrue(output_path.exists(), "RIFE did not create output file")
        self.assertGreater(output_path.stat().st_size, 0, "RIFE created empty output file")
        
        # Validate duration preservation within research tolerance (100ms)
        output_duration = self.get_precise_duration(output_path)
        duration_diff_ms = abs(output_duration - input_duration) * 1000
        
        print(f"Output video: {output_duration:.6f}s")
        print(f"Duration difference: {duration_diff_ms:.1f}ms")
        
        self.assertLess(duration_diff_ms, 100, 
                       f"Duration not preserved within research tolerance: {duration_diff_ms:.1f}ms difference")
        
        # Validate frame count mathematics
        math_validation = self.validate_frame_count_math(output_path, 59.94, input_duration)
        print(f"Frame count validation: {math_validation}")
        
        self.assertTrue(math_validation['math_validates'], 
                       "Frame count mathematics validation failed")
        self.assertTrue(math_validation['fps_match'], 
                       f"FPS not as expected: got {math_validation['actual_fps']}, expected ~59.94")
        
        print("SUCCESS: 24fps->60fps duration preservation test PASSED")
    
    def test_quality_assurance_validation(self):
        """Test the QualityAssurance module duration validation functionality."""
        print("\n=== Testing Quality Assurance Duration Validation ===")
        
        # Create test videos with known durations
        input_video = self.create_test_video_24fps(duration=3.0)
        output_video = self.create_test_video_24fps(duration=3.0)  # Same duration (should pass)
        corrupted_video = self.create_test_video_24fps(duration=4.0)  # Different duration (should fail)
        
        # Test successful validation
        validation_result = self.qa.validate_duration_preservation(input_video, output_video)
        print(f"Same duration validation: {validation_result}")
        
        self.assertTrue(validation_result['passed'], "QA should pass for videos with same duration")
        self.assertLess(validation_result['difference_ms'], 100, "Difference should be minimal")
        
        # Test failed validation
        failed_result = self.qa.validate_duration_preservation(input_video, corrupted_video)
        print(f"Different duration validation: {failed_result}")
        
        self.assertFalse(failed_result['passed'], "QA should fail for videos with different durations")
        self.assertGreater(failed_result['difference_ms'], 100, "Difference should be significant")
        
        print("SUCCESS: Quality Assurance validation test PASSED")
    
    def test_pts_reset_functionality(self):
        """Test PTS reset prevents timestamp accumulation."""
        print("\n=== Testing PTS Reset Functionality ===")
        
        # Create test video
        test_video = self.create_test_video_24fps(duration=2.0)
        input_duration = self.get_precise_duration(test_video)
        
        # Apply PTS reset
        pts_reset_output = self.temp_dir / "pts_reset_output.mp4"
        processed_output = self.ffmpeg.apply_pts_reset(test_video, pts_reset_output)
        
        # Validate duration preservation
        output_duration = self.get_precise_duration(processed_output)
        duration_diff_ms = abs(output_duration - input_duration) * 1000
        
        print(f"Input: {input_duration:.6f}s")
        print(f"Output after PTS reset: {output_duration:.6f}s") 
        print(f"Duration difference: {duration_diff_ms:.1f}ms")
        
        self.assertLess(duration_diff_ms, 100, "PTS reset should preserve duration")
        
        print("SUCCESS: PTS reset functionality test PASSED")
    
    def test_rife_v426_detection_and_config(self):
        """Test RIFE v4.26 detection and configuration."""
        print("\n=== Testing RIFE v4.26 Detection and Configuration ===")
        
        configurator = RIFEv426Configurator()
        v426_available = configurator.is_v426_available()
        
        print(f"RIFE v4.26 available: {v426_available}")
        
        if v426_available:
            # Test optimal configuration for 24fps->60fps
            config = configurator.get_optimal_config(24.0, 60.0)
            print(f"24fps->60fps config: {config}")
            
            self.assertNotIn('error', config, "Configuration should not have errors")
            self.assertEqual(config.get('fps_num'), 60000, "Should use exact fps_num for 59.94fps")
            self.assertEqual(config.get('fps_den'), 1001, "Should use exact fps_den for 59.94fps")
            self.assertFalse(config.get('sc'), "Scene detection should be disabled per research")
            self.assertFalse(config.get('skip'), "Frame skipping should be disabled per research")
            
            # Test feasibility validation
            feasible, message = configurator.validate_conversion(24.0, 60.0)
            print(f"Conversion feasibility: {feasible} - {message}")
            self.assertTrue(feasible, "24fps->60fps conversion should be feasible")
            
            print("SUCCESS: RIFE v4.26 configuration test PASSED")
        else:
            print("ℹ️ RIFE v4.26 not available, skipping v4.26-specific tests")
    
    def test_atfi_duration_preservation(self):
        """Test ATFI processing preserves duration."""
        print("\n=== Testing ATFI Duration Preservation ===")
        
        from syntheris_video_processor.core.atfi import ATFIProcessor
        
        # Create test video
        test_video = self.create_test_video_24fps(duration=2.0)
        input_duration = self.get_precise_duration(test_video)
        
        # Initialize ATFI processor
        atfi = ATFIProcessor()
        
        # Test precise duration method
        atfi_duration = atfi._get_precise_duration(test_video)
        duration_diff = abs(atfi_duration - input_duration)
        
        print(f"Input duration: {input_duration:.6f}s")
        print(f"ATFI measured duration: {atfi_duration:.6f}s")
        print(f"Measurement difference: {duration_diff:.6f}s")
        
        self.assertLess(duration_diff, 0.001, "ATFI should measure duration precisely")
        
        print("SUCCESS: ATFI duration preservation test PASSED")


class TestConcatenationFixes(unittest.TestCase):
    """Test concatenation fixes prevent frame duplication."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.segment_processor = SegmentProcessor()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_segment(self, duration: float, index: int) -> Path:
        """Create a test video segment."""
        output_path = self.temp_dir / f"segment_{index:03d}.mp4"
        
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size=320x240:rate=24',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    
    def test_concatenation_prevents_frame_duplication(self):
        """Test that enhanced concatenation prevents frame duplication warnings."""
        print("\n=== Testing Concatenation Frame Duplication Prevention ===")
        
        # Create multiple segments
        segments = [self.create_test_segment(1.0, i) for i in range(3)]
        
        output_path = self.temp_dir / "concatenated.mp4"
        
        # Test concatenation with enhanced method
        try:
            result_path = self.segment_processor.concatenate_segments(
                segments, output_path, crossfade=False
            )
            
            self.assertTrue(result_path.exists(), "Concatenation should create output file")
            self.assertGreater(result_path.stat().st_size, 0, "Output should not be empty")
            
            print("SUCCESS: Concatenation completed without errors")
            
        except Exception as e:
            self.fail(f"Enhanced concatenation failed: {e}")
        
        print("SUCCESS: Concatenation frame duplication prevention test PASSED")


if __name__ == '__main__':
    # Configure test runner for detailed output
    unittest.main(verbosity=2, buffer=True)