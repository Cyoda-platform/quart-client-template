#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

def main():
    # Create virtual environment if it doesn't exist
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
    
    # Determine the path to the virtual environment's Python executable
    if sys.platform == 'win32':
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"
    
    # Upgrade pip and install requirements
    print("Installing/upgrading pip...")
    subprocess.check_call([str(python_path), "-m", "ensurepip", "--upgrade"])
    subprocess.check_call([str(python_path), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    
    print("Installing requirements...")
    subprocess.check_call([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"])
    
    print("Setup complete! Activate the virtual environment with:")
    if sys.platform == 'win32':
        print("    venv\\Scripts\\activate")
    else:
        print("    source venv/bin/activate")

if __name__ == "__main__":
    main()