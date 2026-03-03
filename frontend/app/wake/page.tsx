"""
Wake AI Page - Main fixture dashboard with AI insights.
"""
"use client";

import { useState } from "react";
import { Waves, Bot, TrendingUp } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { WakeTable } from "@/components/wake/WakeTable";
import { MarketPulseWidget } from "@/components/market/MarketPulseWidget";
import { AISandbox } from "@/components/ai/AISandbox";

export default function WakePage() {
  const [showAISandbox, setShowAISandbox] = useState(false);

  return (
    <Navbar>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
              <Waves className="w-7 h-7 text-blue-600" />
              Wake AI Dashboard
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              AI-powered fixture ranking with enrichment from multiple data sources
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => setShowAISandbox(!showAISandbox)}
            >
              <Bot className="w-4 h-4 mr-2" />
              {showAISandbox ? "Hide AI Sandbox" : "AI Sandbox"}
            </Button>
            <Button>
              <TrendingUp className="w-4 h-4 mr-2" />
              Refresh Rankings
            </Button>
          </div>
        </div>

        {/* AI Sandbox (collapsible) */}
        {showAISandbox && (
          <AISandbox />
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Fixtures Table */}
          <div className="lg:col-span-3">
            <WakeTable />
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <MarketPulseWidget />

            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Pipeline Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Extraction</span>
                  <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full">Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Enrichment</span>
                  <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full">Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Ranking</span>
                  <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full">Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Prediction</span>
                  <span className="text-xs px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 rounded-full">Beta</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Decision</span>
                  <span className="text-xs px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 rounded-full">Beta</span>
                </div>
              </CardContent>
            </Card>

            {/* Available Plugins */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Active Plugins</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>RightShip</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>MarineTraffic</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Idwal</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Signal Ocean</span>
                  <span className="w-2 h-2 bg-gray-300 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>ZeroNorth</span>
                  <span className="w-2 h-2 bg-gray-300 rounded-full"></span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Navbar>
  );
}
