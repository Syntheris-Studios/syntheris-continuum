# Complete User Guide - Syntheris Continuum V4.2.3

> Current application: V5.1.0. This retained guide describes earlier features and examples; use ../README.md, ../CHANGELOG.md and ../MODEL_PROVENANCE.md for current setup and validation status.
**Professional Video Processing with Modular Architecture**

## Table of Contents
1. [Installation & Setup](#installation--setup)
2. [User Interface Walkthrough](#user-interface-walkthrough)  
3. [Feature Deep Dive](#feature-deep-dive)
4. [Batch Processing](#batch-processing)
5. [Settings Reference](#settings-reference)
6. [Output Management](#output-management)
7. [Performance Optimization](#performance-optimization)
8. [Common Workflows](#common-workflows)
9. [Troubleshooting](#troubleshooting)

## Installation & Setup

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **GPU**: NVIDIA GTX 1060+ (RTX series recommended) 
- **RAM**: 16GB+ (32GB for 4K content)
- **Storage**: 10GB+ free space
- **Python**: 3.11 (exact version required)

### Environment Setup

#### 1. Create Virtual Environment
```bash
# Navigate to project directory
cd "Syntheris Continuum Open Source"

# Create Python 3.11 environment
py -3.11 -m venv .venv311_final
```

#### 2. Activate Environment
```bash
# PowerShell
.venv311_final\Scripts\Activate.ps1

# Command Prompt  
.venv311_final\Scripts\activate.bat
```

#### 3. Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install base requirements
pip install -r requirements.txt

# Install PyTorch (CRITICAL VERSION for RTX 40 series)
pip install torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

**WARNING: CRITICAL**: PyTorch 2.3+ has a bug causing crashes on RTX 40 series GPUs. Always use 2.1.1+cu121.

#### 4. Verify Installation
```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')  
print(f'CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
"
```

Expected output:
```
PyTorch: 2.1.1+cu121
CUDA Available: True
GPU: NVIDIA GeForce RTX [Your GPU]
```

## User Interface Walkthrough

### Launching the Application

**Method 1 (Recommended)**: Double-click `windows_launcher.bat`
```
===============================================
  SYNTHERIS CONTINUUM V4.2.3
  MODULAR RIFE PROFESSIONAL VIDEO PROCESSOR
  Precision Interpolation for AI-Generated Video
===============================================
[GPU] NVIDIA GPU detected - GPU acceleration enabled
[ARCHITECTURE] Using fortified modular architecture V4.2.3
```

**Method 2**: Command line
```bash
python syntheris_video_processor/main.py
```

### Interface Layout

The UI opens in your browser at `http://127.0.0.1:7860` with these sections:

#### Header
- **Title**: Syntheris Continuum V4.2.3
- **Architecture Badges**: Clean Architecture, Scene-Cut Processing, ATFI Motion, Quality Assurance

#### Input Settings Panel (Left)
- **Upload Mode**: Single File vs Batch Mode selector
- **File Inputs**: Separate inputs for single/batch uploads
- **Interpolation Settings**: Mode and multiplier/FPS controls
- **Advanced Settings**: Expandable sections with detailed options

#### Output Panel (Right)
- **Status Display**: Current processing status
- **Processing Logs**: Real-time processing output
- **Output Videos**: Download links for completed videos

### File Upload

#### Single File Mode
1. Keep "Upload Mode" on "Single File"  
2. Click "Single File Input"
3. Select your video file (.mp4, .mov, .mkv, .avi, .webm)
4. File appears in the input field

#### Batch Mode  
1. Switch "Upload Mode" to "Batch Mode"
2. Click "Batch Files Input (Select Multiple)"
3. Hold Ctrl (Windows) while clicking multiple files
4. All selected files appear in batch input field

**Supported Formats**: MP4, MOV, MKV, AVI, WebM

## Feature Deep Dive

### Interpolation Modes

#### Multiplier Mode (Recommended)
- **2x**: 24fps -> 48fps, 30fps -> 60fps
- **4x**: 24fps -> 96fps, 30fps -> 120fps  
- **8x**: 24fps -> 192fps (extreme slow motion)

Use cases:
- **2x**: Most common, good balance of quality/speed
- **4x**: Slow motion effects, high-quality archival  
- **8x**: Extreme slow motion, specialized applications

#### Custom FPS Mode
- Set exact target frame rate (e.g., 30fps, 60fps)
- Useful for broadcast standards compliance
- Less predictable than multiplier mode

### Scene-Cut Aware Processing

**What it does**: Automatically detects scene changes and processes each segment separately to prevent ghosting artifacts across cuts.

**Settings**:
- **Enable**: SUCCESS: Recommended ON for all content
- **Threshold**: 0.3 (default) - Lower = more sensitive to cuts
- **Range**: 0.1 (very sensitive) to 0.8 (only obvious cuts)

**Benefits**:
- Eliminates cross-cut ghosting artifacts
- Enables per-segment retry on failures
- Improves overall processing reliability
- 70% quality improvement on cut-heavy content

### ATFI Motion Adaptation

**Adaptive Temporal Frame Interpolation**: Analyzes motion and applies selective interpolation.

**How it works**:
1. First interpolates to high FPS (48-60fps)
2. Detects high-motion vs low-motion areas
3. Selectively keeps more frames in high-motion areas
4. Reduces to target FPS with motion-aware thinning

**Settings**:
- **Enable**: Provides 25% quality enhancement
- **High-motion FPS**: 48 or 60fps for initial interpolation
- **Motion Threshold**: 0.30 (default) - sensitivity to motion
- **Min Duration**: 0.25s - minimum segment length
- **Method**: "scene" (recommended) or "flow"

**Best for**: Content with varying motion (pans, action, static scenes)

### Quality Assurance

Built-in validation system that checks:
- **Frame Rate**: Ensures constant frame rate output
- **Frame Count**: Verifies expected number of frames
- **Audio Sync**: Maintains audio/video synchronization
- **File Integrity**: Confirms playable output

Auto-remediation when possible, warnings when manual intervention needed.

## Batch Processing

### Setup for Batch Processing

1. **Switch Mode**: Select "Batch Mode" radio button
2. **Select Files**: Use "Batch Files Input" to select multiple videos
3. **Configure Settings**: All videos use the same settings
4. **Monitor Progress**: Each file shows individual progress

### Batch Processing Features

#### File Upload Fix
- **Fixed Issue**: Batch file selection now works properly
- **Multiple Selection**: Hold Ctrl while clicking files
- **Visual Feedback**: Selected files appear in batch input field
- **Format Validation**: Only supported formats are selectable

#### Processing Flow
```
[1/3] Processing: video1.mp4
Status: [SEARCH] Analyzing video...
Status: SUCCESS: Complete! Output: output_video1_interpolated.mp4

[2/3] Processing: video2.mp4  
Status: [SEARCH] Analyzing video...
Status: SUCCESS: Complete! Output: output_video2_interpolated.mp4

[3/3] Processing: video3.mp4
SUCCESS: Complete: 3/3 files succeeded
```

#### Error Handling
- **Continue on Error**: If one video fails, others still process
- **Individual Logging**: Each video gets separate error logs  
- **Final Summary**: Shows success/failure count
- **Recovery**: Failed videos can be reprocessed individually

## Settings Reference

### Processing Options

| Setting | Default | Description |
|---------|---------|-------------|
| **Resolution Scale** | 1.0 | Processing resolution multiplier (0.25-4.0) |
| **UHD Mode** | auto | 4K processing optimization (auto/on/off) |
| **Preset** | Auto | Content-type optimization (Auto/Anime/Realistic) |
| **Model Variant** | Auto | RIFE model selection (Auto/4.25/4.26) |

### Quality Options

| Setting | Default | Description |
|---------|---------|-------------|
| **Normalize CFR & Remove Duplicates** | SUCCESS: ON | Fix variable frame rates and remove duplicate frames |
| **Scene-cut aware** | SUCCESS: ON | Process segments separately (70% quality jump) |
| **Scene threshold** | 0.3 | Cut detection sensitivity (0.1-0.8) |
| **Crossfade Joins** | SUCCESS: ON | Smooth transitions between segments |
| **Deflicker** | FAIL: OFF | Reduce flickering (use for AI-generated content) |
| **Auto VRAM Guard** | SUCCESS: ON | Prevent GPU memory overflow |
| **Keep Audio** | SUCCESS: ON | Preserve original audio track |
| **Preview Transcode** | FAIL: OFF | Create browser-compatible preview |

### ATFI Motion Adaptation

| Setting | Default | Description |
|---------|---------|-------------|
| **Enable ATFI** | FAIL: OFF | Motion-adaptive processing (25% enhancement) |
| **High-motion FPS** | 60 | Initial interpolation rate (48/60) |
| **Motion threshold** | 0.30 | Motion detection sensitivity |
| **Min duration** | 0.25 | Minimum segment length (seconds) |
| **Method** | scene | Detection method (scene/flow) |

## Output Management

### Output Location
- **Default**: `outputs/` directory in project root
- **Naming**: `output_[timestamp]_[filename]_interpolated.mp4`
- **Preservation**: Original files never modified

### Output Information
- **File Size**: Typically 2-4x larger than input (more frames)
- **Quality**: Same visual quality, higher temporal resolution
- **Audio**: Original audio preserved and synchronized
- **Metadata**: Color space and HDR information maintained

### File Management
```bash
outputs/
├── output_20250813_143022_video1_interpolated.mp4
├── output_20250813_143156_video2_interpolated.mp4
└── history.jsonl  # Processing logs and metadata
```

## Performance Optimization

### Hardware Recommendations

#### GPU Performance (RIFE processing time for 30-second 1080p clip)
- **RTX 4090**: ~1 minute
- **RTX 4080**: ~1.5 minutes  
- **RTX 4070**: ~2.5 minutes
- **RTX 3080**: ~3 minutes
- **RTX 3060**: ~5 minutes

#### Memory Requirements
- **1080p**: 8GB VRAM minimum
- **1440p**: 12GB VRAM minimum
- **4K**: 16GB+ VRAM (or use Resolution Scale)

### Optimization Settings

#### For Speed (Lower Quality)
```
Resolution Scale: 0.5
UHD Mode: off
Scene-cut aware: OFF (faster but lower quality)
Enable ATFI: OFF (faster processing)
```

#### For Quality (Slower)  
```
Resolution Scale: 1.0
UHD Mode: auto
Scene-cut aware: ON
Enable ATFI: ON
High-motion FPS: 60
```

#### For 4K/Large Files
```
Resolution Scale: 0.75 or 0.5
Auto VRAM Guard: ON
Process in smaller segments
```

## Common Workflows

### Workflow 1: AI-Generated Content (Midjourney, Stable Video)
```
Settings:
- Frame Multiplier: 2x
- Scene-cut aware: ON
- Enable ATFI: ON  
- Deflicker: ON (if sparkly/flickering)
- Keep Audio: ON
```

**Typical Results**: 24fps -> 48fps, smooth motion, eliminated artifacts

### Workflow 2: Realistic Live Action  
```
Settings:
- Frame Multiplier: 2x  
- Scene-cut aware: ON
- Enable ATFI: ON
- Deflicker: OFF
- Keep Audio: ON
```

**Typical Results**: Natural motion enhancement, preserved realism

### Workflow 3: Batch Processing for Production
```
1. Prepare all videos in consistent format
2. Switch to Batch Mode
3. Select all files at once
4. Use conservative settings (2x, ATFI OFF for speed)
5. Monitor progress, address failures individually
```

### Workflow 4: High-Quality Archival  
```
Settings:
- Frame Multiplier: 4x
- Scene-cut aware: ON
- Enable ATFI: ON
- High-motion FPS: 60
- Keep maximum quality
```

**Use Case**: Creating slow-motion versions, archival copies

## Troubleshooting

### Quick Diagnosis

#### Check System Status
```bash
# Verify PyTorch installation
python -c "import torch; print(torch.__version__)"

# Should show: 2.1.1+cu121

# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"  

# Should show: True
```

#### Common Error Patterns

**"Exit code 3221226505"** = PyTorch version issue (RTX 40 series)
- **Solution**: Downgrade to PyTorch 2.1.1+cu121

**"RIFE backend failed"** = Usually file naming/path issues
- **Solution**: Already fixed in current version

**"Batch upload not working"** = Fixed in current version
- **Verify**: "Batch Mode" selected and use "Batch Files Input"

### Performance Issues

**Processing Very Slow**
- Check GPU detection in launcher output
- Verify CUDA drivers updated
- Try Resolution Scale 0.5 for testing

**Out of Memory Errors**
- Enable "Auto VRAM Guard"
- Reduce "Resolution Scale"
- Process smaller segments

**Audio Out of Sync**
- Keep "Normalize CFR & Remove Duplicates" ON
- Ensure "Keep Audio" is enabled
- Check input video doesn't have VFR issues

### For More Help

- See [Troubleshooting Guide](Troubleshooting.md) for comprehensive error solutions
- Check [Technical Reference](Technical_Reference.md) for architectural details
- Review processing logs in outputs/history.jsonl

---

**Version**: Syntheris Continuum V4.2.3  
**Last Updated**: August 2025  
**Architecture**: Modular (Clean)
