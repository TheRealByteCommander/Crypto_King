# Crypto News System für NexusChat

## Übersicht

NexusChat hat jetzt Zugriff auf ein sicheres News-System, das aktuelle Kryptowährungs-Nachrichten von vertrauenswürdigen Quellen liefert. Das System ist mit mehreren Sicherheitsebenen ausgestattet, um Spam und Fake News zu verhindern.

## Sicherheitsfeatures

### 1. Whitelist-basierte Quellen

Nur vertrauenswürdige, etablierte Krypto-News-Portale sind erlaubt:

- **CoinDesk** (Reliability Score: 0.95)
- **CoinTelegraph** (Reliability Score: 0.90)
- **CryptoSlate** (Reliability Score: 0.85)
- **Decrypt** (Reliability Score: 0.88)
- **The Block** (Reliability Score: 0.87)

Neue Quellen können nur durch Code-Änderungen hinzugefügt werden - keine dynamische Erweiterung möglich.

### 2. Rate Limiting

- **Max. 10 Requests pro Minute** pro Quelle
- Verhindert Überlastung und Missbrauch
- Automatische Tracking und Enforcement

### 3. Content Filtering

Automatische Filterung von Spam und Fake News durch:

- **Keyword-Blacklist**: Erkennung von typischen Spam-Phrasen
  - "guaranteed profit", "risk-free", "get rich quick"
  - "pump and dump", "telegram pump"
  - "crypto giveaway", "fake airdrop"
  - "ponzi", "pyramid scheme"
  - etc.

- **Pattern-Erkennung**:
  - Excessive Capitalization (mehr als 3 Großbuchstaben-Wörter)
  - Multiple Exclamation Marks (!!, !!!)
  - Suspicious Marketing Language

### 4. RSS-Feed basiert

- Nutzt offizielle RSS-Feeds der Quellen
- Kein Web-Scraping von HTML-Seiten (reduziert Risiko)
- Strukturierte Daten

## Verwendung

### NexusChat Tool: `get_crypto_news`

NexusChat kann das Tool `get_crypto_news` verwenden, um aktuelle News abzurufen.

**Parameter:**
- `limit` (optional, default: 10, max: 20): Anzahl der Artikel
- `symbols` (optional): Filter für spezifische Kryptowährungen (z.B. `["BTC", "ETH", "SOL"]`)
- `query` (optional): Suchbegriffe (z.B. `"Bitcoin ETF"`, `"Ethereum upgrade"`)

**Beispiele:**

1. **Allgemeine Krypto-News:**
   ```
   get_crypto_news(limit=10)
   ```

2. **News zu spezifischen Coins:**
   ```
   get_crypto_news(symbols=["BTC", "ETH"], limit=5)
   ```

3. **Suche nach Thema:**
   ```
   get_crypto_news(query="Bitcoin ETF", limit=10)
   ```

## Antwortformat

Das Tool gibt eine Liste von Artikeln zurück:

```json
{
  "success": true,
  "count": 10,
  "articles": [
    {
      "title": "Bitcoin Reaches New All-Time High",
      "link": "https://coindesk.com/...",
      "summary": "Bitcoin price surged to...",
      "published": "2024-01-15T10:30:00Z",
      "source": "CoinDesk",
      "source_key": "coindesk.com",
      "reliability_score": 0.95,
      "fetched_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

## Benutzer-Interaktionen

NexusChat kann automatisch News abrufen, wenn Benutzer fragen wie:

- "Was sind die neuesten Bitcoin-News?"
- "Gibt es Neuigkeiten zu Ethereum?"
- "Zeig mir aktuelle Krypto-News"
- "Was passiert gerade im Krypto-Markt?"
- "Suche nach News zu 'Bitcoin ETF'"

## Konfiguration

### Whitelist erweitern

Um eine neue Quelle hinzuzufügen, bearbeite `backend/crypto_news_fetcher.py`:

```python
TRUSTED_SOURCES = {
    # ... bestehende Quellen ...
    "neue-quelle.com": {
        "name": "Neue Quelle",
        "rss": "https://neue-quelle.com/rss",
        "enabled": True,
        "reliability_score": 0.80
    }
}
```

### Rate Limiting anpassen

In `backend/crypto_news_fetcher.py`:

```python
RATE_LIMIT_REQUESTS_PER_MINUTE = 10  # Anpassen
RATE_LIMIT_WINDOW_SECONDS = 60
```

### Spam-Filter erweitern

In `backend/crypto_news_fetcher.py`:

```python
SPAM_KEYWORDS = [
    # ... bestehende Keywords ...
    r'\b(neues-spam-keyword)\b'
]
```

## Dependencies

Das System benötigt folgende Python-Pakete:

- `feedparser` - RSS-Feed Parsing
- `beautifulsoup4` - HTML-Parsing (für zukünftige Erweiterungen)
- `httpx` - HTTP-Client (bereits vorhanden)

Installation:
```bash
pip install feedparser beautifulsoup4
```

## News-Weiterleitung an andere Agents

NexusChat kann wichtige News automatisch an CypherMind und CypherTrade weiterleiten:

### Tool: `share_news_with_agents`

**Parameter:**
- `articles` (erforderlich): Liste von News-Artikeln
- `target_agents` (optional): `["CypherMind"]`, `["CypherTrade"]`, oder `["both"]` (Standard)
- `priority` (optional): `"high"`, `"medium"` (Standard), oder `"low"`

**Beispiel:**
```python
share_news_with_agents(
    articles=[{
        "title": "Bitcoin ETF Approved by SEC",
        "summary": "The SEC has approved the first Bitcoin ETF...",
        "link": "https://...",
        "source": "CoinDesk",
        "symbols": ["BTC"]
    }],
    target_agents=["both"],
    priority="high"
)
```

### Wichtige News-Kriterien

NexusChat sollte nur wirklich relevante News weiterleiten:

**✅ Weiterleiten:**
- Regulatorische Änderungen (SEC, Regierungen, Bans)
- Major Events (ETF Approvals, Hard Forks, Network Upgrades)
- Signifikante Marktbewegungen (Crashes, Bull Runs, ATH)
- Security-Breaches oder Exchange-Probleme
- Institutionelle Adoption oder Whale Movements

**❌ NICHT weiterleiten:**
- Allgemeine Preis-Updates
- Kleinere Updates ohne Trading-Relevanz
- Marketing-News
- Routine-Ankündigungen

### Agent-Nutzung

**CypherMind** erhält News für:
- Bessere Trading-Entscheidungen
- Berücksichtigung von Markt-Events in Analysen
- Kombination von News und technischen Indikatoren

**CypherTrade** erhält News für:
- Risikomanagement
- Erkennung von potenziellen Ausführungsproblemen
- Vorsicht bei Security-Breaches oder Exchange-Problemen

### Automatische News-Bewertung

Das System bewertet News automatisch nach Wichtigkeit:

- **High Importance Keywords**: Regulation, ETF, Hack, Major Event, etc.
- **Medium Importance Keywords**: Listing, Partnership, Update, etc.
- **Reliability Score**: Qualität der Quelle (0.0-1.0)

News mit Importance-Score ≥ 0.4 werden als "wichtig" eingestuft.

## Memory & Learning

NexusChat kann aus News-Interaktionen lernen:

- Welche News-Quellen sind am nützlichsten?
- Welche Themen interessieren Benutzer am meisten?
- Welche News führten zu erfolgreichen Trading-Entscheidungen?
- Welche News waren für andere Agents am wertvollsten?

Diese Informationen werden im Memory-System gespeichert (siehe `MEMORY_SYSTEM.md`).

## Sicherheitshinweise

⚠️ **Wichtig:**

1. **Whitelist ist strikt**: Nur vordefinierte Quellen sind erlaubt
2. **Rate Limiting**: Verhindert Missbrauch und Überlastung
3. **Content Filtering**: Automatische Spam/Fake-News-Erkennung
4. **Keine dynamischen Quellen**: Neue Quellen müssen manuell hinzugefügt werden
5. **RSS-basiert**: Nutzt offizielle Feeds, kein Web-Scraping

## Fehlerbehandlung

- **Rate Limit erreicht**: Tool gibt leere Liste zurück, loggt Warnung
- **Quelle nicht verfügbar**: Wird übersprungen, andere Quellen werden weiter abgefragt
- **Spam erkannt**: Artikel wird gefiltert und nicht zurückgegeben
- **Network-Fehler**: Wird geloggt, andere Quellen werden weiter versucht

## Logging

Alle Aktivitäten werden geloggt:

```bash
# News-Fetches
INFO: Fetching RSS feed from coindesk.com: https://...

# Spam-Erkennung
WARNING: Spam detected: pattern in title/content

# Rate Limiting
WARNING: Rate limit reached for coindesk.com
```

## Zukünftige Erweiterungen

Mögliche Verbesserungen:

- [ ] Sentiment-Analyse für News-Artikel
- [ ] Automatische Relevanz-Bewertung
- [ ] Integration mit Trading-Signalen
- [ ] News-basierte Trading-Alerts
- [ ] Multi-Sprache Support
- [ ] News-Archiv für historische Analysen

