"use client";

import { useState, useEffect, useMemo } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  SortingState,
  ColumnFiltersState,
} from "@tanstack/react-table";
import {
  Waves,
  Bot,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Filter,
  Download,
  RefreshCw,
  Zap,
  BarChart3,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";

interface Fixture {
  id: string;
  vessel_name: string;
  vessel_type: string;
  cargo_type: string;
  cargo_quantity: number;
  load_port: string;
  discharge_port: string
  rate: number | null;
  rate_unit: string;
  charterer: string;
  owner: string;
  laycan_start: string;
  laycan_end: string;
  status: string;
  created_at: string;
  updated_at: string;
  wake_score: number | null;
  ai_summary: string | null;
}

const columnHelper = createColumnHelper<Fixture>();

const getStatusColor = (status: string) => {
  switch (status) {
    case "confirmed":
      return "success";
    case "pending":
      return "warning";
    case "rejected":
      return "danger";
    default:
      return "default";
  }
};

const getWakeScoreColor = (score: number | null) => {
  if (score === null) return "text-gray-400";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
};

const columns = [
  columnHelper.accessor("vessel_name", {
    header: "Vessel",
    cell: (info) => (
      <div className="font-medium text-gray-900">{info.getValue()}</div>
    ),
  }),
  columnHelper.accessor("vessel_type", {
    header: "Type",
    cell: (info) => <span className="text-sm text-gray-600">{info.getValue()}</span>,
  }),
  columnHelper.accessor("cargo_type", {
    header: "Cargo",
    cell: (info) => <span className="text-sm">{info.getValue()}</span>,
  }),
  columnHelper.accessor("rate", {
    header: "Rate",
    cell: (info) => {
      const rate = info.getValue();
      if (rate === null) return <span className="text-gray-400">-</span>;
      return <span className="font-medium">{info.row.original.rate_unit} {rate}</span>;
    },
  }),
  columnHelper.accessor("load_port", {
    header: "Route",
    cell: (info) => (
      <div className="text-sm">
        {info.getValue()} → {info.row.original.discharge_port}
      </div>
    ),
  }),
  columnHelper.accessor("charterer", {
    header: "Charterer",
    cell: (info) => <span className="text-sm text-gray-600">{info.getValue()}</span>,
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => (
      <Badge variant={getStatusColor(info.getValue()) as "default" | "success" | "warning" | "danger" | "info"}>
        {info.getValue()}
      </Badge>
    ),
  }),
  columnHelper.accessor("wake_score", {
    header: "Wake AI",
    cell: (info) => {
      const score = info.getValue();
      return (
        <div className={`flex items-center gap-1 font-bold ${getWakeScoreColor(score)}`}>
          <Bot className="w-4 h-4" />
          {score !== null ? score.toFixed(0) : "-"}
        </div>
      );
    },
  }),
];

export default function WakePage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    async function fetchFixtures() {
      try {
        const res = await fetch("http://localhost:8002/api/v1/fixtures");
        if (res.ok) {
          const data = await res.json();
          setFixtures(data);
        } else {
          setFixtures(getMockFixtures());
        }
      } catch (err) {
        console.log("Using mock fixture data");
        setFixtures(getMockFixtures());
      } finally {
        setLoading(false);
      }
    }
    fetchFixtures();
  }, []);

  const filteredFixtures = useMemo(() => {
    let result = fixtures;
    if (statusFilter !== "all") {
      result = result.filter((f) => f.status === statusFilter);
    }
    return result;
  }, [fixtures, statusFilter]);

  const table = useReactTable({
    data: filteredFixtures,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const avgWakeScore = useMemo(() => {
    const scores = fixtures.filter((f) => f.wake_score !== null).map((f) => f.wake_score!);
    if (scores.length === 0) return 0;
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  }, [fixtures]);

  const confirmedCount = fixtures.filter((f) => f.status === "confirmed").length;

  if (loading) {
    return (
      <Navbar>
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      </Navbar>
    );
  }

  return (
    <Navbar>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <Waves className="w-7 h-7 text-blue-600" />
              Wake AI Dashboard
            </h1>
            <p className="text-gray-500 mt-1">
              AI-powered fixture tracking and predictions
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Sync
            </Button>
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-900">{fixtures.length}</div>
              <div className="text-sm text-gray-500">Total Fixtures</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-green-600">{confirmedCount}</div>
              <div className="text-sm text-gray-500">Confirmed</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className={`text-2xl font-bold ${getWakeScoreColor(avgWakeScore)} flex items-center gap-2`}>
                <Bot className="w-5 h-5" />
                {avgWakeScore.toFixed(0)}
              </div>
              <div className="text-sm text-gray-500">Avg Wake Score</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-900">
                {new Set(fixtures.map((f) => f.charterer)).size}
              </div>
              <div className="text-sm text-gray-500">Active Charterers</div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardContent className="py-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search fixtures..."
                    value={globalFilter}
                    onChange={(e) => setGlobalFilter(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <Select
                options={[
                  { value: "all", label: "All Status" },
                  { value: "confirmed", label: "Confirmed" },
                  { value: "pending", label: "Pending" },
                  { value: "rejected", label: "Rejected" },
                ]}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-40"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getIsSorted() && (
                            <span>
                              {header.column.getIsSorted() === "asc" ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-6 py-12 text-center text-gray-500">
                      <Waves className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p className="text-lg font-medium">No fixtures found</p>
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-6 py-4 whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </Navbar>
  );
}

function getMockFixtures(): Fixture[] {
  return [
    {
      id: "1",
      vessel_name: "MT Pacific Grace",
      vessel_type: "MR Tanker",
      cargo_type: "Naptha",
      cargo_quantity: 45000,
      load_port: "Singapore",
      discharge_port: "Chiba",
      rate: 125,
      rate_unit: "WS",
      charterer: "Trafigura",
      owner: "National Shipping",
      laycan_start: "2024-03-15",
      laycan_end: "2024-03-20",
      status: "confirmed",
      created_at: "2024-03-10T10:00:00Z",
      updated_at: "2024-03-10T10:00:00Z",
      wake_score: 85,
      ai_summary: "Strong fixture with premium rate",
    },
    {
      id: "2",
      vessel_name: "STI Sapphire",
      vessel_type: "LR2",
      cargo_type: "Gas Oil",
      cargo_quantity: 80000,
      load_port: "Ras Tanura",
      discharge_port: "Rotterdam",
      rate: 95,
      rate_unit: "WS",
      charterer: "Vitol",
      owner: "STI Shipping",
      laycan_start: "2024-03-20",
      laycan_end: "2024-03-25",
      status: "confirmed",
      created_at: "2024-03-11T09:00:00Z",
      updated_at: "2024-03-11T09:00:00Z",
      wake_score: 72,
      ai_summary: "Standard rate, good vessel",
    },
    {
      id: "3",
      vessel_name: "MT Ocean Pride",
      vessel_type: "VLCC",
      cargo_type: "Crude",
      cargo_quantity: 280000,
      load_port: "Kuwait",
      discharge_port: "Mumbai",
      rate: 52,
      rate_unit: "WS",
      charterer: "Reliance",
      owner: "Ocean Tankers",
      laycan_start: "2024-03-18",
      laycan_end: "2024-03-22",
      status: "pending",
      created_at: "2024-03-12T14:00:00Z",
      updated_at: "2024-03-12T14:00:00Z",
      wake_score: 68,
      ai_summary: "Negotiating, rate below market",
    },
  ];
}
