import ast
import io
import signal
import sys
from typing import List

from scigym.api import DEFAULT_AVAILABLE_PACKAGES, CodeRequest, CodeResult


def timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out (exceeded 3 minutes)")


class Code:


    def __init__(
        self,
        available_tools: List[str] = DEFAULT_AVAILABLE_PACKAGES,
    ):
        self.allowed_modules = available_tools

    def _safe_execute(
        self,
        code: str,
        safe_globals={},
        return_vars: List[str] | None = None,
        max_stdout_length: int = 10000,
        max_execution_minutes=10,
    ) -> CodeResult:
        pass                                                                                 

             
                                                    
                                                                                   
                                                                                               
                                                                                    
                                                                                   

                
                                                                               
           
                                                  
        try:
            tree = ast.parse(code)
            unauthorized_imports = []

            for node in ast.walk(tree):
                                                                                        
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name.split(".")[0]                        
                        if module_name not in self.allowed_modules:
                            return CodeResult(
                                False,
                                error=f"Unauthorized modules {module_name} detected. Only these modules are allowed: {', '.join(self.allowed_modules)}.",
                            )

                                                                                      
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split(".")[0]                        
                        if module_name not in self.allowed_modules:
                            return CodeResult(
                                False,
                                error=f"Unauthorized modules {module_name} detected. Only these modules are allowed: {', '.join(self.allowed_modules)}.",
                            )

        except SyntaxError as e:
            return CodeResult(False, error=f"Syntax error in code: {str(e)}")

        if return_vars:
            for var in return_vars:
                safe_globals[var] = None

                                                   
        stdout_buffer = io.StringIO()
        original_stdout = sys.stdout

        if return_vars:
            for var_name in return_vars:
                safe_globals[var_name] = None

        try:
            sys.stdout = stdout_buffer
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(max_execution_minutes * 60)
            exec(code, safe_globals)
            signal.alarm(0)

                                              
            if return_vars:
                requested_vars = {}
                for var_name in return_vars:
                    requested_vars[var_name] = safe_globals[var_name]
            else:
                requested_vars = None

                                                  
            stdout_output = stdout_buffer.getvalue()
            if len(stdout_output) > max_stdout_length:
                stdout_output = stdout_output[:max_stdout_length] + "\n... [output truncated]"

            return CodeResult(True, data=requested_vars, std_out=stdout_output)

        except TimeoutError:
            return CodeResult(
                False,
                error=f"Your requested code runs too long. Execution timed out (exceeded {max_execution_minutes} minutes)",
            )
        except Exception as e:
                                              
            return CodeResult(False, error=str(e))
        finally:
                                                                   
            sys.stdout = original_stdout
            signal.alarm(0)

    def execute_request(self, request: CodeRequest, safe_globals=None) -> CodeResult:
        pass                               

             
                                               

                
                                                      
           
        if not request.code:
            return CodeResult(False, error=f"Missing code to execute")

                                                                 
        return self._safe_execute(
            request.code, return_vars=request.return_vars, safe_globals=safe_globals
        )
