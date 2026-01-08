#!/usr/bin/env python3
"""
WebGridPlayer Distribution Verification
Checks that all files are present and ready for distribution
"""

import os
import sys
from pathlib import Path

def check_distribution():
    """Verify the distribution is complete and ready."""
    print("🔍 WebGridPlayer Distribution Check")
    print("=" * 40)
    
    # Required files for distribution
    required_files = [
        'webgridplayer.py',
        'README.md', 
        'LICENSE',
        'requirements.txt',
        'pyproject.toml',
        'install_webgridplayer.sh',
        'run_webgridplayer.sh',
        'install_desktop.sh',
        'WebGridPlayer.desktop',
        'webgridplayer.svg',
        '.gitignore',
        'CHANGELOG.md',
        'CONTRIBUTING.md',
        'QUICK_START.md',
        'examples.py',
        'test_stream_extraction.py'
    ]
    
    missing_files = []
    present_files = []
    
    for file in required_files:
        if Path(file).exists():
            size = Path(file).stat().st_size
            present_files.append(f"✅ {file} ({size:,} bytes)")
        else:
            missing_files.append(f"❌ {file}")
    
    print("Present files:")
    for file in present_files:
        print(f"  {file}")
    
    if missing_files:
        print("\nMissing files:")
        for file in missing_files:
            print(f"  {file}")
        return False
    
    # Check file permissions
    print("\nExecutable files:")
    executable_files = ['install_webgridplayer.sh', 'run_webgridplayer.sh', 'install_desktop.sh']
    for file in executable_files:
        if Path(file).exists():
            if os.access(file, os.X_OK):
                print(f"  ✅ {file} (executable)")
            else:
                print(f"  ⚠️  {file} (not executable)")
    
    # Check Python syntax
    print("\nPython syntax check:")
    python_files = ['webgridplayer.py', 'examples.py', 'test_stream_extraction.py']
    for file in python_files:
        try:
            with open(file, 'r') as f:
                compile(f.read(), file, 'exec')
            print(f"  ✅ {file}")
        except SyntaxError as e:
            print(f"  ❌ {file}: Syntax error at line {e.lineno}")
            return False
        except Exception as e:
            print(f"  ⚠️  {file}: {e}")
    
    # Calculate total size
    total_size = sum(Path(f).stat().st_size for f in required_files if Path(f).exists())
    print(f"\nTotal distribution size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    
    print(f"\n🎉 Distribution is ready!")
    print("Ready for:")
    print("  • GitHub repository upload")
    print("  • PyPI package distribution") 
    print("  • Docker containerization")
    print("  • Standalone releases")
    
    return True

if __name__ == "__main__":
    success = check_distribution()
    sys.exit(0 if success else 1)