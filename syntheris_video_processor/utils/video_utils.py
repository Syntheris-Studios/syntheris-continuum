"""
Video utilities for FFmpeg operations and video probing
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

def _ffprobe_json(cmd: List[str]) -> Dict[str, Any]:
    """Execute ffprobe and return JSON output"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, 
            encoding='utf-8', timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return {}

def probe_video(video_path: Path) -> Dict[str, Any]:
    """Probe video file for technical information"""
    data = _ffprobe_json([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,avg_frame_rate,r_frame_rate,nb_frames,duration',
        '-of', 'json', str(video_path)
    ])
    
    stream = (data.get('streams') or [{}])[0]
    
    # Parse frame rates
    avg_str = stream.get('avg_frame_rate', '0/1')
    r_str = stream.get('r_frame_rate', '0/1') 
    
    def parse_rate(rate_str: str) -> float:
        try:
            if '/' in rate_str:
                num, den = rate_str.split('/')
                return float(num) / float(den) if float(den) != 0 else 0.0
            return float(rate_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    avg = parse_rate(avg_str)
    r = parse_rate(r_str)
    
    # Get other properties
    width = int(stream.get('width') or 0)
    height = int(stream.get('height') or 0)
    
    try:
        nb = int(stream.get('nb_frames') or 0)
    except (ValueError, TypeError):
        nb = 0
    
    try:
        dur = float(stream.get('duration') or 0)
    except (ValueError, TypeError):
        dur = 0.0
        
    return {
        'avg_frame_rate': avg,
        'r_frame_rate': r,
        'nb_frames': nb,
        'duration': dur,
        'width': width,
        'height': height,
    }

def probe_audio(video_path: Path) -> Dict[str, Any]:
    """Probe audio stream information"""
    data = _ffprobe_json([
        'ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_name,channels,channel_layout',
        '-of', 'json', str(video_path)
    ])
    
    streams = data.get('streams') or []
    if not streams:
        return {'has_audio': False}
    
    s = streams[0]
    return {
        'has_audio': True,
        'codec': s.get('codec_name'),
        'channels': s.get('channels'),
        'layout': s.get('channel_layout'),
    }

def probe_color(video_path: Path) -> Dict[str, Any]:
    """Probe color space information"""
    data = _ffprobe_json([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=color_space,color_transfer,color_primaries',
        '-of', 'json', str(video_path)
    ])
    
    stream = (data.get('streams') or [{}])[0]
    prim = (stream.get('color_primaries') or '').lower()
    trc = (stream.get('color_transfer') or '').lower()
    spc = (stream.get('color_space') or stream.get('colorspace') or '').lower()
    
    is_hdr10 = (prim == 'bt2020' and ('smpte2084' in trc) and ('bt2020nc' in spc or 'bt2020_ncl' in spc))
    
    return {
        'primaries': prim or None,
        'transfer': trc or None,
        'matrix': spc or None,
        'sdr_or_hdr': 'HDR10' if is_hdr10 else 'SDR'
    }

def color_tag_args(color_meta: Dict[str, Any]) -> List[str]:
    """Generate FFmpeg color tagging arguments"""
    if color_meta.get('sdr_or_hdr') == 'HDR10':
        return ['-color_primaries', 'bt2020', '-color_trc', 'smpte2084', '-colorspace', 'bt2020nc']
    return ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']

def probe_timecode(video_path: Path) -> Optional[str]:
    """Extract timecode from video metadata"""
    try:
        data = _ffprobe_json([
            'ffprobe', '-v', 'error', '-show_entries', 'format_tags=timecode',
            '-of', 'json', str(video_path)
        ])
        tags = (data.get('format') or {}).get('tags') or {}
        return tags.get('timecode')
    except Exception:
        return None

def format_timecode(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def get_video_info(video_path: Path) -> Dict[str, Any]:
    """Get comprehensive video information"""
    video_info = probe_video(video_path)
    audio_info = probe_audio(video_path)
    color_info = probe_color(video_path)
    timecode = probe_timecode(video_path)
    
    return {
        **video_info,
        **audio_info,
        **color_info,
        'timecode': timecode,
        'file_size': video_path.stat().st_size if video_path.exists() else 0,
        'file_path': str(video_path)
    }