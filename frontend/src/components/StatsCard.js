import React from "react";

const StatsCard = ({ title, value, icon: Icon, color, testId }) => {
  const colorClasses = {
    green: "from-green-600/20 to-emerald-600/20 border-green-500/30 text-green-400",
    red: "from-red-600/20 to-rose-600/20 border-red-500/30 text-red-400",
    blue: "from-blue-600/20 to-indigo-600/20 border-blue-500/30 text-blue-400",
    cyan: "from-cyan-600/20 to-teal-600/20 border-cyan-500/30 text-cyan-400",
    purple: "from-purple-600/20 to-violet-600/20 border-purple-500/30 text-purple-400",
    indigo: "from-indigo-600/20 to-purple-600/20 border-indigo-500/30 text-indigo-400"
  };

  return (
    <div 
      className={`cyber-card p-4 md:p-6 bg-gradient-to-br ${colorClasses[color]} touch-manipulation`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-2 md:mb-3">
        <h3 className="text-xs md:text-sm font-medium text-slate-400 truncate pr-2">{title}</h3>
        <Icon className={`w-4 h-4 md:w-5 md:h-5 flex-shrink-0 ${colorClasses[color].split(' ')[3]}`} />
      </div>
      <p className={`text-xl md:text-2xl font-bold mono ${colorClasses[color].split(' ')[3]} break-words`}>
        {value}
      </p>
    </div>
  );
};

export default StatsCard;