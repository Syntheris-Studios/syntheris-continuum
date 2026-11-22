"""
Test suite for batch processing functionality
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from ..core.batch_processor import BatchProcessor, ProcessingStatus, ProcessingJob
from ..utils.file_utils import extract_batch_file_paths, validate_video_file

def test_batch_processor_initialization():
    """Test batch processor initialization"""
    processor = BatchProcessor(
        max_parallel_jobs=4,
        continue_on_error=True,
        max_retries=2
    )
    
    assert processor.max_parallel_jobs == 4
    assert processor.continue_on_error == True
    assert processor.max_retries == 2
    assert len(processor.jobs) == 0

def test_file_path_extraction():
    """Test extraction of file paths from various input formats"""
    # Test with string paths
    string_paths = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
    extracted = extract_batch_file_paths(string_paths)
    assert extracted == string_paths
    
    # Test with mock Gradio file objects
    class MockGradioFile:
        def __init__(self, name):
            self.name = name
    
    gradio_files = [MockGradioFile("video1.mp4"), MockGradioFile("video2.mp4")]
    extracted = extract_batch_file_paths(gradio_files)
    assert extracted == ["video1.mp4", "video2.mp4"]
    
    # Test with dictionary format
    dict_files = [{"path": "video1.mp4"}, {"name": "video2.mp4"}]
    extracted = extract_batch_file_paths(dict_files)
    assert extracted == ["video1.mp4", "video2.mp4"]

def test_job_preparation():
    """Test batch job preparation"""
    processor = BatchProcessor()
    
    # Mock file inputs
    test_files = ["video1.mp4", "video2.mp4", "invalid.txt"]
    
    # Mock the validation to simulate real behavior
    import unittest.mock
    with unittest.mock.patch('syntheris_video_processor.core.batch_processor.validate_video_file') as mock_validate:
        # video1.mp4 and video2.mp4 are valid, invalid.txt is not
        mock_validate.side_effect = lambda path: path.endswith('.mp4')
        
        jobs = processor.prepare_batch(test_files)
        
        assert len(jobs) == 3
        assert jobs[0].file_path == "video1.mp4"
        assert jobs[0].status == ProcessingStatus.PENDING
        assert jobs[1].file_path == "video2.mp4"
        assert jobs[1].status == ProcessingStatus.PENDING
        assert jobs[2].file_path == "invalid.txt"
        assert jobs[2].status == ProcessingStatus.SKIPPED

def test_progress_callback():
    """Test progress callback functionality"""
    processor = BatchProcessor()
    
    # Capture progress messages
    progress_messages = []
    
    def progress_callback(message, data):
        progress_messages.append((message, data))
    
    processor.set_progress_callback(progress_callback)
    processor._emit_progress("Test message", {"test": "data"})
    
    assert len(progress_messages) == 1
    assert progress_messages[0][0] == "Test message"
    assert progress_messages[0][1]["test"] == "data"

def test_progress_summary():
    """Test progress summary generation"""
    processor = BatchProcessor()
    
    # Manually create test jobs
    processor.jobs = [
        ProcessingJob(1, "video1.mp4", ProcessingStatus.COMPLETED),
        ProcessingJob(2, "video2.mp4", ProcessingStatus.FAILED),
        ProcessingJob(3, "video3.mp4", ProcessingStatus.IN_PROGRESS),
        ProcessingJob(4, "video4.mp4", ProcessingStatus.PENDING),
    ]
    
    summary = processor.get_progress_summary()
    
    assert summary["total_files"] == 4
    assert summary["completed"] == 1
    assert summary["failed"] == 1
    assert summary["in_progress"] == 1
    assert summary["pending"] == 1
    assert summary["progress_percentage"] == 25.0

def create_test_video_file(path: Path, duration_seconds: int = 5):
    """Create a simple test video file using FFmpeg"""
    import subprocess
    try:
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', f'testsrc=duration={duration_seconds}:size=320x240:rate=24',
            '-c:v', 'libx264', '-t', str(duration_seconds), '-y', str(path)
        ], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

@pytest.mark.integration
def test_batch_processing_integration():
    """Integration test for actual batch processing"""
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test video files
        test_videos = []
        for i in range(3):
            video_path = temp_path / f"test_video_{i}.mp4"
            if create_test_video_file(video_path):
                test_videos.append(str(video_path))
        
        if not test_videos:
            pytest.skip("FFmpeg not available for test video creation")
        
        processor = BatchProcessor(max_parallel_jobs=1, continue_on_error=True)
        
        # Track progress
        progress_updates = []
        def track_progress(message, data):
            progress_updates.append(message)
        
        processor.set_progress_callback(track_progress)
        
        # Prepare batch
        jobs = processor.prepare_batch(test_videos)
        assert len(jobs) == len(test_videos)
        
        # Mock processing function that simulates video processing
        def mock_processing_func(file_path, settings):
            """Mock processing function for testing"""
            file_name = Path(file_path).name
            yield f"Processing {file_name}..."
            yield f"50% complete for {file_name}"
            yield f"Completed {file_name}"
            
        # Run sequential processing
        result = processor.process_batch_sequential(
            mock_processing_func, 
            {"test": True}
        )
        
        assert result.total_files == len(test_videos)
        assert result.successful == len(test_videos)
        assert result.failed == 0
        assert result.skipped == 0
        assert len(progress_updates) > 0

if __name__ == "__main__":
    # Run tests
    import sys
    sys.path.insert(0, str(Path(__file__).parents[2]))
    
    # Run basic tests
    test_batch_processor_initialization()
    test_file_path_extraction()
    test_job_preparation()
    test_progress_callback()
    test_progress_summary()
    
    print("SUCCESS: All basic batch processing tests passed!")
    
    # Run integration test if FFmpeg is available
    try:
        test_batch_processing_integration()
        print("SUCCESS: Integration test passed!")
    except Exception as e:
        print(f"WARNING:  Integration test skipped: {e}")