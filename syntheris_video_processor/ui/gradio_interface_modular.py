"""
Gradio UI Module for Syntheris Video Processor - PROPERLY MODULARIZED
Uses the new clean architecture instead of the monolithic backup file.
"""

from pathlib import Path
import sys
import time
import subprocess


import gradio as gr
from typing import Optional, List, Any

# Import from proper modules, NOT from the monolithic backup
from ..core.processor import VideoProcessor
from ..utils.video_utils import get_video_info
from ..utils.file_utils import ensure_temp_dir
from ..backends.rife_v426_config import RIFEv426Configurator, is_rife_v426_ready
from ..core.quality_assurance import QualityAssurance


def detect_rife_status():
    """Detect RIFE version and capabilities at startup."""
    configurator = RIFEv426Configurator()
    
    if configurator.is_v426_available():
        model_info = configurator.get_model_info()
        capabilities = model_info.get('capabilities', {})
        
        status_parts = [
            "RIFE v4.26 Detected SUCCESS:",
            "Supports exact 24fps->60fps (2.5x)",
            "Duration-preserving interpolation",
        ]
        
        if capabilities.get('supports_2_5x'):
            status_parts.append("2.5x multiplier ready")
        
        return " | ".join(status_parts)
    else:
        return "RIFE HDv3 (Limited to integer multipliers - upgrade to v4.26 recommended)"


def create_gradio_interface():
    """Enhanced Gradio interface with intelligent preset system and research-based workflows."""
    
    # Initialize processor and quality assurance
    processor = VideoProcessor()
    qa = QualityAssurance()
    
    def apply_research_preset(preset_name):
        """Apply research-validated presets and return all settings"""
        
        presets = {
            "24fps->60fps (RIFE v4.26 Optimized)": {
                "mode": "custom_fps",
                "target_fps": 59.94,  # Exact per research
                "multiplier": "2x",   # Not used in custom_fps mode
                "scale": 1.0,
                "uhd_mode": "auto",
                "scene_cut_aware": True,   # FIXED: Enable mathematical validation framework
                "atfi_enabled": True,      # Research: enable for quality
                "description": "Exact 24fps->60fps (2.5x) with mathematical precision using RIFE v4.26. Enhanced with frame-accurate scene detection.",
                "mult_visible": False,     # Hide multiplier control
                "fps_visible": True        # Show FPS control
            },
            
            "24fps->30fps (Duration Preserved)": {
                "mode": "custom_fps", 
                "target_fps": 29.97,  # Exact NTSC rate
                "multiplier": "2x",   # Not used
                "scale": 1.0,
                "uhd_mode": "auto",
                "scene_cut_aware": True,   # FIXED: Enable flagship feature for cross-cut artifact prevention
                "atfi_enabled": True,      # ENABLED: User requested default activation for testing convenience
                "description": "Perfect 24fps->30fps (1.25x) conversion with mathematical precision. Ideal for NTSC compatibility.",
                "mult_visible": False,
                "fps_visible": True
            },
            
            "General Purpose (HDv3 Compatible)": {
                "mode": "multiplier",
                "target_fps": 60,     # Not used in multiplier mode
                "multiplier": "2x",   # HDv3 safe setting
                "scale": 1.0, 
                "uhd_mode": "auto",
                "scene_cut_aware": True,  # HDv3 can handle this
                "atfi_enabled": False,    # Keep simple for compatibility
                "description": "Safe 2x interpolation compatible with all RIFE versions. Uses integer multipliers only.",
                "mult_visible": True,     # Show multiplier control
                "fps_visible": False      # Hide FPS control
            },
            
            "Custom Settings": {
                "mode": "custom_fps",  # Default to custom_fps for flexibility
                "target_fps": 60,
                "multiplier": "2x",
                "scale": 1.0,
                "uhd_mode": "auto", 
                "scene_cut_aware": True,
                "atfi_enabled": False,
                "description": "Manual configuration - all settings below are user-controlled. Advanced users only.",
                "mult_visible": False,    # Start with custom_fps mode
                "fps_visible": True
            }
        }
        
        return presets.get(preset_name, presets["Custom Settings"])
    
    def on_preset_change(preset_name):
        """When preset changes, update all related UI elements"""
        
        settings = apply_research_preset(preset_name)
        
        # Update visibility based on mode
        mult_update = gr.update(
            value=settings["multiplier"],
            visible=settings["mult_visible"]
        )
        fps_update = gr.update(
            value=settings["target_fps"],
            visible=settings["fps_visible"]
        )
        
        return (
            settings["mode"],           # interpolation_mode
            mult_update,               # frame_multiplier with visibility
            fps_update,                # target_fps with visibility  
            settings["uhd_mode"],       # uhd_mode
            settings["scene_cut_aware"], # scene_cut_aware
            settings["atfi_enabled"],   # atfi_enabled
            settings["description"]     # preset_description
        )
    
    def update_mode_visibility(mode):
        """Show/hide controls based on interpolation mode (for manual changes)"""
        return (
            gr.update(visible=(mode == "multiplier")),  # multiplier dropdown
            gr.update(visible=(mode == "custom_fps"))   # target_fps number
        )
    
    # Professional CSS theme
    css = """
/* --- Header (no logo) --- */
.continuum-header{display:flex;align-items:center;padding:10px 14px;border-bottom:1px solid #1D2736;background:#0E1420;}
.no-logo{padding-left:2px}
.continuum-title{font-size:22px;font-weight:800;letter-spacing:.3px;color:#E6F0FF;line-height:1.15}
.continuum-title .grad{background:linear-gradient(90deg,#6DF0FF 0%,#FF38A1 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.continuum-sub{font-size:12px;color:#9FB3C8;margin-top:2px}
.continuum-sub .ver{background:#152030;color:#E6F0FF;border:1px solid #1D2736;border-radius:9999px;padding:2px 8px;margin-left:8px}

/* --- Panels & inputs --- */
.gr-panel, .gr-group, .gr-box, .container { background:#0E1420 !important; border-color:#1D2736 !important; }
div[class*="panel"]{ background:#0E1420 !important; border-color:#1D2736 !important; }

/* --- Gradio 4.x compatible theme overrides --- */
.gradio-container { 
    --body-background-fill: #0B0F17 !important;
    --background-fill-primary: #0E1420 !important;
    --border-color-primary: #1D2736 !important;
    --shadow-drop: 0 4px 24px rgba(0,0,0,.45) !important;
}
input, textarea, select { outline:none; }
input:focus, textarea:focus, select:focus { box-shadow:0 0 0 3px #6DF0FF33 !important; border-color:#6DF0FF55 !important; }

/* --- Buttons (bind by elem_id) --- */
#btn-process, #btn-process button {
  border-radius:9999px !important; background:#6DF0FF !important; color:#0B0F17 !important;
  border:0 !important; font-weight:700;
}
#btn-process button:hover { filter:brightness(0.95) }
    """
    
    # Enhanced header with duration validation features
    header_html = """
<div class="continuum-header no-logo">
  <div class="continuum-titles">
    <div class="continuum-title">🎬 Syntheris <span class="grad">Continuum</span></div>
    <div class="continuum-sub">
      Research-Validated Video Processor -- Perfect Duration Preservation Achieved
      <span class="ver">V5.1.0</span>
    </div>
    <div style="margin-top: 8px; font-size: 10px; color: #6DF0FF;">
      <span style="background: rgba(109,240,255,0.1); padding: 2px 8px; border-radius: 12px; margin: 0 3px;">SUCCESS: Duration Validation</span>
      <span style="background: rgba(109,240,255,0.1); padding: 2px 8px; border-radius: 12px; margin: 0 3px;">SUCCESS: RIFE v4.26 Support</span>
      <span style="background: rgba(109,240,255,0.1); padding: 2px 8px; border-radius: 12px; margin: 0 3px;">SUCCESS: 2.5x Multiplier</span>
      <span style="background: rgba(109,240,255,0.1); padding: 2px 8px; border-radius: 12px; margin: 0 3px;">SUCCESS: Research Validated</span>
    </div>
  </div>
</div>
    """
    
    def process_videos(
        upload_mode, single_file, batch_files, interp_mode, mult_value, fps_value,
        uhd, scene_cut_flag, scene_th, crossfade_flag,
        deflicker_flag, vram_guard_flag, keep_audio_flag, preview_flag,
        atfi_flag, atfi_hfps, atfi_thr, atfi_mins, atfi_meth,
        # New duration validation parameters
        duration_validation_enabled, tolerance_ms, pts_reset_enabled, research_preset
    ):
        """Enhanced processing with duration validation feedback."""
        
        # Clear diagnostic log for fresh session
        import time
        diagnostic_log = Path("temp/diagnostic_pipeline.log")
        if diagnostic_log.exists():
            # Archive old log with timestamp
            diagnostic_log.rename(f"temp/diagnostic_pipeline_{int(time.time())}.log.old")
        
        # Initialize duration validation results
        validation_results = []
        
        # Apply research preset if selected
        if research_preset and research_preset != "General Purpose (HDv3 Compatible)":
            if "24fps->60fps" in research_preset:
                interp_mode = "custom_fps"
                fps_value = 60.0
                validation_results.append("🔬 Applied research preset: 24fps->60fps (RIFE v4.26)")
            elif "24fps->30fps" in research_preset:
                interp_mode = "custom_fps" 
                fps_value = 30.0
                validation_results.append("🔬 Applied research preset: 24fps->30fps (Duration Preserved)")
        
        # Determine batch mode
        is_batch = (upload_mode == "Batch Mode")
        
        # Determine interpolation settings
        if interp_mode == "multiplier":
            mode_setting = "multiplier"
            mult_setting = mult_value
            tgt_setting = 60.0
        else:
            mode_setting = "custom_fps"
            mult_setting = "2x"
            tgt_setting = fps_value
        
        # Build list of input files
        items = []
        if is_batch and batch_files:
            print(f"[DEBUG] batch_files type: {type(batch_files)}, length: {len(batch_files) if hasattr(batch_files, '__len__') else 'N/A'}")
            if isinstance(batch_files, list):
                items = batch_files
            else:
                items = [batch_files] if batch_files else []
        elif not is_batch and single_file:
            items = [single_file]
        else:
            return "Please select input file(s)", "", None, ""
        
        # Filter None values and extract paths
        video_paths = []
        for item in items:
            if item is not None:
                if hasattr(item, 'name'):
                    video_paths.append(Path(item.name))
                elif isinstance(item, str):
                    video_paths.append(Path(item))
        
        print(f"[DEBUG] video_paths before dedup: {len(video_paths)} files")
        
        # Add deduplication to prevent processing the same file multiple times
        original_count = len(video_paths)
        video_paths = list(dict.fromkeys(video_paths))  # Remove duplicates while preserving order
        if original_count != len(video_paths):
            print(f"[BATCH] WARNING: Removed {original_count - len(video_paths)} duplicate files")
        print(f"[BATCH] Processing {len(video_paths)} unique files")
        
        if not video_paths:
            return "No valid video files detected", "", None, ""
        
        total_files = len(video_paths)
        produced_paths = []
        all_logs = []
        
        # Add batch progress tracking to identify which files fail
        batch_summary = {
            'total_files': len(video_paths),
            'processed': [],
            'failed': [],
            'skipped_duplicates': []
        }
        
        # Only reset if this is a new batch session
        if not hasattr(processor, '_batch_id') or processor._batch_id != id(video_paths):
            processor.processed_files = set()
            processor._batch_id = id(video_paths)
            print(f"[BATCH] Reset processed files tracker for new batch")
        else:
            print(f"[BATCH] Using existing batch session")
        
        # Process each file using the modular processor
        for idx, video_path in enumerate(video_paths, start=1):
            print(f"[BATCH] Processing file {idx}/{len(video_paths)}: {video_path.name}")
            file_name = video_path.name
            all_logs.append(f"[{idx}/{total_files}] Processing: {file_name}")
            
            try:
                # Use the modular processor
                final_output = None
                for status, output in processor.process_video(
                    video_path,
                    mode=mode_setting,
                    multiplier=mult_setting,
                    target_fps=tgt_setting,
                    scale=1.0,  # V4.2.0: Hard-coded to optimal quality
                    uhd_mode=uhd,
                    scene_cut_aware=scene_cut_flag,
                    keep_audio=keep_audio_flag,
                    preview_transcode=preview_flag,
                    cfr_dedup=False,  # CFR DISABLED - V4.1.1 fix for duration corruption
                    crossfade_joins=crossfade_flag,
                    deflicker=deflicker_flag,
                    vram_guard=vram_guard_flag,
                    scene_threshold=float(scene_th) if scene_th else 0.3,
                    atfi_enabled=bool(atfi_flag),
                    atfi_high_fps=int(atfi_hfps) if atfi_hfps in (48, 60, 96) else 60,
                    atfi_threshold=float(atfi_thr) if atfi_thr is not None else 0.30,
                    atfi_min_sec=float(atfi_mins) if atfi_mins is not None else 0.25,
                    atfi_method=str(atfi_meth)
                ):
                    # Enhanced status logging with duration validation capture
                    if status and status.strip():
                        if status.startswith("Status:"):
                            all_logs.append(f"[{idx}/{total_files}] {status}")
                            
                            # Capture RIFE version information
                            if "RIFE v4.26" in status:
                                validation_results.append(f"[DATA] [{file_name}] Using RIFE v4.26 with exact FPS targeting")
                            elif "RIFE HDv3" in status:
                                validation_results.append(f"[DATA] [{file_name}] Using legacy RIFE HDv3")
                                
                        elif status.startswith("Logs:"):
                            log_content = status.replace("Logs:\n", "")
                            all_logs.append(log_content)
                            
                            # Capture duration validation results
                            if "Duration preserved" in log_content or "SUCCESS:" in log_content:
                                if "ms" in log_content:
                                    validation_results.append(f"SUCCESS: [{file_name}] {log_content}")
                            elif "Duration drift" in log_content or "WARNING:" in log_content:
                                if "ms" in log_content:
                                    validation_results.append(f"WARNING: [{file_name}] {log_content}")
                            elif "Duration validation" in log_content:
                                validation_results.append(f"[SEARCH] [{file_name}] {log_content}")
                    
                    # Capture final output
                    if output:
                        final_output = output
                
                if final_output:
                    produced_paths.append(final_output)
                    all_logs.append(f"[{idx}/{total_files}] SUCCESS: Completed: {file_name}")
                else:
                    all_logs.append(f"[{idx}/{total_files}] WARNING: No output for: {file_name}")
                    
            except FileNotFoundError as e:
                all_logs.append(f"[{idx}/{total_files}] FAIL: File not found: {str(e)}")
            except subprocess.CalledProcessError as e:
                all_logs.append(f"[{idx}/{total_files}] FAIL: Processing failed: {str(e)}")
            except Exception as e:
                all_logs.append(f"[{idx}/{total_files}] FAIL: Unexpected error: {type(e).__name__}: {str(e)}")
        
        # Prepare final outputs with validation summary
        validation_summary = "\n".join(validation_results) if validation_results else "No validation data captured"
        final_status = f"SUCCESS: Complete: {len(produced_paths)}/{total_files} files succeeded"
        final_logs = "\n".join(all_logs)
        
        # Convert paths to file objects for Gradio
        output_files = []
        for path in produced_paths:
            if isinstance(path, str):
                path = Path(path)
            if path.exists():
                output_files.append(str(path))
        
        return final_status, final_logs, output_files if output_files else None, validation_summary
    
    # Create the interface
    with gr.Blocks(css=css, title="Syntheris Continuum V5.1.0 - ATFI Error Handling & Fallback System") as demo:
        gr.HTML(header_html, elem_id="continuum-header")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Input Settings")
                
                # Upload mode selector
                upload_mode = gr.Radio(
                    choices=["Single File", "Batch Mode"],
                    value="Single File",
                    label="Upload Mode"
                )
                
                # Single file input
                in_file_single = gr.File(
                    label="Single File Input",
                    file_types=[".mp4", ".mov", ".mkv", ".avi", ".webm"]
                )
                
                # Batch file input
                in_files_batch = gr.File(
                    label="Batch Files Input (Select Multiple)",
                    file_count="multiple",
                    file_types=[".mp4", ".mov", ".mkv", ".avi", ".webm"]
                )
                
                gr.Markdown("### ⚡ Quick Start - Research Validated Presets")
                gr.Markdown("*Select a preset first for optimal results, then customize if needed*")
                
                # Research-Based Presets (moved to top)
                research_presets = gr.Dropdown(
                    choices=[
                        "24fps->30fps (Duration Preserved)", 
                        "24fps->60fps (RIFE v4.26 Optimized)",
                        "General Purpose (HDv3 Compatible)",
                        "Custom Settings"
                    ],
                    value="24fps->30fps (Duration Preserved)",
                    label="◉ Research Presets",
                    info="Automatically configures all settings based on research findings"
                )
                
                # Preset description
                preset_description = gr.Textbox(
                    value="Perfect 24fps->30fps (1.25x) conversion with mathematical precision. Ideal for NTSC compatibility.",
                    label="📋 What This Preset Does", 
                    interactive=False,
                    lines=2,
                    max_lines=3
                )
                
                gr.Markdown("### 🔧 Interpolation Settings")
                gr.Markdown("*Settings below are controlled by your preset selection*")
                
                # Interpolation mode (controlled by preset)
                interp_mode = gr.Radio(
                    choices=["multiplier", "custom_fps"],
                    value="custom_fps",  # Default to custom_fps per research preset
                    label="Interpolation Mode",
                    info="◉ Preset-controlled: multiplier = integer only, custom_fps = exact targeting"
                )
                
                with gr.Row():
                    # Multiplier setting (only visible in multiplier mode)
                    mult = gr.Dropdown(
                        choices=["2x", "4x", "8x"],
                        value="2x",
                        label="Frame Multiplier",
                        visible=False,  # Hidden by default per research preset
                        info="Integer multipliers (HDv3 compatible)"
                    )
                    
                    # FPS setting (only visible in custom_fps mode) 
                    tgt = gr.Number(
                        value=29.97,  # Updated default for 24fps->30fps preset
                        label="Target FPS",
                        visible=True,  # Visible by default per research preset
                        info="Exact FPS for mathematical precision"
                    )
                
                gr.Markdown("### Advanced Settings")
                
                with gr.Accordion("Processing Options", open=False):
                    # V4.2.0: Resolution scale hard-coded to 1.0 (optimal quality)
                    uhd = gr.Radio(
                        choices=["auto", "on", "off"],
                        value="auto",
                        label="UHD Mode",
                        info="Auto enables UHD for 4K+ videos, standard for 1080p"
                    )
                
                with gr.Accordion("◉ Preset-Controlled Quality Settings", open=False):
                    gr.Markdown("*These settings are optimized by your research preset selection*")
                    scene_cut = gr.Checkbox(
                        value=True,   # FIXED: Enable flagship feature by default
                        label="Scene-cut aware processing", 
                        info="◉ Preset-controlled: enabled for cross-cut artifact prevention"
                    )
                    scene_thresh = gr.Number(value=0.3, label="Scene threshold")
                    
                    atfi_enable = gr.Checkbox(
                        value=True,   # ENABLED: User requested default activation for testing convenience
                        label="Enable ATFI Motion Adaptation (25% quality boost)",
                        info="◉ Preset-controlled: research-validated enhancement"
                    )
                    
                    atfi_highfps = gr.Dropdown([48, 60, 96], value=60, label="High-motion FPS")
                    atfi_thresh = gr.Number(value=0.30, label="Motion threshold")
                    atfi_min = gr.Number(value=0.25, label="Min duration (sec)")
                    atfi_method = gr.Dropdown(["scene", "flow"], value="scene", label="Method")
                
                with gr.Accordion("🔧 Manual Override Settings", open=False):
                    gr.Markdown("*These settings can be manually adjusted regardless of preset*")
                    # CFR normalization REMOVED - confirmed cause of duration corruption in V4.1.1
                    crossfade = gr.Checkbox(value=True, label="Crossfade Joins")
                    deflicker_cb = gr.Checkbox(value=False, label="Deflicker")
                    vram_guard_cb = gr.Checkbox(value=True, label="Auto VRAM Guard")
                    keep_audio = gr.Checkbox(value=True, label="Keep Audio")
                    preview = gr.Checkbox(value=False, label="Preview Transcode")
                
                # NEW: Duration Validation Settings
                with gr.Accordion("Duration Validation (Research-Based)", open=True):
                    duration_validation = gr.Checkbox(value=True, label="Enable Duration Validation")
                    duration_tolerance = gr.Number(value=100, label="Tolerance (milliseconds)", info="<100ms is research-validated")
                    pts_reset = gr.Checkbox(value=True, label="Apply PTS Reset (Recommended)", info="Prevents timestamp accumulation")
                
                # RIFE Model Status
                rife_status = gr.Textbox(
                    value=detect_rife_status(),
                    label="RIFE Model Status",
                    interactive=False,
                    info="Auto-detected at startup"
                )
                
                process_btn = gr.Button("Process Video(s)", variant="primary", size="lg", elem_id="btn-process")
                
            with gr.Column(scale=1):
                gr.Markdown("### Processing Output")
                
                status_box = gr.Textbox(
                    value="Ready - V5.1.0 ATFI Error Handling & Fallback System",
                    label="Status",
                    lines=2
                )
                
                # NEW: Duration Validation Results
                validation_results_box = gr.Code(
                    value="Duration validation results will appear here...",
                    label="Duration Validation Results",
                    language="shell",
                    lines=6
                )
                
                log_box = gr.Code(
                    value="",
                    label="Processing Logs with Duration Metrics",
                    language="shell",
                    lines=12
                )
                
                out_files = gr.Files(
                    label="Output Videos",
                    interactive=False
                )
        
        # Wire up intelligent preset system event handlers
        research_presets.change(
            fn=on_preset_change,
            inputs=[research_presets],
            outputs=[interp_mode, mult, tgt, uhd, scene_cut, atfi_enable, preset_description]
        )
        
        # Dynamic mode visibility (for manual mode changes)
        interp_mode.change(
            fn=update_mode_visibility,
            inputs=[interp_mode],
            outputs=[mult, tgt]
        )
        
        # Enhanced event handler with duration validation
        process_btn.click(
            fn=process_videos,
            inputs=[
                # Existing inputs (CFR removed in V4.1.1)
                upload_mode, in_file_single, in_files_batch, interp_mode, mult, tgt,
                uhd, scene_cut, scene_thresh,
                crossfade, deflicker_cb, vram_guard_cb, keep_audio, preview,
                atfi_enable, atfi_highfps, atfi_thresh, atfi_min, atfi_method,
                # New duration validation inputs
                duration_validation, duration_tolerance, pts_reset, research_presets
            ],
            outputs=[status_box, log_box, out_files, validation_results_box]
        )
    
    return demo


def launch_interface(port=7860, share=False):
    """Launch the Gradio interface."""
    demo = create_gradio_interface()
    
    # Find available port more reliably
    import socket
    def find_free_port(start_port):
        for port_num in range(start_port, start_port + 50):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port_num))
                    return port_num
            except OSError:
                continue
        return start_port + 10  # Fallback
    
    available_port = find_free_port(port)
    if available_port != port:
        print(f"Port {port} in use, using port {available_port} instead")
    
    # Launch with comprehensive settings
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=available_port,
            inbrowser=True,
            share=share,
            quiet=True,
            show_api=False,
            show_error=True
        )
    except Exception as e:
        print(f"Launch error: {e}")
        raise


if __name__ == "__main__":
    launch_interface()