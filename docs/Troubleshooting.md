# Troubleshooting Guide - Syntheris Continuum V4.2.3

> Current application: V5.1.0. This retained guide describes earlier features and examples; use ../README.md, ../CHANGELOG.md and ../MODEL_PROVENANCE.md for current setup and validation status.
**Common issues and solutions for video processing problems**

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [UI Launch Problems](#ui-launch-problems)
3. [Processing Failures](#processing-failures)
4. [Pipeline Fortification Issues (V4.2.3)](#pipeline-fortification-issues-v310)
5. [Performance Issues](#performance-issues)
6. [File Upload Problems](#file-upload-problems)
7. [Output Issues](#output-issues)
8. [Hardware Problems](#hardware-problems)
9. [Advanced Troubleshooting](#advanced-troubleshooting)

## Installation Issues

### Python Version Problems

**Issue**: "Python 3.11 not found" or version conflicts
```
Error: Python 3.11 is required
```

**Solutions**:
1. **Install Python 3.11 specifically**:
   ```bash
   # Download from python.org and install Python 3.11.x
   # Verify: py -3.11 --version
   ```

2. **Create venv with correct Python**:
   ```bash
   py -3.11 -m venv .venv311_final
   .venv311_final\Scripts\Activate.ps1
   ```

### PyTorch Installation Issues

**Issue**: RTX 40 Series GPU crashes with "Exit code 3221226505"
```
RuntimeError: CUDA out of memory
Process finished with exit code 3221226505
```

**Root Cause**: GPU memory exhaustion during RIFE processing.

**Solution (V4.2.3 Automatic)**: Pipeline Fortification automatically handles this error with:
- Progressive resolution scaling (15% reduction per retry)
- Dynamic VRAM cleanup
- Intelligent retry system

**Manual Solution** (if fortification disabled):
```bash
# Use exact PyTorch version
pip install torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
```

Expected output:
```
PyTorch: 2.1.1+cu121
CUDA: True
```

### Dependency Conflicts

**Issue**: Package version conflicts
```
ERROR: pip's dependency resolver does not currently consider all the packages
```

**Solutions**:
1. **Use locked requirements**:
   ```bash
   pip install -r requirements-lock.txt
   ```

2. **Fresh environment**:
   ```bash
   # Delete existing venv and recreate
   rmdir /s .venv311_final
   py -3.11 -m venv .venv311_final
   .venv311_final\Scripts\Activate.ps1
   pip install -U pip
   pip install -r requirements.txt
   ```

## UI Launch Problems

### Gradio Compatibility Issues

**Issue**: UI fails to launch with schema errors
```
TypeError: argument of type 'bool' is not iterable
AttributeError: module 'gradio' has no attribute 'Interface'
```

**Root Cause**: Gradio version incompatibilities

**Solutions**:
1. **Gradio patches are automatically applied** - These errors should be resolved in V4.2.3

2. **If issues persist**, check dependencies:
   ```bash
   # Verify all dependencies installed
   pip install -r requirements.txt
   
   # Check specific compatibility
   python -c "import gradio; print(f'Gradio: {gradio.__version__}')"
   ```

### Port Already in Use

**Issue**: "Address already in use" error
```
OSError: [Errno 98] Address already in use
```

**Solutions**:
```bash
# Method 1: Use different port
python syntheris_video_processor/main.py --port 7861

# Method 2: Kill existing process
netstat -ano | findstr :7860
taskkill /PID [ProcessID] /F
```

### Import Errors

**Issue**: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'syntheris_video_processor'
```

**Solutions**:
1. **Activate virtual environment**:
   ```bash
   .venv311_final\Scripts\Activate.ps1
   ```

2. **Install in development mode**:
   ```bash
   pip install -e .
   ```

3. **Run from correct directory**:
   ```bash
   # Must be in project root
   cd "Syntheris Continuum Open Source"
   python syntheris_video_processor/main.py
   ```

## Processing Failures

### RIFE Backend Errors

**Issue**: "RIFE backend failed" or processing hangs
```
RuntimeError: RIFE processing failed with exit code 1
```

**Common Causes & Solutions**:

1. **GPU Memory Issues**:
   ```bash
   # Enable VRAM guard
   Auto VRAM Guard: ON
   
   # Reduce resolution scale
   Resolution Scale: 0.5 or 0.75
   
   # Process shorter segments
   Scene-cut aware: ON
   ```

2. **File Path Issues**:
   - Use files without spaces in names
   - Avoid special characters (é, ñ, etc.)
   - Keep path lengths under 260 characters
   - Use MP4 format when possible

3. **Input Format Problems**:
   ```bash
   # Convert problematic files
   ffmpeg -i "input.mov" -c:v libx264 -c:a aac "input.mp4"
   ```

### Segment Processing Failures

**Issue**: Some segments fail while others succeed
```
[2/5] Processing segment: FAILED
[3/5] Processing segment: SUCCESS
```

**Solutions**:
1. **Check individual segments**:
   - Look in `temp/job_[id]/` directory
   - Examine failed segment files
   - Process segment manually to identify issue

2. **Adjust scene detection**:
   ```
   Scene threshold: 0.5 (less sensitive)
   # OR
   Scene-cut aware: OFF (single segment)
   ```

### ATFI Processing Issues

**Issue**: ATFI processing fails or produces poor results
```
ATFI motion analysis failed
```

**Solutions**:
1. **Disable ATFI temporarily**:
   ```
   Enable ATFI: OFF
   ```

2. **Adjust ATFI settings**:
   ```
   Motion threshold: 0.40 (less sensitive)
   High-motion FPS: 48 (lower)
   Method: scene (more reliable)
   ```

## Pipeline Fortification Issues (V4.2.3)

### Fortification System Not Activating

**Issue**: Processing failures occur without fortification retry attempts
```
Processing failed: RIFE exit code 3221226505
(No retry attempts shown)
```

**Solutions**:
1. **Verify fortification is enabled**:
   ```python
   # Check if fortification patch is applied
   from fortification.processor_fortified_patch import apply_fortification_patch
   # Should be automatically applied in V4.2.3
   ```

2. **Enable fortification manually**:
   ```python
   processor = apply_fortification_patch(
       processor_instance=your_processor,
       enable_fortification=True,
       processing_mode="BALANCED"
   )
   ```

### Excessive Retry Attempts

**Issue**: Fortification system retries too many times, slowing processing
```
[Fortification] Retry attempt 5/3 - Progressive scaling applied
```

**Solutions**:
1. **Adjust retry limits**:
   ```python
   fortification = PipelineFortification(
       max_retries=2,  # Reduce from default 3
       initial_scale_reduction=0.20  # More aggressive scaling
   )
   ```

2. **Use conservative processing mode**:
   ```
   Processing Mode: SAFE or MINIMAL
   # Starts with lower resource usage
   ```

### Processing Mode Selection Issues

**Issue**: Automatic processing mode selection too aggressive or conservative

**Available Processing Modes**:
- **ULTRA**: Maximum quality, highest resource usage
- **HIGH**: Balanced quality/performance  
- **BALANCED**: Default mode (recommended)
- **SAFE**: Conservative resource usage
- **MINIMAL**: Lowest resource usage, basic quality

**Solutions**:
1. **Manual mode selection**:
   ```python
   processor.process_video(
       video_file="input.mp4",
       fortification_mode="SAFE"  # Override automatic selection
   )
   ```

2. **System-specific optimization**:
   ```
   # RTX 4090: ULTRA or HIGH
   # RTX 4080: HIGH or BALANCED  
   # RTX 4070: BALANCED or SAFE
   # RTX 3080: SAFE or MINIMAL
   ```

### Fallback System Issues

**Issue**: FFmpeg minterpolate fallback produces poor quality
```
[Fortification] RIFE failed, falling back to FFmpeg minterpolate
```

**Solutions**:
1. **Disable fallback temporarily**:
   ```python
   # Process with RIFE-only (will fail if RIFE can't handle)
   processor.process_video(
       video_file="input.mp4",
       enable_fallback=False
   )
   ```

2. **Optimize fallback settings**:
   ```
   # Reduce input complexity for better fallback results
   Resolution Scale: 0.75
   Scene-cut aware: ON (shorter segments)
   ```

### Memory Scaling Issues

**Issue**: Progressive resource scaling too aggressive or insufficient
```
[Fortification] Memory scaling applied: 85% -> 70% -> 55%
CUDA out of memory persists
```

**Solutions**:
1. **Adjust scaling parameters**:
   ```python
   fortification = PipelineFortification(
       initial_scale_reduction=0.25,  # More aggressive initial scaling
       min_resolution_scale=0.25     # Allow more reduction
   )
   ```

2. **Pre-emptive scaling**:
   ```
   # Start with lower baseline
   Resolution Scale: 0.5
   Processing Mode: SAFE
   ```

### Concatenation Fallback Problems

**Issue**: Enhanced concatenation system fails on all three strategies
```
[Fortification] concat_demuxer failed
[Fortification] filter_complex failed  
[Fortification] full_re_encode failed
```

**Solutions**:
1. **Check segment integrity**:
   ```bash
   # Manually verify segments in temp directory
   ffprobe temp/job_*/segment_*.mp4
   ```

2. **Simplify concatenation**:
   ```
   # Disable complex features that may cause concatenation issues
   Crossfade Joins: OFF
   Normalize CFR: ON
   ```

### Performance Statistics Monitoring

**Issue**: Want to monitor fortification performance and success rates

**Solutions**:
1. **Enable detailed logging**:
   ```python
   import logging
   logging.getLogger('fortification').setLevel(logging.DEBUG)
   ```

2. **Access performance stats**:
   ```python
   # After processing
   stats = processor.get_fortification_stats()
   print(f"Success rate: {stats['success_rate']}")
   print(f"Average retries: {stats['avg_retries']}")
   print(f"Fallback usage: {stats['fallback_rate']}")
   ```

### Disabling Fortification

**Issue**: Need to disable fortification for debugging or compatibility

**Solutions**:
1. **Temporary disable**:
   ```python
   processor.process_video(
       video_file="input.mp4",
       enable_fortification=False
   )
   ```

2. **System-wide disable**:
   ```python
   # In configuration or main.py
   FORTIFICATION_ENABLED = False
   ```

## Performance Issues

### Slow Processing Speed

**Issue**: Processing takes much longer than expected

**GPU Performance Check**:
```bash
# Verify GPU is detected
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

**Solutions**:
1. **GPU Optimization**:
   ```
   Resolution Scale: 0.75
   UHD Mode: off
   Auto VRAM Guard: ON
   ```

2. **Reduce Quality for Speed**:
   ```
   Scene-cut aware: OFF (faster but lower quality)
   Enable ATFI: OFF
   Crossfade Joins: OFF
   ```

3. **Check Background Processes**:
   - Close other GPU-intensive applications
   - Check Task Manager for high CPU/GPU usage
   - Ensure adequate cooling (GPU throttling)

### Out of Memory Errors

**Issue**: CUDA out of memory or system RAM exhaustion
```
RuntimeError: CUDA out of memory. Tried to allocate [X] MiB
```

**Solutions**:
1. **Immediate fixes**:
   ```
   Resolution Scale: 0.5
   Auto VRAM Guard: ON
   ```

2. **Process in smaller segments**:
   ```
   Scene-cut aware: ON
   Scene threshold: 0.2 (more segments)
   ```

3. **System-level solutions**:
   - Close other applications
   - Restart GPU driver: `nvidia-smi -r`
   - Check available system RAM

## File Upload Problems

### Batch Upload Not Working

**Issue**: Can't select multiple files in batch mode

**Solutions**:
1. **Correct procedure**:
   - Switch "Upload Mode" to "Batch Mode" 
   - Use "Batch Files Input (Select Multiple)" button
   - Hold Ctrl while clicking files
   - Ensure all files appear in batch input field

2. **Browser issues**:
   - Try different browser (Chrome recommended)
   - Clear browser cache
   - Disable browser extensions

### Unsupported File Formats

**Issue**: "Unsupported file format" error

**Supported formats**: MP4, MOV, MKV, AVI, WebM

**Solutions**:
```bash
# Convert to MP4
ffmpeg -i "input.flv" -c:v libx264 -c:a aac "output.mp4"

# For variable frame rate videos
ffmpeg -i "input.mp4" -vf "fps=30" -c:a copy "output_cfr.mp4"
```

### File Size Limitations

**Issue**: Large files fail to upload or process

**Solutions**:
1. **Pre-process large files**:
   ```bash
   # Compress before processing
   ffmpeg -i "large_input.mp4" -crf 23 -preset fast "compressed_input.mp4"
   
   # Split into segments
   ffmpeg -i "large_input.mp4" -t 60 -c copy "segment1.mp4"
   ```

2. **Adjust processing settings**:
   ```
   Resolution Scale: 0.5
   Scene-cut aware: ON (enables segments)
   ```

## Output Issues

### Audio Sync Problems

**Issue**: Audio and video out of sync in output

**Solutions**:
1. **Enable CFR normalization**:
   ```
   Normalize CFR & Remove Duplicates: ON
   ```

2. **Check input video**:
   ```bash
   # Analyze input for VFR issues
   ffprobe -v error -select_streams v:0 -show_entries frame=pkt_pts_time -of csv=p=0 input.mp4 | head -20
   ```

3. **Manual audio fix**:
   ```bash
   # Extract and re-sync audio
   ffmpeg -i "processed_video.mp4" -i "original_audio.mp4" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "synced_output.mp4"
   ```

### Poor Output Quality

**Issue**: Output has artifacts, ghosting, or quality loss

**Solutions**:
1. **Enable quality features**:
   ```
   Scene-cut aware: ON
   Enable ATFI: ON
   Crossfade Joins: ON
   ```

2. **Check input quality**:
   - Use high-quality source material
   - Avoid heavily compressed inputs
   - Check for input artifacts

3. **Adjust processing settings**:
   ```
   Resolution Scale: 1.0 (full resolution)
   UHD Mode: auto
   ```

### Missing Output Files

**Issue**: Processing completes but no output file

**Solutions**:
1. **Check outputs directory**:
   ```
   outputs/
   └── output_[timestamp]_[filename]_interpolated.mp4
   ```

2. **Verify processing logs**:
   - Look for error messages in UI
   - Check temp directory for partial files

3. **Manual file recovery**:
   ```bash
   # Check temp directory
   dir temp\job_*
   # Look for completed segments
   ```

## Hardware Problems

### GPU Not Detected

**Issue**: "GPU not detected" or "CUDA unavailable"

**Solutions**:
1. **Verify NVIDIA drivers**:
   ```bash
   nvidia-smi
   # Should show GPU information
   ```

2. **Update drivers**:
   - Download latest drivers from NVIDIA
   - Use DDU (Display Driver Uninstaller) for clean install
   - Restart system after installation

3. **Check CUDA installation**:
   ```bash
   nvcc --version
   python -c "import torch; print(torch.version.cuda)"
   ```

### Thermal Throttling

**Issue**: GPU performance decreases during processing

**Solutions**:
1. **Monitor temperatures**:
   ```bash
   nvidia-smi -l 1
   # Watch GPU temp and clock speeds
   ```

2. **Improve cooling**:
   - Clean GPU fans and heatsink
   - Increase case ventilation
   - Consider custom fan curves

3. **Reduce processing load**:
   ```
   Resolution Scale: 0.75
   Processing in smaller batches
   ```

## Advanced Troubleshooting

### Debug Mode Activation

Enable detailed logging for complex issues:

```python
# Add to main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Process Monitoring

Monitor system resources during processing:

```bash
# Windows Task Manager
taskmgr

# PowerShell GPU monitoring
nvidia-smi dmon -i 0

# Memory monitoring
Get-Process python | Sort-Object WorkingSet64 -Descending
```

### Log Analysis

Check processing logs for errors:

```bash
# Application logs
dir outputs\*.log

# System event logs (Windows)
eventvwr.msc
```

### Safe Mode Processing

For unstable systems, use conservative settings:

```
Resolution Scale: 0.5
Scene-cut aware: ON
Enable ATFI: OFF
Auto VRAM Guard: ON
Multiplier: 2x (avoid 4x/8x)
```

### Emergency Recovery

If system becomes unstable:

1. **Force quit processing**:
   - Ctrl+C in terminal
   - Task Manager -> End Python process

2. **Clean temporary files**:
   ```bash
   rmdir /s temp
   mkdir temp
   ```

3. **Reset GPU**:
   ```bash
   nvidia-smi -r
   ```

### Community Support

For issues not covered here:

1. **Check documentation**:
   - [Technical Reference](Technical_Reference.md)
   - [Advanced Features](Advanced_Features.md)

2. **Gather diagnostic information**:
   ```bash
   # System info
   python -c "import sys, torch; print(f'Python: {sys.version}'); print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
   
   # GPU info
   nvidia-smi
   
   # Processing logs
   # Include last 50 lines of processing output
   ```

---

**Version**: Syntheris Continuum V4.2.3  
**Last Updated**: August 2025  
**For complex issues**: Include system specs, error messages, and processing logs
