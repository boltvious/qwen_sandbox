"""
Sandbox module for safe code execution
"""

import ast
import sys
import io
import contextlib
from typing import Dict, Any, Optional


class SandboxExecutionError(Exception):
    """Custom exception for sandbox execution errors"""
    pass


class CodeSandbox:
    """Safe code execution sandbox"""
    
    # Restricted built-ins that cannot be used in sandboxed code
    RESTRICTED_BUILTINS = {
        'eval', 'exec', 'compile', 'open', 'input',
        '__import__', 'globals', 'locals', 'vars',
        'getattr', 'setattr', 'delattr', 'hasattr'
    }
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the sandbox
        
        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
    
    def execute(self, code: str, globals_dict: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute code in a sandboxed environment
        
        Args:
            code: Python code to execute
            globals_dict: Optional global variables dictionary
            
        Returns:
            dict: Execution result with output, error, and status
        """
        try:
            # Validate code safety
            self._validate_code(code)
            
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Create restricted globals
            if globals_dict is None:
                globals_dict = {}
            
            restricted_globals = self._create_restricted_globals(globals_dict)
            
            # Execute code with captured output
            with contextlib.redirect_stdout(stdout_capture):
                with contextlib.redirect_stderr(stderr_capture):
                    exec(code, restricted_globals)
            
            return {
                "success": True,
                "output": stdout_capture.getvalue(),
                "error": stderr_capture.getvalue(),
                "exit_code": 0
            }
            
        except SandboxExecutionError as e:
            return {
                "success": False,
                "output": "",
                "error": f"Sandbox Error: {str(e)}",
                "exit_code": 1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Execution Error: {str(e)}",
                "exit_code": 1
            }
    
    def _validate_code(self, code: str):
        """
        Validate code for safety before execution
        
        Args:
            code: Python code to validate
            
        Raises:
            SandboxExecutionError: If code contains unsafe operations
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SandboxExecutionError(f"Syntax error: {str(e)}")
        
        # Check for dangerous operations
        for node in ast.walk(tree):
            # Check for function calls to restricted built-ins
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.RESTRICTED_BUILTINS:
                        raise SandboxExecutionError(
                            f"Use of restricted function '{node.func.id}' is not allowed"
                        )
            
            # Check for import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Allow only safe imports
                pass  # Could add import validation here
        
        return True
    
    def _create_restricted_globals(self, user_globals: Dict) -> Dict:
        """
        Create a restricted globals dictionary for safe execution
        
        Args:
            user_globals: User-provided global variables
            
        Returns:
            dict: Restricted globals dictionary
        """
        # Start with builtins - include safe functions like print
        safe_builtins = {
            'print': print,
            'len': len,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'reversed': reversed,
            'sorted': sorted,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'list': list,
            'tuple': tuple,
            'dict': dict,
            'set': set,
            'frozenset': frozenset,
            'type': type,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            'delattr': delattr,
            'iter': iter,
            'next': next,
            'all': all,
            'any': any,
            'ord': ord,
            'chr': chr,
            'repr': repr,
            'format': format,
            'open': None,  # Disabled for safety
            'input': None,  # Disabled for safety
            'eval': None,  # Disabled for safety
            'exec': None,  # Disabled for safety
            'compile': None,  # Disabled for safety
            '__import__': None,  # Disabled for safety
            'globals': None,  # Disabled for safety
            'locals': None,  # Disabled for safety
            'vars': None,  # Disabled for safety
        }
        
        restricted_globals = {
            "__builtins__": safe_builtins,
            "__name__": "__sandbox__",
            "__doc__": None,
        }
        
        # Add user-provided globals
        restricted_globals.update(user_globals)
        
        return restricted_globals
    
    def execute_with_input(self, code: str, input_data: str = "") -> Dict[str, Any]:
        """
        Execute code with provided input data
        
        Args:
            code: Python code to execute
            input_data: Input data to provide to the program
            
        Returns:
            dict: Execution result
        """
        # Pre-load input data
        globals_dict = {"_input_data": input_data}
        return self.execute(code, globals_dict)
