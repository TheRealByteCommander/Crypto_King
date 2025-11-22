# PWA Icons

Dieses Verzeichnis enthält die Icons für die Progressive Web App.

## Erforderliche Icons

Erstellen Sie die folgenden Icons im `public` Verzeichnis:

- `favicon.ico` - Standard Favicon (64x64, 32x32, 24x24, 16x16)
- `logo192.png` - 192x192 Pixel Icon
- `logo512.png` - 512x512 Pixel Icon

## Icon Design Empfehlungen

- **Hintergrund**: Indigo/Purple Gradient (#4f46e5 bis #7c3aed)
- **Symbol**: Bot/Trading Symbol
- **Stil**: Modern, minimalistisch
- **Padding**: 20% Padding um das Symbol

## Online Tools zum Erstellen

1. **Favicon.io**: https://favicon.io/
2. **RealFaviconGenerator**: https://realfavicongenerator.net/
3. **PWA Asset Generator**: https://github.com/onderceylan/pwa-asset-generator

## Quick Generate (mit Node.js)

```bash
npx pwa-asset-generator logo.svg public/ --manifest public/manifest.json
```

Platzhalter-Icons können aus einem einfachen SVG erstellt werden.
