#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir('c:\\Users\\Kronborgs_LabPC\\netboot-orchestrator')

try:
    # Stage changes
    subprocess.run(['git', 'add', 'netboot/entrypoint-backend.sh'], check=True)
    print("[✓] Staged entrypoint-backend.sh")
    
    # Commit
    subprocess.run(['git', 'commit', '-m', 'Add iPXE bootloader downloads to entrypoint - fixes missing undionly.kpxe'], check=True)
    print("[✓] Committed changes")
    
    # Push
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    print("[✓] Pushed to origin/main")
    
    print("\n[SUCCESS] Deployment ready on GitHub")
    
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Command failed: {e}")
    sys.exit(1)
