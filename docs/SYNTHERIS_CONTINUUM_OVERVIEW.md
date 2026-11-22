# Syntheris Continuum V5.1.0

Syntheris Continuum is a local video interpolation application: it generates intermediate frames to change a clip's frame rate, with controls for scene handling, motion adaptation and batch processing. A Gradio interface brings together RIFE inference and FFmpeg preparation, assembly and audio handling. It is useful between clip generation or capture and editing; it is not a full editor or restoration suite.

## What the pipeline adds

These are engineering features implemented around RIFE, not claims of a new interpolation model or proven superiority over other products.

### Duration preservation

The processor records source duration, checks intermediate and final durations, and attempts correction through trimming or cloned-frame padding when necessary. Quality checks compare duration and frame-count relationships. These checks aim to keep the timeline stable; they do not guarantee invisible corrections or success on every input.

Code: [processor.py](../syntheris_video_processor/core/processor.py), [quality_assurance.py](../syntheris_video_processor/core/quality_assurance.py), [media_utils.py](../syntheris_video_processor/core/media_utils.py).

### ATFI error handling and fallback

Motion-adaptive ATFI processing adds analysis and selective interpolation around the backend. The processor catches failures, logs diagnostic details and attempts direct interpolation through its fallback method. If that also fails, it can retain the original segment. Completion therefore does not necessarily mean every segment received interpolation. Timeout handling and GPU cleanup improve failure visibility without promising a universal completion rate.

Code: [atfi.py](../syntheris_video_processor/core/atfi.py), [atfi_fortified.py](../syntheris_video_processor/core/atfi_fortified.py), [processor.py](../syntheris_video_processor/core/processor.py), especially `_fallback_interpolation`.

### RIFE v4.26 and exact FPS targeting

The release includes v4.26 configuration and detection support, with fractional FPS command construction. The command builder passes a decimal `--fps` value; it does not pass unsupported `--fps_num` or `--fps_den` switches. Research-oriented preset metadata includes rational rates such as 60000/1001, while the effective command uses the requested target FPS. Check the actual selected rate rather than assuming a preset name means exactly 60 fps.

The bundled HDv3 weight's exact upstream release is undocumented. A v4.26 capability label does not identify that weight. See [model provenance](../MODEL_PROVENANCE.md).

Code: [rife_v426_config.py](../syntheris_video_processor/backends/rife_v426_config.py), [rife_v426_manager.py](../syntheris_video_processor/backends/rife_v426_manager.py), [RIFE backend](../syntheris_video_processor/backends/rife_backend_final_fixed.py), [inference_video.py](../Practical-RIFE/inference_video.py).

### Research-oriented presets and PTS handling

The project's “research-validated” terminology refers to configurations and checks informed by retained research notes. It is not an independent certification. Presets encode FPS, scene and skipping choices. Timestamp-reset helpers and segment concatenation address timebase accumulation: the repaired concat-demuxer path resets each input to zero and lets the demuxer advance the timeline. The current crossfade-filter builder uses simple concatenation to avoid duplication; this release does not promise crossfade joins.

Code: [preset configuration](../syntheris_video_processor/backends/rife_v426_config.py), [media_utils.py](../syntheris_video_processor/core/media_utils.py), [segments.py](../syntheris_video_processor/core/segments.py), especially `_concat_with_pts_reset` and `_build_crossfade_filter`.

### Batch processing and media handling

Batch orchestration tracks per-file status and errors. Scene segmentation, optional CFR preparation, audio extraction/muxing and output validation surround inference. Recovery paths can change the result: for example, emergency audio handling may preserve video without audio. Review logs and outputs before delivery.

Code: [batch_processor.py](../syntheris_video_processor/core/batch_processor.py), [segments.py](../syntheris_video_processor/core/segments.py), [media_utils.py](../syntheris_video_processor/core/media_utils.py), [UI](../syntheris_video_processor/ui/gradio_interface_modular.py).

## Architecture and processing flow

`Windows launcher → quick_launcher → Gradio UI → VideoProcessor / batch orchestration → RIFE + FFmpeg → validation and output`

The processor coordinates input inspection, optional preparation and scene splitting, per-segment interpolation or ATFI, assembly, audio handling, and duration checks/corrections. Options and recovery paths can bypass stages. RIFE uses PyTorch; FFmpeg/ffprobe perform media operations and inspection. OpenCV and NumPy support image and numerical work.

The source release includes application code and a RIFE weight, but no installed Python environment or bundled system FFmpeg executable. Dependencies are installed locally from [requirements.txt](../requirements.txt).

## Requirements, GPU support and launch

Use Windows, an existing 64-bit Python 3.11 installation, FFmpeg and ffprobe on PATH, internet access for setup, and sufficient disk/RAM/VRAM for the chosen clips. Memory needs depend on resolution and workload; this overview gives no untested universal capacity guarantee.

One pinned GPU package set is intended for both RTX 4080 and RTX 5090: PyTorch 2.7.1+cu128, torchvision 0.22.1+cu128 and torchaudio 2.7.1+cu128. There is no separate GPU-specific requirements file. A compatible NVIDIA driver is required. The release preparation verified real kernel execution on RTX 5090; RTX 4080 was not physically tested in this pass. Setup checks CUDA availability and exercises the selected device; CPU verification is not a promise of practical CPU throughput.

1. Run `setup.bat`. It creates an app-local `.venv`, installs requirements, checks imports/dependencies, exercises the compute device, checks FFmpeg and creates the desktop shortcut.
2. Open the **Syntheris Continuum** shortcut or run `windows_launcher.bat`.
3. Open the local address printed by the launcher, normally `http://127.0.0.1:7860`.

Setup accepts `-PythonExe` for an existing interpreter and `-NonInteractive` for unattended execution. It does not install or repair system Python. The launcher requires the local venv. See [setup](../scripts/setup.ps1) and [environment verification](../scripts/verify_environment.py).

## Boundaries and evidence

- **No AI upscaler is integrated.** Interpolation preserves output resolution; scale/UHD settings control RIFE's internal interpolation scale, not super-resolution. See [inference_video.py](../Practical-RIFE/inference_video.py).
- No FILM backend or FILM model is shipped.
- No performance, quality-improvement or reliability benchmark is re-certified. Older numeric marketing claims are historical.
- Release validation established setup/GPU checks, 45 passing configured tests with one legacy-module skip, and HTTP serving. These checks do not certify every real-world clip or production reliability.
- Code is MIT; branding is excluded. Dependencies retain their own terms, including NVIDIA runtime terms. See [licensing notices](../THIRD_PARTY_NOTICES.md).

## Read further

This overview and the root README describe the current release. The longer retained guides include historical examples; use current setup instructions and dependency pins when they differ.

- [User Guide](User_Guide_Complete.md)
- [Technical Reference](Technical_Reference.md)
- [Testing Guide](../TESTING_GUIDE.md)
- [Troubleshooting](Troubleshooting.md)
- [Duration preservation research](<Research- Duration preservation in AI video interpolation pipelines.md>)
