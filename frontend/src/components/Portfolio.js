import React, { useState, useEffect } from "react";
import axios from "axios";
import { TrendingUp, TrendingDown, Wallet, DollarSign, RefreshCw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API}/portfolio`);
      setPortfolio(response.data);
    } catch (err) {
      console.error("Error fetching portfolio:", err);
      setError("Fehler beim Laden des Portfolios");
      setPortfolio({
        success: false,
        assets: [],
        usdt_balance: 0,
        total_portfolio_value: 0,
        total_unrealized_pnl: 0
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="bg-slate-800/50 border-indigo-500/30">
        <CardHeader>
          <CardTitle className="text-slate-200 flex items-center">
            <Wallet className="w-5 h-5 mr-2 text-indigo-400" />
            Portfolio
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-slate-400">Lade Portfolio...</div>
        </CardContent>
      </Card>
    );
  }

  if (error || !portfolio || !portfolio.success) {
    return (
      <Card className="bg-slate-800/50 border-indigo-500/30">
        <CardHeader>
          <CardTitle className="text-slate-200 flex items-center justify-between">
            <div className="flex items-center">
              <Wallet className="w-5 h-5 mr-2 text-indigo-400" />
              Portfolio
            </div>
            <button
              onClick={fetchPortfolio}
              className="text-indigo-400 hover:text-indigo-300"
              aria-label="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-red-400">
            {error || portfolio?.error || "Fehler beim Laden des Portfolios"}
          </div>
        </CardContent>
      </Card>
    );
  }

  const { assets, usdt_balance, total_portfolio_value, total_unrealized_pnl } = portfolio;

  return (
    <Card className="bg-slate-800/50 border-indigo-500/30">
      <CardHeader>
        <CardTitle className="text-slate-200 flex items-center justify-between">
          <div className="flex items-center">
            <Wallet className="w-5 h-5 mr-2 text-indigo-400" />
            Portfolio Übersicht
          </div>
          <button
            onClick={fetchPortfolio}
            className="text-indigo-400 hover:text-indigo-300 transition-colors"
            aria-label="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-indigo-500/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Portfolio Wert</p>
                <p className="text-2xl font-bold text-slate-100">
                  ${total_portfolio_value.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <DollarSign className="w-8 h-8 text-indigo-400" />
            </div>
          </div>
          
          <div className="bg-slate-900/50 rounded-lg p-4 border border-indigo-500/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">USDT Balance</p>
                <p className="text-2xl font-bold text-slate-100">
                  ${usdt_balance.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <Wallet className="w-8 h-8 text-green-400" />
            </div>
          </div>
          
          <div className={`bg-slate-900/50 rounded-lg p-4 border ${
            total_unrealized_pnl >= 0 
              ? 'border-green-500/20' 
              : 'border-red-500/20'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Unrealized P&L</p>
                <div className="flex items-center space-x-2">
                  {total_unrealized_pnl >= 0 ? (
                    <TrendingUp className="w-5 h-5 text-green-400" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  )}
                  <p className={`text-2xl font-bold ${
                    total_unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    ${total_unrealized_pnl.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Assets Table */}
        {assets && assets.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-indigo-500/20 hover:bg-slate-700/30">
                  <TableHead className="text-slate-300">Asset</TableHead>
                  <TableHead className="text-slate-300 text-right">Menge</TableHead>
                  <TableHead className="text-slate-300 text-right">Aktueller Preis</TableHead>
                  <TableHead className="text-slate-300 text-right">Wert (USDT)</TableHead>
                  <TableHead className="text-slate-300 text-right">Entry Preis</TableHead>
                  <TableHead className="text-slate-300 text-right">Unrealized P&L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets.map((asset, index) => (
                  <TableRow 
                    key={asset.asset || index}
                    className="border-indigo-500/20 hover:bg-slate-700/30"
                  >
                    <TableCell className="font-medium text-slate-100">
                      <div>
                        <div className="font-bold">{asset.asset}</div>
                        {asset.bots && asset.bots.length > 0 && (
                          <div className="text-xs text-slate-500 mt-1">
                            {asset.bots.length} Bot{asset.bots.length > 1 ? 's' : ''}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-slate-300 font-mono">
                      {asset.quantity.toLocaleString('de-DE', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 8 
                      })}
                    </TableCell>
                    <TableCell className="text-right text-slate-300 font-mono">
                      ${asset.current_price.toLocaleString('de-DE', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 6 
                      })}
                    </TableCell>
                    <TableCell className="text-right text-slate-100 font-mono font-semibold">
                      ${asset.value_usdt.toLocaleString('de-DE', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                      })}
                    </TableCell>
                    <TableCell className="text-right text-slate-400 font-mono text-sm">
                      ${asset.entry_price.toLocaleString('de-DE', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 6 
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end space-x-1">
                        {asset.unrealized_pnl >= 0 ? (
                          <TrendingUp className="w-4 h-4 text-green-400" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-400" />
                        )}
                        <div>
                          <div className={`font-mono font-semibold ${
                            asset.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            ${asset.unrealized_pnl.toLocaleString('de-DE', { 
                              minimumFractionDigits: 2, 
                              maximumFractionDigits: 2 
                            })}
                          </div>
                          <div className={`text-xs font-mono ${
                            asset.unrealized_pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            ({asset.unrealized_pnl_percent >= 0 ? '+' : ''}{asset.unrealized_pnl_percent.toFixed(2)}%)
                          </div>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
            <p>Keine Assets im Portfolio</p>
            <p className="text-sm mt-2">Aktiviere einen Bot, um mit dem Trading zu beginnen.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default Portfolio;

