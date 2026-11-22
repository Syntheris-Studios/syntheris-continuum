"""
Comprehensive system monitoring and diagnostics for video processing
"""

import psutil
import platform
import subprocess
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import queue
import logging
import torch
import numpy as np

from .gpu_utils import GPUMemoryManager, detect_gpu_capabilities
from .hardware_encoder import HardwareEncoder

@dataclass
class SystemSnapshot:
    """Single point-in-time system measurement"""
    timestamp: datetime
    cpu_percent: float
    cpu_freq_mhz: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    gpu_utilization: Dict[int, float]
    gpu_memory_used: Dict[int, float] 
    gpu_temperature: Dict[int, float]
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: List[float]  # Unix systems only

@dataclass
class ProcessingStats:
    """Statistics for video processing operations"""
    session_start: datetime
    videos_processed: int
    total_frames_processed: int
    total_processing_time: float
    average_fps: float
    peak_memory_usage_gb: float
    peak_gpu_utilization: float
    errors_encountered: int
    warnings_encountered: int
    last_processing_time: float
    efficiency_rating: str  # excellent, good, fair, poor

class SystemMonitor:
    """
    Real-time system monitoring and diagnostics
    """
    
    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.gpu_manager = GPUMemoryManager()
        self.hardware_encoder = HardwareEncoder()
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.samples_queue = queue.Queue(maxsize=1000)
        self.callbacks = []
        
        # Processing statistics
        self.processing_stats = ProcessingStats(
            session_start=datetime.now(),
            videos_processed=0,
            total_frames_processed=0,
            total_processing_time=0.0,
            average_fps=0.0,
            peak_memory_usage_gb=0.0,
            peak_gpu_utilization=0.0,
            errors_encountered=0,
            warnings_encountered=0,
            last_processing_time=0.0,
            efficiency_rating="unknown"
        )
        
        # System baseline (measured at startup)
        self.baseline_snapshot = self._take_system_snapshot()
        
        # Alert thresholds
        self.alert_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "gpu_utilization": 95.0,
            "gpu_memory_percent": 90.0,
            "gpu_temperature": 85,
            "disk_usage_percent": 95.0
        }
        
        # Setup logging
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup monitoring logger"""
        logger = logging.getLogger("system_monitor")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def add_callback(self, callback: Callable[[SystemSnapshot], None]):
        """Add callback for real-time monitoring updates"""
        self.callbacks.append(callback)
    
    def start_monitoring(self):
        """Start real-time system monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time system monitoring"""
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                snapshot = self._take_system_snapshot()
                
                # Add to queue (drop oldest if full)
                try:
                    self.samples_queue.put_nowait(snapshot)
                except queue.Full:
                    try:
                        self.samples_queue.get_nowait()  # Remove oldest
                        self.samples_queue.put_nowait(snapshot)
                    except queue.Empty:
                        pass
                
                # Check for alerts
                self._check_alerts(snapshot)
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.warning(f"Callback error: {e}")
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(self.sample_interval)
    
    def _take_system_snapshot(self) -> SystemSnapshot:
        """Take comprehensive system measurement"""
        now = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_mhz = cpu_freq.current if cpu_freq else 0
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        
        # Network metrics
        net_io = psutil.net_io_counters()
        network_bytes_sent = net_io.bytes_sent if net_io else 0
        network_bytes_recv = net_io.bytes_recv if net_io else 0
        
        # Process count
        process_count = len(psutil.pids())
        
        # Load average (Unix systems)
        try:
            load_average = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_average = [0.0, 0.0, 0.0]
        
        # GPU metrics
        gpu_utilization = {}
        gpu_memory_used = {}
        gpu_temperature = {}
        
        gpu_info = self.gpu_manager.get_gpu_info()
        for gpu_id, info in gpu_info.items():
            gpu_utilization[gpu_id] = info.get("utilization_gpu", 0)
            
            total_mem = info.get("memory_total", 0)
            used_mem = info.get("memory_used", 0)
            gpu_memory_used[gpu_id] = (used_mem / total_mem * 100) if total_mem > 0 else 0
            
            gpu_temperature[gpu_id] = info.get("temperature", 0)
        
        return SystemSnapshot(
            timestamp=now,
            cpu_percent=cpu_percent,
            cpu_freq_mhz=cpu_freq_mhz,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            gpu_utilization=gpu_utilization,
            gpu_memory_used=gpu_memory_used,
            gpu_temperature=gpu_temperature,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            process_count=process_count,
            load_average=load_average
        )
    
    def _check_alerts(self, snapshot: SystemSnapshot):
        """Check for system alerts and warnings"""
        alerts = []
        
        # CPU alerts
        if snapshot.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
        
        # Memory alerts
        if snapshot.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append(f"High memory usage: {snapshot.memory_percent:.1f}%")
        
        # GPU alerts
        for gpu_id, util in snapshot.gpu_utilization.items():
            if util > self.alert_thresholds["gpu_utilization"]:
                alerts.append(f"GPU {gpu_id} high utilization: {util:.1f}%")
        
        for gpu_id, mem_percent in snapshot.gpu_memory_used.items():
            if mem_percent > self.alert_thresholds["gpu_memory_percent"]:
                alerts.append(f"GPU {gpu_id} high memory usage: {mem_percent:.1f}%")
        
        for gpu_id, temp in snapshot.gpu_temperature.items():
            if temp > self.alert_thresholds["gpu_temperature"]:
                alerts.append(f"GPU {gpu_id} high temperature: {temp}°C")
        
        # Disk alerts
        if snapshot.disk_usage_percent > self.alert_thresholds["disk_usage_percent"]:
            alerts.append(f"High disk usage: {snapshot.disk_usage_percent:.1f}%")
        
        # Log alerts
        for alert in alerts:
            self.logger.warning(f"SYSTEM ALERT: {alert}")
    
    def get_current_snapshot(self) -> SystemSnapshot:
        """Get current system snapshot"""
        return self._take_system_snapshot()
    
    def get_recent_samples(self, count: int = 60) -> List[SystemSnapshot]:
        """Get recent monitoring samples"""
        samples = []
        temp_queue = queue.Queue()
        
        # Extract samples without blocking
        while not self.samples_queue.empty() and len(samples) < count:
            try:
                sample = self.samples_queue.get_nowait()
                samples.append(sample)
                temp_queue.put(sample)
            except queue.Empty:
                break
        
        # Put samples back
        while not temp_queue.empty():
            try:
                self.samples_queue.put_nowait(temp_queue.get_nowait())
            except queue.Full:
                break
        
        return sorted(samples, key=lambda x: x.timestamp)[-count:]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        current = self.get_current_snapshot()
        baseline = self.baseline_snapshot
        
        # Calculate changes from baseline
        cpu_change = current.cpu_percent - baseline.cpu_percent
        memory_change = current.memory_percent - baseline.memory_percent
        
        # System information
        system_info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
            "total_disk_gb": psutil.disk_usage('/').total / (1024**3)
        }
        
        # GPU capabilities
        gpu_capabilities = detect_gpu_capabilities()
        
        # Hardware encoding info
        encoding_info = self.hardware_encoder.get_encoding_info()
        
        # Current performance
        performance = {
            "cpu_percent": current.cpu_percent,
            "cpu_change": cpu_change,
            "memory_percent": current.memory_percent,
            "memory_change": memory_change,
            "memory_available_gb": current.memory_available_gb,
            "disk_free_gb": current.disk_free_gb,
            "gpu_utilization": current.gpu_utilization,
            "gpu_memory_used": current.gpu_memory_used,
            "gpu_temperature": current.gpu_temperature,
            "load_average": current.load_average
        }
        
        return {
            "timestamp": current.timestamp.isoformat(),
            "system_info": system_info,
            "gpu_capabilities": gpu_capabilities,
            "encoding_capabilities": encoding_info,
            "current_performance": performance,
            "processing_stats": asdict(self.processing_stats),
            "monitoring_active": self.monitoring,
            "sample_count": self.samples_queue.qsize()
        }
    
    def update_processing_stats(self, 
                               frames_processed: int = 0,
                               processing_time: float = 0.0,
                               had_error: bool = False,
                               had_warning: bool = False):
        """Update processing statistics"""
        self.processing_stats.total_frames_processed += frames_processed
        self.processing_stats.total_processing_time += processing_time
        
        if processing_time > 0:
            self.processing_stats.videos_processed += 1
            self.processing_stats.last_processing_time = processing_time
            
            # Update average FPS
            if self.processing_stats.total_processing_time > 0:
                self.processing_stats.average_fps = (
                    self.processing_stats.total_frames_processed / 
                    self.processing_stats.total_processing_time
                )
        
        # Update peak usage
        current = self.get_current_snapshot()
        current_memory = current.memory_used_gb
        if current_memory > self.processing_stats.peak_memory_usage_gb:
            self.processing_stats.peak_memory_usage_gb = current_memory
        
        # Update peak GPU utilization
        max_gpu_util = max(current.gpu_utilization.values()) if current.gpu_utilization else 0
        if max_gpu_util > self.processing_stats.peak_gpu_utilization:
            self.processing_stats.peak_gpu_utilization = max_gpu_util
        
        # Update error/warning counts
        if had_error:
            self.processing_stats.errors_encountered += 1
        if had_warning:
            self.processing_stats.warnings_encountered += 1
        
        # Calculate efficiency rating
        self.processing_stats.efficiency_rating = self._calculate_efficiency_rating()
    
    def _calculate_efficiency_rating(self) -> str:
        """Calculate overall processing efficiency rating"""
        score = 0
        
        # FPS score (0-25 points)
        if self.processing_stats.average_fps >= 15:
            score += 25
        elif self.processing_stats.average_fps >= 10:
            score += 20
        elif self.processing_stats.average_fps >= 5:
            score += 15
        elif self.processing_stats.average_fps >= 1:
            score += 10
        
        # GPU utilization score (0-25 points)
        if self.processing_stats.peak_gpu_utilization >= 80:
            score += 25
        elif self.processing_stats.peak_gpu_utilization >= 60:
            score += 20
        elif self.processing_stats.peak_gpu_utilization >= 40:
            score += 15
        elif self.processing_stats.peak_gpu_utilization >= 20:
            score += 10
        
        # Error rate score (0-25 points)
        if self.processing_stats.videos_processed > 0:
            error_rate = self.processing_stats.errors_encountered / self.processing_stats.videos_processed
            if error_rate == 0:
                score += 25
            elif error_rate < 0.05:  # <5% error rate
                score += 20
            elif error_rate < 0.10:  # <10% error rate
                score += 15
            elif error_rate < 0.20:  # <20% error rate
                score += 10
        
        # Resource efficiency score (0-25 points)
        current = self.get_current_snapshot()
        if current.memory_percent < 70 and max(current.gpu_memory_used.values(), default=0) < 80:
            score += 25
        elif current.memory_percent < 80 and max(current.gpu_memory_used.values(), default=0) < 90:
            score += 20
        elif current.memory_percent < 90:
            score += 15
        
        # Convert score to rating
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"
    
    def generate_performance_report(self, 
                                   save_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "report_generated": datetime.now().isoformat(),
            "monitoring_duration": (datetime.now() - self.processing_stats.session_start).total_seconds(),
            "system_summary": self.get_system_summary(),
            "performance_analysis": self._analyze_performance(),
            "recommendations": self._generate_recommendations(),
            "recent_samples": [asdict(s) for s in self.get_recent_samples(30)]
        }
        
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Performance report saved to {save_path}")
        
        return report
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze system performance patterns"""
        recent_samples = self.get_recent_samples(60)  # Last 60 samples
        
        if not recent_samples:
            return {"status": "insufficient_data"}
        
        # CPU analysis
        cpu_values = [s.cpu_percent for s in recent_samples]
        cpu_analysis = {
            "average": sum(cpu_values) / len(cpu_values),
            "peak": max(cpu_values),
            "minimum": min(cpu_values),
            "stability": "stable" if max(cpu_values) - min(cpu_values) < 30 else "unstable"
        }
        
        # Memory analysis
        memory_values = [s.memory_percent for s in recent_samples]
        memory_analysis = {
            "average": sum(memory_values) / len(memory_values),
            "peak": max(memory_values),
            "minimum": min(memory_values),
            "trend": self._calculate_trend(memory_values)
        }
        
        # GPU analysis
        gpu_analysis = {}
        if recent_samples[0].gpu_utilization:
            for gpu_id in recent_samples[0].gpu_utilization.keys():
                gpu_util_values = [s.gpu_utilization.get(gpu_id, 0) for s in recent_samples]
                gpu_mem_values = [s.gpu_memory_used.get(gpu_id, 0) for s in recent_samples]
                gpu_temp_values = [s.gpu_temperature.get(gpu_id, 0) for s in recent_samples]
                
                gpu_analysis[f"gpu_{gpu_id}"] = {
                    "utilization_average": sum(gpu_util_values) / len(gpu_util_values),
                    "utilization_peak": max(gpu_util_values),
                    "memory_average": sum(gpu_mem_values) / len(gpu_mem_values),
                    "memory_peak": max(gpu_mem_values),
                    "temperature_average": sum(gpu_temp_values) / len(gpu_temp_values),
                    "temperature_peak": max(gpu_temp_values),
                    "thermal_throttling": any(t > 83 for t in gpu_temp_values)
                }
        
        return {
            "cpu": cpu_analysis,
            "memory": memory_analysis,
            "gpu": gpu_analysis,
            "overall_health": self._assess_overall_health(cpu_analysis, memory_analysis, gpu_analysis)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend in values"""
        if len(values) < 3:
            return "unknown"
        
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        diff_percent = (second_half - first_half) / first_half * 100
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def _assess_overall_health(self, cpu_analysis: Dict, memory_analysis: Dict, gpu_analysis: Dict) -> str:
        """Assess overall system health"""
        issues = 0
        
        # Check CPU health
        if cpu_analysis["average"] > 80:
            issues += 2
        elif cpu_analysis["average"] > 60:
            issues += 1
        
        if cpu_analysis["stability"] == "unstable":
            issues += 1
        
        # Check memory health
        if memory_analysis["average"] > 85:
            issues += 2
        elif memory_analysis["average"] > 70:
            issues += 1
        
        if memory_analysis["trend"] == "increasing":
            issues += 1
        
        # Check GPU health
        for gpu_id, gpu_info in gpu_analysis.items():
            if gpu_info.get("temperature_peak", 0) > 85:
                issues += 2
            elif gpu_info.get("temperature_peak", 0) > 75:
                issues += 1
            
            if gpu_info.get("thermal_throttling", False):
                issues += 2
        
        # Determine health rating
        if issues == 0:
            return "excellent"
        elif issues <= 2:
            return "good"
        elif issues <= 4:
            return "fair"
        else:
            return "poor"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        current = self.get_current_snapshot()
        capabilities = detect_gpu_capabilities()
        
        # Memory recommendations
        if current.memory_percent > 85:
            recommendations.append("System memory usage is high. Consider closing unnecessary applications or upgrading RAM.")
        
        # GPU recommendations
        for gpu_id, temp in current.gpu_temperature.items():
            if temp > 80:
                recommendations.append(f"GPU {gpu_id} temperature is high ({temp}°C). Check cooling and reduce processing load.")
        
        # Processing recommendations
        if self.processing_stats.average_fps < 5:
            recommendations.append("Processing speed is below optimal. Consider reducing resolution or using lower quality settings.")
        
        # Multi-GPU recommendations
        if capabilities.get("device_count", 0) > 1 and self.processing_stats.average_fps < 15:
            recommendations.append("Multiple GPUs detected. Enable multi-GPU parallel processing for better performance.")
        
        # Hardware encoding recommendations
        encoding_info = self.hardware_encoder.get_encoding_info()
        if encoding_info["available_encoders"]:
            recommendations.append("Hardware encoders available. Enable hardware encoding for faster video processing.")
        
        # Storage recommendations
        if current.disk_free_gb < 10:
            recommendations.append("Low disk space detected. Free up disk space to avoid processing issues.")
        
        return recommendations

class DiagnosticTool:
    """
    Comprehensive diagnostic tool for troubleshooting
    """
    
    def __init__(self):
        self.monitor = SystemMonitor()
        self.gpu_manager = GPUMemoryManager()
        self.hardware_encoder = HardwareEncoder()
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostic"""
        diagnostic_results = {
            "diagnostic_timestamp": datetime.now().isoformat(),
            "system_check": self._check_system_requirements(),
            "gpu_diagnostic": self._diagnose_gpu(),
            "encoding_diagnostic": self._diagnose_encoding(),
            "dependency_check": self._check_dependencies(),
            "performance_test": self._run_performance_test(),
            "recommendations": []
        }
        
        # Generate recommendations based on results
        diagnostic_results["recommendations"] = self._generate_diagnostic_recommendations(diagnostic_results)
        
        return diagnostic_results
    
    def _check_system_requirements(self) -> Dict[str, Any]:
        """Check minimum system requirements"""
        requirements = {
            "python_version_ok": platform.python_version() >= "3.8",
            "memory_sufficient": psutil.virtual_memory().total >= 8 * (1024**3),  # 8GB
            "disk_space_ok": psutil.disk_usage('/').free >= 10 * (1024**3),  # 10GB
            "cpu_cores_ok": psutil.cpu_count() >= 4
        }
        
        requirements["all_requirements_met"] = all(requirements.values())
        
        return requirements
    
    def _diagnose_gpu(self) -> Dict[str, Any]:
        """Comprehensive GPU diagnostic"""
        gpu_diagnostic = {
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "devices": []
        }
        
        if gpu_diagnostic["cuda_available"]:
            for gpu_id in range(gpu_diagnostic["device_count"]):
                device_info = {
                    "gpu_id": gpu_id,
                    "name": torch.cuda.get_device_name(gpu_id),
                    "compute_capability": torch.cuda.get_device_capability(gpu_id),
                    "memory_total_gb": torch.cuda.get_device_properties(gpu_id).total_memory / (1024**3),
                    "memory_available_gb": self.gpu_manager.get_available_vram_gb(gpu_id),
                    "suitable_for_processing": self.gpu_manager.get_available_vram_gb(gpu_id) >= 4.0
                }
                
                # Test basic GPU functionality
                try:
                    torch.cuda.set_device(gpu_id)
                    test_tensor = torch.randn(100, 100, device=f'cuda:{gpu_id}')
                    result = torch.matmul(test_tensor, test_tensor.t())
                    device_info["basic_operations_ok"] = True
                    del test_tensor, result
                    torch.cuda.empty_cache()
                except Exception as e:
                    device_info["basic_operations_ok"] = False
                    device_info["error"] = str(e)
                
                gpu_diagnostic["devices"].append(device_info)
        
        return gpu_diagnostic
    
    def _diagnose_encoding(self) -> Dict[str, Any]:
        """Diagnose video encoding capabilities"""
        encoding_info = self.hardware_encoder.get_encoding_info()
        
        # Test basic encoding functionality
        try:
            # Try to create a simple test video
            test_cmd = [
                "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=0.1:size=320x240:rate=1",
                "-f", "null", "-"
            ]
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            basic_encoding_ok = result.returncode == 0
        except Exception:
            basic_encoding_ok = False
        
        return {
            "ffmpeg_available": encoding_info["ffmpeg_version"] is not None,
            "ffmpeg_version": encoding_info["ffmpeg_version"],
            "hardware_encoders_count": len(encoding_info["available_encoders"]),
            "available_encoders": list(encoding_info["available_encoders"].keys()),
            "nvidia_support": encoding_info["hardware_support"]["nvidia"],
            "intel_support": encoding_info["hardware_support"]["intel"],
            "amd_support": encoding_info["hardware_support"]["amd"],
            "basic_encoding_test": basic_encoding_ok
        }
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check critical dependencies"""
        dependencies = {
            "torch": self._check_import("torch"),
            "cv2": self._check_import("cv2"),
            "numpy": self._check_import("numpy"),
            "psutil": self._check_import("psutil"),
            "gradio": self._check_import("gradio"),
            "ffmpeg": self._check_command("ffmpeg")
        }
        
        # Optional dependencies
        optional_deps = {
            "pynvml": self._check_import("pynvml"),
            "cpuinfo": self._check_import("cpuinfo")
        }
        
        return {
            "required_dependencies": dependencies,
            "optional_dependencies": optional_deps,
            "all_required_available": all(dependencies.values()),
            "optional_count": sum(optional_deps.values())
        }
    
    def _check_import(self, module_name: str) -> bool:
        """Check if module can be imported"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def _check_command(self, command: str) -> bool:
        """Check if command is available"""
        try:
            result = subprocess.run([command, "-version"], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _run_performance_test(self) -> Dict[str, Any]:
        """Run basic performance test"""
        test_results = {}
        
        # CPU test
        start_time = time.time()
        for _ in range(1000000):
            _ = sum(range(100))
        cpu_test_time = time.time() - start_time
        test_results["cpu_test_time"] = cpu_test_time
        
        # Memory test
        try:
            start_time = time.time()
            large_array = np.random.randn(10000, 1000)
            result = np.dot(large_array, large_array.T)
            memory_test_time = time.time() - start_time
            test_results["memory_test_time"] = memory_test_time
            test_results["memory_test_ok"] = True
            del large_array, result
        except Exception as e:
            test_results["memory_test_ok"] = False
            test_results["memory_error"] = str(e)
        
        # GPU test
        if torch.cuda.is_available():
            try:
                start_time = time.time()
                gpu_array = torch.randn(5000, 5000, device='cuda')
                result = torch.matmul(gpu_array, gpu_array.t())
                gpu_test_time = time.time() - start_time
                test_results["gpu_test_time"] = gpu_test_time
                test_results["gpu_test_ok"] = True
                del gpu_array, result
                torch.cuda.empty_cache()
            except Exception as e:
                test_results["gpu_test_ok"] = False
                test_results["gpu_error"] = str(e)
        else:
            test_results["gpu_test_ok"] = False
            test_results["gpu_error"] = "CUDA not available"
        
        return test_results
    
    def _generate_diagnostic_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # System requirements
        req = results["system_check"]
        if not req["python_version_ok"]:
            recommendations.append("Upgrade Python to version 3.8 or higher")
        if not req["memory_sufficient"]:
            recommendations.append("Upgrade system memory to at least 8GB")
        if not req["disk_space_ok"]:
            recommendations.append("Free up disk space (at least 10GB recommended)")
        
        # GPU recommendations
        gpu_diag = results["gpu_diagnostic"]
        if not gpu_diag["cuda_available"]:
            recommendations.append("Install CUDA-compatible GPU for hardware acceleration")
        else:
            unsuitable_gpus = [d for d in gpu_diag["devices"] if not d["suitable_for_processing"]]
            if unsuitable_gpus:
                recommendations.append("Some GPUs have insufficient VRAM (<4GB). Consider upgrading for better performance.")
        
        # Encoding recommendations
        enc_diag = results["encoding_diagnostic"]
        if not enc_diag["ffmpeg_available"]:
            recommendations.append("Install FFmpeg for video processing capabilities")
        if enc_diag["hardware_encoders_count"] == 0:
            recommendations.append("No hardware encoders detected. Install appropriate drivers for faster encoding.")
        
        # Dependency recommendations
        dep_check = results["dependency_check"]
        if not dep_check["all_required_available"]:
            missing = [name for name, available in dep_check["required_dependencies"].items() if not available]
            recommendations.append(f"Install missing dependencies: {', '.join(missing)}")
        
        return recommendations