#!/usr/bin/env python3
"""
Python Script zum Pushen aller Änderungen ins Git-Repo
"""
import subprocess
import os
import sys

def run_command(cmd, description):
    """Führt einen Git-Befehl aus und gibt die Ausgabe zurück."""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")
    print(f"Befehl: {cmd}")
    print("-"*60)
    
    try:
        # Wechsle ins Projekt-Verzeichnis
        os.chdir(r"C:\Users\mschm\Crypto_King")
        
        # Führe Befehl aus
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Zeige Ausgabe
        if result.stdout:
            print("✅ Ausgabe:")
            print(result.stdout)
        if result.stderr:
            print("⚠️ Fehler/Warnungen:")
            print(result.stderr)
        if result.returncode != 0:
            print(f"❌ Exit Code: {result.returncode}")
            return False
        
        print(f"✅ Erfolgreich! (Exit Code: {result.returncode})")
        return True
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

def main():
    """Hauptfunktion - Führt alle Git-Befehle aus."""
    print("🚀 Git Push Script für Kerzen-Tracking-System")
    print("="*60)
    
    # Schritt 1: Status prüfen
    if not run_command("git status", "Git Status prüfen"):
        print("\n❌ Git Status fehlgeschlagen. Prüfe ob Git verfügbar ist.")
        return
    
    # Schritt 2: Alle Dateien hinzufügen
    print("\n" + "="*60)
    print("➕ Stage alle Änderungen...")
    print("="*60)
    
    files_to_add = [
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
        "COMMIT_ANLEITUNG.md",
        "UPDATE_ZUSAMMENFASSUNG.md",
        "git_push.ps1",
        "commit_candle_tracking.sh",
        "PUSH_ANLEITUNG_FINAL.md",
        "push_to_repo.py"
    ]
    
    # Versuche git add -A (einfacher)
    if not run_command("git add -A", "Alle Dateien stagen (git add -A)"):
        print("\n⚠️ git add -A fehlgeschlagen, versuche einzelne Dateien...")
        for file in files_to_add:
            if os.path.exists(file):
                run_command(f'git add "{file}"', f"Hinzufügen: {file}")
    
    # Schritt 3: Status nach add prüfen
    run_command("git status --short", "Status nach git add")
    
    # Schritt 4: Committen
    commit_message = """Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking

- CandleTracker Klasse für kontinuierliches Kerzen-Tracking
- Pre-Trade: 200 Kerzen vor jedem Trade
- During-Trade: Alle Kerzen während Position offen ist
- Post-Trade: 200 Kerzen nach jedem Verkauf
- Integration in Bot-Manager und Memory-System
- CypherMind Tool erweitert: get_bot_candles()
- Pattern-Extraktion aus Kerzen-Daten für Learning
- Vollständige Dokumentation aktualisiert"""
    
    # Escaped commit message für Windows
    commit_cmd = f'git commit -m "{commit_message.replace(chr(10), " ").replace(chr(34), chr(39))}"'
    
    if not run_command('git commit -m "Feat: Kerzen-Tracking-System implementiert"', "Committen"):
        print("\n⚠️ Commit fehlgeschlagen. Möglicherweise keine Änderungen vorhanden.")
        run_command("git status", "Prüfe Status...")
    
    # Schritt 5: Letzten Commit anzeigen
    run_command("git log --oneline -1", "Letzter Commit")
    
    # Schritt 6: Remote prüfen
    run_command("git remote -v", "Remote-Repositories")
    
    # Schritt 7: Branch prüfen
    run_command("git branch", "Aktueller Branch")
    
    # Schritt 8: Pushen
    print("\n" + "="*60)
    print("🚀 Pushe ins Repo...")
    print("="*60)
    
    if not run_command("git push", "Pushen ins Remote-Repo"):
        print("\n⚠️ Push fehlgeschlagen. Versuche mit explizitem Branch...")
        run_command("git push origin main", "Pushen (origin main)")
        run_command("git push origin master", "Pushen (origin master)")
    
    # Schritt 9: Finaler Status
    print("\n" + "="*60)
    print("✅ Finaler Status")
    print("="*60)
    run_command("git status", "Finaler Git Status")
    
    print("\n" + "="*60)
    print("🎉 Fertig!")
    print("="*60)

if __name__ == "__main__":
    main()

