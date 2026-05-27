#!/usr/bin/env python3
"""
Code Executor - Safe code execution for Jarvis
Runs code snippets in a controlled environment
"""

import subprocess
import tempfile
import os
import uuid
from typing import Dict, Optional


class CodeExecutor:
    """Execute code safely"""

    def __init__(self):
        self.timeout = 30  # seconds
        self.allowed_languages = {
            "python": ["python3", "-c"],
            "javascript": ["node", "-e"],
            "bash": ["bash", "-c"],
        }

    def execute(self, code: str, language: str = "python") -> Dict:
        """Execute code and return result"""
        if language not in self.allowed_languages:
            return {"error": f"Language {language} not allowed", "output": ""}

        try:
            cmd = self.allowed_languages[language]

            # Create temp file for longer code
            if len(code) > 500:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f".{language}", delete=False
                ) as f:
                    f.write(code)
                    temp_file = f.name

                if language == "python":
                    cmd = ["python3", temp_file]
                elif language == "javascript":
                    cmd = ["node", temp_file]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                os.unlink(temp_file)
            else:
                cmd.append(code)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Code execution timed out", "output": "", "timeout": True}
        except Exception as e:
            return {"error": str(e), "output": ""}

    def execute_python(self, code: str) -> str:
        """Execute Python code"""
        result = self.execute(code, "python")

        if result.get("error"):
            return f"Error: {result['error']}"

        if result.get("output"):
            return result["output"].strip()

        return "Code executed successfully (no output)."

    def calculate(self, expression: str) -> str:
        """Quick calculator"""
        try:
            # Safe evaluation of math expressions
            allowed_chars = set("0123456789+-*/.() ")
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return str(result)
        except:
            pass

        # Fallback to Python
        code = f"print({expression})"
        result = self.execute_python(code)
        return result


# Global instance
_code_executor = None


def get_code_executor() -> CodeExecutor:
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor


# Quick functions
def run_code(code: str, language: str = "python") -> str:
    """Run code and return output"""
    executor = get_code_executor()
    result = executor.execute(code, language)

    if result.get("error"):
        return f"Error: {result['error']}"

    output = result.get("output", "").strip()
    if not output:
        return "Code executed successfully (no output)."

    return output


def calculate(expression: str) -> str:
    """Quick calculation"""
    executor = get_code_executor()
    return executor.calculate(expression)


if __name__ == "__main__":
    executor = CodeExecutor()

    print("Testing code execution:")

    # Test calculation
    print(f"  2 + 2 = {executor.calculate('2 + 2')}")
    print(f"  10 * 5 = {executor.calculate('10 * 5')}")

    # Test code
    result = executor.execute_python("print('Hello from Python!')")
    print(f"  Code: {result}")
