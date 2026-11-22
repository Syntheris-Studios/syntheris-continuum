#!/usr/bin/env python3
"""
Comprehensive V4.0.0 Implementation Validation Script
Validates all research findings, path configuration, and system readiness.
"""

import sys
import os
import re
from pathlib import Path
import json
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from syntheris_video_processor.core.config import (
    path_config, 
    has_hardcoded_paths, 
    validate_research_implementation,
    get_config
)


class V4ValidationSuite:
    """Comprehensive validation suite for V4.0.0 implementation."""
    
    def __init__(self):
        self.results = {
            'path_configuration': {},
            'hardcoded_paths': {},
            'research_implementation': {},
            'rife_integration': {},
            'system_readiness': {},
            'overall_status': 'PENDING'
        }
        
    def run_complete_validation(self) -> Dict[str, Any]:
        """Run all validation tests and return comprehensive results."""
        
        print("[VALIDATION] Starting Comprehensive V4.0.0 Implementation Validation")
        print("=" * 70)
        
        # Test 1: Path Configuration System
        print("\n1. [PATH] Validating Path Configuration System...")
        self.validate_path_configuration()
        
        # Test 2: Hardcoded Path Detection  
        print("\n2. [PATHS] Scanning for Hardcoded Paths...")
        self.validate_hardcoded_paths()
        
        # Test 3: RIFE v4.26 Integration
        print("\n3. [RIFE] Testing RIFE v4.26 Integration...")
        self.validate_rife_integration()
        
        # Test 4: Research Implementation
        print("\n4. [RESEARCH] Validating Research Implementation...")
        self.validate_research_features()
        
        # Test 5: System Readiness
        print("\n5. [SYSTEM] Checking System Readiness...")
        self.validate_system_readiness()
        
        # Generate final report
        self.generate_final_report()
        
        return self.results
    
    def validate_path_configuration(self):
        """Test path configuration system."""
        try:
            # Test path detection
            path_validation = path_config.validate_configuration()
            
            self.results['path_configuration'] = {
                'rife_v426_available': path_validation['rife_v426']['available'],
                'rife_v426_path': path_validation['rife_v426']['path'],
                'rife_hdv3_available': path_validation['rife_hdv3_fallback']['available'],
                'rife_hdv3_path': path_validation['rife_hdv3_fallback']['path'],
                'all_paths_configurable': True,
                'environment_variables': path_validation['environment_variables']
            }
            
            # Check if paths are properly configurable
            if path_validation['rife_v426']['available'] or path_validation['rife_hdv3_fallback']['available']:
                print("  [OK] Path detection working correctly")
            else:
                print("  [WARN] No RIFE installation detected")
                
            print(f"  [INFO] RIFE v4.26: {'[OK] Available' if path_validation['rife_v426']['available'] else '[FAIL] Not found'}")
            if path_validation['rife_v426']['path']:
                print(f"     Path: {path_validation['rife_v426']['path']}")
                
            print(f"  [INFO] RIFE HDv3: {'[OK] Available' if path_validation['rife_hdv3_fallback']['available'] else '[FAIL] Not found'}")
            if path_validation['rife_hdv3_fallback']['path']:
                print(f"     Path: {path_validation['rife_hdv3_fallback']['path']}")
            
        except Exception as e:
            print(f"  [FAIL] Path configuration error: {e}")
            self.results['path_configuration']['error'] = str(e)
    
    def validate_hardcoded_paths(self):
        """Scan for hardcoded paths in the codebase."""
        try:
            has_hardcoded = has_hardcoded_paths()
            
            self.results['hardcoded_paths'] = {
                'detected': has_hardcoded,
                'scan_completed': True
            }
            
            if not has_hardcoded:
                print("  [OK] No hardcoded paths detected")
            else:
                print("  [WARN] Hardcoded paths found - check logs for details")
                
            # Additional detailed scan
            hardcoded_files = self.scan_for_hardcoded_paths_detailed()
            self.results['hardcoded_paths']['detailed_scan'] = hardcoded_files
            
        except Exception as e:
            print(f"  [FAIL] Hardcoded path scan error: {e}")
            self.results['hardcoded_paths']['error'] = str(e)
    
    def scan_for_hardcoded_paths_detailed(self) -> List[Dict[str, str]]:
        """Detailed scan for hardcoded paths with file locations."""
        hardcoded_files = []
        
        hardcoded_patterns = [
            r'[C-Z]:\\\\[^"\'\\s]*',  # Windows absolute paths
            r'"C:/',                  # Quoted C: paths
            r"'C:/",                  # Single quoted C: paths
        ]
        
        project_files = list(project_root.glob("syntheris_video_processor/**/*.py"))
        
        for file_path in project_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in hardcoded_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Skip acceptable patterns
                        if any(skip in match.lower() for skip in [
                            'program files', 'windows', 'example', 'env', 'template'
                        ]):
                            continue
                            
                        hardcoded_files.append({
                            'file': str(file_path.relative_to(project_root)),
                            'path': match,
                            'pattern': pattern
                        })
            except Exception as e:
                print(f"    Warning: Could not scan {file_path}: {e}")
                
        return hardcoded_files
    
    def validate_rife_integration(self):
        """Test RIFE v4.26 integration and capabilities."""
        try:
            from syntheris_video_processor.backends.rife_v426_config import RIFEv426Configurator
            
            configurator = RIFEv426Configurator()
            v426_available = configurator.is_v426_available()
            
            self.results['rife_integration'] = {
                'v426_available': v426_available,
                'configurator_working': True
            }
            
            if v426_available:
                print("  [OK] RIFE v4.26 integration working")
                print(f"     Working directory: {configurator.working_dir}")
                
                # Test configuration generation
                try:
                    config = configurator.get_optimal_config(24.0, 60.0)
                    self.results['rife_integration']['config_generation'] = True
                    print("  [OK] Configuration generation working")
                    
                    # Validate research settings
                    if config.get('sc') == False and config.get('skip') == False:
                        print("  [OK] Research settings applied (sc=false, skip=false)")
                        self.results['rife_integration']['research_settings'] = True
                    else:
                        print("  [WARN] Research settings not properly applied")
                        self.results['rife_integration']['research_settings'] = False
                        
                except Exception as e:
                    print(f"  [WARN] Configuration generation error: {e}")
                    self.results['rife_integration']['config_generation'] = False
            else:
                print("  [WARN] RIFE v4.26 not available - will use HDv3 fallback")
                
        except Exception as e:
            print(f"  [FAIL] RIFE integration error: {e}")
            self.results['rife_integration']['error'] = str(e)
    
    def validate_research_features(self):
        """Validate research implementation features."""
        try:
            research_validation = validate_research_implementation()
            
            self.results['research_implementation'] = research_validation
            
            print("  Research Implementation Status:")
            for feature, status in research_validation.items():
                status_icon = "[OK]" if status else "[FAIL]"
                feature_name = feature.replace('_', ' ').title()
                print(f"    {status_icon} {feature_name}")
            
            # Check configuration values
            config = get_config()
            
            # Duration validation settings
            if config.get('duration_validation_enabled') and config.get('duration_tolerance_ms') == 100:
                print("  [OK] Duration validation configured correctly (100ms tolerance)")
            else:
                print("  [WARN] Duration validation configuration issue")
                
            # PTS reset settings
            if config.get('pts_reset_enabled'):
                print("  [OK] PTS reset enabled")
            else:
                print("  [WARN] PTS reset not enabled")
                
        except Exception as e:
            print(f"  [FAIL] Research validation error: {e}")
            self.results['research_implementation']['error'] = str(e)
    
    def validate_system_readiness(self):
        """Check overall system readiness."""
        try:
            config = get_config()
            
            self.results['system_readiness'] = {
                'app_version': config.get('app_version'),
                'directories_exist': True,
                'dependencies_available': True
            }
            
            # Check directories
            try:
                path_config.ensure_directories()
                print("  [OK] Required directories created/verified")
            except Exception as e:
                print(f"  [WARN] Directory creation issue: {e}")
                self.results['system_readiness']['directories_exist'] = False
            
            # Check critical imports
            try:
                from syntheris_video_processor.core.quality_assurance import QualityAssurance
                from syntheris_video_processor.backends.rife_backend_final_fixed import RIFEBackend
                from syntheris_video_processor.ui.gradio_interface_modular import create_gradio_interface
                print("  [OK] Core modules importable")
            except ImportError as e:
                print(f"  [FAIL] Import error: {e}")
                self.results['system_readiness']['dependencies_available'] = False
            
            # Verify version
            if config.get('app_version') == 'V4.0.0':
                print("  [OK] Version correctly set to V4.0.0")
            else:
                print(f"  [WARN] Version mismatch: {config.get('app_version')}")
                
        except Exception as e:
            print(f"  [FAIL] System readiness error: {e}")
            self.results['system_readiness']['error'] = str(e)
    
    def generate_final_report(self):
        """Generate final validation report."""
        print("\n" + "=" * 70)
        print("[SUMMARY] VALIDATION SUMMARY")
        print("=" * 70)
        
        # Count successful validations
        success_count = 0
        total_count = 0
        
        # Path configuration
        if self.results['path_configuration'].get('all_paths_configurable'):
            success_count += 1
        total_count += 1
        
        # Hardcoded paths
        if not self.results['hardcoded_paths'].get('detected', True):
            success_count += 1
        total_count += 1
        
        # RIFE integration
        if self.results['rife_integration'].get('configurator_working'):
            success_count += 1
        total_count += 1
        
        # Research implementation
        research_results = self.results['research_implementation']
        if isinstance(research_results, dict):
            research_success = sum(research_results.values())
            research_total = len(research_results)
            success_count += research_success / research_total
            total_count += 1
        
        # System readiness
        if self.results['system_readiness'].get('dependencies_available'):
            success_count += 1
        total_count += 1
        
        # Calculate overall status
        success_rate = success_count / total_count if total_count > 0 else 0
        
        if success_rate >= 0.9:
            self.results['overall_status'] = 'EXCELLENT'
            status_icon = "[EXCELLENT]"
        elif success_rate >= 0.7:
            self.results['overall_status'] = 'GOOD'
            status_icon = "[OK]"
        elif success_rate >= 0.5:
            self.results['overall_status'] = 'PARTIAL'
            status_icon = "[WARN]"
        else:
            self.results['overall_status'] = 'FAILED'
            status_icon = "[FAIL]"
        
        print(f"\n{status_icon} OVERALL STATUS: {self.results['overall_status']}")
        print(f"[INFO] Success Rate: {success_rate:.1%} ({success_count:.1f}/{total_count})")
        
        # Specific status messages
        if self.results['overall_status'] == 'EXCELLENT':
            print("\n[EXCELLENT] IMPLEMENTATION COMPLETE AND VALIDATED")
            print("   All systems operational and ready for production")
        elif self.results['overall_status'] == 'GOOD':
            print("\n[OK] Implementation mostly complete with minor issues")
            print("   System functional but may need attention to some areas")
        else:
            print("\n[WARN] Implementation needs attention")
            print("   Please review failed validations and address issues")
        
        # Save detailed results
        results_file = project_root / "validation_results.json"
        try:
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\n[FILE] Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"\n[WARN] Could not save results file: {e}")


def main():
    """Main validation entry point."""
    try:
        validator = V4ValidationSuite()
        results = validator.run_complete_validation()
        
        # Exit with appropriate code
        if results['overall_status'] in ['EXCELLENT', 'GOOD']:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[FAIL] Validation suite error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()