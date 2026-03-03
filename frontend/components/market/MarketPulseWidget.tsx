"use client";

import { TrendingUp, TrendingDown, DollarSign, BarChart3, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface MarketIndex {
  name: string;
  value: number;
  change: number;
  unit: string;
}

const marketIndices: MarketIndex[] = [
  { name: "BDI (Baltic Dry)", value: 2156, change: 2.4, unit: "pts" },
  { name: "VLCC TD3", value: 48, change: -1.2, unit: "WS" },
  { name: "MR TC2", value: 185, change: 3.1, unit: "WS" },
  { name: "LR2 TC1", value: 125, change: 0.8, unit: "WS" },
  { name: "TCE Average", value: 24500, change: 5.2, unit: "$/day" },
];

export function MarketPulseWidget() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            Market Pulse
          </CardTitle>
          <Button variant="outline" size="sm">
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {marketIndices.map((index, i) => (
            <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50">
              <div>
                <div className="text-sm font-medium text-gray-900">{index.name}</div>
                <div className="text-xs text-gray-500">{index.unit}</div>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">
                  {index.name.includes("$")
                    ? `$${index.value.toLocaleString()}`
                    : index.value.toLocaleString()}
                </div>
                <div
                  className={`text-xs flex items-center gap-1 ${
                    index.change >= 0 ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {index.change >= 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  {index.change >= 0 ? "+" : ""}
                  {index.change}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
