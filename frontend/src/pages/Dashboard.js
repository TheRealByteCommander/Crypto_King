import React, { useState, useEffect } from "react";
import axios from "axios";
import toast, { Toaster } from "react-hot-toast";
import {
  Activity,
  Bot,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PlayCircle,
  StopCircle,
  RefreshCw,
  BarChart3,
  MessageSquare,
  Settings
} from "lucide-react";
import BotControl from "../components/BotControl";
import PerformanceChart from "../components/PerformanceChart";
import TradeHistory from "../components/TradeHistory";
import AgentLogs from "../components/AgentLogs";
import StatsCard from "../components/StatsCard";
import AgentStatus from "../components/AgentStatus";
import LearningInsights from "../components/LearningInsights";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [botStatus, setBotStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [agents, setAgents] = useState(null);
  const [ws, setWs] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchAllData();
    connectWebSocket();
    
    const interval = setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        fetchAllData();
      }
    }, 10000);

    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, []);

  const connectWebSocket = () => {
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log("WebSocket connected");
      toast.success("Real-time updates connected");
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket message:", data);
      
      if (data.type === "status_update") {
        setBotStatus(data.data);
      } else if (data.type === "bot_started") {
        toast.success("Bot started successfully!");
        fetchAllData();
      } else if (data.type === "bot_stopped") {
        toast.info("Bot stopped");
        fetchAllData();
      }
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    websocket.onclose = () => {
      console.log("WebSocket disconnected");
      setTimeout(connectWebSocket, 5000);
    };

    setWs(websocket);
  };

  const fetchAllData = async () => {
    try {
      const [statusRes, statsRes, agentsRes] = await Promise.all([
        axios.get(`${API}/bot/status`),
        axios.get(`${API}/stats`),
        axios.get(`${API}/agents`)
      ]);
      
      setBotStatus(statusRes.data);
      setStats(statsRes.data);
      setAgents(agentsRes.data.agents);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const handleRefresh = () => {
    toast.promise(
      fetchAllData(),
      {
        loading: "Refreshing...",
        success: "Data refreshed",
        error: "Failed to refresh"
      }
    );
  };

  return (
    <div className="min-h-screen relative">
      <Toaster position="top-right" />
      <div className="cyber-grid"></div>
      
      <div className="relative z-10">
        {/* Header */}
        <header className="bg-slate-900/50 backdrop-blur-xl border-b border-indigo-500/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold glow-cyan">Project CypherTrade</h1>
                  <p className="text-sm text-slate-400 mt-1">AI-Powered Crypto Trading System</p>
                </div>
              </div>
              
              <button
                onClick={handleRefresh}
                className="cyber-button flex items-center space-x-2"
                data-testid="refresh-button"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatsCard
              title="Profit/Loss"
              value={stats ? `$${stats.profit_loss_usdt}` : "$0.00"}
              icon={stats && stats.profit_loss_usdt >= 0 ? TrendingUp : TrendingDown}
              color={stats && stats.profit_loss_usdt >= 0 ? "green" : "red"}
              testId="profit-loss-card"
            />
            <StatsCard
              title="Total Trades"
              value={stats ? stats.total_trades : 0}
              icon={Activity}
              color="blue"
              testId="total-trades-card"
            />
            <StatsCard
              title="Total Bought"
              value={stats ? `$${stats.total_bought_usdt}` : "$0.00"}
              icon={DollarSign}
              color="cyan"
              testId="total-bought-card"
            />
            <StatsCard
              title="Total Sold"
              value={stats ? `$${stats.total_sold_usdt}` : "$0.00"}
              icon={DollarSign}
              color="purple"
              testId="total-sold-card"
            />
          </div>

          {/* Agent Status */}
          {agents && (
            <div className="mb-8">
              <AgentStatus agents={agents} />
            </div>
          )}

          {/* Bot Control */}
          <div className="mb-8">
            <BotControl 
              botStatus={botStatus} 
              onStatusChange={fetchAllData}
            />
          </div>

          {/* Tabs */}
          <div className="cyber-card p-6">
            <div className="flex space-x-4 border-b border-indigo-500/20 mb-6 overflow-x-auto">
              <button
                onClick={() => setActiveTab("overview")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap ${
                  activeTab === "overview"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="overview-tab"
              >
                <BarChart3 className="w-4 h-4 inline mr-2" />
                Performance
              </button>
              <button
                onClick={() => setActiveTab("trades")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap ${
                  activeTab === "trades"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="trades-tab"
              >
                <Activity className="w-4 h-4 inline mr-2" />
                Trade History
              </button>
              <button
                onClick={() => setActiveTab("logs")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap ${
                  activeTab === "logs"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="logs-tab"
              >
                <MessageSquare className="w-4 h-4 inline mr-2" />
                Agent Logs
              </button>
              <button
                onClick={() => setActiveTab("learning")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap ${
                  activeTab === "learning"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="learning-tab"
              >
                <Settings className="w-4 h-4 inline mr-2" />
                AI Learning
              </button>
            </div>

            {activeTab === "overview" && <PerformanceChart />}
            {activeTab === "trades" && <TradeHistory />}
            {activeTab === "logs" && <AgentLogs />}
            {activeTab === "learning" && <LearningInsights />}
          </div>
        </main>

        {/* Footer */}
        <footer className="mt-16 py-8 border-t border-indigo-500/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center text-slate-400 text-sm">
              <p>Project CypherTrade - Powered by Autogen AI Agents</p>
              <p className="mt-2">⚠️ Always use with caution. Cryptocurrency trading involves risk.</p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Dashboard;
