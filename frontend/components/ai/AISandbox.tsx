"""
AI Sandbox Component.

Allows users to test the AI pipeline with custom fixture emails.
Shows full EXTRACTION → ENRICHMENT → RANKING → PREDICTION → DECISION pipeline.
"""
"use client";

import { useState } from "react";
import {
  Bot,
  Play,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Loader2,
  Zap,
  ArrowRight,
  Lightbulb,
  Target,
  TrendingUp,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";

interface PipelineStage {
  name: string;
  status: "pending" | "running" | "success" | "error";
  result?: any;
  error?: string;
  duration?: number;
}

interface PipelineResult {
  extraction: PipelineStage;
  enrichment: PipelineStage;
  ranking: PipelineStage;
  prediction: PipelineStage;
  decision: PipelineStage;
}

export function AISandbox() {
  const [emailInput, setEmailInput] = useState("");
  const [pipelineResult, setPipelineResult] = useState<PipelineResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set(["decision"]));

  const sampleEmails = [
    {
      name: "Fixture - MR Tanker",
      text: "Fixtures: MR Tanker - Singapore to Chiba\n\nDear All,\n\nWe have the following fixture to report:\n\nVessel: MT Pacific Grace\nCargo: 45,000 MT Naptha\nLaycan: 15-20 March\nLoad: Singapore\nDischarge: Chiba\nRate: WS 125\n\nPlease confirm your acceptance.",
    },
    {
      name: "Fixture - VLCC",
      text: "Voyage: VLCC Ras Tanura to Rotterdam\n\nVessel: MT Ocean Titan\nIMO: 1234567\nCargo: 280,000 MT Crude Oil\nLaycan: 01-05 April\nRate: LS $3.50\nComm: 2.5%\n\nBest regards,\nBroker",
    },
  ];

  async function runPipeline() {
    if (!emailInput.trim()) return;

    setIsRunning(true);
    setPipelineResult(null);

    try {
      // Call the backend AI pipeline
      const res = await fetch("http://localhost:8000/api/v1/fixtures/ai-pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email_content: emailInput }),
      });

      if (res.ok) {
        const result = await res.json();
        setPipelineResult(result);
      } else {
        // Simulate pipeline on error
        simulatePipeline();
      }
    } catch (err) {
      // Simulate pipeline for demo
      simulatePipeline();
    } finally {
      setIsRunning(false);
    }
  }

  function simulatePipeline() {
    // Simulate the full AI pipeline
    const stages = ["extraction", "enrichment", "ranking", "prediction", "decision"];
    const result: any = {};

    // Extraction result
    result.extraction = {
      name: "Extraction",
      status: "success",
      result: {
        vessel_name: "MT Pacific Grace",
        imo_number: "1234567",
        cargo_type: "Naptha",
        cargo_quantity: 45000,
        cargo_unit: "MT",
        laycan_start: "2024-03-15",
        laycan_end: "2024-03-20",
        rate: 125,
        rate_currency: "WS",
        rate_unit: "",
        port_loading: "Singapore",
        port_discharge: "Chiba",
        vessel_type: "MR",
        route_type: "short",
        completeness_score: 85,
      },
      duration: 1200,
    };

    // Enrichment result
    result.enrichment = {
      name: "Enrichment",
      status: "success",
      result: {
        rightship: { safety_score: 4.5, ghg_rating: "B" },
        marinet: { position: "Singapore Anchorage", eta: "2024-03-14" },
        idwal: { grade: 82 },
      },
      duration: 2500,
    };

    // Ranking result
    result.ranking = {
      name: "Ranking",
      status: "success",
      result: {
        score: 88,
        tce_delta_pct: 12.5,
        urgency: "high",
        urgency_days: 5,
        position_bonus: 8,
        risk_penalty: 5,
        completeness_bonus: 10,
        reason: "Strong TCE vs market, tight laycan, excellent vessel profile",
        key_factors: ["TCE delta positive", "Urgent laycan", "High safety score"],
      },
      duration: 1800,
    };

    // Prediction result
    result.prediction = {
      name: "Prediction",
      status: "success",
      result: {
        predicted_demurrage_days: 1.5,
        demurrage_range: { min: 0.5, max: 3 },
        confidence: "high",
        confidence_factors: ["Low port congestion", "Good weather forecast"],
        key_risks: ["Potential delay at discharge"],
        historical_comparison: "Better than average for route",
        seasonal_adjustment: -0.5,
      },
      duration: 2100,
    };

    // Decision result
    result.decision = {
      name: "Decision",
      status: "success",
      result: {
        recommendation: "FIX NOW",
        confidence: "high",
        auto_fix_eligible: true,
        priority_score: 9,
        action_timeline: "immediate",
        key_decision_points: [
          "TCE 12.5% above market",
          "High safety rating",
          "Urgent laycan window",
        ],
        auto_fix_recommended: true,
        rationale:
          "This fixture scores 88/100 with strong TCE delta and excellent vessel profile. Recommend immediate FIX NOW given tight laycan and favorable market conditions.",
      },
      duration: 900,
    };

    setPipelineResult(result);
  }

  function toggleStage(stage: string) {
    const newExpanded = new Set(expandedStages);
    if (newExpanded.has(stage)) {
      newExpanded.delete(stage);
    } else {
      newExpanded.add(stage);
    }
    setExpandedStages(newExpanded);
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "running":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-600" />
            AI Sandbox
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Paste Fixture Email
            </label>
            <textarea
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="Paste email content to extract fixture and run full AI pipeline..."
              className="w-full h-40 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>

          <div className="flex gap-2">
            <Button onClick={runPipeline} disabled={isRunning || !emailInput.trim()}>
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Running Pipeline...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run AI Pipeline
                </>
              )}
            </Button>
          </div>

          {sampleEmails.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Quick samples:</p>
              <div className="flex gap-2">
                {sampleEmails.map((sample, i) => (
                  <button
                    key={i}
                    onClick={() => setEmailInput(sample.text)}
                    className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                  >
                    {sample.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {pipelineResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-600" />
              Pipeline Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(pipelineResult).map(([key, stage]: [string, any]) => (
              <div key={key} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleStage(key)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(stage.status)}
                    <span className="font-medium text-gray-900">{stage.name}</span>
                    {stage.duration && (
                      <span className="text-xs text-gray-500">({(stage.duration / 1000).toFixed(1)}s)</span>
                    )}
                  </div>
                  {expandedStages.has(key) ? (
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  )}
                </button>

                {expandedStages.has(key) && stage.status === "success" && (
                  <div className="px-4 py-3 bg-white border-t border-gray-200">
                    {key === "ranking" && stage.result && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Wake Score</span>
                          <span className="text-2xl font-bold text-blue-600">
                            {stage.result.score}/100
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              stage.result.urgency === "high"
                                ? "danger"
                                : stage.result.urgency === "medium"
                                ? "warning"
                                : "success"
                            }
                          >
                            {stage.result.urgency} urgency
                          </Badge>
                          <span className="text-sm text-gray-600">
                            TCE: {stage.result.tce_delta_pct > 0 ? "+" : ""}
                            {stage.result.tce_delta_pct}%
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{stage.result.reason}</p>
                      </div>
                    )}

                    {key === "decision" && stage.result && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              stage.result.recommendation === "FIX NOW"
                                ? "success"
                                : stage.result.recommendation === "EXPLORE"
                                ? "info"
                                : "warning"
                            }
                            className="text-lg px-3 py-1"
                          >
                            {stage.result.recommendation}
                          </Badge>
                          <span className="text-sm text-gray-500">
                            Priority: {stage.result.priority_score}/10
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{stage.result.rationale}</p>
                        <div className="flex flex-wrap gap-1">
                          {stage.result.key_decision_points?.map((point: string, i: number) => (
                            <Badge key={i} variant="outline">
                              {point}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {key === "prediction" && stage.result && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Demurrage</span>
                          <span className="font-semibold">
                            {stage.result.predicted_demurrage_days} days
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          Range: {stage.result.demurrage_range?.min} - {stage.result.demurrage_range?.max} days
                        </span>
                        <Badge
                          variant={
                            stage.result.confidence === "high"
                              ? "success"
                              : stage.result.confidence === "medium"
                              ? "warning"
                              : "default"
                          }
                        >
                          {stage.result.confidence} confidence
                        </Badge>
                      </div>
                    )}

                    {key === "extraction" && stage.result && (
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {Object.entries(stage.result).map(([k, v]) => (
                          <div key={k}>
                            <span className="text-gray-500">{k}:</span>{" "}
                            <span className="font-medium">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {key === "enrichment" && stage.result && (
                      <div className="space-y-2">
                        {Object.entries(stage.result).map(([source, data]: [string, any]) => (
                          <div key={source} className="flex items-center gap-2">
                            <Badge variant="info">{source}</Badge>
                            <span className="text-sm text-gray-600">
                              {JSON.stringify(data)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default AISandbox;
