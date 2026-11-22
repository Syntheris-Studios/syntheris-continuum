"""
Quality enhancement utilities for multi-pass processing and temporal stabilization
"""

import torch
import torch.nn.functional as F
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
import tempfile
from concurrent.futures import ThreadPoolExecutor
import queue
import threading

from .gpu_utils import GPUMemoryManager
from .video_utils import get_video_info

class TemporalStabilizer:
    """
    Temporal stabilization for reducing flickering and artifacts in interpolated videos
    """
    
    def __init__(self, gpu_id: int = 0, window_size: int = 5):
        self.gpu_id = gpu_id
        self.window_size = window_size  # Number of frames to consider for stabilization
        self.device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        self.gpu_manager = GPUMemoryManager()
        
    def stabilize_sequence(self, 
                          frames: List[np.ndarray], 
                          progress_callback: Optional[Callable] = None) -> List[np.ndarray]:
        """
        Apply temporal stabilization to sequence of frames
        """
        if len(frames) < 3:
            return frames
            
        stabilized_frames = []
        half_window = self.window_size // 2
        
        with torch.cuda.device(self.gpu_id):
            for i, frame in enumerate(frames):
                if progress_callback and i % 10 == 0:
                    progress = i / len(frames) * 100
                    progress_callback(f"Temporal stabilization: {progress:.1f}%")
                
                # Get temporal window around current frame
                start_idx = max(0, i - half_window)
                end_idx = min(len(frames), i + half_window + 1)
                window_frames = frames[start_idx:end_idx]
                
                # Apply stabilization
                stabilized_frame = self._stabilize_frame(frame, window_frames, i - start_idx)
                stabilized_frames.append(stabilized_frame)
                
        return stabilized_frames
    
    def _stabilize_frame(self, 
                        current_frame: np.ndarray, 
                        window_frames: List[np.ndarray], 
                        current_idx: int) -> np.ndarray:
        """
        Stabilize single frame using temporal window
        """
        if len(window_frames) == 1:
            return current_frame
        
        # Convert to tensors
        tensors = []
        for frame in window_frames:
            tensor = torch.from_numpy(frame).float().permute(2, 0, 1) / 255.0
            tensor = tensor.unsqueeze(0).to(self.device)
            tensors.append(tensor)
        
        current_tensor = tensors[current_idx]
        
        with torch.no_grad():
            # Temporal filtering using weighted average
            weights = self._calculate_temporal_weights(tensors, current_idx)
            
            # Apply weighted combination
            stabilized_tensor = torch.zeros_like(current_tensor)
            total_weight = 0
            
            for i, (frame_tensor, weight) in enumerate(zip(tensors, weights)):
                # Calculate similarity to current frame
                similarity = self._calculate_frame_similarity(current_tensor, frame_tensor)
                adjusted_weight = weight * similarity
                
                stabilized_tensor += frame_tensor * adjusted_weight
                total_weight += adjusted_weight
            
            if total_weight > 0:
                stabilized_tensor /= total_weight
            else:
                stabilized_tensor = current_tensor
            
            # Apply edge-preserving smoothing
            stabilized_tensor = self._edge_preserving_smooth(current_tensor, stabilized_tensor)
        
        # Convert back to numpy
        output = stabilized_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = np.clip(output * 255, 0, 255).astype(np.uint8)
        
        return output
    
    def _calculate_temporal_weights(self, tensors: List[torch.Tensor], current_idx: int) -> List[float]:
        """Calculate temporal weights for frame blending"""
        weights = []
        center_frame = tensors[current_idx]
        
        for i, tensor in enumerate(tensors):
            if i == current_idx:
                weights.append(0.5)  # High weight for current frame
            else:
                # Distance-based weight
                distance = abs(i - current_idx)
                temporal_weight = np.exp(-distance / 2.0)
                
                # Motion-based adjustment
                motion_weight = self._calculate_motion_weight(center_frame, tensor)
                
                final_weight = temporal_weight * motion_weight
                weights.append(final_weight)
        
        return weights
    
    def _calculate_motion_weight(self, frame1: torch.Tensor, frame2: torch.Tensor) -> float:
        """Calculate motion-based weight between frames"""
        # Calculate optical flow magnitude
        diff = torch.abs(frame1 - frame2)
        motion_magnitude = torch.mean(diff)
        
        # Higher motion = lower weight
        motion_weight = torch.exp(-motion_magnitude * 5.0)
        
        return float(motion_weight.cpu())
    
    def _calculate_frame_similarity(self, frame1: torch.Tensor, frame2: torch.Tensor) -> float:
        """Calculate similarity between frames"""
        # Use SSIM-like metric
        mean1 = torch.mean(frame1)
        mean2 = torch.mean(frame2)
        
        var1 = torch.var(frame1)
        var2 = torch.var(frame2)
        
        covar = torch.mean((frame1 - mean1) * (frame2 - mean2))
        
        c1 = 0.01
        c2 = 0.03
        
        ssim = ((2 * mean1 * mean2 + c1) * (2 * covar + c2)) / \
               ((mean1**2 + mean2**2 + c1) * (var1 + var2 + c2))
        
        return float(torch.clamp(ssim, 0, 1).cpu())
    
    def _edge_preserving_smooth(self, 
                               original: torch.Tensor, 
                               smoothed: torch.Tensor, 
                               edge_threshold: float = 0.1) -> torch.Tensor:
        """Apply edge-preserving smoothing"""
        # Calculate edge mask
        grad_x = torch.abs(F.conv2d(original, 
                                   torch.tensor([[[[-1, 1]]]]).float().to(self.device), 
                                   padding=1))
        grad_y = torch.abs(F.conv2d(original,
                                   torch.tensor([[[[-1], [1]]]]).float().to(self.device),
                                   padding=1))
        
        edges = torch.sqrt(grad_x**2 + grad_y**2)
        edge_mask = (edges > edge_threshold).float()
        
        # Blend based on edge strength
        result = edge_mask * original + (1 - edge_mask) * smoothed
        
        return result

class ArtifactReducer:
    """
    Reduce common interpolation artifacts like ghosting, blurring, and aliasing
    """
    
    def __init__(self, gpu_id: int = 0):
        self.gpu_id = gpu_id
        self.device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        self.gpu_manager = GPUMemoryManager()
    
    def reduce_artifacts(self, 
                        frames: List[np.ndarray],
                        original_frames: List[np.ndarray] = None,
                        progress_callback: Optional[Callable] = None) -> List[np.ndarray]:
        """
        Apply artifact reduction to interpolated frames
        """
        enhanced_frames = []
        
        with torch.cuda.device(self.gpu_id):
            for i, frame in enumerate(frames):
                if progress_callback and i % 10 == 0:
                    progress = i / len(frames) * 100
                    progress_callback(f"Artifact reduction: {progress:.1f}%")
                
                # Get reference frames if available
                ref_frame = None
                if original_frames and i < len(original_frames):
                    ref_frame = original_frames[i]
                
                enhanced_frame = self._reduce_frame_artifacts(frame, ref_frame)
                enhanced_frames.append(enhanced_frame)
        
        return enhanced_frames
    
    def _reduce_frame_artifacts(self, 
                               frame: np.ndarray, 
                               reference: Optional[np.ndarray] = None) -> np.ndarray:
        """Reduce artifacts in single frame"""
        # Convert to tensor
        tensor = torch.from_numpy(frame).float().permute(2, 0, 1) / 255.0
        tensor = tensor.unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            enhanced = tensor
            
            # Apply denoising
            enhanced = self._apply_denoising(enhanced)
            
            # Reduce ghosting artifacts
            enhanced = self._reduce_ghosting(enhanced, tensor)
            
            # Sharpen details
            enhanced = self._selective_sharpening(enhanced)
            
            # Apply reference-guided enhancement if available
            if reference is not None:
                ref_tensor = torch.from_numpy(reference).float().permute(2, 0, 1) / 255.0
                ref_tensor = ref_tensor.unsqueeze(0).to(self.device)
                enhanced = self._reference_guided_enhancement(enhanced, ref_tensor)
        
        # Convert back
        output = enhanced.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = np.clip(output * 255, 0, 255).astype(np.uint8)
        
        return output
    
    def _apply_denoising(self, tensor: torch.Tensor, strength: float = 0.1) -> torch.Tensor:
        """Apply subtle denoising"""
        # Gaussian blur for noise reduction
        kernel_size = 3
        sigma = 0.5
        
        # Create Gaussian kernel
        kernel = torch.exp(-torch.arange(-(kernel_size//2), kernel_size//2 + 1).float()**2 / (2 * sigma**2))
        kernel = kernel / kernel.sum()
        kernel_2d = kernel.unsqueeze(0) * kernel.unsqueeze(1)
        kernel_2d = kernel_2d.unsqueeze(0).unsqueeze(0).to(self.device)
        
        # Apply separable convolution
        blurred = F.conv2d(tensor, kernel_2d.expand(3, 1, -1, -1), 
                          padding=kernel_size//2, groups=3)
        
        # Blend with original
        denoised = (1 - strength) * tensor + strength * blurred
        
        return denoised
    
    def _reduce_ghosting(self, enhanced: torch.Tensor, original: torch.Tensor) -> torch.Tensor:
        """Reduce ghosting artifacts"""
        # Calculate confidence map based on gradient consistency
        grad_x_enh = F.conv2d(enhanced, torch.tensor([[[[-1, 1]]]]).float().to(self.device))
        grad_y_enh = F.conv2d(enhanced, torch.tensor([[[[-1], [1]]]]).float().to(self.device))
        
        grad_x_orig = F.conv2d(original, torch.tensor([[[[-1, 1]]]]).float().to(self.device))
        grad_y_orig = F.conv2d(original, torch.tensor([[[[-1], [1]]]]).float().to(self.device))
        
        grad_consistency = torch.exp(-torch.abs(grad_x_enh - grad_x_orig) - torch.abs(grad_y_enh - grad_y_orig))
        
        # Use consistency to blend
        result = grad_consistency * enhanced + (1 - grad_consistency) * original
        
        return result
    
    def _selective_sharpening(self, tensor: torch.Tensor, strength: float = 0.2) -> torch.Tensor:
        """Apply selective sharpening to enhance details"""
        # Create sharpening kernel
        sharpen_kernel = torch.tensor([[[
            [0, -0.5, 0],
            [-0.5, 3, -0.5], 
            [0, -0.5, 0]
        ]]]).float().to(self.device)
        
        sharpened = F.conv2d(tensor, sharpen_kernel.expand(3, 1, -1, -1), 
                           padding=1, groups=3)
        
        # Calculate edge mask for selective application
        edges = self._calculate_edge_mask(tensor)
        
        # Apply sharpening only to edges
        result = edges * (strength * sharpened + (1 - strength) * tensor) + (1 - edges) * tensor
        
        return result
    
    def _calculate_edge_mask(self, tensor: torch.Tensor) -> torch.Tensor:
        """Calculate edge mask for selective processing"""
        grad_x = torch.abs(F.conv2d(tensor, torch.tensor([[[[-1, 1]]]]).float().to(self.device), padding=1))
        grad_y = torch.abs(F.conv2d(tensor, torch.tensor([[[[-1], [1]]]]).float().to(self.device), padding=1))
        
        edges = torch.sqrt(grad_x**2 + grad_y**2)
        edge_mask = torch.sigmoid((edges - 0.1) * 10)  # Smooth threshold
        
        return edge_mask
    
    def _reference_guided_enhancement(self, 
                                    enhanced: torch.Tensor, 
                                    reference: torch.Tensor) -> torch.Tensor:
        """Use reference frame to guide enhancement"""
        # Calculate feature similarity
        similarity = self._calculate_feature_similarity(enhanced, reference)
        
        # Blend based on similarity
        alpha = 0.3
        guided = alpha * reference + (1 - alpha) * enhanced
        
        # Use similarity as confidence
        result = similarity * guided + (1 - similarity) * enhanced
        
        return result
    
    def _calculate_feature_similarity(self, frame1: torch.Tensor, frame2: torch.Tensor) -> torch.Tensor:
        """Calculate local feature similarity"""
        # Use patch-based comparison
        patch_size = 5
        padding = patch_size // 2
        
        # Calculate local means
        mean1 = F.avg_pool2d(F.pad(frame1, [padding]*4, mode='reflect'), 
                            patch_size, stride=1)
        mean2 = F.avg_pool2d(F.pad(frame2, [padding]*4, mode='reflect'), 
                            patch_size, stride=1)
        
        # Calculate similarity
        similarity = torch.exp(-torch.abs(mean1 - mean2) * 5.0)
        
        return similarity

class MultiPassProcessor:
    """
    Multi-pass processing system for enhanced quality
    """
    
    def __init__(self, 
                 gpu_id: int = 0,
                 enable_temporal_stabilization: bool = True,
                 enable_artifact_reduction: bool = True):
        self.gpu_id = gpu_id
        self.gpu_manager = GPUMemoryManager()
        
        self.temporal_stabilizer = TemporalStabilizer(gpu_id) if enable_temporal_stabilization else None
        self.artifact_reducer = ArtifactReducer(gpu_id) if enable_artifact_reduction else None
        
    def process_video_multipass(self,
                               interpolated_frames: List[np.ndarray],
                               original_frames: List[np.ndarray] = None,
                               progress_callback: Optional[Callable] = None) -> List[np.ndarray]:
        """
        Apply multi-pass enhancement to interpolated video
        """
        enhanced_frames = interpolated_frames.copy()
        
        # Pass 1: Temporal Stabilization
        if self.temporal_stabilizer:
            if progress_callback:
                progress_callback("Multi-pass enhancement: Pass 1 - Temporal stabilization")
            
            enhanced_frames = self.temporal_stabilizer.stabilize_sequence(
                enhanced_frames, progress_callback
            )
            
            # Memory cleanup
            self.gpu_manager.clear_memory_cache(self.gpu_id)
        
        # Pass 2: Artifact Reduction
        if self.artifact_reducer:
            if progress_callback:
                progress_callback("Multi-pass enhancement: Pass 2 - Artifact reduction")
            
            enhanced_frames = self.artifact_reducer.reduce_artifacts(
                enhanced_frames, original_frames, progress_callback
            )
            
            # Memory cleanup
            self.gpu_manager.clear_memory_cache(self.gpu_id)
        
        # Pass 3: Final Quality Enhancement
        if progress_callback:
            progress_callback("Multi-pass enhancement: Pass 3 - Final optimization")
        
        enhanced_frames = self._final_quality_pass(enhanced_frames, progress_callback)
        
        return enhanced_frames
    
    def _final_quality_pass(self, 
                           frames: List[np.ndarray],
                           progress_callback: Optional[Callable] = None) -> List[np.ndarray]:
        """Apply final quality enhancement pass"""
        enhanced_frames = []
        
        with torch.cuda.device(self.gpu_id):
            for i, frame in enumerate(frames):
                if progress_callback and i % 20 == 0:
                    progress = i / len(frames) * 100
                    progress_callback(f"Final enhancement: {progress:.1f}%")
                
                # Apply final corrections
                enhanced_frame = self._apply_final_corrections(frame)
                enhanced_frames.append(enhanced_frame)
        
        return enhanced_frames
    
    def _apply_final_corrections(self, frame: np.ndarray) -> np.ndarray:
        """Apply final color and contrast corrections"""
        # Convert to tensor
        tensor = torch.from_numpy(frame).float().permute(2, 0, 1) / 255.0
        tensor = tensor.unsqueeze(0).to(f"cuda:{self.gpu_id}")
        
        with torch.no_grad():
            # Subtle contrast enhancement
            enhanced = self._enhance_contrast(tensor)
            
            # Color balance adjustment
            enhanced = self._adjust_color_balance(enhanced)
            
            # Final cleanup
            enhanced = torch.clamp(enhanced, 0, 1)
        
        # Convert back
        output = enhanced.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = (output * 255).astype(np.uint8)
        
        return output
    
    def _enhance_contrast(self, tensor: torch.Tensor, strength: float = 0.1) -> torch.Tensor:
        """Apply subtle contrast enhancement"""
        # Calculate histogram-based contrast adjustment
        mean_val = torch.mean(tensor)
        
        # S-curve for contrast
        enhanced = torch.sigmoid((tensor - mean_val) * (1 + strength)) * 2 - 1
        enhanced = (enhanced + 1) / 2  # Normalize back to [0,1]
        
        # Blend with original
        result = (1 - strength) * tensor + strength * enhanced
        
        return result
    
    def _adjust_color_balance(self, tensor: torch.Tensor) -> torch.Tensor:
        """Apply subtle color balance adjustment"""
        # Calculate channel means
        r_mean = torch.mean(tensor[:, 0])
        g_mean = torch.mean(tensor[:, 1]) 
        b_mean = torch.mean(tensor[:, 2])
        
        # Calculate overall mean
        overall_mean = (r_mean + g_mean + b_mean) / 3
        
        # Apply subtle corrections
        balance_strength = 0.05
        r_factor = 1 + balance_strength * (overall_mean - r_mean) / (overall_mean + 1e-6)
        g_factor = 1 + balance_strength * (overall_mean - g_mean) / (overall_mean + 1e-6)
        b_factor = 1 + balance_strength * (overall_mean - b_mean) / (overall_mean + 1e-6)
        
        balanced = tensor.clone()
        balanced[:, 0] *= r_factor
        balanced[:, 1] *= g_factor
        balanced[:, 2] *= b_factor
        
        return torch.clamp(balanced, 0, 1)
    
    def get_enhancement_info(self) -> Dict[str, Any]:
        """Get information about enhancement capabilities"""
        return {
            "temporal_stabilization": self.temporal_stabilizer is not None,
            "artifact_reduction": self.artifact_reducer is not None,
            "gpu_id": self.gpu_id,
            "multi_pass_processing": True,
            "available_vram_gb": self.gpu_manager.get_available_vram_gb(self.gpu_id)
        }