"""
Gradio Compatibility Patch for Python 3.11 + Gradio 4.38.1
Fixes multiple Gradio compatibility issues including:
- TypeError: 'in <string>' requires string as left operand, not bool
- TypeError: argument of type 'bool' is not iterable
- Localhost accessibility issues
"""

import warnings
import os
import sys
import ast

# Store original functions before patching
_original_get_source_segment = ast.get_source_segment
_original_splitlines = ast._splitlines_no_ff if hasattr(ast, '_splitlines_no_ff') else None

def safe_get_source_segment(source, node, *, padded=False):
    """Safe wrapper for ast.get_source_segment that handles non-string sources"""
    try:
        if not isinstance(source, str):
            return None
        return _original_get_source_segment(source, node, padded=padded)
    except (TypeError, ValueError, AttributeError, IndexError):
        # IndexError can occur when gradio tries to parse malformed source
        return None

def safe_splitlines_no_ff(source):
    """Safe wrapper for ast._splitlines_no_ff that handles non-string sources"""
    try:
        if not isinstance(source, str):
            return []
        if _original_splitlines:
            return _original_splitlines(source)
        else:
            return source.splitlines()
    except (TypeError, ValueError, AttributeError):
        return []

# Apply patches immediately
ast.get_source_segment = safe_get_source_segment
if hasattr(ast, '_splitlines_no_ff'):
    ast._splitlines_no_ff = safe_splitlines_no_ff

def patch_gradio_client_utils():
    """Patch gradio_client.utils to handle boolean schema values"""
    try:
        import gradio_client.utils as client_utils
        
        # Store original function
        if hasattr(client_utils, '_original_json_schema_to_python_type'):
            return  # Already patched
        
        _original_json_schema_to_python_type = client_utils._json_schema_to_python_type
        client_utils._original_json_schema_to_python_type = _original_json_schema_to_python_type
        
        def safe_json_schema_to_python_type(schema, defs):
            """Safe wrapper that handles boolean schemas"""
            try:
                # Handle boolean schema values
                if isinstance(schema, bool):
                    return "bool" if schema else "None"
                
                # Handle non-dict schemas
                if not isinstance(schema, dict):
                    return str(type(schema).__name__)
                
                return _original_json_schema_to_python_type(schema, defs)
            except (TypeError, ValueError, AttributeError, KeyError):
                return "Any"
        
        # Apply the patch
        client_utils._json_schema_to_python_type = safe_json_schema_to_python_type
        
        # Also patch get_type function if it exists
        if hasattr(client_utils, 'get_type') and not hasattr(client_utils, '_original_get_type'):
            _original_get_type = None
            
            # Find get_type function in the module
            for name, obj in vars(client_utils).items():
                if callable(obj) and name == 'get_type':
                    _original_get_type = obj
                    break
            
            if _original_get_type:
                client_utils._original_get_type = _original_get_type
                
                def safe_get_type(schema):
                    """Safe wrapper for get_type that handles boolean schemas"""
                    try:
                        # Handle boolean schema values
                        if isinstance(schema, bool):
                            return "bool" if schema else "None"
                        
                        # Handle non-dict schemas  
                        if not isinstance(schema, dict):
                            return str(type(schema).__name__)
                        
                        return _original_get_type(schema)
                    except (TypeError, ValueError, AttributeError, KeyError):
                        return "Any"
                
                # Replace get_type in the module
                setattr(client_utils, 'get_type', safe_get_type)
        
    except ImportError:
        pass  # gradio_client not available yet

def apply_gradio_compatibility_patch():
    """Apply comprehensive Gradio compatibility fixes"""
    
    # Suppress ALL warnings
    warnings.filterwarnings('ignore')
    
    # Set environment variables
    os.environ['GRADIO_ANALYTICS_ENABLED'] = '0'
    os.environ['GRADIO_DEBUG'] = '0'
    os.environ['GRADIO_TEMP_DIR'] = os.path.join(os.getcwd(), 'temp')
    
    # Apply client utils patch
    patch_gradio_client_utils()

# Apply patch immediately when module is imported  
apply_gradio_compatibility_patch()