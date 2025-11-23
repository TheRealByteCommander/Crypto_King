#!/bin/bash
# Backend Debug Script - Prüft Backend-Status und Logs

echo "=== Backend Debug ==="
echo ""

# 1. Prüfe Backend Status
echo "[INFO] Prüfe Backend Status..."
sudo supervisorctl status cyphertrade-backend

echo ""
echo "[INFO] Backend Error Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-backend-error.log 2>/dev/null || echo "[WARNING] Error-Log-Datei nicht gefunden"

echo ""
echo "[INFO] Backend Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-backend.log 2>/dev/null || echo "[WARNING] Log-Datei nicht gefunden"

echo ""
echo "[INFO] Teste Backend API Endpoints..."
echo ""

# Test /api/stats
echo "[TEST] GET /api/stats"
curl -s http://localhost:8001/api/stats | head -20 || echo "[ERROR] /api/stats nicht erreichbar"

echo ""
echo "[TEST] GET /api/market/volatile"
curl -s http://localhost:8001/api/market/volatile | head -20 || echo "[ERROR] /api/market/volatile nicht erreichbar"

echo ""
echo "[TEST] GET /api/trades"
curl -s http://localhost:8001/api/trades | head -20 || echo "[ERROR] /api/trades nicht erreichbar"

echo ""
echo "=== Fertig ==="

