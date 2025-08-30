#!/usr/bin/env python3
"""
Test runner script for FinVault backend.
"""
import subprocess
import sys
import os

def run_tests():
    """Run the test suite."""
    # Change to backend directory
    os.chdir(os.path.dirname(__file__))

    # Install dependencies if needed
    print("Installing test dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
    ], check=True)

    # Run tests
    print("Running tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "--verbose",
        "--tb=short",
        "--asyncio-mode=auto",
        "tests/"
    ])

    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
