"use client";

import { useState } from "react";
import {
  X,
  Ship,
  Anchor,
  MapPin,
  Calendar,
  DollarSign,
  FileText,
  Clock,
  Bot,
  TrendingUp,
  TrendingDown,
  Mail,
  Calculator,
  History,
  ExternalLink,
  Mic,
  MessageSquare,
  Share2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Spinner } from "@/components/ui/Spinner";
import { MiniMap } from "@/components/wake/MiniMap";

interface Fixture {
  id: string;
  vessel_name: string;
  vessel_type: string;
  imo_number: string | null;
  cargo_type: string;
  cargo_quantity: number;
  cargo_unit: string;
  port_loading: string;
  port_discharge: string;
  rate: number | null;
  rate_currency: string;
  rate_unit: string;
  charterer: string | null;
  owner: string | null;
  laycan_start: string;
  laycan_end: string;
  status: string;
  wake_score: number | null;
  tce_estimate: number | null;
  market_diff: number | null;
  enrichment_data: Record<string, unknown> | null;
  created_at: string;
  updated_at?: string;
}

interface FixtureCardProps {
  fixture: Fixture | null;
  isOpen: boolean;
  onClose: () => void;
  onFixNow: () => void;
  onOpenVoice: () => void;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case "confirmed":
      return "success";
    case "negotiating":
      return "warning";
    case "rejected":
      return "danger";
    default:
      return "default";
  }
};

export function FixtureCard({ fixture, isOpen, onClose, onFixNow, onOpenVoice }: FixtureCardProps) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!isOpen || !fixture) return null;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const formatRate = () => {
    if (!fixture.rate) return "-";
    return `${fixture.rate_currency} ${fixture.rate} ${fixture.rate_unit}`;
  };

  const enrichment = fixture.enrichment_data as Record<string, unknown> | null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white dark:bg-gray-800 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
              <Ship className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">
                {fixture.vessel_name}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {fixture.vessel_type}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Wake Score Banner */}
        {fixture.wake_score !== null && (
          <div className="px-6 py-3 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`text-3xl font-bold ${
                  fixture.wake_score >= 80 ? "text-green-600" :
                  fixture.wake_score >= 60 ? "text-yellow-600" : "text-red-600"
                }`}>
                  {fixture.wake_score.toFixed(0)}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">Wake Score</div>
                  <div className="text-xs text-gray-500">AI Rank</div>
                </div>
              </div>
              <Button size="sm" onClick={onFixNow}>
                <Anchor className="w-4 h-4 mr-2" />
                FIX NOW
              </Button>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 border-b border-gray-200 dark:border-gray-700">
            <TabsList className="w-full justify-start gap-1 bg-transparent h-auto py-2">
              <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
              <TabsTrigger value="map" className="text-xs">Map</TabsTrigger>
              <TabsTrigger value="emails" className="text-xs">Emails</TabsTrigger>
              <TabsTrigger value="laytime" className="text-xs">Laytime</TabsTrigger>
              <TabsTrigger value="history" className="text-xs">History</TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-y-auto">
            <TabsContent value="overview" className="m-0 p-6 space-y-6">
              {/* Status */}
              <div className="flex items-center gap-3">
                <Badge variant={getStatusColor(fixture.status) as "default" | "success" | "warning" | "danger"}>
                  {fixture.status}
                </Badge>
                {fixture.imo_number && (
                  <span className="text-sm text-gray-500">IMO: {fixture.imo_number}</span>
                )}
              </div>

              {/* Route */}
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300 mb-2">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm font-medium">Route</span>
                </div>
                <div className="flex items-center gap-2 text-lg font-medium text-gray-900 dark:text-white">
                  {fixture.port_loading}
                  <span className="text-gray-400">→</span>
                  {fixture.port_discharge}
                </div>
              </div>

              {/* Cargo */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Cargo</div>
                  <div className="font-medium text-gray-900 dark:text-white">{fixture.cargo_type}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    {fixture.cargo_quantity.toLocaleString()} {fixture.cargo_unit}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Rate</div>
                  <div className="font-medium text-gray-900 dark:text-white">{formatRate()}</div>
                </div>
              </div>

              {/* Laycan */}
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300 mb-2">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm font-medium">Laycan</span>
                </div>
                <div className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <Clock className="w-4 h-4 text-gray-400" />
                  {formatDate(fixture.laycan_start)} - {formatDate(fixture.laycan_end)}
                </div>
              </div>

              {/* Charterer & Owner */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Charterer</div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {fixture.charterer || "-"}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Owner</div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {fixture.owner || "-"}
                  </div>
                </div>
              </div>

              {/* TCE & Market Diff */}
              {fixture.tce_estimate !== null && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400 mb-1">
                      <TrendingUp className="w-4 h-4" />
                      TCE Estimate
                    </div>
                    <div className="text-xl font-bold text-green-600 dark:text-green-400">
                      ${fixture.tce_estimate.toLocaleString()}
                    </div>
                  </div>
                  {fixture.market_diff !== null && (
                    <div className={`p-4 rounded-lg ${
                      fixture.market_diff >= 0 
                        ? "bg-green-50 dark:bg-green-900/20" 
                        : "bg-red-50 dark:bg-red-900/20"
                    }`}>
                      <div className={`flex items-center gap-2 text-sm mb-1 ${
                        fixture.market_diff >= 0 
                          ? "text-green-700 dark:text-green-400" 
                          : "text-red-700 dark:text-red-400"
                      }`}>
                        {fixture.market_diff >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        vs Market
                      </div>
                      <div className={`text-xl font-bold ${
                        fixture.market_diff >= 0 
                          ? "text-green-600 dark:text-green-400" 
                          : "text-red-600 dark:text-red-400"
                      }`}>
                        {fixture.market_diff >= 0 ? "+" : ""}{fixture.market_diff.toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Enrichment Data */}
              {enrichment && (
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Enrichment Data
                  </h4>
                  {Object.entries(enrichment).map(([source, data]) => (
                    <div key={source} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <div className="text-xs font-medium text-gray-500 uppercase mb-1">{source}</div>
                      <pre className="text-xs text-gray-700 dark:text-gray-300 overflow-x-auto">
                        {JSON.stringify(data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="map" className="m-0 p-4 h-full">
              <div className="h-full rounded-lg overflow-hidden">
                <MiniMap 
                  portLoading={fixture.port_loading} 
                  portDischarge={fixture.port_discharge}
                  vesselPosition={enrichment?.position as { lat: number; lng: number } | null}
                />
              </div>
            </TabsContent>

            <TabsContent value="emails" className="m-0 p-6">
              <div className="text-center py-8">
                <Mail className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-500 dark:text-gray-400">No emails linked yet</p>
                <Button variant="outline" size="sm" className="mt-4">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Link Email
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="laytime" className="m-0 p-6">
              <div className="text-center py-8">
                <Calculator className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-500 dark:text-gray-400">No laytime data yet</p>
                <Button variant="outline" size="sm" className="mt-4">
                  <Calculator className="w-4 h-4 mr-2" />
                  Open Calculator
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="history" className="m-0 p-6">
              <div className="text-center py-8">
                <History className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-500 dark:text-gray-400">No history yet</p>
              </div>
            </TabsContent>
          </div>
        </Tabs>

        {/* Footer Actions */}
        <div className="flex items-center gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" size="sm" className="flex-1" onClick={onOpenVoice}>
            <Mic className="w-4 h-4 mr-2" />
            Voice
          </Button>
          <Button variant="outline" size="sm" className="flex-1">
            <MessageSquare className="w-4 h-4 mr-2" />
            Comment
          </Button>
          <Button variant="outline" size="sm" className="flex-1">
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
        </div>
      </div>
    </>
  );
}
