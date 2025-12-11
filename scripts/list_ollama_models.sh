#!/bin/bash
# Script zum Anzeigen aller verfügbaren Ollama-Modelle auf dem Server
#
# Verwendung:
#   ./scripts/list_ollama_models.sh
#   oder
#   bash scripts/list_ollama_models.sh

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_API_TAGS="${OLLAMA_BASE_URL}/api/tags"

echo "=================================================================================="
echo "📦 OLLAMA MODELLE AUFLISTEN"
echo "=================================================================================="
echo ""
echo "Server: ${OLLAMA_BASE_URL}"
echo ""

# Prüfe Verbindung
echo "[INFO] Prüfe Verbindung zum Ollama-Server..."
if ! curl -s --connect-timeout 5 "${OLLAMA_API_TAGS}" > /dev/null 2>&1; then
    echo "❌ FEHLER: Konnte nicht zu Ollama Server verbinden (${OLLAMA_BASE_URL})"
    echo "   Stelle sicher, dass Ollama läuft: sudo systemctl status ollama"
    echo "   Oder starte Ollama: ollama serve"
    exit 1
fi

echo "[OK] Ollama-Server ist erreichbar"
echo ""

# Hole Modelle
echo "[INFO] Lade verfügbare Modelle..."
MODELS_JSON=$(curl -s "${OLLAMA_API_TAGS}")

# Prüfe ob Modelle gefunden wurden
MODEL_COUNT=$(echo "${MODELS_JSON}" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('models', [])))" 2>/dev/null || echo "0")

if [ "${MODEL_COUNT}" = "0" ]; then
    echo "⚠️  Keine Modelle auf dem Ollama Server gefunden."
    echo "   Installiere ein Modell mit: ollama pull <modell-name>"
    echo ""
    echo "Beispiele:"
    echo "  ollama pull llama3.2"
    echo "  ollama pull deepseek-r1:32b"
    exit 0
fi

echo "[OK] ${MODEL_COUNT} Modell(e) gefunden"
echo ""
echo "=================================================================================="
echo "VERFÜGBARE MODELLE:"
echo "=================================================================================="
echo ""

# Zeige Modelle mit Python (falls verfügbar)
if command -v python3 >/dev/null 2>&1; then
    echo "${MODELS_JSON}" | python3 -c "
import sys, json
from datetime import datetime

try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    
    # Sortiere nach Name
    models.sort(key=lambda x: x.get('name', '').lower())
    
    for i, model in enumerate(models, 1):
        name = model.get('name', 'N/A')
        size = model.get('size', 0)
        modified_at = model.get('modified_at', '')
        
        print(f'{i:2d}. {name}')
        
        if size:
            # Formatiere Größe
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    print(f'    📏 Größe: {size:.2f} {unit}')
                    break
                size /= 1024.0
        
        if modified_at:
            try:
                dt = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
                print(f'    📅 Modifiziert: {dt.strftime(\"%Y-%m-%d %H:%M:%S\")}')
            except:
                pass
        
        print()
    
except Exception as e:
    print(f'Fehler beim Parsen: {e}')
    sys.exit(1)
" 2>/dev/null || {
    # Fallback: Zeige rohes JSON
    echo "${MODELS_JSON}" | python3 -m json.tool 2>/dev/null || echo "${MODELS_JSON}"
}
else
    # Fallback: Zeige rohes JSON
    echo "${MODELS_JSON}" | python3 -m json.tool 2>/dev/null || echo "${MODELS_JSON}"
fi

echo ""
echo "=================================================================================="
echo "💡 TIPPS:"
echo "=================================================================================="
echo "  • Neues Modell installieren: ollama pull <modell-name>"
echo "  • Modell löschen: ollama rm <modell-name>"
echo "  • Alle Modelle anzeigen: ollama list"
echo "  • Modell testen: ollama run <modell-name>"
echo ""
echo "Beispiele:"
echo "  ollama pull llama3.2"
echo "  ollama pull deepseek-r1:32b"
echo "  ollama pull qwen2.5:7b"
echo "=================================================================================="

