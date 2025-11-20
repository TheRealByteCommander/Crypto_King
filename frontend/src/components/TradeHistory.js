import React, { useState, useEffect } from "react";
import axios from "axios";
import { TrendingUp, TrendingDown, ExternalLink } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TradeHistory = () => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchTrades = async () => {
    try {
      const response = await axios.get(`${API}/trades`);
      setTrades(response.data);
    } catch (error) {
      console.error("Error fetching trades:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading trades...</div>
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">No trades executed yet</div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto" data-testid="trade-history">
      <table className="w-full">
        <thead>
          <tr className="border-b border-indigo-500/20">
            <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Time</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Symbol</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Side</th>
            <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Quantity</th>
            <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Amount (USDT)</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Status</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => (
            <tr 
              key={index}
              className="border-b border-indigo-500/10 hover:bg-slate-800/30 transition-colors"
              data-testid={`trade-row-${index}`}
            >
              <td className="py-3 px-4 text-sm text-slate-300 mono">
                {new Date(trade.timestamp).toLocaleString()}
              </td>
              <td className="py-3 px-4 text-sm text-slate-100 font-medium mono">
                {trade.symbol}
              </td>
              <td className="py-3 px-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  trade.side === "BUY" 
                    ? "bg-green-500/20 text-green-400" 
                    : "bg-red-500/20 text-red-400"
                }`}>
                  {trade.side === "BUY" ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                  {trade.side}
                </span>
              </td>
              <td className="py-3 px-4 text-sm text-slate-300 text-right mono">
                {parseFloat(trade.executed_qty).toFixed(6)}
              </td>
              <td className="py-3 px-4 text-sm text-slate-100 text-right mono font-medium">
                ${parseFloat(trade.quote_qty).toFixed(2)}
              </td>
              <td className="py-3 px-4">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/20 text-indigo-400">
                  {trade.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TradeHistory;