"""
Unit tests for pipeline fortification and failure handling.
Tests various failure scenarios to ensure 99.5%+ success rate.
"""

import unittest
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import logging

# Import modules to test
from syntheris_video_processor.core.pipeline_fortification import (
    PipelineFortification,
    ProcessingMode,
    RetryConfig,
    EnhancedConcatenation
)
from syntheris_video_processor.core.atfi_fortified import FortifiedATFIProcessor


class TestPipelineFortification(unittest.TestCase):
    """Test pipeline fortification functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.fortification = PipelineFortification()
        # Disable logging during tests
        self.fortification.logger.setLevel(logging.CRITICAL)
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch.object(PipelineFortification, "validate_preprocessing", return_value={"valid": True})
    def test_retry_on_gpu_memory_error(self, mock_validate):
        """Test retry logic for GPU memory errors with resolution downgrade"""
        
        # Create mock processing function that fails with GPU error first time
        call_count = 0
        
        def mock_process(input_path, output_path, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First attempt - GPU memory error
                raise RuntimeError("CUDA out of memory")
            else:
                # Second attempt succeeds with lower resolution
                self.assertLess(kwargs['scale'], 1.0)  # Verify scale was reduced
                yield "Processing successful"
                return output_path
        
        # Create dummy input file
        input_file = self.temp_dir / "input.mp4"
        input_file.touch()
        output_file = self.temp_dir / "output.mp4"
        
        # Generators return the output path through StopIteration.value.
        # Keep retry/downgrade assertions; isolate actual retry behavior from I/O.
        self.fortification.retry_config.initial_delay = 0
        progress = self.fortification.process_with_retry(
            mock_process, input_file, output_file, scale=1.0
        )
        while True:
            try:
                next(progress)
            except StopIteration as completed:
                result = completed.value
                break

        # Verify retry was successful
        self.assertEqual(call_count, 2)
        self.assertEqual(result, output_file)
    
    def test_retry_on_exit_code_failures(self):
        """Test retry logic for RIFE exit code failures"""
        
        # Test exit code 3221226505 (Windows GPU crash)
        error = RuntimeError("RIFE failed with exit code 3221226505")
        strategy = self.fortification._analyze_failure(error)
        self.assertEqual(strategy, 'downgrade')
        
        # Test exit code 1 (general failure)
        error = RuntimeError("RIFE failed with exit code 1")
        strategy = self.fortification._analyze_failure(error)
        self.assertEqual(strategy, 'downgrade')
    
    def test_progressive_mode_downgrade(self):
        """Test progressive processing mode downgrade"""
        
        modes = [
            ProcessingMode.ULTRA,
            ProcessingMode.HIGH,
            ProcessingMode.MEDIUM,
            ProcessingMode.LOW,
            ProcessingMode.SAFE
        ]
        
        for i, mode in enumerate(modes[:-1]):
            downgraded = self.fortification._downgrade_mode(mode)
            self.assertEqual(downgraded, modes[i + 1])
        
        # Safe mode should stay at safe
        downgraded = self.fortification._downgrade_mode(ProcessingMode.SAFE)
        self.assertEqual(downgraded, ProcessingMode.SAFE)
    
    def test_parameter_adjustment_by_mode(self):
        """Test parameter adjustment based on processing mode"""
        
        params = {
            'scale': 1.0,
            'uhd_mode': 'auto',
            'multiplier': '4x'
        }
        
        # Test ULTRA mode (no changes)
        adjusted = self.fortification._adjust_parameters_for_mode(
            params, ProcessingMode.ULTRA
        )
        self.assertEqual(adjusted['scale'], 1.0)
        
        # Test HIGH mode (90% scale)
        adjusted = self.fortification._adjust_parameters_for_mode(
            params, ProcessingMode.HIGH
        )
        self.assertAlmostEqual(adjusted['scale'], 0.9)
        
        # Test SAFE mode (50% scale, minimal settings)
        adjusted = self.fortification._adjust_parameters_for_mode(
            params, ProcessingMode.SAFE
        )
        self.assertAlmostEqual(adjusted['scale'], 0.5)
        self.assertEqual(adjusted['uhd_mode'], 'off')
        self.assertEqual(adjusted['multiplier'], '2x')
    
    @patch('subprocess.run')
    def test_video_integrity_check(self, mock_run):
        """Test video integrity validation"""
        
        # Mock successful FFprobe output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [{"width": 1920, "height": 1080}]}',
            stderr=''
        )
        
        video_path = self.temp_dir / "test.mp4"
        video_path.touch()
        
        result = self.fortification._check_video_integrity(video_path)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['width'], 1920)
        self.assertEqual(result['height'], 1080)
    
    @patch('subprocess.run')
    def test_corrupted_frame_detection(self, mock_run):
        """Test detection of corrupted frames"""
        
        # First call - FFprobe success
        # Second call - FFmpeg detects errors
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout='{"streams": [{"width": 1920, "height": 1080}]}',
                stderr=''
            ),
            MagicMock(
                returncode=0,
                stderr='[error] Corrupted frame detected'
            )
        ]
        
        video_path = self.temp_dir / "corrupted.mp4"
        video_path.touch()
        
        result = self.fortification._check_video_integrity(video_path)
        
        self.assertFalse(result['valid'])
        self.assertIn('Corrupted', result['message'])
    
    def test_fallback_processing(self):
        """Test fallback to basic FFmpeg interpolation"""
        
        input_file = self.temp_dir / "input.mp4"
        input_file.touch()
        output_file = self.temp_dir / "output.mp4"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = None
            for msg in self.fortification._fallback_processing(
                input_file,
                output_file
            ):
                if isinstance(msg, Path):
                    result = msg
            
            # Verify FFmpeg minterpolate was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            self.assertIn('minterpolate', ' '.join(call_args))


class TestEnhancedConcatenation(unittest.TestCase):
    """Test enhanced concatenation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.concat = EnhancedConcatenation()
        self.concat.logger.setLevel(logging.CRITICAL)
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_segment_validation(self):
        """Test video segment validation"""
        
        # Test non-existent file
        result = self.concat._validate_segment(Path("nonexistent.mp4"))
        self.assertFalse(result)
        
        # Test empty file
        empty_file = self.temp_dir / "empty.mp4"
        empty_file.touch()
        result = self.concat._validate_segment(empty_file)
        self.assertFalse(result)
        
        # Test valid file (mocked)
        valid_file = self.temp_dir / "valid.mp4"
        valid_file.write_bytes(b"dummy video data")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"streams": [{"width": 1920}]}'
            )
            result = self.concat._validate_segment(valid_file)
            self.assertTrue(result)
    
    @patch.object(EnhancedConcatenation, '_validate_segment', return_value=True)
    @patch('subprocess.run')
    def test_concatenation_with_fallback(self, mock_run, mock_validate):
        """Test concatenation with fallback methods"""
        
        # Create test segments
        segments = []
        for i in range(3):
            segment = self.temp_dir / f"segment_{i}.mp4"
            segment.write_bytes(b"dummy video data")
            segments.append(segment)
        
        output = self.temp_dir / "output.mp4"
        
        # First attempt fails, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Concat failed"),  # Primary fails
            MagicMock(returncode=0)  # Fallback succeeds
        ]
        
        result = self.concat.concatenate_with_validation(
            segments,
            output
        )
        
        # Verify fallback was used
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(result, output)
    
    @patch.object(EnhancedConcatenation, '_validate_segment', return_value=True)
    def test_single_segment_optimization(self, mock_validate):
        """Test that single segments are just copied"""
        
        segment = self.temp_dir / "single.mp4"
        segment.write_bytes(b"dummy video data")
        output = self.temp_dir / "output.mp4"
        
        with patch('shutil.copy2') as mock_copy:
            result = self.concat.concatenate_with_validation(
                [segment],
                output
            )
            
            mock_copy.assert_called_once_with(segment, output)
            self.assertEqual(result, output)


class TestFortifiedATFI(unittest.TestCase):
    """Test fortified ATFI processor"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.atfi = FortifiedATFIProcessor()
        self.atfi.logger.setLevel(logging.CRITICAL)
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_alternative_output_detection(self):
        """Test detection of alternative RIFE output names"""
        
        # Create alternative output files
        alternatives = [
            self.temp_dir / "segment_001_2X_60fps.mp4",
            self.temp_dir / "segment_001_4X_120fps.mp4",
            self.temp_dir / "input_2X_60fps.mp4"
        ]
        
        for alt in alternatives:
            alt.write_bytes(b"dummy video data")
        
        found = self.atfi._find_alternative_outputs(self.temp_dir, 1)
        
        self.assertEqual(len(found), 3)
        # Verify sorted by size (all same size in this test)
        self.assertIn(alternatives[0], found)
    
    @patch('subprocess.run')
    def test_motion_detection_fallback(self, mock_run):
        """Test motion detection with fallback on failure"""
        
        # Mock FFmpeg timeout
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 60)
        
        video = self.temp_dir / "video.mp4"
        video.touch()
        
        intervals = self.atfi._detect_motion_with_fallback(
            video, 0.3, 0.25, 'scene'
        )
        
        # Should return empty list on failure
        self.assertEqual(intervals, [])
    
    def test_performance_tracking(self):
        """Test performance statistics tracking"""
        
        # Simulate processing
        self.atfi.performance_stats['total_processed'] = 10
        self.atfi.performance_stats['successful'] = 9
        self.atfi.performance_stats['failed'] = 1
        
        stats = self.atfi.get_performance_stats()
        
        self.assertEqual(stats['total_processed'], 10)
        self.assertEqual(stats['successful'], 9)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['success_rate'], 90.0)


class TestFailureScenarios(unittest.TestCase):
    """Integration tests for specific failure scenarios from batch processing"""
    
    def test_rife_exit_code_3221226505(self):
        """Test handling of RIFE exit code 3221226505 (GPU crash)"""
        
        fortification = PipelineFortification()
        fortification.logger.setLevel(logging.CRITICAL)
        
        # Simulate the error
        error = RuntimeError("RIFE failed with exit code 3221226505")
        strategy = fortification._analyze_failure(error)
        
        # Should trigger downgrade for GPU issues
        self.assertEqual(strategy, 'downgrade')
    
    def test_rife_exit_code_1(self):
        """Test handling of RIFE exit code 1 (general failure)"""
        
        fortification = PipelineFortification()
        fortification.logger.setLevel(logging.CRITICAL)
        
        error = RuntimeError("RIFE failed with exit code 1")
        strategy = fortification._analyze_failure(error)
        
        # Should trigger downgrade
        self.assertEqual(strategy, 'downgrade')
    
    @patch.object(EnhancedConcatenation, '_validate_segment', return_value=True)
    def test_ffmpeg_concat_exit_code_3015096584(self, mock_validate):
        """Test handling of FFmpeg concat exit code 3015096584"""
        
        concat = EnhancedConcatenation()
        concat.logger.setLevel(logging.CRITICAL)
        
        # Create test segments
        temp_dir = Path(tempfile.mkdtemp())
        try:
            segments = []
            for i in range(2):
                segment = temp_dir / f"segment_{i}.mp4"
                segment.write_bytes(b"dummy video data")
                segments.append(segment)
            
            output = temp_dir / "output.mp4"
            
            with patch('subprocess.run') as mock_run:
                # Simulate the specific error
                mock_run.side_effect = [
                    MagicMock(
                        returncode=3015096584,
                        stderr="FFmpeg concatenation failed"
                    ),
                    MagicMock(returncode=0)  # Fallback succeeds
                ]
                
                # Should use fallback method
                result = concat.concatenate_with_validation(
                    segments,
                    output
                )
                
                # Verify fallback was used
                self.assertEqual(mock_run.call_count, 2)
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()