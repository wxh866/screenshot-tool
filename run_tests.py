#!/usr/bin/env python
"""运行全部测试套件"""
import sys
import subprocess
from pathlib import Path

root = Path(__file__).parent

def main():
    """运行pytest"""
    args = [
        sys.executable, "-m", "pytest",
        str(root / "tests"),
        "-v",
        "--tb=short",
    ]
    result = subprocess.run(args, cwd=str(root))
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
