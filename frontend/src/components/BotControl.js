import React, { useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { PlayCircle, StopCircle, Settings } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const BotControl = ({ botStatus, onStatusChange }) => {
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

  const isRunning = botStatus?.is_running || false;

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
        toast.success(response.data.message);
        onStatusChange();
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error("Failed to start bot: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/bot/stop`);
      
      if (response.data.success) {
        toast.success(response.data.message);
        onStatusChange();
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error("Failed to stop bot: " + error.message);
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
        </div>
        <div className="flex items-center space-x-2">
          <span className={`status-indicator ${isRunning ? 'active' : 'inactive'}`}></span>
          <span className="text-sm text-slate-400">
            {isRunning ? "Running" : "Stopped"}
          </span>
        </div>
      </div>

      {!isRunning ? (
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

          <Button
            onClick={handleStart}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium py-6 text-lg"
            data-testid="start-bot-button"
          >
            <PlayCircle className="w-5 h-5 mr-2" />
            {loading ? "Starting..." : "Start Trading Bot"}
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-slate-800/30 rounded-lg p-4 border border-indigo-500/20">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-slate-400 mb-1">Strategy</p>
                <p className="text-slate-100 font-medium mono">
                  {botStatus?.config?.strategy || "N/A"}
                </p>
              </div>
              <div>
                <p className="text-slate-400 mb-1">Symbol</p>
                <p className="text-slate-100 font-medium mono">
                  {botStatus?.config?.symbol || "N/A"}
                </p>
              </div>
              <div>
                <p className="text-slate-400 mb-1">Amount</p>
                <p className="text-slate-100 font-medium mono">
                  ${botStatus?.config?.amount || "0"}
                </p>
              </div>
              {botStatus?.balances && (
                <>
                  <div>
                    <p className="text-slate-400 mb-1">USDT Balance</p>
                    <p className="text-green-400 font-medium mono">
                      ${botStatus.balances.USDT?.toFixed(2) || "0.00"}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 mb-1">
                      {Object.keys(botStatus.balances).find(k => k !== 'USDT') || 'Asset'}
                    </p>
                    <p className="text-cyan-400 font-medium mono">
                      {Object.entries(botStatus.balances)
                        .filter(([k]) => k !== 'USDT')
                        .map(([_, v]) => v?.toFixed(6))[0] || "0.000000"}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          <Button
            onClick={handleStop}
            disabled={loading}
            className="w-full bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white font-medium py-6 text-lg"
            data-testid="stop-bot-button"
          >
            <StopCircle className="w-5 h-5 mr-2" />
            {loading ? "Stopping..." : "Stop Trading Bot"}
          </Button>
        </div>
      )}
    </div>
  );
};

export default BotControl;