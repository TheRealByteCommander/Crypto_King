#!/usr/bin/env python3
"""
Script zum Anzeigen aller verfügbaren Ollama-Modelle auf dem Server.

Verwendung:
    python3 scripts/list_ollama_models.py
    oder
    ./scripts/list_ollama_models.py
"""

import requests
import json
import sys
from typing import List, Dict, Any
from datetime import datetime

# Ollama API Base URL (Standard: 192.168.178.155:11434)
OLLAMA_BASE_URL = "http://192.168.178.155:11434"
OLLAMA_API_TAGS = f"{OLLAMA_BASE_URL}/api/tags"


def get_ollama_models() -> Dict[str, Any]:
    """
    Ruft die Liste aller verfügbaren Ollama-Modelle ab.
    
    Returns:
        Dict mit 'models' Liste oder Fehler-Informationen
    """
    try:
        response = requests.get(OLLAMA_API_TAGS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"❌ FEHLER: Konnte nicht zu Ollama Server verbinden ({OLLAMA_BASE_URL})")
        print("   Stelle sicher, dass Ollama läuft: sudo systemctl status ollama")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"❌ FEHLER: Timeout beim Verbinden zu Ollama Server ({OLLAMA_BASE_URL})")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ FEHLER: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ FEHLER: Ungültige Antwort von Ollama Server")
        sys.exit(1)


def format_size(size_bytes: int) -> str:
    """Formatiert Bytes in lesbare Größe (GB, MB, etc.)."""
    if size_bytes is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_date(date_str: str) -> str:
    """Formatiert ISO-Datum in lesbares Format."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return date_str


def display_models(models_data: Dict[str, Any], verbose: bool = False):
    """
    Zeigt die verfügbaren Modelle an.
    
    Args:
        models_data: Dict mit 'models' Liste von Ollama API
        verbose: Wenn True, zeigt zusätzliche Details
    """
    if 'models' not in models_data:
        print("❌ FEHLER: Keine Modelle in der Antwort gefunden")
        print(f"   Antwort: {json.dumps(models_data, indent=2)}")
        return
    
    models = models_data['models']
    
    if not models:
        print("⚠️  Keine Modelle auf dem Ollama Server gefunden.")
        print("   Installiere ein Modell mit: ollama pull <modell-name>")
        return
    
    print("=" * 80)
    print(f"📦 OLLAMA MODELLE ({len(models)} verfügbar)")
    print("=" * 80)
    print()
    
    # Sortiere Modelle nach Name
    sorted_models = sorted(models, key=lambda x: x.get('name', '').lower())
    
    for i, model in enumerate(sorted_models, 1):
        name = model.get('name', 'N/A')
        size = model.get('size', 0)
        modified_at = model.get('modified_at', '')
        
        # Zeige Modell-Name (Haupt-Info)
        print(f"{i:2d}. {name}")
        
        if verbose:
            # Zeige zusätzliche Details
            if size:
                print(f"    📏 Größe: {format_size(size)}")
            if modified_at:
                print(f"    📅 Modifiziert: {format_date(modified_at)}")
            
            # Zeige Digest falls verfügbar
            digest = model.get('digest', '')
            if digest:
                print(f"    🔑 Digest: {digest[:16]}...")
            
            # Zeige Details falls verfügbar
            details = model.get('details', {})
            if details:
                parent_model = details.get('parent_model', '')
                format_info = details.get('format', '')
                family = details.get('family', '')
                
                if parent_model:
                    print(f"    👤 Parent: {parent_model}")
                if format_info:
                    print(f"    📋 Format: {format_info}")
                if family:
                    print(f"    🏷️  Family: {family}")
        
        print()
    
    print("=" * 80)
    print(f"💡 Tipp: Verwende 'ollama pull <modell-name>' um ein neues Modell zu installieren")
    print(f"💡 Tipp: Verwende 'ollama list' für eine einfache Liste")
    print("=" * 80)


def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Zeigt alle verfügbaren Ollama-Modelle auf dem Server an",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s                    # Zeige alle Modelle
  %(prog)s -v                  # Zeige Modelle mit Details
  %(prog)s --url http://remote:11434  # Verbinde zu entferntem Ollama Server
        """
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Zeige zusätzliche Details (Größe, Datum, etc.)'
    )
    parser.add_argument(
        '--url',
        default=OLLAMA_BASE_URL,
        help=f'Ollama Server URL (Standard: {OLLAMA_BASE_URL})'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Ausgabe als JSON'
    )
    
    args = parser.parse_args()
    
    # Setze globale URL falls überschrieben
    global OLLAMA_BASE_URL, OLLAMA_API_TAGS
    OLLAMA_BASE_URL = args.url.rstrip('/')
    OLLAMA_API_TAGS = f"{OLLAMA_BASE_URL}/api/tags"
    
    # Hole Modelle
    models_data = get_ollama_models()
    
    # JSON-Ausgabe
    if args.json:
        print(json.dumps(models_data, indent=2, ensure_ascii=False))
        return
    
    # Normale Ausgabe
    display_models(models_data, verbose=args.verbose)


if __name__ == "__main__":
    main()

