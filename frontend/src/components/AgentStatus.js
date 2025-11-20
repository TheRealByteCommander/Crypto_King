import React from "react";
import { Bot, Brain, Zap } from "lucide-react";

const AgentStatus = ({ agents }) => {
  const agentIcons = {
    nexuschat: Bot,
    cyphermind: Brain,
    cyphertrade: Zap
  };

  const agentColors = {
    nexuschat: "cyan",
    cyphermind: "purple",
    cyphertrade: "green"
  };

  return (
    <div className="cyber-card p-6" data-testid="agent-status-panel">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">AI Agents</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(agents).map(([key, agent]) => {
          const Icon = agentIcons[key] || Bot;
          const color = agentColors[key] || "blue";
          
          return (
            <div
              key={key}
              className="bg-slate-800/30 rounded-lg p-4 border border-indigo-500/20 hover:border-indigo-500/40 transition-all"
              data-testid={`agent-${key}`}
            >
              <div className="flex items-start space-x-3">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br from-${color}-600/30 to-${color}-700/30 flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 text-${color}-400`} />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-slate-100 mb-1">{agent.name}</h3>
                  <p className="text-xs text-slate-400 mb-2">{agent.role}</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Provider:</span>
                      <span className="text-slate-300 font-medium mono">{agent.provider}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Model:</span>
                      <span className="text-slate-300 font-medium mono">{agent.model}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AgentStatus;