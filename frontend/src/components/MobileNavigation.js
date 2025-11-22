import React from 'react';
import { BarChart3, Activity, MessageSquare, Settings, Bot } from 'lucide-react';

const MobileNavigation = ({ activeTab, setActiveTab }) => {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-slate-900/95 backdrop-blur-xl border-t border-indigo-500/20 z-50 md:hidden mobile-safe-bottom">
      <div className="flex justify-around items-center h-16">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
            activeTab === 'overview'
              ? 'text-indigo-400'
              : 'text-slate-400'
          }`}
          aria-label="Performance"
        >
          <BarChart3 className="w-6 h-6 mb-1" />
          <span className="text-xs font-medium">Performance</span>
        </button>
        
        <button
          onClick={() => setActiveTab('trades')}
          className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
            activeTab === 'trades'
              ? 'text-indigo-400'
              : 'text-slate-400'
          }`}
          aria-label="Trades"
        >
          <Activity className="w-6 h-6 mb-1" />
          <span className="text-xs font-medium">Trades</span>
        </button>
        
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
            activeTab === 'chat'
              ? 'text-indigo-400'
              : 'text-slate-400'
          }`}
          aria-label="NexusChat"
        >
          <Bot className="w-6 h-6 mb-1" />
          <span className="text-xs font-medium">Chat</span>
        </button>
        
        <button
          onClick={() => setActiveTab('logs')}
          className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
            activeTab === 'logs'
              ? 'text-indigo-400'
              : 'text-slate-400'
          }`}
          aria-label="Logs"
        >
          <MessageSquare className="w-6 h-6 mb-1" />
          <span className="text-xs font-medium">Logs</span>
        </button>
        
        <button
          onClick={() => setActiveTab('learning')}
          className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
            activeTab === 'learning'
              ? 'text-indigo-400'
              : 'text-slate-400'
          }`}
          aria-label="Learning"
        >
          <Settings className="w-6 h-6 mb-1" />
          <span className="text-xs font-medium">Learning</span>
        </button>
      </div>
    </nav>
  );
};

export default MobileNavigation;
