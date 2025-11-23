# 🔍 Trading Mode Debug - Browser-Konsole

## Schritt 1: Browser-Konsole öffnen

1. **F12** drücken (oder Rechtsklick → Untersuchen)
2. **Console Tab** öffnen
3. Folgenden Code eingeben und **Enter** drücken:

```javascript
// Prüfe ob Trading Mode im DOM ist
const tradingMode = document.querySelector('[data-testid="trading-mode-select"]');
console.log('Trading Mode Select:', tradingMode);

// Prüfe alle Labels
const labels = Array.from(document.querySelectorAll('label'));
const tradingLabel = labels.find(l => l.textContent.includes('Trading Mode'));
console.log('Trading Mode Label:', tradingLabel);

// Prüfe Grid-Container
const grids = Array.from(document.querySelectorAll('.grid'));
const formGrid = grids.find(g => {
    const text = g.textContent;
    return text.includes('Strategy') && text.includes('Timeframe');
});
console.log('Form Grid:', formGrid);
if (formGrid) {
    console.log('Grid Children:', formGrid.children.length);
    Array.from(formGrid.children).forEach((child, idx) => {
        console.log(`Child ${idx}:`, child);
    });
}

// Prüfe ob Trading Mode im JavaScript ist
fetch('/static/js/main.*.js')
  .then(r => r.text())
  .then(text => {
    if (text.includes('tradingMode')) {
        console.log('✅ tradingMode im JavaScript Bundle gefunden');
    } else {
        console.log('❌ tradingMode NICHT im JavaScript Bundle');
    }
  });
```

## Schritt 2: Network Tab prüfen

1. **Network Tab** öffnen
2. Seite neu laden (F5)
3. Prüfe ob `main.*.js` geladen wird
4. Klicke auf die main.js Datei
5. Prüfe ob `tradingMode` in der Response enthalten ist

## Schritt 3: Build direkt prüfen

Auf dem Server:

```bash
cd /app
bash verify-build-content.sh
```

Dies zeigt, ob Trading Mode wirklich im Build ist.

