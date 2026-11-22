"""
Advanced batch processing with parallel capabilities for high-volume video processing
"""

import asyncio
import concurrent.futures
import time
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Generator, Union
from dataclasses import dataclass
from enum import Enum

from ..utils.file_utils import extract_batch_file_paths, validate_video_file
from ..utils.video_utils import get_video_info

class ProcessingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProcessingJob:
    """Individual video processing job"""
    index: int
    file_path: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None

@dataclass
class BatchResult:
    """Results of batch processing operation"""
    total_files: int
    successful: int
    failed: int
    skipped: int
    total_duration: float
    jobs: List[ProcessingJob]
    summary_report: Dict[str, Any]

class BatchProcessor:
    """
    High-performance batch processor for video interpolation
    Supports parallel processing and comprehensive progress tracking
    """
    
    def __init__(self, 
                 max_parallel_jobs: int = 2,
                 continue_on_error: bool = True,
                 max_retries: int = 1):
        self.max_parallel_jobs = max_parallel_jobs
        self.continue_on_error = continue_on_error
        self.max_retries = max_retries
        self.jobs: List[ProcessingJob] = []
        self.progress_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback
        
    def _emit_progress(self, message: str, data: Dict[str, Any] = None):
        """Emit progress update to callback"""
        if self.progress_callback:
            self.progress_callback(message, data or {})
    
    def prepare_batch(self, file_inputs: Union[List[str], Any]) -> List[ProcessingJob]:
        """
        Prepare batch jobs from file inputs
        Handles various input formats from Gradio Files component
        """
        # Extract file paths from various input formats
        if hasattr(file_inputs, '__iter__') and not isinstance(file_inputs, str):
            file_paths = extract_batch_file_paths(file_inputs)
        else:
            file_paths = extract_batch_file_paths([file_inputs])
            
        # Validate and create jobs
        jobs = []
        for idx, file_path in enumerate(file_paths, 1):
            if validate_video_file(file_path):
                job = ProcessingJob(index=idx, file_path=file_path)
                
                # Get file info for better progress reporting
                try:
                    job.file_info = get_video_info(Path(file_path))
                except Exception as e:
                    job.file_info = {"error": str(e)}
                    
                jobs.append(job)
            else:
                # Create skipped job for invalid files
                job = ProcessingJob(
                    index=idx, 
                    file_path=file_path,
                    status=ProcessingStatus.SKIPPED,
                    error_message="Invalid or inaccessible video file"
                )
                jobs.append(job)
                
        self.jobs = jobs
        return jobs
    
    def process_batch_sequential(self, 
                                processing_func: Callable[[str, Dict[str, Any]], Generator[str, None, Optional[str]]],
                                processing_settings: Dict[str, Any]) -> BatchResult:
        """
        Process batch sequentially - safer for memory-intensive operations
        """
        start_time = time.time()
        successful = 0
        failed = 0
        skipped = 0
        
        total_files = len(self.jobs)
        
        self._emit_progress(f"Starting sequential processing of {total_files} files", {
            "total_files": total_files,
            "mode": "sequential"
        })
        
        for job in self.jobs:
            if job.status == ProcessingStatus.SKIPPED:
                skipped += 1
                continue
                
            job.status = ProcessingStatus.IN_PROGRESS
            job.start_time = time.time()
            
            file_name = Path(job.file_path).name
            
            self._emit_progress(f"[{job.index}/{total_files}] Processing: {file_name}", {
                "current_job": job.index,
                "total_jobs": total_files,
                "file_name": file_name,
                "status": "processing"
            })
            
            retry_count = 0
            while retry_count <= self.max_retries:
                try:
                    # Process the video
                    for progress_message in processing_func(job.file_path, processing_settings):
                        # Extract progress information
                        if 'Status:' in progress_message:
                            clean_msg = progress_message.split('Status: ')[-1].split('\n')[0]
                        else:
                            clean_msg = progress_message
                        status_msg = f"[{job.index}/{total_files}] {file_name}: {clean_msg}"
                        
                        self._emit_progress(status_msg, {
                            "current_job": job.index,
                            "total_jobs": total_files,
                            "file_name": file_name,
                            "progress_detail": progress_message
                        })
                    
                    # If we get here, processing was successful
                    job.status = ProcessingStatus.COMPLETED
                    job.end_time = time.time()
                    successful += 1
                    break
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if retry_count <= self.max_retries:
                        self._emit_progress(f"[{job.index}/{total_files}] Retry {retry_count}/{self.max_retries} for {file_name}: {error_msg}", {
                            "current_job": job.index,
                            "retry_count": retry_count,
                            "error": error_msg
                        })
                        time.sleep(2)  # Brief delay before retry
                    else:
                        job.status = ProcessingStatus.FAILED
                        job.error_message = error_msg
                        job.end_time = time.time()
                        failed += 1
                        
                        self._emit_progress(f"[{job.index}/{total_files}] FAILED: {file_name} - {error_msg}", {
                            "current_job": job.index,
                            "total_jobs": total_files,
                            "file_name": file_name,
                            "error": error_msg,
                            "status": "failed"
                        })
                        
                        if not self.continue_on_error:
                            break
                            
            if not self.continue_on_error and job.status == ProcessingStatus.FAILED:
                break
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Generate summary report
        summary = self._generate_summary_report(total_duration, successful, failed, skipped)
        
        return BatchResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_duration=total_duration,
            jobs=self.jobs,
            summary_report=summary
        )
    
    def process_batch_parallel(self, 
                              processing_func: Callable[[str, Dict[str, Any]], Optional[str]],
                              processing_settings: Dict[str, Any]) -> BatchResult:
        """
        Process batch in parallel - for high-end systems with multiple GPUs
        NOTE: This requires careful GPU memory management
        """
        start_time = time.time()
        
        # Filter out skipped jobs
        valid_jobs = [job for job in self.jobs if job.status != ProcessingStatus.SKIPPED]
        total_files = len(self.jobs)
        
        self._emit_progress(f"Starting parallel processing of {len(valid_jobs)} files (max {self.max_parallel_jobs} concurrent)", {
            "total_files": total_files,
            "valid_files": len(valid_jobs),
            "max_parallel": self.max_parallel_jobs,
            "mode": "parallel"
        })
        
        def process_single_job(job: ProcessingJob) -> ProcessingJob:
            """Process a single job with error handling"""
            job.status = ProcessingStatus.IN_PROGRESS
            job.start_time = time.time()
            
            try:
                output_path = processing_func(job.file_path, processing_settings)
                if output_path:
                    job.output_path = output_path
                    job.status = ProcessingStatus.COMPLETED
                else:
                    job.status = ProcessingStatus.FAILED
                    job.error_message = "Processing returned no output"
            except Exception as e:
                job.status = ProcessingStatus.FAILED
                job.error_message = str(e)
            finally:
                job.end_time = time.time()
                
            return job
        
        # Process jobs in parallel batches
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_jobs) as executor:
            completed_jobs = list(executor.map(process_single_job, valid_jobs))
        
        # Update job statuses
        job_dict = {job.file_path: job for job in completed_jobs}
        for job in self.jobs:
            if job.file_path in job_dict:
                updated_job = job_dict[job.file_path]
                job.status = updated_job.status
                job.output_path = updated_job.output_path
                job.error_message = updated_job.error_message
                job.start_time = updated_job.start_time
                job.end_time = updated_job.end_time
        
        # Count results
        successful = sum(1 for job in self.jobs if job.status == ProcessingStatus.COMPLETED)
        failed = sum(1 for job in self.jobs if job.status == ProcessingStatus.FAILED)
        skipped = sum(1 for job in self.jobs if job.status == ProcessingStatus.SKIPPED)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        summary = self._generate_summary_report(total_duration, successful, failed, skipped)
        
        return BatchResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_duration=total_duration,
            jobs=self.jobs,
            summary_report=summary
        )
    
    def _generate_summary_report(self, total_duration: float, successful: int, failed: int, skipped: int) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        total_files = len(self.jobs)
        
        # Calculate processing statistics
        processing_times = [
            job.end_time - job.start_time 
            for job in self.jobs 
            if job.start_time and job.end_time
        ]
        
        avg_time_per_file = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # File size statistics
        total_input_size = 0
        total_output_size = 0
        
        for job in self.jobs:
            if job.file_info and not job.file_info.get('error'):
                total_input_size += job.file_info.get('file_size', 0)
            
            if job.output_path:
                try:
                    output_path = Path(job.output_path)
                    if output_path.exists():
                        total_output_size += output_path.stat().st_size
                except Exception:
                    pass
        
        return {
            "batch_summary": {
                "total_files": total_files,
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "success_rate": (successful / total_files * 100) if total_files > 0 else 0,
            },
            "timing": {
                "total_duration_seconds": total_duration,
                "total_duration_formatted": self._format_duration(total_duration),
                "average_time_per_file": avg_time_per_file,
                "average_time_formatted": self._format_duration(avg_time_per_file),
            },
            "data_processed": {
                "total_input_size_bytes": total_input_size,
                "total_output_size_bytes": total_output_size,
                "total_input_size_formatted": self._format_file_size(total_input_size),
                "total_output_size_formatted": self._format_file_size(total_output_size),
            },
            "errors": [
                {
                    "index": job.index,
                    "file_path": job.file_path,
                    "error": job.error_message
                }
                for job in self.jobs if job.status == ProcessingStatus.FAILED
            ]
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs:.1f}s"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        
        return f"{s} {size_names[i]}"
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary"""
        total = len(self.jobs)
        completed = sum(1 for job in self.jobs if job.status == ProcessingStatus.COMPLETED)
        failed = sum(1 for job in self.jobs if job.status == ProcessingStatus.FAILED)
        in_progress = sum(1 for job in self.jobs if job.status == ProcessingStatus.IN_PROGRESS)
        
        return {
            "total_files": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "progress_percentage": (completed / total * 100) if total > 0 else 0
        }