# MCP Server Integration

## Übersicht

Das Project CypherTrade unterstützt jetzt **MCP (Model Context Protocol) Server**, um Trading-Tools für AI-Agenten bereitzustellen.

## Konfiguration

MCP Server kann in der `backend/.env` Datei aktiviert werden:

```env
MCP_ENABLED=true
MCP_PORT=8002
```

Standardmäßig ist MCP Server deaktiviert (`MCP_ENABLED=false`).

## Verfügbare Tools

Der MCP Server stellt folgende Tools bereit:

### 1. `get_bot_status`
Ruft den aktuellen Status des Trading-Bots ab.

**Parameter:** Keine

**Beispiel:**
```json
{
  "tool_name": "get_bot_status",
  "parameters": {}
}
```

### 2. `get_trade_history`
Ruft die Handelshistorie ab.

**Parameter:**
- `limit` (optional, Standard: 10): Anzahl der zurückzugebenden Trades

**Beispiel:**
```json
{
  "tool_name": "get_trade_history",
  "parameters": {
    "limit": 20
  }
}
```

### 3. `get_market_analysis`
Ruft aktuelle Marktanalysen ab.

**Parameter:**
- `limit` (optional, Standard: 5): Anzahl der zurückzugebenden Analysen

**Beispiel:**
```json
{
  "tool_name": "get_market_analysis",
  "parameters": {
    "limit": 10
  }
}
```

### 4. `get_performance_stats`
Ruft Performance-Statistiken ab.

**Parameter:** Keine

**Beispiel:**
```json
{
  "tool_name": "get_performance_stats",
  "parameters": {}
}
```

### 5. `get_agent_memory`
Ruft Memory/Learning-Daten für einen spezifischen Agenten ab.

**Parameter:**
- `agent_name` (erforderlich): Name des Agenten (NexusChat, CypherMind, CypherTrade)
- `limit` (optional, Standard: 10): Anzahl der zurückzugebenden Memories

**Beispiel:**
```json
{
  "tool_name": "get_agent_memory",
  "parameters": {
    "agent_name": "CypherMind",
    "limit": 20
  }
}
```

### 6. `get_learning_insights`
Ruft kollektive Learning-Insights von allen Agenten ab.

**Parameter:** Keine

**Beispiel:**
```json
{
  "tool_name": "get_learning_insights",
  "parameters": {}
}
```

## API-Endpunkte

### Tools auflisten
```
GET /mcp/tools
```

Gibt eine Liste aller verfügbaren Tools zurück.

### Tool ausführen
```
POST /mcp/tools/{tool_name}
```

Führt ein Tool mit den angegebenen Parametern aus.

**Request Body:**
```json
{
  "parameters": {
    "limit": 10
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    // Tool-spezifische Ergebnisse
  }
}
```

### Health Check
```
GET /mcp/health
```

Prüft den Status des MCP Servers.

## Verwendung mit AI-Agenten

MCP Server ermöglicht es AI-Agenten, auf Trading-Daten und -Funktionen zuzugreifen, ohne direkt mit der Binance API oder der Datenbank interagieren zu müssen.

**Beispiel-Integration:**
```python
import httpx

async def get_trading_stats():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/mcp/tools/get_performance_stats",
            json={"parameters": {}}
        )
        return response.json()
```

## Sicherheit

⚠️ **Wichtig:** MCP Server sollte nur in vertrauenswürdigen Umgebungen aktiviert werden. Die Tools ermöglichen Zugriff auf sensible Trading-Daten.

## Fehlerbehandlung

Alle Tools geben strukturierte Fehlerantworten zurück:

```json
{
  "success": false,
  "error": "Fehlerbeschreibung"
}
```

## Logging

MCP Server-Aktivitäten werden im Backend-Log protokolliert:

```bash
tail -f /var/log/supervisor/cyphertrade-backend.log | grep MCP
```

