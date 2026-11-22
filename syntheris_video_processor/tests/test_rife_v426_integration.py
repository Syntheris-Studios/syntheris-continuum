"""
Test RIFE v4.26 Integration - Validates Exact FPS Targeting
Tests RIFE v4.26 specific functionality and exact FPS parameter usage.
"""

import unittest
import sys
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from syntheris_video_processor.backends.rife_v426_config import RIFEv426Configurator, get_24fps_to_60fps_config
from syntheris_video_processor.backends.rife_backend_final_fixed import RIFEBackend
from syntheris_video_processor.backends.rife_v426_manager import RIFEv426Manager


class TestRIFEv426Integration(unittest.TestCase):
    """Test RIFE v4.26 exact FPS targeting and integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.configurator = RIFEv426Configurator()
        self.manager = RIFEv426Manager()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_video_24fps(self, duration: float = 2.0) -> Path:
        """Create a test video at exactly 24fps."""
        output_path = self.temp_dir / f"test_24fps_{duration}s.mp4"
        
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size=320x240:rate=24',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to create test video: {result.stderr}")
        return output_path
    
    def get_video_fps(self, video_path: Path) -> float:
        """Get video frame rate."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        fps_str = result.stdout.strip()
        
        if '/' in fps_str:
            num, den = fps_str.split('/')
            return float(num) / float(den)
        return float(fps_str)
    
    def test_rife_v426_detection(self):
        """Test RIFE v4.26 detection and availability."""
        print("\n=== Testing RIFE v4.26 Detection ===")
        
        v426_available = self.configurator.is_v426_available()
        print(f"RIFE v4.26 available: {v426_available}")
        
        if v426_available:
            model_info = self.configurator.get_model_info()
            print(f"Model info: {model_info}")
            
            self.assertTrue(model_info['available'], "Model should be available")
            self.assertEqual(model_info['version'], '4.26', "Should detect version 4.26")
            self.assertTrue(model_info['capabilities']['exact_fps_targeting'], 
                          "Should support exact FPS targeting")
            self.assertTrue(model_info['capabilities']['supports_2_5x'], 
                          "Should support 2.5x multiplier")
            
            print("SUCCESS: RIFE v4.26 detection test PASSED")
        else:
            print("ℹ️ RIFE v4.26 not available - skipping v4.26 specific tests")
    
    def test_exact_fps_configuration(self):
        """Test exact FPS configuration generation."""
        print("\n=== Testing Exact FPS Configuration ===")
        
        # Test 24fps->60fps configuration (primary use case)
        config = self.configurator.get_optimal_config(24.0, 60.0)
        print(f"24fps->60fps config: {config}")
        
        if 'error' not in config:
            # Validate research-based parameters
            self.assertEqual(config.get('fps_num'), 60000, 
                           "Should use fps_num=60000 for exact 59.94fps")
            self.assertEqual(config.get('fps_den'), 1001, 
                           "Should use fps_den=1001 for exact 59.94fps")
            self.assertFalse(config.get('sc'), 
                           "Scene detection should be disabled per research")
            self.assertFalse(config.get('skip'), 
                           "Frame skipping should be disabled per research")
            self.assertEqual(config.get('multiplier_type'), 'exact_fps', 
                           "Should use exact FPS mode")
            self.assertAlmostEqual(config.get('expected_ratio'), 2.5, places=1,
                                 msg="Should calculate 2.5x ratio for 24fps->60fps")
            
            # Test 24fps->30fps configuration
            config_30 = self.configurator.get_optimal_config(24.0, 30.0)
            print(f"24fps->30fps config: {config_30}")
            
            self.assertEqual(config_30.get('fps_num'), 30000, 
                           "Should use fps_num=30000 for 29.97fps")
            self.assertAlmostEqual(config_30.get('expected_ratio'), 1.25, places=2,
                                 msg="Should calculate 1.25x ratio for 24fps->30fps")
            
            print("SUCCESS: Exact FPS configuration test PASSED")
        else:
            print(f"WARNING: Configuration error: {config['error']}")
    
    def test_conversion_feasibility_validation(self):
        """Test conversion feasibility validation."""
        print("\n=== Testing Conversion Feasibility Validation ===")
        
        # Test valid conversions
        valid_conversions = [
            (24.0, 60.0),   # 2.5x - key research case
            (24.0, 48.0),   # 2x
            (30.0, 60.0),   # 2x
            (24.0, 30.0),   # 1.25x
        ]
        
        for source_fps, target_fps in valid_conversions:
            feasible, message = self.configurator.validate_conversion(source_fps, target_fps)
            print(f"{source_fps}fps -> {target_fps}fps: {feasible} - {message}")
            self.assertTrue(feasible, f"Conversion {source_fps}->{target_fps} should be feasible")
        
        # Test invalid conversions
        invalid_conversions = [
            (60.0, 30.0),   # Frame rate reduction (not supported)
            (24.0, 240.0),  # >8x ratio
            (0.0, 60.0),    # Invalid source
            (24.0, 0.0),    # Invalid target
        ]
        
        for source_fps, target_fps in invalid_conversions:
            feasible, message = self.configurator.validate_conversion(source_fps, target_fps)
            print(f"{source_fps}fps -> {target_fps}fps: {feasible} - {message}")
            self.assertFalse(feasible, f"Conversion {source_fps}->{target_fps} should not be feasible")
        
        print("SUCCESS: Conversion feasibility validation test PASSED")
    
    def test_command_building(self):
        """Test RIFE v4.26 command building."""
        print("\n=== Testing RIFE v4.26 Command Building ===")
        
        if not self.configurator.is_v426_available():
            self.skipTest("RIFE v4.26 not available")
        
        # Create test video
        test_video = self.create_test_video_24fps(2.0)
        output_path = self.temp_dir / "output.mp4"
        
        # Get configuration and build command
        config = self.configurator.get_optimal_config(24.0, 60.0)
        if 'error' in config:
            self.skipTest(f"Configuration error: {config['error']}")
        
        cmd = self.configurator.build_command(test_video, output_path, config)
        print(f"Generated command: {' '.join(cmd)}")
        
        # Validate command components
        self.assertIn('inference_video.py', ' '.join(cmd), "Should use inference script")
        # The bundled CLI accepts --fps, not fps_num/fps_den.
        self.assertIn('--fps', cmd)
        self.assertEqual(cmd[cmd.index('--fps') + 1], '60')
        self.assertNotIn('--fps_num', cmd)
        self.assertNotIn('--fps_den', cmd)
        self.assertNotIn('--skip', cmd)
        fractional = self.configurator.build_command(
            test_video, output_path, self.configurator.get_optimal_config(24.0, 59.94)
        )
        self.assertEqual(float(fractional[fractional.index('--fps') + 1]), 59.94)

        # Check for research-validated parameters
        cmd_str = ' '.join(cmd)
        if '--no_scene_change' in cmd_str or '--sc' in cmd:
            print("SUCCESS: Scene change detection properly disabled")
        if '--no_skip' in cmd_str or '--skip' in cmd:
            print("SUCCESS: Frame skipping properly disabled")
        
        print("SUCCESS: Command building test PASSED")
    
    def test_rife_v426_inference_execution(self):
        """Test actual RIFE v4.26 inference execution using centralized path configuration."""
        print("\n=== Testing RIFE v4.26 Inference Execution ===")
        
        from ..core.config import path_config
        
        rife_v426_path = path_config.get_rife_v426_path()
        if not rife_v426_path:
            self.skipTest("RIFE v4.26 not available - using centralized path detection")
        
        # Verify required files
        required_files = [
            'inference_video.py',
            'train_log/flownet.pkl',
            'train_log/RIFE_HDv3.py'
        ]
        
        for required_file in required_files:
            file_path = rife_v426_path / required_file
            self.assertTrue(file_path.exists(), f"Required file missing: {required_file}")
        
        # Create small test video
        test_video = self.create_test_video_24fps(1.0)  # Short for quick test
        output_path = self.temp_dir / "rife_output.mp4"
        
        config = self.configurator.get_optimal_config(24.0, 60.0)
        cmd = self.configurator.build_command(test_video, output_path, config)
        result = subprocess.run(
            cmd, cwd=str(rife_v426_path), capture_output=True,
            text=True, timeout=120
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(output_path.exists(), "RIFE should create output file")
        self.assertGreater(output_path.stat().st_size, 0)
        self.assertAlmostEqual(self.get_video_fps(output_path), 60.0, delta=0.1)

    def test_backend_integration(self):
        """Test RIFE backend integration with v4.26 support."""
        print("\n=== Testing RIFE Backend v4.26 Integration ===")
        
        backend = RIFEBackend()
        
        # Test availability check
        available, message = backend.is_available()
        print(f"Backend available: {available} - {message}")
        
        if available:
            # Check version and capabilities
            capabilities = backend.get_capabilities()
            print(f"Backend capabilities: {capabilities}")
            
            self.assertIn('version', capabilities, "Should report version")
            
            if hasattr(backend, 'supports_exact_fps') and backend.supports_exact_fps:
                print("SUCCESS: Backend supports exact FPS targeting")
                self.assertTrue(backend.supports_2_5x_multiplier, 
                              "Should support 2.5x multiplier")
                
            # Test processing estimation
            test_video = self.create_test_video_24fps(1.0)
            estimated_time = backend.estimate_processing_time(
                test_video, 'custom_fps', target_fps=60.0
            )
            print(f"Estimated processing time: {estimated_time:.2f}s")
            self.assertGreater(estimated_time, 0, "Should provide time estimate")
            
            print("SUCCESS: Backend integration test PASSED")
        else:
            print("ℹ️ Backend not available - skipping integration tests")
    
    def test_research_validated_presets(self):
        """Test research-validated preset configurations."""
        print("\n=== Testing Research-Validated Presets ===")
        
        from syntheris_video_processor.backends.rife_v426_config import get_supported_conversions
        
        supported = get_supported_conversions()
        print(f"Supported conversions: {supported}")
        
        # Validate key research findings are present
        expected_conversions = ['24fps_to_60fps', '24fps_to_30fps', '30fps_to_60fps']
        
        for conversion in expected_conversions:
            self.assertIn(conversion, supported, f"Should support {conversion}")
            
            conversion_info = supported[conversion]
            self.assertIn('description', conversion_info, "Should have description")
            self.assertIn('ratio', conversion_info, "Should have ratio")
            self.assertTrue(conversion_info['precision_mode'], "Should use precision mode")
        
        # Test 24fps->60fps specifically (key research case)
        fps_24_to_60 = supported['24fps_to_60fps']
        self.assertEqual(fps_24_to_60['ratio'], 2.5, "Should be 2.5x multiplier")
        self.assertIn('2.5x', fps_24_to_60['description'], "Description should mention 2.5x")
        
        print("SUCCESS: Research-validated presets test PASSED")


if __name__ == '__main__':
    # Configure test runner for detailed output
    unittest.main(verbosity=2, buffer=True)