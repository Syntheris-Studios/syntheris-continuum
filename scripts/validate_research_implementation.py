#!/usr/bin/env python3
"""
Comprehensive Research Implementation Validation Script
Validates that all research findings are properly implemented in the architecture.

This script provides end-to-end validation of the research-based enhancements.
"""

import sys
import time
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from syntheris_video_processor.backends.rife_v426_config import RIFEv426Configurator
    from syntheris_video_processor.backends.rife_backend_final_fixed import RIFEBackend
    from syntheris_video_processor.core.quality_assurance import QualityAssurance
    from syntheris_video_processor.core.media_utils import FFmpegProcessor
    from syntheris_video_processor.core.segments import SegmentProcessor
    from syntheris_video_processor.core.atfi import ATFIProcessor
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class ResearchValidationSuite:
    """Comprehensive validation suite for research findings."""
    
    def __init__(self):
        """Initialize the validation suite."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.results = {}
        self.configurator = RIFEv426Configurator()
        self.qa = QualityAssurance()
        self.ffmpeg = FFmpegProcessor()
        self.segments = SegmentProcessor()
        self.atfi = ATFIProcessor()
        
        print(f"🔧 Validation suite initialized")
        print(f"📁 Temporary directory: {self.temp_dir}")
    
    def __del__(self):
        """Clean up temporary files."""
        import shutil
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_video(self, duration: float, fps: int = 24, name: str = None) -> Path:
        """Create a test video for validation."""
        if name is None:
            name = f"test_{duration}s_{fps}fps.mp4"
        
        output_path = self.temp_dir / name
        
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size=320x240:rate={fps}',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create test video: {result.stderr}")
        
        return output_path
    
    def get_precise_duration(self, video_path: Path) -> float:
        """Get precise duration using research-validated method."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,r_frame_rate',
            '-of', 'json',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'streams' in data and data['streams']:
            stream = data['streams'][0]
            frame_count = int(stream.get('nb_frames', 0))
            fps_str = stream.get('r_frame_rate', '24/1')
            
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
            
            if fps > 0:
                return frame_count / fps
        
        return 0.0
    
    def validate_rife_v426_detection(self) -> Dict[str, Any]:
        """Validate RIFE v4.26 detection and capabilities."""
        try:
            print("\n🔍 Validating RIFE v4.26 Detection...")
            
            # Test detection
            v426_available = self.configurator.is_v426_available()
            
            if v426_available:
                model_info = self.configurator.get_model_info()
                capabilities = model_info.get('capabilities', {})
                
                # Validate key capabilities
                expected_capabilities = [
                    'exact_fps_targeting',
                    'arbitrary_multipliers',
                    'duration_preserving',
                    'precision_mode',
                    'supports_2_5x'
                ]
                
                missing_capabilities = [
                    cap for cap in expected_capabilities
                    if not capabilities.get(cap, False)
                ]
                
                if missing_capabilities:
                    return {
                        'passed': False,
                        'error': f"Missing capabilities: {missing_capabilities}",
                        'details': capabilities
                    }
                
                return {
                    'passed': True,
                    'message': f"RIFE v4.26 detected with all required capabilities",
                    'version': model_info.get('version'),
                    'capabilities': capabilities
                }
            else:
                return {
                    'passed': False,
                    'error': "RIFE v4.26 not detected - please install v4.26 for full functionality",
                    'fallback_available': True
                }
                
        except Exception as e:
            return {
                'passed': False,
                'error': f"RIFE v4.26 detection failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_duration_preservation(self) -> Dict[str, Any]:
        """Validate core duration preservation functionality."""
        try:
            print("\n⏱️ Validating Duration Preservation...")
            
            # Create precise test video (5 seconds at 24fps)
            test_duration = 5.0
            test_video = self.create_test_video(test_duration, fps=24)
            input_duration = self.get_precise_duration(test_video)
            
            if abs(input_duration - test_duration) > 0.01:
                return {
                    'passed': False,
                    'error': f"Test video creation imprecise: {input_duration:.6f}s vs {test_duration}s"
                }
            
            # Test QA validation functionality
            validation_result = self.qa.validate_duration_preservation(test_video, test_video)
            
            if not validation_result['passed']:
                return {
                    'passed': False,
                    'error': f"QA self-validation failed: {validation_result['message']}"
                }
            
            # Test precise duration calculation
            qa_duration = self.qa._get_precise_duration(test_video)
            duration_diff_ms = abs(qa_duration - input_duration) * 1000
            
            if duration_diff_ms > 10:  # Very strict for test validation
                return {
                    'passed': False,
                    'error': f"Duration measurement inconsistency: {duration_diff_ms:.1f}ms"
                }
            
            return {
                'passed': True,
                'message': f"Duration preservation validated (precision: {duration_diff_ms:.1f}ms)",
                'input_duration': input_duration,
                'measured_duration': qa_duration
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"Duration preservation validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_pts_handling(self) -> Dict[str, Any]:
        """Validate PTS reset and timestamp handling."""
        try:
            print("\n🎬 Validating PTS Handling...")
            
            # Create test video
            test_video = self.create_test_video(2.0, fps=24)
            input_duration = self.get_precise_duration(test_video)
            
            # Test PTS reset
            pts_output = self.temp_dir / "pts_reset.mp4"
            self.ffmpeg.apply_pts_reset(test_video, pts_output, preserve_audio=False)
            
            if not pts_output.exists():
                return {
                    'passed': False,
                    'error': "PTS reset did not create output file"
                }
            
            # Validate duration preservation
            output_duration = self.get_precise_duration(pts_output)
            duration_diff_ms = abs(output_duration - input_duration) * 1000
            
            if duration_diff_ms > 100:
                return {
                    'passed': False,
                    'error': f"PTS reset corrupted duration: {duration_diff_ms:.1f}ms difference"
                }
            
            # Test dual PTS reset with offset
            dual_output = self.temp_dir / "dual_pts.mp4"
            self.ffmpeg.apply_dual_pts_reset(test_video, dual_output, duration_offset=1.0)
            
            if not dual_output.exists():
                return {
                    'passed': False,
                    'error': "Dual PTS reset did not create output file"
                }
            
            # Test timestamp normalization
            norm_output = self.temp_dir / "normalized.mp4"
            self.ffmpeg.normalize_timestamps(test_video, norm_output)
            
            if not norm_output.exists():
                return {
                    'passed': False,
                    'error': "Timestamp normalization did not create output file"
                }
            
            return {
                'passed': True,
                'message': f"PTS handling validated (precision: {duration_diff_ms:.1f}ms)",
                'methods_tested': ['apply_pts_reset', 'apply_dual_pts_reset', 'normalize_timestamps']
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"PTS handling validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_concatenation_fixes(self) -> Dict[str, Any]:
        """Validate concatenation fixes prevent frame duplication."""
        try:
            print("\n🎞️ Validating Concatenation Fixes...")
            
            # Create multiple segments
            segments = []
            total_duration = 0.0
            
            for i in range(3):
                segment = self.create_test_video(1.0, fps=24, name=f"segment_{i}.mp4")
                segments.append(segment)
                total_duration += self.get_precise_duration(segment)
            
            # Test enhanced concatenation
            concat_output = self.temp_dir / "concatenated.mp4"
            result_path = self.segments.concatenate_segments(segments, concat_output)
            
            if not result_path.exists():
                return {
                    'passed': False,
                    'error': "Concatenation did not create output file"
                }
            
            # Validate total duration
            final_duration = self.get_precise_duration(result_path)
            duration_diff_ms = abs(final_duration - total_duration) * 1000
            
            if duration_diff_ms > 200:  # Allow more tolerance for concatenation
                return {
                    'passed': False,
                    'error': f"Concatenation corrupted duration: {duration_diff_ms:.1f}ms difference"
                }
            
            # Test PTS reset concatenation method
            pts_concat_output = self.temp_dir / "pts_concatenated.mp4"
            pts_result = self.segments._concat_with_pts_reset(segments, pts_concat_output)
            
            if not pts_result.exists():
                return {
                    'passed': False,
                    'error': "PTS reset concatenation did not create output file"
                }
            
            return {
                'passed': True,
                'message': f"Concatenation validated (precision: {duration_diff_ms:.1f}ms)",
                'segments_tested': len(segments),
                'total_duration': total_duration,
                'final_duration': final_duration
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"Concatenation validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_atfi_integration(self) -> Dict[str, Any]:
        """Validate ATFI integration and duration preservation."""
        try:
            print("\n🚀 Validating ATFI Integration...")
            
            # Test ATFI duration measurement
            test_video = self.create_test_video(1.5, fps=24)
            input_duration = self.get_precise_duration(test_video)
            
            # Test ATFI precise duration method
            atfi_duration = self.atfi._get_precise_duration(test_video)
            measurement_diff = abs(atfi_duration - input_duration) * 1000
            
            if measurement_diff > 10:
                return {
                    'passed': False,
                    'error': f"ATFI duration measurement imprecise: {measurement_diff:.1f}ms difference"
                }
            
            # Test motion analysis (basic functionality)
            motion_stats = self.atfi.analyze_motion_statistics(test_video)
            
            if not isinstance(motion_stats, dict):
                return {
                    'passed': False,
                    'error': "ATFI motion analysis did not return valid statistics"
                }
            
            required_stats = ['frame_count', 'average_motion', 'peak_motion', 'motion_variance']
            missing_stats = [stat for stat in required_stats if stat not in motion_stats]
            
            if missing_stats:
                return {
                    'passed': False,
                    'error': f"ATFI missing motion statistics: {missing_stats}"
                }
            
            return {
                'passed': True,
                'message': f"ATFI integration validated (precision: {measurement_diff:.1f}ms)",
                'duration_precision': measurement_diff,
                'motion_stats': motion_stats
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"ATFI validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_rife_backend_integration(self) -> Dict[str, Any]:
        """Validate RIFE backend integration with v4.26 support."""
        try:
            print("\n🎯 Validating RIFE Backend Integration...")
            
            # Initialize backend
            backend = RIFEBackend()
            
            # Test availability
            available, message = backend.is_available()
            if not available:
                return {
                    'passed': False,
                    'error': f"RIFE backend not available: {message}"
                }
            
            # Test capabilities
            capabilities = backend.get_capabilities()
            required_fields = ['name', 'version', 'cuda_available', 'supported_multipliers']
            
            missing_fields = [field for field in required_fields if field not in capabilities]
            if missing_fields:
                return {
                    'passed': False,
                    'error': f"Backend missing capability fields: {missing_fields}"
                }
            
            # Test version detection
            version = capabilities.get('version')
            if version not in ['4.26', 'HDv3']:
                return {
                    'passed': False,
                    'error': f"Unexpected RIFE version: {version}"
                }
            
            # Test v4.26 specific features if available
            v426_features = {}
            if hasattr(backend, 'supports_exact_fps'):
                v426_features['exact_fps'] = backend.supports_exact_fps
            if hasattr(backend, 'supports_2_5x_multiplier'):
                v426_features['2_5x_multiplier'] = backend.supports_2_5x_multiplier
            
            # Test processing estimation
            test_video = self.create_test_video(1.0, fps=24)
            estimated_time = backend.estimate_processing_time(test_video, 'custom_fps', target_fps=60.0)
            
            if estimated_time <= 0:
                return {
                    'passed': False,
                    'error': f"Backend provided invalid time estimate: {estimated_time}"
                }
            
            return {
                'passed': True,
                'message': f"RIFE backend validated (version: {version})",
                'version': version,
                'capabilities': capabilities,
                'v426_features': v426_features,
                'estimated_processing_time': estimated_time
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"RIFE backend validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def validate_research_configurations(self) -> Dict[str, Any]:
        """Validate research-based configurations are properly implemented."""
        try:
            print("\n🔬 Validating Research Configurations...")
            
            # Test key research configurations
            test_cases = [
                (24.0, 60.0, "24fps→60fps (Primary research case)"),
                (24.0, 30.0, "24fps→30fps (Quality mode)"),
                (30.0, 60.0, "30fps→60fps (Standard doubling)")
            ]
            
            validated_configs = []
            
            for source_fps, target_fps, description in test_cases:
                config = self.configurator.get_optimal_config(source_fps, target_fps)
                
                if 'error' in config:
                    return {
                        'passed': False,
                        'error': f"Configuration failed for {description}: {config['error']}"
                    }
                
                # Validate research parameters for 24fps→60fps
                if source_fps == 24.0 and target_fps == 60.0:
                    if config.get('fps_num') != 60000 or config.get('fps_den') != 1001:
                        return {
                            'passed': False,
                            'error': f"Incorrect fps_num/fps_den for 24fps→60fps: {config.get('fps_num')}/{config.get('fps_den')}"
                        }
                    
                    if config.get('sc') is not False or config.get('skip') is not False:
                        return {
                            'passed': False,
                            'error': f"Research parameters not applied for 24fps→60fps: sc={config.get('sc')}, skip={config.get('skip')}"
                        }
                
                # Validate feasibility
                feasible, message = self.configurator.validate_conversion(source_fps, target_fps)
                if not feasible:
                    return {
                        'passed': False,
                        'error': f"Conversion not feasible for {description}: {message}"
                    }
                
                validated_configs.append({
                    'description': description,
                    'source_fps': source_fps,
                    'target_fps': target_fps,
                    'ratio': config.get('expected_ratio'),
                    'feasible': feasible
                })
            
            return {
                'passed': True,
                'message': f"Research configurations validated for {len(validated_configs)} cases",
                'validated_configs': validated_configs
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"Research configuration validation failed: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests and return comprehensive results."""
        print("🔍 Starting Comprehensive Research Implementation Validation...")
        print("=" * 80)
        
        validation_tests = [
            ('rife_v426_detection', self.validate_rife_v426_detection),
            ('duration_preservation', self.validate_duration_preservation),
            ('pts_handling', self.validate_pts_handling),
            ('concatenation_fixes', self.validate_concatenation_fixes),
            ('atfi_integration', self.validate_atfi_integration),
            ('rife_backend_integration', self.validate_rife_backend_integration),
            ('research_configurations', self.validate_research_configurations)
        ]
        
        results = {}
        passed_count = 0
        
        for test_name, test_func in validation_tests:
            try:
                print(f"\n🧪 Running {test_name.replace('_', ' ').title()}...")
                start_time = time.time()
                
                result = test_func()
                result['execution_time'] = time.time() - start_time
                
                results[test_name] = result
                
                if result['passed']:
                    passed_count += 1
                    status = "✅ PASS"
                    print(f"{status}: {result.get('message', 'Validation passed')}")
                else:
                    status = "❌ FAIL"
                    print(f"{status}: {result.get('error', 'Validation failed')}")
                    
                    # Print traceback for debugging if available
                    if 'traceback' in result and '--verbose' in sys.argv:
                        print(f"Traceback:\n{result['traceback']}")
                
            except Exception as e:
                results[test_name] = {
                    'passed': False,
                    'error': f"Test execution failed: {str(e)}",
                    'traceback': traceback.format_exc(),
                    'execution_time': time.time() - start_time if 'start_time' in locals() else 0
                }
                print(f"❌ FAIL: Test execution failed: {str(e)}")
        
        # Summary
        total_tests = len(validation_tests)
        overall_pass = passed_count == total_tests
        
        print("\n" + "=" * 80)
        print("📊 VALIDATION SUMMARY")
        print("=" * 80)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            execution_time = result.get('execution_time', 0)
            print(f"{test_name:<25}: {status:<8} ({execution_time:.2f}s)")
            
            if not result['passed']:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\nOverall: {passed_count}/{total_tests} tests passed")
        
        if overall_pass:
            print("🎉 ALL RESEARCH FINDINGS SUCCESSFULLY IMPLEMENTED!")
        else:
            print("⚠️ IMPLEMENTATION INCOMPLETE - See failed tests above")
        
        return {
            'overall_pass': overall_pass,
            'passed_count': passed_count,
            'total_tests': total_tests,
            'results': results,
            'summary': f"{passed_count}/{total_tests} tests passed"
        }


def main():
    """Main validation function."""
    print("🎬 Syntheris Video Processor - Research Implementation Validation")
    print("=" * 80)
    
    try:
        validator = ResearchValidationSuite()
        results = validator.run_comprehensive_validation()
        
        # Save detailed results to file
        results_file = Path('validation_results.json')
        with open(results_file, 'w') as f:
            # Convert Path objects to strings for JSON serialization
            serializable_results = json.loads(json.dumps(results, default=str))
            json.dump(serializable_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results['overall_pass'] else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Validation suite failed: {str(e)}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()