"""
GPU utilities for memory management and performance optimization
"""

import torch
import gc
import subprocess
import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

class GPUMemoryManager:
    """Advanced GPU memory management for video processing"""
    
    def __init__(self):
        self.device_count = torch.cuda.device_count()
        self.memory_fractions = {}
        self.memory_pools = {}
        self.reserved_memory = {}
        
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.nvml_available = True
            except:
                self.nvml_available = False
        else:
            self.nvml_available = False
    
    def get_gpu_info(self) -> Dict[int, Dict[str, Any]]:
        """Get comprehensive GPU information"""
        gpu_info = {}
        
        for gpu_id in range(self.device_count):
            info = {
                "name": torch.cuda.get_device_name(gpu_id),
                "compute_capability": torch.cuda.get_device_capability(gpu_id),
                "total_memory": torch.cuda.get_device_properties(gpu_id).total_memory,
                "available": True
            }
            
            if self.nvml_available:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    temp_info = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    
                    info.update({
                        "memory_total": mem_info.total,
                        "memory_used": mem_info.used,
                        "memory_free": mem_info.free,
                        "utilization_gpu": util_info.gpu,
                        "utilization_memory": util_info.memory,
                        "temperature": temp_info
                    })
                except:
                    pass
            
            # Get PyTorch memory info
            if gpu_id < torch.cuda.device_count():
                torch.cuda.set_device(gpu_id)
                info.update({
                    "pytorch_allocated": torch.cuda.memory_allocated(gpu_id),
                    "pytorch_cached": torch.cuda.memory_reserved(gpu_id),
                    "pytorch_max_allocated": torch.cuda.max_memory_allocated(gpu_id)
                })
            
            gpu_info[gpu_id] = info
            
        return gpu_info
    
    def estimate_vram_usage(self, width: int, height: int, fps: float, multiplier: int) -> Tuple[float, float]:
        """
        Estimate VRAM usage for video processing
        Returns: (estimated_gb, recommended_scale)
        """
        # Base model overhead (RIFE model weights)
        base_model_gb = 2.1
        
        # Frame memory calculation
        # Each frame: width * height * channels * bytes_per_pixel
        frame_bytes = width * height * 3 * 4  # RGB float32
        frame_gb = frame_bytes / (1024**3)
        
        # Buffer requirements
        # Need to hold: input frames, intermediate frames, output frames
        frames_in_memory = 8  # Conservative estimate
        buffer_multiplier = multiplier * 2  # Input + output frames
        
        processing_gb = frame_gb * frames_in_memory * buffer_multiplier
        
        # Total estimate with safety margin
        total_gb = (base_model_gb + processing_gb) * 1.3
        
        # Recommend scale based on typical VRAM sizes
        available_gb = self.get_available_vram_gb()
        
        if total_gb > available_gb:
            # Calculate scale to fit in available VRAM
            scale_factor = (available_gb / total_gb) ** 0.5  # Square root for area scaling
            recommended_scale = max(0.25, min(1.0, scale_factor))
        else:
            recommended_scale = 1.0
            
        return total_gb, recommended_scale
    
    def get_available_vram_gb(self, gpu_id: int = 0) -> float:
        """Get available VRAM in GB for specific GPU"""
        if self.nvml_available:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return mem_info.free / (1024**3)
            except:
                pass
        
        # Fallback to PyTorch
        torch.cuda.set_device(gpu_id)
        total = torch.cuda.get_device_properties(gpu_id).total_memory
        allocated = torch.cuda.memory_allocated(gpu_id)
        return (total - allocated) / (1024**3)
    
    def optimize_memory_settings(self, gpu_id: int = 0, memory_fraction: float = 0.9):
        """Optimize PyTorch memory settings for video processing"""
        torch.cuda.set_device(gpu_id)
        
        # Enable memory growth to avoid pre-allocating all memory
        if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
            torch.cuda.set_per_process_memory_fraction(memory_fraction, gpu_id)
        
        # Enable cudnn optimizations
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        
        # Clear any existing cache
        torch.cuda.empty_cache()
        
        # Store settings
        self.memory_fractions[gpu_id] = memory_fraction
        
        return {
            "gpu_id": gpu_id,
            "memory_fraction": memory_fraction,
            "cudnn_benchmark": True,
            "available_memory_gb": self.get_available_vram_gb(gpu_id)
        }
    
    def adaptive_resolution_scaling(self, width: int, height: int, gpu_id: int = 0) -> Tuple[int, int, float]:
        """
        Automatically determine optimal resolution scaling
        Returns: (new_width, new_height, scale_factor)
        """
        available_gb = self.get_available_vram_gb(gpu_id)
        
        # VRAM thresholds for different resolutions
        if available_gb >= 16:  # High-end GPU
            max_pixels = 3840 * 2160  # 4K
        elif available_gb >= 8:   # Mid-range GPU
            max_pixels = 2560 * 1440  # 1440p
        elif available_gb >= 6:   # Budget GPU
            max_pixels = 1920 * 1080  # 1080p
        else:                     # Very limited
            max_pixels = 1280 * 720   # 720p
        
        current_pixels = width * height
        
        if current_pixels <= max_pixels:
            return width, height, 1.0
        
        # Calculate scale factor to fit target resolution
        scale_factor = (max_pixels / current_pixels) ** 0.5
        
        # Round to common scale factors
        if scale_factor >= 0.75:
            scale_factor = 0.75
        elif scale_factor >= 0.5:
            scale_factor = 0.5
        else:
            scale_factor = 0.25
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Ensure dimensions are even (required for video encoding)
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)
        
        return new_width, new_height, scale_factor
    
    def clear_memory_cache(self, gpu_id: Optional[int] = None):
        """Clear GPU memory cache and run garbage collection"""
        if gpu_id is not None:
            torch.cuda.set_device(gpu_id)
            torch.cuda.empty_cache()
        else:
            # Clear all GPUs
            for i in range(self.device_count):
                torch.cuda.set_device(i)
                torch.cuda.empty_cache()
        
        # Force Python garbage collection
        gc.collect()
    
    def monitor_memory_usage(self, gpu_id: int = 0) -> Dict[str, float]:
        """Monitor real-time memory usage"""
        torch.cuda.set_device(gpu_id)
        
        info = {
            "allocated_gb": torch.cuda.memory_allocated(gpu_id) / (1024**3),
            "cached_gb": torch.cuda.memory_reserved(gpu_id) / (1024**3),
            "max_allocated_gb": torch.cuda.max_memory_allocated(gpu_id) / (1024**3),
        }
        
        if self.nvml_available:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                info.update({
                    "total_gb": mem_info.total / (1024**3),
                    "used_gb": mem_info.used / (1024**3),
                    "free_gb": mem_info.free / (1024**3),
                    "utilization_percent": util_info.gpu,
                    "memory_utilization_percent": util_info.memory
                })
            except:
                pass
        
        return info
    
    def setup_optimal_device(self, required_vram_gb: float = 4.0) -> int:
        """
        Find and setup optimal GPU device for processing
        Returns GPU ID of best available device
        """
        best_gpu = 0
        best_score = -1
        
        for gpu_id in range(self.device_count):
            gpu_info = self.get_gpu_info()[gpu_id]
            
            # Skip if not enough VRAM
            available_gb = self.get_available_vram_gb(gpu_id)
            if available_gb < required_vram_gb:
                continue
            
            # Score based on available memory and compute capability
            compute_score = gpu_info["compute_capability"][0] * 10 + gpu_info["compute_capability"][1]
            memory_score = available_gb
            
            # Prefer lower utilization
            utilization_penalty = gpu_info.get("utilization_gpu", 0) / 100
            
            total_score = compute_score + memory_score - utilization_penalty
            
            if total_score > best_score:
                best_score = total_score
                best_gpu = gpu_id
        
        # Setup optimal settings for selected GPU
        self.optimize_memory_settings(best_gpu)
        
        return best_gpu

class VRAMProfiler:
    """Profile VRAM usage during video processing"""
    
    def __init__(self, gpu_id: int = 0):
        self.gpu_id = gpu_id
        self.memory_manager = GPUMemoryManager()
        self.samples = []
        self.monitoring = False
    
    def start_monitoring(self):
        """Start monitoring VRAM usage"""
        self.monitoring = True
        self.samples = []
        
        # Reset peak memory counter
        torch.cuda.reset_peak_memory_stats(self.gpu_id)
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return statistics"""
        self.monitoring = False
        
        if not self.samples:
            return {}
        
        peak_allocated = torch.cuda.max_memory_allocated(self.gpu_id) / (1024**3)
        peak_reserved = torch.cuda.max_memory_reserved(self.gpu_id) / (1024**3)
        
        allocated_values = [s["allocated_gb"] for s in self.samples]
        
        return {
            "peak_allocated_gb": peak_allocated,
            "peak_reserved_gb": peak_reserved,
            "average_allocated_gb": sum(allocated_values) / len(allocated_values),
            "max_sampled_gb": max(allocated_values),
            "min_sampled_gb": min(allocated_values),
            "samples_count": len(self.samples),
            "memory_efficiency": peak_allocated / peak_reserved if peak_reserved > 0 else 1.0
        }
    
    def sample(self):
        """Take a memory usage sample"""
        if self.monitoring:
            sample = self.memory_manager.monitor_memory_usage(self.gpu_id)
            sample["timestamp"] = time.time()
            self.samples.append(sample)

def detect_gpu_capabilities() -> Dict[str, Any]:
    """Detect and return GPU capabilities for optimization"""
    if not torch.cuda.is_available():
        return {"cuda_available": False}
    
    manager = GPUMemoryManager()
    gpu_info = manager.get_gpu_info()
    
    capabilities = {
        "cuda_available": True,
        "device_count": manager.device_count,
        "devices": gpu_info,
        "amp_supported": torch.cuda.is_available() and hasattr(torch.cuda.amp, 'autocast'),
        "nvml_available": manager.nvml_available
    }
    
    # Determine processing recommendations
    total_vram = sum(info.get("memory_total", 0) for info in gpu_info.values()) / (1024**3)
    
    if total_vram >= 24:
        capabilities["processing_tier"] = "professional"  # Can handle 4K at full quality
        capabilities["recommended_parallel"] = 4
    elif total_vram >= 12:
        capabilities["processing_tier"] = "enthusiast"   # Can handle 4K with scaling
        capabilities["recommended_parallel"] = 2
    elif total_vram >= 8:
        capabilities["processing_tier"] = "mainstream"   # Good for 1080p
        capabilities["recommended_parallel"] = 2
    else:
        capabilities["processing_tier"] = "budget"       # Limited to lower resolutions
        capabilities["recommended_parallel"] = 1
    
    return capabilities

# Global instance for easy access
gpu_manager = GPUMemoryManager()