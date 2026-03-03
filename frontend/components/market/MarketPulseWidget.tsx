"""
Market Pulse Widget Component.

Displays Baltic indices and market data for the maritime industry.
"""
"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, RefreshCw, DollarSign, Anchor } from "lucide-react";

interface MarketIndex {
  name: string;
  value: number;
  change: number;
  changePercent: number;
  unit: string;
}

interface MarketData {
  baltic_dirty: MarketIndex;
  baltic_clean: MarketIndex;
  baltic_lr2: MarketIndex;
  baltic_lr1: MarketIndex;
  baltic_mr: MarketIndex;
  spot_rates: Record<string, number>;
  last_updated: string;
}

export function MarketPulseWidget() {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMarketData();
  }, []);

  async function fetchMarketData() {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch from backend - in production this would be a real market data API
      const res = await fetch("http://localhost:8000/api/v1/market/indices");
      
      if (res.ok) {
        const data = await res.json();
        setMarketData(data);
      } else {
        // Use mock data if API not available
        setMarketData(getMockMarketData());
      }
    } catch (err) {
      // Use mock data on error
      setMarketData(getMockMarketData());
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !marketData) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
        <div className="text-center text-gray-500 py-4">
          Unable to load market data
        </div>
      </div>
    );
  }

  const indices = [
    { ...marketData.baltic_dirty, label: "BDI (Dirty)" },
    { ...marketData.baltic_clean, label: "BCI (Clean)" },
    { ...marketData.baltic_lr2, label: "LR2" },
    { ...marketData.baltic_lr1, label: "LR1" },
    { ...marketData.baltic_mr, label: "MR" },
  ];

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900">Market Pulse</h3>
        </div>
        <button
          onClick={fetchMarketData}
          className="p-1 hover:bg-gray-100 rounded"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 text-gray-500 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>
      
      <div className="p-4 space-y-3">
        {indices.map((index) => (
          <div key={index.label} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Anchor className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-600">{index.label}</span>
            </div>
            <div className="flex items-center gap-<span className="3">
              font-semibold text-gray-900">
                {index.unit === "$" ? "$" : ""}{index.value.toLocaleString()}
              </span>
              <span
                className={`flex items-center text-xs font-medium ${
                  index.change >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {index.change >= 0 ? (
                  <TrendingUp className="w-3 h-3 mr-1" />
                ) : (
                  <TrendingDown className="w-3 h-3 mr-1" />
                )}
                {index.changePercent >= 0 ? "+" : ""}
                {index.changePercent.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
        Last updated: {new Date(marketData.last_updated).toLocaleTimeString()}
      </div>
    </div>
  );
}

function getMockMarketData(): MarketData {
  return {
    baltic_dirty: { name: "BDI", value: 1842, change: 127, changePercent: 7.4, unit: "$" },
    baltic_clean: { name: "BCI", value: 2156, change: -45, changePercent: -2.0, unit: "$" },
    baltic_lr2: { name: "LR2", value: 14567, change: 234, changePercent: 1.6, unit: "$/day" },
    baltic_lr1: { name: "LR1", value: 11234, change: -89, changePercent: -0.8, unit: "$/day" },
    baltic_mr: { name: "MR", value: 8934, change: 156, changePercent: 1.8, unit: "$/day" },
    spot_rates: {
      "VLCC AG-Japan": 45000,
      "LR2 AG-Japan": 28000,
      "MR AG-Japan": 15000,
    },
    last_updated: new Date().toISOString(),
  };
}

export default MarketPulseWidget;
