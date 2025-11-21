import React, { useState, useEffect } from "react";
import axios from "axios";
import { Brain, TrendingUp, AlertCircle, BookOpen } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const LearningInsights = () => {
  const [insights, setInsights] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState("CypherMind");

  useEffect(() => {
    fetchInsights();
    fetchLessons();
    
    const interval = setInterval(() => {
      fetchInsights();
      fetchLessons();
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedAgent]);

  const fetchInsights = async () => {
    try {
      const response = await axios.get(`${API}/memory/insights/collective`);
      setInsights(response.data);
    } catch (error) {
      console.error("Error fetching insights:", error);
    }
  };

  const fetchLessons = async () => {
    try {
      const response = await axios.get(`${API}/memory/${selectedAgent}/lessons`);
      setLessons(response.data.lessons || []);
    } catch (error) {
      console.error("Error fetching lessons:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading learning insights...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="learning-insights">
      {/* Agent Selector */}
      <div className="flex space-x-2">
        {["NexusChat", "CypherMind", "CypherTrade"].map((agent) => (
          <button
            key={agent}
            onClick={() => setSelectedAgent(agent)}
            className={`px-4 py-2 rounded-lg transition-all ${
              selectedAgent === agent
                ? "bg-indigo-600 text-white"
                : "bg-slate-800/50 text-slate-400 hover:bg-slate-800"
            }`}
            data-testid={`agent-${agent.toLowerCase()}-btn`}
          >
            {agent}
          </button>
        ))}
      </div>

      {/* Agent Memory Stats */}
      {insights && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(insights).map(([agentName, data]) => (
            <div
              key={agentName}
              className="cyber-card p-4 bg-gradient-to-br from-slate-900/80 to-slate-800/50"
              data-testid={`memory-stats-${agentName.toLowerCase()}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-100">{agentName}</h3>
                <Brain className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Memories:</span>
                  <span className="text-slate-100 font-mono">
                    {data.total_memories || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Recent Lessons:</span>
                  <span className="text-slate-100 font-mono">
                    {data.recent_lessons?.length || 0}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Lessons Learned */}
      <div className="cyber-card p-6">
        <div className="flex items-center space-x-3 mb-4">
          <BookOpen className="w-6 h-6 text-purple-400" />
          <h3 className="text-xl font-semibold text-slate-100">
            Recent Lessons from {selectedAgent}
          </h3>
        </div>

        {lessons.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No lessons learned yet. Start trading to accumulate experience!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {lessons.map((lesson, index) => (
              <div
                key={index}
                className="bg-slate-800/30 rounded-lg p-4 border border-indigo-500/20 hover:border-indigo-500/40 transition-all"
                data-testid={`lesson-${index}`}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <span className="text-purple-400 text-xs font-bold">
                        {index + 1}
                      </span>
                    </div>
                  </div>
                  <p className="text-slate-200 leading-relaxed flex-1">
                    {lesson}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Learning Progress Indicator */}
      <div className="cyber-card p-6 bg-gradient-to-r from-purple-900/20 to-indigo-900/20 border-purple-500/30">
        <div className="flex items-center space-x-3 mb-3">
          <TrendingUp className="w-6 h-6 text-purple-400" />
          <h3 className="text-lg font-semibold text-slate-100">
            AI Learning Status
          </h3>
        </div>
        <p className="text-slate-300 text-sm mb-4">
          The agents continuously learn from every trade, improving their decision-making
          over time. More trades = Better predictions.
        </p>
        <div className="bg-slate-900/50 rounded-lg p-3 border border-purple-500/20">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Learning Mode:</span>
            <span className="text-green-400 font-semibold flex items-center">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
              Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningInsights;
