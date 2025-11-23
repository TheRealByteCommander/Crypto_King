// Debug Script - Prüft ob Trading Mode Komponente gerendert wird
// Führe im Browser-Konsole aus: 

// 1. Prüfe ob BotControl Component gerendert wird
const botControl = document.querySelector('[data-testid="bot-control-panel"]');
console.log('BotControl gefunden:', botControl !== null);

// 2. Prüfe ob Trading Mode Select vorhanden ist
const tradingModeSelect = document.querySelector('[data-testid="trading-mode-select"]');
console.log('Trading Mode Select gefunden:', tradingModeSelect !== null);
if (tradingModeSelect) {
    console.log('Trading Mode Select:', tradingModeSelect);
    console.log('Parent:', tradingModeSelect.parentElement);
}

// 3. Prüfe alle Select-Komponenten
const allSelects = document.querySelectorAll('select, [role="combobox"]');
console.log('Alle Selects gefunden:', allSelects.length);
allSelects.forEach((sel, idx) => {
    console.log(`Select ${idx}:`, sel, sel.getAttribute('data-testid'), sel.textContent);
});

// 4. Prüfe Grid-Container
const gridContainer = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-5');
if (!gridContainer) {
    const grids = document.querySelectorAll('.grid');
    console.log('Alle Grids gefunden:', grids.length);
    grids.forEach((grid, idx) => {
        console.log(`Grid ${idx}:`, grid.className, grid.children.length);
    });
} else {
    console.log('Grid Container gefunden:', gridContainer);
    console.log('Grid Children:', gridContainer.children.length);
    Array.from(gridContainer.children).forEach((child, idx) => {
        console.log(`Grid Child ${idx}:`, child, child.textContent.substring(0, 50));
    });
}

// 5. Prüfe ob Trading Mode Label vorhanden ist
const labels = Array.from(document.querySelectorAll('label')).filter(l => 
    l.textContent.includes('Trading Mode') || l.textContent.includes('trading')
);
console.log('Trading Mode Labels:', labels.length);
labels.forEach((label, idx) => {
    console.log(`Label ${idx}:`, label.textContent, label.nextElementSibling);
});

