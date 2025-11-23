import React, { useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { PlayCircle, StopCircle, Settings, Plus, X } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const BotControl = ({ botsStatus = {}, onStatusChange }) => {
  const [strategy, setStrategy] = useState("ma_crossover");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [amount, setAmount] = useState("100");
  const [loading, setLoading] = useState(false);
  const [strategies, setStrategies] = useState({
    "ma_crossover": "Moving Average Crossover (SMA 20/50)",
    "rsi": "RSI - Relative Strength Index",
    "macd": "MACD - Moving Average Convergence Divergence",
    "bollinger_bands": "Bollinger Bands - Volatility Strategy",
    "combined": "Combined Strategy (MA + RSI + MACD)"
  });

  // Convert botsStatus to array for easier rendering
  const botsArray = Object.entries(botsStatus || {}).map(([botId, status]) => ({
    botId,
    ...status
  }));

  const hasRunningBots = botsArray.some(bot => bot.is_running);
  const totalBots = botsArray.length;
  const runningBotsCount = botsArray.filter(bot => bot.is_running).length;

  React.useEffect(() => {
    // Fetch available strategies
    axios.get(`${API}/strategies`)
      .then(response => {
        if (response.data.strategies) {
          setStrategies(response.data.strategies);
        }
      })
      .catch(error => {
        console.error("Error fetching strategies:", error);
      });
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/bot/start`, {
        strategy,
        symbol,
        amount: parseFloat(amount)
      });
      
      if (response.data.success) {
        toast.success(response.data.message || "Bot started successfully!");
        onStatusChange();
        // Reset form
        setSymbol("BTCUSDT");
        setAmount("100");
      } else {
        toast.error(response.data.message || "Failed to start bot");
      }
    } catch (error) {
      toast.error("Failed to start bot: " + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async (botId = null) => {
    setLoading(true);
    try {
      const url = botId ? `${API}/bot/stop?bot_id=${encodeURIComponent(botId)}` : `${API}/bot/stop`;
      const response = await axios.post(url);
      
      if (response.data.success) {
        toast.success(response.data.message || "Bot stopped successfully!");
        onStatusChange();
      } else {
        toast.error(response.data.message || "Failed to stop bot");
      }
    } catch (error) {
      toast.error("Failed to stop bot: " + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cyber-card p-6" data-testid="bot-control-panel">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Settings className="w-6 h-6 text-indigo-400" />
          <h2 className="text-xl font-semibold text-slate-100">Bot Control</h2>
          {totalBots > 0 && (
            <span className="px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded text-sm">
              {runningBotsCount}/{totalBots} Running
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <span className={`status-indicator ${hasRunningBots ? 'active' : 'inactive'}`}></span>
          <span className="text-sm text-slate-400">
            {hasRunningBots ? "Active" : "Inactive"}
          </span>
        </div>
      </div>

      {/* Running Bots List */}
      {botsArray.length > 0 && (
        <div className="space-y-3 mb-6">
          <h3 className="text-md font-semibold text-slate-300 mb-3">Running Bots ({runningBotsCount})</h3>
          {botsArray.map((bot) => {
            if (!bot.is_running) return null;
            return (
              <div
                key={bot.botId}
                className="bg-slate-800/30 rounded-lg p-4 border border-indigo-500/20"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="status-indicator active"></span>
                      <span className="text-xs text-slate-400 font-mono">
                        ID: {bot.botId.substring(0, 8)}...
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-slate-400 mb-1">Strategy</p>
                        <p className="text-slate-100 font-medium mono">
                          {bot.config?.strategy || "N/A"}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-400 mb-1">Symbol</p>
                        <p className="text-slate-100 font-medium mono">
                          {bot.config?.symbol || "N/A"}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-400 mb-1">Amount</p>
                        <p className="text-slate-100 font-medium mono">
                          ${bot.config?.amount || "0"}
                        </p>
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => handleStop(bot.botId)}
                    disabled={loading}
                    className="ml-4 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white"
                    size="sm"
                  >
                    <StopCircle className="w-4 h-4 mr-1" />
                    Stop
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Bot Form */}
      <div className="border-t border-indigo-500/20 pt-6">
        <div className="flex items-center space-x-2 mb-4">
          <Plus className="w-5 h-5 text-indigo-400" />
          <h3 className="text-md font-semibold text-slate-300">Start New Bot</h3>
        </div>
        
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="strategy" className="text-slate-300 mb-2 block">Strategy</Label>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger className="bg-slate-800/50 border-indigo-500/30" data-testid="strategy-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(strategies).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="symbol" className="text-slate-300 mb-2 block">Symbol</Label>
              <Input
                id="symbol"
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="bg-slate-800/50 border-indigo-500/30 text-slate-100"
                placeholder="BTCUSDT"
                data-testid="symbol-input"
              />
            </div>

            <div>
              <Label htmlFor="amount" className="text-slate-300 mb-2 block">Amount (USDT)</Label>
              <Input
                id="amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="bg-slate-800/50 border-indigo-500/30 text-slate-100"
                placeholder="100"
                data-testid="amount-input"
              />
            </div>
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={handleStart}
              disabled={loading}
              className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium py-6 text-lg"
              data-testid="start-bot-button"
            >
              <PlayCircle className="w-5 h-5 mr-2" />
              {loading ? "Starting..." : "Start New Bot"}
            </Button>
            {hasRunningBots && (
              <Button
                onClick={() => handleStop()}
                disabled={loading}
                className="bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white font-medium py-6 px-6"
                data-testid="stop-all-bots-button"
              >
                <StopCircle className="w-5 h-5 mr-2" />
                Stop All
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BotControl;
