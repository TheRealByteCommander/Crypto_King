#!/bin/bash
# Behebt Git Merge-Konflikte beim Update

echo "=== Git Merge-Konflikt beheben ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Zeige Status
echo "[INFO] Aktueller Git-Status:"
git status

echo ""
echo "[INFO] Stashe lokale Änderungen..."
git stash

echo ""
echo "[INFO] Hole neueste Änderungen..."
git pull

echo ""
echo "[INFO] Neuester Commit:"
git log -1 --oneline

echo ""
echo "=== Fertig ==="
echo "Lokale Änderungen wurden gestasht und neueste Updates geholt."
echo "Falls du die gestashten Änderungen brauchst: git stash pop"

