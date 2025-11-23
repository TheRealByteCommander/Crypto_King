import React, { useState, useEffect } from "react";
import axios from "axios";
import { Bot, Brain, Zap, Info, AlertTriangle, Activity } from "lucide-react";
import { formatBerlinTimeOnly } from "../utils/dateUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const AgentLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`${API}/logs`);
      setLogs(response.data);
    } catch (error) {
      console.error("Error fetching logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const getAgentIcon = (agentName) => {
    const icons = {
      "NexusChat": Bot,
      "CypherMind": Brain,
      "CypherTrade": Zap
    };
    return icons[agentName] || Info;
  };

  const getMessageTypeColor = (type) => {
    const colors = {
      "info": "text-blue-400 bg-blue-500/10",
      "analysis": "text-purple-400 bg-purple-500/10",
      "trade": "text-green-400 bg-green-500/10",
      "error": "text-red-400 bg-red-500/10"
    };
    return colors[type] || colors.info;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading logs...</div>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">No agent logs available yet</div>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto" data-testid="agent-logs">
      {logs.map((log, index) => {
        const Icon = getAgentIcon(log.agent_name);
        
        return (
          <div
            key={index}
            className={`p-4 rounded-lg border border-indigo-500/20 ${getMessageTypeColor(log.message_type)}`}
            data-testid={`log-entry-${index}`}
          >
            <div className="flex items-start space-x-3">
              <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-sm">{log.agent_name}</span>
                  <span className="text-xs text-slate-500 mono">
                    {formatBerlinTimeOnly(log.timestamp)}
                  </span>
                </div>
                <p className="text-sm leading-relaxed">{log.message}</p>
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium">
                  {log.message_type}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AgentLogs;