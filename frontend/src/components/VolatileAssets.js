import React, { useState, useEffect } from "react";
import axios from "axios";
import { TrendingUp, TrendingDown, RefreshCw, Zap } from "lucide-react";
import { formatBerlinTimeOnly } from "../utils/dateUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const VolatileAssets = () => {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchVolatileAssets = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/market/volatile?limit=20`);
      if (response.data.success) {
        setAssets(response.data.assets || []);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error("Error fetching volatile assets:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVolatileAssets();
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchVolatileAssets, 60000);
    return () => clearInterval(interval);
  }, []);

  const formatPrice = (price) => {
    if (price >= 1) {
      return price.toFixed(2);
    } else if (price >= 0.01) {
      return price.toFixed(4);
    } else {
      return price.toFixed(8);
    }
  };

  const formatVolume = (volume) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(2)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(2)}K`;
    }
    return volume.toFixed(2);
  };

  const getAssetType = (symbol) => {
    const memeCoins = ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME'];
    const baseAsset = symbol.replace(/USDT|BUSD|BTC|ETH|BNB$/i, '');
    
    if (memeCoins.some(meme => baseAsset.includes(meme))) {
      return { type: 'meme', label: 'Meme', color: 'text-pink-400' };
    }
    if (symbol.includes('BTC') && !symbol.startsWith('BTC')) {
      return { type: 'btc', label: 'BTC Pair', color: 'text-orange-400' };
    }
    if (symbol.includes('ETH') && !symbol.startsWith('ETH')) {
      return { type: 'eth', label: 'ETH Pair', color: 'text-blue-400' };
    }
    return { type: 'coin', label: 'Coin', color: 'text-cyan-400' };
  };

  if (loading && assets.length === 0) {
    return (
      <div className="cyber-card p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Zap className="w-6 h-6 text-yellow-400" />
          <h2 className="text-2xl font-bold text-white">Volatilste Assets (24 Stunden)</h2>
        </div>
        <button
          onClick={fetchVolatileAssets}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Aktualisieren
        </button>
      </div>

      {lastUpdate && (
        <p className="text-sm text-slate-400 mb-4">
          Letzte Aktualisierung: {formatBerlinTimeOnly(lastUpdate)}
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-3 px-4 text-slate-400 font-semibold">Symbol</th>
              <th className="text-left py-3 px-4 text-slate-400 font-semibold">Typ</th>
              <th className="text-right py-3 px-4 text-slate-400 font-semibold">Preis</th>
              <th className="text-right py-3 px-4 text-slate-400 font-semibold">24h Änderung</th>
              <th className="text-right py-3 px-4 text-slate-400 font-semibold">Durchschn. Volumen</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset, index) => {
              const assetType = getAssetType(asset.symbol);
              const isPositive = asset.priceChangePercent >= 0;
              
              return (
                <tr
                  key={asset.symbol}
                  className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className="font-mono text-white font-semibold">{asset.symbol}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-1 rounded ${assetType.color} bg-slate-800/50`}>
                      {assetType.label}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-white font-mono">{formatPrice(asset.price)}</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {isPositive ? (
                        <TrendingUp className="w-4 h-4 text-green-400" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-400" />
                      )}
                      <span
                        className={`font-semibold font-mono ${
                          isPositive ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {isPositive ? '+' : ''}{asset.priceChangePercent.toFixed(2)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-slate-300 font-mono text-sm">
                      {formatVolume(asset.volume)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {assets.length === 0 && !loading && (
        <div className="text-center py-12 text-slate-400">
          Keine volatilen Assets gefunden
        </div>
      )}
    </div>
  );
};

export default VolatileAssets;

