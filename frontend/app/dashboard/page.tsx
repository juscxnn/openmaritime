"""
Role-based Dashboard Views.

Different dashboards for Broker, Owner, and Charterer roles.
"""
"use client";

import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Ship,
  Anchor,
  TrendingUp,
  DollarSign,
  Users,
  AlertTriangle,
  Clock,
  MapPin,
  Target,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { WakeTable } from "@/components/wake/WakeTable";
import { MarketPulseWidget } from "@/components/market/MarketPulseWidget";

type Role = "broker" | "owner" | "charterer" | "analyst";

interface DashboardStats {
  totalFixtures: number;
  pendingFixtures: number;
  highPriorityFixtures: number;
  averageTCE: number;
  marketDiff: number;
}

export default function DashboardPage() {
  const [role, setRole] = useState<Role>("broker");
  const [stats, setStats] = useState<DashboardStats>({
    totalFixtures: 0,
    pendingFixtures: 0,
    highPriorityFixtures: 0,
    averageTCE: 0,
    marketDiff: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, [role]);

  async function fetchDashboardStats() {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/fixtures?limit=100`);
      if (res.ok) {
        const fixtures = await res.json();
        const highPriority = fixtures.filter(
          (f: any) => f.wake_score && f.wake_score >= 80
        ).length;
        const avgTCE = fixtures.reduce(
          (sum: number, f: any) => sum + (f.tce_estimate || 0),
          0
        ) / fixtures.length;
        const avgDiff = fixtures.reduce(
          (sum: number, f: any) => sum + (f.market_diff || 0),
          0
        ) / fixtures.length;

        setStats({
          totalFixtures: fixtures.length,
          pendingFixtures: fixtures.filter((f: any) => f.status === "new").length,
          highPriorityFixtures: highPriority,
          averageTCE: avgTCE,
          marketDiff: avgDiff,
        });
      }
    } catch (err) {
      // Use defaults on error
      setStats({
        totalFixtures: 24,
        pendingFixtures: 8,
        highPriorityFixtures: 12,
        averageTCE: 28500,
        marketDiff: 3.2,
      });
    }
    setLoading(false);
  }

  const roleConfigs = {
    broker: {
      title: "Broker Dashboard",
      description: "Ranked fixtures, TCE-delta heatmap, risk analysis",
      stats: [
        { label: "Total Fixtures", value: stats.totalFixtures, icon: Ship, color: "blue" },
        { label: "High Priority", value: stats.highPriorityFixtures, icon: Target, color: "green" },
        { label: "Pending Action", value: stats.pendingFixtures, icon: Clock, color: "yellow" },
        { label: "Avg Market Diff", value: `${stats.marketDiff > 0 ? "+" : ""}${stats.marketDiff.toFixed(1)}%`, icon: TrendingUp, color: stats.marketDiff >= 0 ? "green" : "red" },
      ],
    },
    owner: {
      title: "Owner Dashboard",
      description: "Vessel positioning, laycan exposure, demurrage risk",
      stats: [
        { label: "Active Voyages", value: 15, icon: Ship, color: "blue" },
        { label: "Laycan This Week", value: 4, icon: Clock, color: "yellow" },
        { label: "Demurrage Risk", value: "Low", icon: AlertTriangle, color: "green" },
        { label: "Port Delays", value: 2, icon: MapPin, color: "red" },
      ],
    },
    charterer: {
      title: "Charterer Dashboard",
      description: "Benchmark rates, vessel pool vs spot, route analytics",
      stats: [
        { label: "Active Fixtures", value: stats.totalFixtures, icon: Ship, color: "blue" },
        { label: "Avg Rate", value: `$${stats.averageTCE.toLocaleString()}`, icon: DollarSign, color: "green" },
        { label: "Market Position", value: "+3.2%", icon: TrendingUp, color: "green" },
        { label: "Vessels Tracked", value: 156, icon: Anchor, color: "blue" },
      ],
    },
    analyst: {
      title: "Analyst Dashboard",
      description: "Market trends, historical analysis, reporting",
      stats: [
        { label: "Reports Generated", value: 12, icon: TrendingUp, color: "blue" },
        { label: "Data Sources", value: 8, icon: Database, color: "green" },
        { label: "Alerts", value: 3, icon: AlertTriangle, color: "yellow" },
        { label: "Last Update", value: "2 min ago", icon: Clock, color: "gray" },
      ],
    },
  };

  const config = roleConfigs[role];

  return (
    <Navbar>
      <div className="space-y-6">
        {/* Role Selector */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <LayoutDashboard className="w-7 h-7 text-blue-600" />
              Dashboard
            </h1>
            <p className="text-gray-500 mt-1">{config.description}</p>
          </div>
          <div className="flex gap-2">
            {(Object.keys(roleConfigs) as Role[]).map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  role === r
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {config.stats.map((stat, i) => (
            <Card key={i}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{stat.label}</p>
                    <p className={`text-2xl font-bold ${
                      stat.color === "green" ? "text-green-600" :
                      stat.color === "red" ? "text-red-600" :
                      stat.color === "yellow" ? "text-yellow-600" :
                      "text-gray-900"
                    }`}>
                      {stat.value}
                    </p>
                  </div>
                  <stat.icon className={`w-8 h-8 ${
                    stat.color === "green" ? "text-green-100" :
                    stat.color === "red" ? "text-red-100" :
                    stat.color === "yellow" ? "text-yellow-100" :
                    "text-blue-100"
                  }`} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Fixtures Table */}
          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Fixtures</CardTitle>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      Export
                    </Button>
                    <Button size="sm">
                      Add Fixture
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <WakeTable />
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Market Pulse */}
            <MarketPulseWidget />

            {/* Role-specific widgets */}
            {role === "broker" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Top Opportunities</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                    <span className="text-sm font-medium">VLCC AG-Japan</span>
                    <Badge variant="success">+15.2% TCE</Badge>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                    <span className="text-sm font-medium">LR2 Ras-Rot</span>
                    <Badge variant="success">+8.7% TCE</Badge>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-yellow-50 rounded">
                    <span className="text-sm font-medium">MR Singapore</span>
                    <Badge variant="warning">+2.1% TCE</Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {role === "owner" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Voyage Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Underway</span>
                    <Badge variant="success">8</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">In Port</span>
                    <Badge variant="warning">4</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Ballast</span>
                    <Badge variant="info">3</Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {role === "charterer" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Rate Benchmark</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Current Avg</span>
                    <span className="font-semibold">$28,500/day</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Market Index</span>
                    <span className="font-semibold">$27,600/day</span>
                  </div>
                  <div className="pt-2 border-t">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-green-600">vs Index</span>
                      <Badge variant="success">+3.2%</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </Navbar>
  );
}

function Database({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}
