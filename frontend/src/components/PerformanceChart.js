import React, { useState, useEffect } from "react";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { formatBerlinTimeOnly } from "../utils/dateUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const PerformanceChart = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await axios.get(`${API}/trades`);
      const trades = response.data;

      // Process trades for chart
      let runningBalance = 0;
      const chartData = trades.reverse().map((trade, index) => {
        const amount = parseFloat(trade.quote_qty || 0);
        if (trade.side === "SELL") {
          runningBalance += amount;
        } else if (trade.side === "BUY") {
          runningBalance -= amount;
        }

        return {
          name: `Trade ${index + 1}`,
          timestamp: formatBerlinTimeOnly(trade.timestamp),
          balance: runningBalance,
          type: trade.side
        };
      });

      setData(chartData);
    } catch (error) {
      console.error("Error fetching chart data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading chart data...</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">No trading data available yet</div>
      </div>
    );
  }

  return (
    <div className="w-full" style={{ minHeight: '320px', height: '320px' }} data-testid="performance-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(99, 102, 241, 0.1)" />
          <XAxis 
            dataKey="timestamp" 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <Tooltip 
            contentStyle={{
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '8px',
              color: '#e0e7ff'
            }}
          />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="balance" 
            stroke="#22d3ee" 
            strokeWidth={2}
            dot={{ fill: '#22d3ee', r: 4 }}
            activeDot={{ r: 6 }}
            name="P&L (USDT)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;