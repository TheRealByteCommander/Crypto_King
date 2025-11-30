import subprocess
import os
import sys

os.chdir(r"C:\Users\mschm\Crypto_King")

print("="*60)
print("Git Push - Kerzen-Tracking-System")
print("="*60)

# Status vorher
print("\n[1] Status vorher:")
result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
print(result.stdout)

# Add alle Dateien
print("\n[2] Stage alle Dateien...")
files = [
    "backend/candle_tracker.py",
    "backend/bot_manager.py",
    "backend/agent_tools.py",
    "backend/memory_manager.py",
    "backend/agent_configs/cyphermind_config.yaml",
    "README.md",
    "MEMORY_SYSTEM.md",
    "CANDLE_TRACKING_ANALYSE.md",
    "CANDLE_TRACKING_IMPLEMENTATION.md",
    "POSITION_TRACKING_UPDATE.md",
    "CHANGELOG_CANDLE_TRACKING.md",
]

for file in files:
    if os.path.exists(file):
        subprocess.run(["git", "add", file])

# Oder einfach alle
result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
print(result.stdout)

# Status nach add
print("\n[3] Status nach add:")
result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
print(result.stdout)

# Commit
print("\n[4] Committe...")
result = subprocess.run(["git", "commit", "-m", "Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Push
print("\n[5] Push ins Repo...")
result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Finaler Status
print("\n[6] Finaler Status:")
result = subprocess.run(["git", "status"], capture_output=True, text=True)
print(result.stdout)

print("\n" + "="*60)
print("Fertig!")
print("="*60)

