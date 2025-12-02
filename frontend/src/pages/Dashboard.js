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
  Settings,
  Wallet
} from "lucide-react";
import BotControl from "../components/BotControl";
import PerformanceChart from "../components/PerformanceChart";
import TradeHistory from "../components/TradeHistory";
import AgentLogs from "../components/AgentLogs";
import StatsCard from "../components/StatsCard";
import AgentStatus from "../components/AgentStatus";
import LearningInsights from "../components/LearningInsights";
import MobileNavigation from "../components/MobileNavigation";
import NexusChat from "../components/NexusChat";
import VolatileAssets from "../components/VolatileAssets";
import Portfolio from "../components/Portfolio";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [botsStatus, setBotsStatus] = useState({}); // Dictionary: { bot_id: status }
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
    if (!BACKEND_URL) {
      console.error("BACKEND_URL is not defined");
      return;
    }
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws`;
    const websocket = new WebSocket(wsUrl);

    // Throttle status updates to reduce performance warnings
    let lastStatusUpdate = 0;
    const STATUS_UPDATE_THROTTLE_MS = 1000; // Update at most once per second

    websocket.onopen = () => {
      console.log("WebSocket connected");
      toast.success("Real-time updates connected");
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Only log non-status messages to reduce console spam
      if (data.type !== "status_update") {
        console.log("WebSocket message:", data);
      }
      
      if (data.type === "status_update") {
        // Throttle status updates to reduce performance warnings
        const now = Date.now();
        if (now - lastStatusUpdate >= STATUS_UPDATE_THROTTLE_MS) {
          // Handle both single bot status and all bots status
          if (data.bot_id) {
            // Single bot update
            setBotsStatus(prev => ({
              ...prev,
              [data.bot_id]: data.data
            }));
          } else if (data.data && typeof data.data === 'object' && !data.data.bot_id) {
            // All bots status object
            setBotsStatus(data.data);
          } else {
            // Single bot status (backward compatibility)
            setBotsStatus(prev => ({
              ...prev,
              [data.data?.bot_id || 'default']: data.data
            }));
          }
          lastStatusUpdate = now;
        }
      } else if (data.type === "bot_started") {
        // Only show success if it was actually successful
        if (data.success !== false) {
          const botId = data.bot_id || data.data?.bot_id || 'unknown';
          toast.success(`${data.message || "Bot started successfully!"} (ID: ${botId.substring(0, 8)}...)`);
        }
        fetchAllData();
      } else if (data.type === "bot_start_failed") {
        // Show error message when bot start failed
        const botId = data.bot_id || 'unknown';
        toast.error(`${data.message || "Failed to start bot"} (ID: ${botId.substring(0, 8)}...)`);
        fetchAllData();
      } else if (data.type === "bot_stopped") {
        const botId = data.bot_id || data.data?.bot_id || 'unknown';
        toast.success(`Bot stopped (ID: ${botId.substring(0, 8)}...)`);
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
        axios.get(`${API}/bot/status`), // Returns all bots status
        axios.get(`${API}/stats`),
        axios.get(`${API}/agents`)
      ]);
      
      // Handle both single bot response (backward compatibility) and multiple bots
      if (statusRes.data && typeof statusRes.data === 'object') {
        if (statusRes.data.bot_id) {
          // Single bot response (backward compatibility)
          setBotsStatus({ [statusRes.data.bot_id]: statusRes.data });
        } else {
          // Multiple bots response
          setBotsStatus(statusRes.data);
        }
      }
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
      <Toaster 
        position="top-right" 
        toastOptions={{
          className: 'mobile-toast',
          duration: 3000,
        }}
        containerStyle={{
          top: window.innerWidth < 640 ? 80 : 20,
        }}
      />
      <div className="cyber-grid"></div>
      
      <div className="relative z-10">
        {/* Header */}
        <header className="bg-slate-900/50 backdrop-blur-xl border-b border-indigo-500/20 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 md:py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 md:space-x-4 flex-1 min-w-0">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 md:w-7 md:h-7 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <h1 className="text-lg md:text-3xl font-bold glow-cyan truncate">Project CypherTrade</h1>
                  <p className="text-xs md:text-sm text-slate-400 mt-0.5 hidden sm:block">AI-Powered Crypto Trading System</p>
                </div>
              </div>
              
              <button
                onClick={handleRefresh}
                className="cyber-button flex items-center space-x-1 md:space-x-2 px-3 md:px-4 py-2 touch-manipulation"
                data-testid="refresh-button"
                aria-label="Refresh"
              >
                <RefreshCw className="w-4 h-4 md:w-5 md:h-5" />
                <span className="hidden md:inline">Refresh</span>
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 md:py-8 pb-20 md:pb-8">
          {/* Stats Overview (letzte 24h) */}
          <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6 mb-4 md:mb-8">
            <StatsCard
              title="Profit/Loss (24h)"
              value={stats ? `$${stats.profit_loss_usdt_24h ?? stats.profit_loss_usdt}` : "$0.00"}
              icon={
                stats && (stats.profit_loss_usdt_24h ?? stats.profit_loss_usdt) >= 0
                  ? TrendingUp
                  : TrendingDown
              }
              color={
                stats && (stats.profit_loss_usdt_24h ?? stats.profit_loss_usdt) >= 0
                  ? "green"
                  : "red"
              }
              testId="profit-loss-card"
            />
            <StatsCard
              title="Trades (24h)"
              value={stats ? (stats.total_trades_24h ?? stats.total_trades) : 0}
              icon={Activity}
              color="blue"
              testId="total-trades-card"
            />
            <StatsCard
              title="Bought (24h)"
              value={
                stats
                  ? `$${stats.total_bought_usdt_24h ?? stats.total_bought_usdt}`
                  : "$0.00"
              }
              icon={DollarSign}
              color="cyan"
              testId="total-bought-card"
            />
            <StatsCard
              title="Sold (24h)"
              value={
                stats
                  ? `$${stats.total_sold_usdt_24h ?? stats.total_sold_usdt}`
                  : "$0.00"
              }
              icon={DollarSign}
              color="purple"
              testId="total-sold-card"
            />
          </div>

          {/* Agent Status */}
          {agents && (
            <div className="mb-4 md:mb-8">
              <AgentStatus agents={agents} />
            </div>
          )}

          {/* Bot Control - Multi-Bot Support */}
          <div className="mb-4 md:mb-8">
            <BotControl 
              botsStatus={botsStatus} 
              onStatusChange={fetchAllData}
            />
          </div>

          {/* Tabs - Desktop only */}
          <div className="cyber-card p-4 md:p-6">
            <div className="hidden md:flex space-x-4 border-b border-indigo-500/20 mb-6 overflow-x-auto">
              <button
                onClick={() => setActiveTab("overview")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
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
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
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
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
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
                onClick={() => setActiveTab("chat")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
                  activeTab === "chat"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="chat-tab"
              >
                <MessageSquare className="w-4 h-4 inline mr-2" />
                NexusChat
              </button>
              <button
                onClick={() => setActiveTab("portfolio")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
                  activeTab === "portfolio"
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-slate-400 hover:text-slate-300"
                }`}
                data-testid="portfolio-tab"
              >
                <Wallet className="w-4 h-4 inline mr-2" />
                Portfolio
              </button>
              <button
                onClick={() => setActiveTab("learning")}
                className={`pb-4 px-4 font-medium transition-colors whitespace-nowrap touch-manipulation ${
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

            {activeTab === "overview" && (
              <>
                <div className="mb-6">
                  <VolatileAssets />
                </div>
                <PerformanceChart />
              </>
            )}
            {activeTab === "trades" && <TradeHistory />}
            {activeTab === "logs" && <AgentLogs />}
            {activeTab === "portfolio" && <Portfolio />}
            {activeTab === "chat" && (
              <div className="h-[600px]">
                <NexusChat />
              </div>
            )}
            {activeTab === "learning" && <LearningInsights />}
          </div>
        </main>

        {/* Mobile Navigation */}
        <MobileNavigation activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Footer */}
        <footer className="hidden md:block mt-16 py-8 border-t border-indigo-500/20">
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
