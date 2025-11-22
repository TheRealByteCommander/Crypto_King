#!/bin/bash
# Prüft ob die konfigurierten Ollama-Modelle auf dem Remote-Server verfügbar sind

OLLAMA_SERVER="192.168.178.155"
OLLAMA_PORT="11434"
OLLAMA_URL="http://${OLLAMA_SERVER}:${OLLAMA_PORT}"

echo "=== Prüfe Ollama-Modelle auf Remote-Server ==="
echo "Server: ${OLLAMA_URL}"
echo ""

# Prüfe Verbindung zum Ollama-Server
echo "[INFO] Prüfe Verbindung zum Ollama-Server..."
if curl -s --connect-timeout 5 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo "[SUCCESS] Ollama-Server ist erreichbar"
else
    echo "[ERROR] Ollama-Server ist NICHT erreichbar!"
    echo "        Bitte prüfen Sie ob der Server läuft und die IP-Adresse korrekt ist."
    exit 1
fi

echo ""
echo "[INFO] Verfügbare Modelle auf dem Server:"
curl -s "${OLLAMA_URL}/api/tags" | python3 -m json.tool 2>/dev/null || curl -s "${OLLAMA_URL}/api/tags"

echo ""
echo "=== Prüfe konfigurierte Modelle ==="

# Definiere die Modelle aus der .env (passen Sie diese an Ihre Konfiguration an)
declare -a MODELS=(
    "ajindal/llama3.1-storm:8b"
    "0xroyce/plutus:latest"
    "Qwen2.5:7b-instruct"
)

# Alternativ: Lesen Sie die Modelle direkt aus der .env Datei
if [ -f "/app/backend/.env" ]; then
    echo "[INFO] Lese Modelle aus /app/backend/.env..."
    NEXUSCHAT_MODEL=$(grep "^NEXUSCHAT_MODEL=" /app/backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    CYPHERMIND_MODEL=$(grep "^CYPHERMIND_MODEL=" /app/backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    CYPHERTRADE_MODEL=$(grep "^CYPHERTRADE_MODEL=" /app/backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    
    if [ ! -z "$NEXUSCHAT_MODEL" ] || [ ! -z "$CYPHERMIND_MODEL" ] || [ ! -z "$CYPHERTRADE_MODEL" ]; then
        MODELS=()
        [ ! -z "$NEXUSCHAT_MODEL" ] && MODELS+=("$NEXUSCHAT_MODEL")
        [ ! -z "$CYPHERMIND_MODEL" ] && MODELS+=("$CYPHERMIND_MODEL")
        [ ! -z "$CYPHERTRADE_MODEL" ] && MODELS+=("$CYPHERTRADE_MODEL")
        echo "[SUCCESS] Modelle aus .env geladen"
    fi
fi

# Hole Liste aller verfügbaren Modelle
AVAILABLE_MODELS=$(curl -s "${OLLAMA_URL}/api/tags" | python3 -c "import sys, json; data = json.load(sys.stdin); print('\n'.join([m.get('name', '') for m in data.get('models', [])]))" 2>/dev/null || echo "")

for MODEL in "${MODELS[@]}"; do
    echo -n "Prüfe Model: ${MODEL} ... "
    
    # Prüfe ob Modell in der Liste vorhanden ist
    if echo "$AVAILABLE_MODELS" | grep -q "^${MODEL}$"; then
        echo "[✓] Verfügbar"
    elif echo "$AVAILABLE_MODELS" | grep -q "${MODEL}"; then
        echo "[✓] Verfügbar (Teilstring-Match)"
    else
        echo "[✗] NICHT gefunden!"
        echo "    Bitte installieren Sie das Modell mit:"
        echo "    curl -X POST ${OLLAMA_URL}/api/pull -d '{\"name\": \"${MODEL}\"}'"
    fi
done

echo ""
echo "=== Teste Model-Zugriff ==="
# Teste ob man auf die Modelle zugreifen kann
TEST_MODEL="${MODELS[0]}"
echo "Teste Modell: ${TEST_MODEL}"

RESPONSE=$(curl -s -X POST "${OLLAMA_URL}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${TEST_MODEL}\", \"prompt\": \"Hello\", \"stream\": false}" \
    2>&1)

if echo "$RESPONSE" | grep -q '"response"'; then
    echo "[SUCCESS] Modell-Zugriff funktioniert!"
else
    echo "[WARNING] Modell-Zugriff könnte Probleme haben"
    echo "Response: ${RESPONSE:0:200}"
fi

echo ""
echo "=== Zusammenfassung ==="
echo "Wenn alle Modelle verfügbar sind, können Sie das Backend starten:"
echo "  sudo supervisorctl restart cyphertrade-backend"
echo ""
echo "Um fehlende Modelle zu installieren:"
echo "  ssh auf den Ollama-Server (192.168.178.155) und ausführen:"
for MODEL in "${MODELS[@]}"; do
    echo "    ollama pull ${MODEL}"
done

