#!/bin/bash
# Diagnose-Script: Findet heraus, warum server.py nicht importiert werden kann

set -e

echo "=========================================="
echo "Server.py Import Diagnose"
echo "=========================================="
echo ""

BACKEND_DIR="/app/backend"

if [ ! -d "$BACKEND_DIR" ]; then
    BACKEND_DIR="./backend"
    if [ ! -d "$BACKEND_DIR" ]; then
        echo "[ERROR] Backend-Verzeichnis nicht gefunden"
        exit 1
    fi
fi

cd "$BACKEND_DIR" || exit 1

# Aktiviere venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv nicht gefunden!"
    exit 1
fi

echo "[INFO] Python-Pfad: $(which python)"
echo "[INFO] Python-Version: $(python --version)"
echo "[INFO] Arbeitsverzeichnis: $(pwd)"
echo ""

# Prüfe ob server.py existiert
if [ ! -f "server.py" ]; then
    echo "[ERROR] server.py nicht gefunden!"
    exit 1
fi

echo "[INFO] server.py gefunden"
echo ""

# Prüfe Syntax
echo "[INFO] Prüfe Syntax von server.py..."
python -m py_compile server.py 2>&1 || {
    echo "[ERROR] Syntax-Fehler in server.py gefunden!"
    exit 1
}
echo "[OK] Syntax OK"
echo ""

# Prüfe Imports Schritt für Schritt
echo "[INFO] Prüfe Imports Schritt für Schritt..."
echo ""

python3 << 'PYTHON_EOF'
import sys
import traceback

# Füge Backend-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, '/app/backend')

print("=" * 60)
print("Import-Test für server.py")
print("=" * 60)
print()

# Liste aller Imports aus server.py (in Reihenfolge)
imports_to_test = [
    ("fastapi", "FastAPI, APIRouter, WebSocket"),
    ("fastapi.responses", "StreamingResponse, JSONResponse"),
    ("fastapi.exceptions", "RequestValidationError"),
    ("starlette.middleware.cors", "CORSMiddleware"),
    ("starlette.exceptions", "HTTPException"),
    ("dotenv", "load_dotenv"),
    ("motor.motor_asyncio", "AsyncIOMotorClient"),
    ("bson", "ObjectId"),
    ("pydantic", "BaseModel, Field, ConfigDict"),
    ("config", "settings"),
    ("agents", "AgentManager"),
    ("bot_manager", "BotManager, TradingBot"),
    ("constants", "BOT_BROADCAST_INTERVAL_SECONDS"),
    ("validators", "validate_all_services, validate_mongodb_connection"),
    ("mcp_server", "create_mcp_server"),
    ("autonomous_manager", "AutonomousManager"),
    ("trading_pairs_cache", "get_trading_pairs_cache"),
]

failed_imports = []

for module_name, items in imports_to_test:
    try:
        if "," in items:
            # Multiple imports
            exec(f"from {module_name} import {items}")
        else:
            # Single import
            exec(f"from {module_name} import {items}")
        print(f"✓ {module_name} ({items})")
    except ImportError as e:
        print(f"✗ {module_name} ({items}) - FEHLER: {e}")
        failed_imports.append((module_name, items, str(e)))
    except Exception as e:
        print(f"✗ {module_name} ({items}) - FEHLER: {type(e).__name__}: {e}")
        failed_imports.append((module_name, items, str(e)))

print()
print("=" * 60)

# Versuche server.py zu importieren
print()
print("Versuche server.py zu importieren...")
try:
    import server
    print("✓ server.py erfolgreich importiert!")
    print(f"  app verfügbar: {hasattr(server, 'app')}")
    if hasattr(server, 'app'):
        print(f"  app Typ: {type(server.app)}")
except ImportError as e:
    print(f"✗ ImportError beim Import von server: {e}")
    print()
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ {type(e).__name__} beim Import von server: {e}")
    print()
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
if failed_imports:
    print("FEHLGESCHLAGENE IMPORTS:")
    for module, items, error in failed_imports:
        print(f"  - {module} ({items}): {error}")
    print()
    print("LÖSUNG:")
    print("  pip install <fehlendes-modul>")
else:
    print("ALLE IMPORTS ERFOLGREICH!")
print("=" * 60)
PYTHON_EOF

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[ERROR] Import-Test fehlgeschlagen!"
    echo ""
    echo "Nächste Schritte:"
    echo "  1. Prüfe ob alle Dependencies installiert sind:"
    echo "     cd $BACKEND_DIR"
    echo "     source venv/bin/activate"
    echo "     pip install -r requirements.txt"
    echo ""
    echo "  2. Prüfe ob .env Datei vorhanden ist:"
    echo "     ls -la $BACKEND_DIR/.env"
    echo ""
    echo "  3. Prüfe MongoDB-Verbindung:"
    echo "     python -c \"from config import settings; print(settings.mongo_url)\""
    exit 1
fi

echo ""
echo "[SUCCESS] Alle Imports erfolgreich!"

