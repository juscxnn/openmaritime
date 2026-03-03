"use client";

import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Users,
  Anchor,
  FileText,
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface StatCard {
  title: string;
  value: string | number;
  change?: string;
  trend?: "up" | "down";
  icon: React.ReactNode;
}

export default function DashboardPage() {
  const [role, setRole] = useState<"broker" | "owner" | "charterer">("broker");

  const stats: StatCard[] = [
    {
      title: "Active Fixtures",
      value: 12,
      change: "+3 this week",
      trend: "up",
      icon: <FileText className="w-5 h-5 text-blue-600" />,
    },
    {
      title: "Pending Negotiations",
      value: 8,
      change: "-2 from yesterday",
      trend: "down",
      icon: <Clock className="w-5 h-5 text-yellow-600" />,
    },
    {
      title: "Market TCE",
      value: "$24,500",
      change: "+8.2%",
      trend: "up",
      icon: <TrendingUp className="w-5 h-5 text-green-600" />,
    },
    {
      title: "Active Vessels",
      value: 45,
      icon: <Anchor className="w-5 h-5 text-purple-600" />,
    },
  ];

  const recentFixtures = [
    { id: "1", vessel: "MT Pacific Grace", charterer: "Trafigura", status: "confirmed", rate: "WS 125" },
    { id: "2", vessel: "STI Sapphire", charterer: "Vitol", status: "pending", rate: "WS 95" },
    { id: "3", vessel: "MT Ocean Pride", charterer: "Reliance", status: "pending", rate: "WS 52" },
  ];

  const marketUpdates = [
    { id: "1", title: "VLCC Rates Surge", source: "Poten", time: "2 hours ago" },
    { id: "2", title: "LR2 Spot Rates Stable", source: "Clarksons", time: "4 hours ago" },
    { id: "3", title: "MR Tanker Demand Strong", source: "GIBSON", time: "6 hours ago" },
  ];

  return (
    <Navbar>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <LayoutDashboard className="w-7 h-7 text-blue-600" />
              Dashboard
            </h1>
            <p className="text-gray-500 mt-1">
              Overview for {role.charAt(0).toUpperCase() + role.slice(1)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={role === "broker" ? "default" : "outline"}
              size="sm"
              onClick={() => setRole("broker")}
            >
              Broker
            </Button>
            <Button
              variant={role === "owner" ? "default" : "outline"}
              size="sm"
              onClick={() => setRole("owner")}
            >
              Owner
            </Button>
            <Button
              variant={role === "charterer" ? "default" : "outline"}
              size="sm"
              onClick={() => setRole("charterer")}
            >
              Charterer
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => (
            <Card key={index}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-500">{stat.title}</div>
                    <div className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</div>
                    {stat.change && (
                      <div className={`text-xs mt-1 flex items-center gap-1 ${
                        stat.trend === "up" ? "text-green-600" : "text-red-600"
                      }`}>
                        {stat.trend === "up" ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {stat.change}
                      </div>
                    )}
                  </div>
                  <div className="p-2 bg-gray-50 rounded-lg">
                    {stat.icon}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Fixtures</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentFixtures.map((fixture) => (
                  <div key={fixture.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900">{fixture.vessel}</div>
                      <div className="text-sm text-gray-500">{fixture.charterer}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{fixture.rate}</div>
                      <div className={`text-xs ${
                        fixture.status === "confirmed" ? "text-green-600" : "text-yellow-600"
                      }`}>
                        {fixture.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Market Updates</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {marketUpdates.map((update) => (
                  <div key={update.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-blue-600" />
                      <div>
                        <div className="font-medium text-gray-900">{update.title}</div>
                        <div className="text-xs text-gray-500">{update.source}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-400">{update.time}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Navbar>
  );
}
