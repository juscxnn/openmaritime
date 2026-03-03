"use client";

import { useState, useEffect } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  SortingState,
} from "@tanstack/react-table";

interface Fixture {
  id: string;
  vessel_name: string;
  imo_number: string | null;
  cargo_type: string;
  cargo_quantity: number;
  cargo_unit: string;
  laycan_start: string;
  laycan_end: string;
  rate: number | null;
  rate_currency: string;
  rate_unit: string;
  port_loading: string;
  port_discharge: string;
  charterer: string | null;
  broker: string | null;
  status: string;
  wake_score: number | null;
  tce_estimate: number | null;
  market_diff: number | null;
  enrichment_data: Record<string, unknown> | null;
  created_at: string;
}

const columnHelper = createColumnHelper<Fixture>();

const columns = [
  columnHelper.display({
    id: "rank",
    header: "Rank",
    cell: (info) => {
      const score = info.row.original.wake_score;
      if (!score) return "-";
      return (
        <div className="flex items-center gap-2">
          <span className={`font-bold ${score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-gray-600"}`}>
            {score.toFixed(0)}
          </span>
        </div>
      );
    },
  }),
  columnHelper.accessor((row) => `${row.vessel_name} / ${row.imo_number || "N/A"}`, {
    id: "vessel",
    header: "Vessel / IMO",
    cell: (info) => (
      <div>
        <div className="font-medium text-gray-900">{info.row.original.vessel_name}</div>
        <div className="text-xs text-gray-500">{info.row.original.imo_number || "No IMO"}</div>
      </div>
    ),
  }),
  columnHelper.accessor((row) => `${row.cargo_quantity}k ${row.cargo_type}`, {
    id: "cargo",
    header: "Cargo / Qty",
    cell: (info) => (
      <div>
        <div className="text-gray-900">{info.row.original.cargo_quantity.toLocaleString()} {info.row.original.cargo_unit}</div>
        <div className="text-xs text-gray-500">{info.row.original.cargo_type}</div>
      </div>
    ),
  }),
  columnHelper.accessor("laycan_start", {
    header: "Laycan",
    cell: (info) => {
      const start = new Date(info.getValue());
      const end = new Date(info.row.original.laycan_end);
      const daysLeft = Math.ceil((start.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
      return (
        <div>
          <div className="text-gray-900">
            {start.toLocaleDateString("en-US", { month: "short", day: "numeric" })} -{" "}
            {end.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          </div>
          <div className={`text-xs ${daysLeft <= 3 ? "text-red-600 font-medium" : daysLeft <= 7 ? "text-yellow-600" : "text-gray-500"}`}>
            {daysLeft > 0 ? `${daysLeft}d left` : "Expired"}
          </div>
        </div>
      );
    },
  }),
  columnHelper.accessor("rate", {
    header: "Rate",
    cell: (info) => {
      const rate = info.getValue();
      if (!rate) return "-";
      const currency = info.row.original.rate_currency;
      const unit = info.row.original.rate_unit;
      return (
        <span className="font-medium text-gray-900">
          {currency} {rate.toFixed(2)}{unit}
        </span>
      );
    },
  }),
  columnHelper.accessor("enrichment_data", {
    header: "RightShip",
    cell: (info) => {
      const data = info.getValue() as Record<string, unknown> | null;
      if (!data?.rightship) {
        return <span className="text-gray-400">-</span>;
      }
      const rs = data.rightship as { safety?: number; ghg?: string };
      return (
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            rs.safety && rs.safety >= 4 ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
          }`}>
            {rs.safety?.toFixed(1) || "-"}{"★"}
          </span>
          <span className="text-xs text-gray-500">{rs.ghg || "-"}</span>
        </div>
      );
    },
  }),
  columnHelper.display({
    id: "position",
    header: "Position / ETA",
    cell: (info) => {
      const data = info.row.original.enrichment_data as Record<string, unknown> | null;
      if (!data?.position) {
        return <span className="text-gray-400">-</span>;
      }
      const pos = data.position as { lat?: number; lon?: number; eta?: string };
      return (
        <div className="text-xs">
          <div className="text-gray-900">{pos.lat?.toFixed(1)}N / {pos.lon?.toFixed(1)}E</div>
          {pos.eta && <div className="text-gray-500">~{pos.eta}</div>}
        </div>
      );
    },
  }),
  columnHelper.accessor("market_diff", {
    header: "Market Diff",
    cell: (info) => {
      const diff = info.getValue();
      if (diff === null || diff === undefined) return "-";
      return (
        <span className={`font-medium ${diff > 0 ? "text-green-600" : diff < 0 ? "text-red-600" : "text-gray-600"}`}>
          {diff > 0 ? "+" : ""}{diff.toFixed(1)}% TCE
        </span>
      );
    },
  }),
  columnHelper.display({
    id: "wake_score",
    header: "Wake Score",
    cell: (info) => {
      const score = info.row.original.wake_score;
      if (!score) return "-";
      return (
        <div className="w-24">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${score >= 80 ? "bg-green-500" : score >= 60 ? "bg-yellow-500" : "bg-gray-400"}`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-sm font-medium">{score.toFixed(0)}%</span>
          </div>
        </div>
      );
    },
  }),
  columnHelper.display({
    id: "actions",
    header: "Actions",
    cell: (info) => (
      <button className="bg-blue-600 text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-blue-700 transition-colors">
        FIX NOW
      </button>
    ),
  }),
];

export function WakeTable() {
  const [data, setData] = useState<Fixture[]>(getMockFixtures());
  const [sorting, setSorting] = useState<SortingState>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchFixtures() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/fixtures`);
        if (res.ok) {
          const json = await res.json();
          if (json.length > 0) {
            setData(json);
          }
        }
      } catch (err) {
        console.log("Using mock fixture data");
      }
    }
    fetchFixtures();
  }, []);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
  });

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="text-gray-500">Loading fixtures...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {loading ? (
        <div className="p-12 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() && (
                        <span>{header.column.getIsSorted() === "asc" ? "↑" : "↓"}</span>
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
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500">
                  No fixtures found. Add fixtures via API or email sync.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}

function getMockFixtures(): Fixture[] {
  return [
    {
      id: "1",
      vessel_name: "MT Pacific Grace",
      imo_number: "9753161",
      cargo_type: "Naptha",
      cargo_quantity: 45000,
      cargo_unit: "MT",
      laycan_start: "2024-03-15",
      laycan_end: "2024-03-20",
      rate: 28.5,
      rate_currency: "$",
      rate_unit: "/mt",
      port_loading: "Singapore",
      port_discharge: "Chiba",
      charterer: "Trafigura",
      broker: "Clarksons",
      status: "confirmed",
      wake_score: 88,
      tce_estimate: 24500,
      market_diff: 12.5,
      enrichment_data: {
        rightship: { safety: 4.2, ghg: "A" },
        position: { lat: 22.3, lon: 114.1, eta: "3 days" },
      },
      created_at: "2024-03-10T10:00:00Z",
    },
    {
      id: "2",
      vessel_name: "STI Sapphire",
      imo_number: "9863294",
      cargo_type: "Gas Oil",
      cargo_quantity: 80000,
      cargo_unit: "MT",
      laycan_start: "2024-03-20",
      laycan_end: "2024-03-25",
      rate: 95,
      rate_currency: "WS",
      rate_unit: "",
      port_loading: "Ras Tanura",
      port_discharge: "Rotterdam",
      charterer: "Vitol",
      broker: "Gibson",
      status: "confirmed",
      wake_score: 72,
      tce_estimate: 18200,
      market_diff: 3.2,
      enrichment_data: {
        rightship: { safety: 3.8, ghg: "B" },
        position: { lat: 35.2, lon: 12.5, eta: "5 days" },
      },
      created_at: "2024-03-11T09:00:00Z",
    },
    {
      id: "3",
      vessel_name: "MT Ocean Pride",
      imo_number: "9321483",
      cargo_type: "Crude",
      cargo_quantity: 280000,
      cargo_unit: "MT",
      laycan_start: "2024-03-18",
      laycan_end: "2024-03-22",
      rate: 52,
      rate_currency: "WS",
      rate_unit: "",
      port_loading: "Kuwait",
      port_discharge: "Mumbai",
      charterer: "Reliance",
      broker: "Poten",
      status: "pending",
      wake_score: 65,
      tce_estimate: 15800,
      market_diff: -2.1,
      enrichment_data: {
        rightship: { safety: 4.0, ghg: "A" },
        position: { lat: 25.3, lon: 55.2, eta: "1 day" },
      },
      created_at: "2024-03-12T14:00:00Z",
    },
    {
      id: "4",
      vessel_name: "VLCC Eternal",
      imo_number: "9456782",
      cargo_type: "Crude",
      cargo_quantity: 300000,
      cargo_unit: "MT",
      laycan_start: "2024-03-25",
      laycan_end: "2024-03-30",
      rate: 48,
      rate_currency: "WS",
      rate_unit: "",
      port_loading: "Basrah",
      port_discharge: "Singapore",
      charterer: "BP",
      broker: "EA Gibson",
      status: "pending",
      wake_score: 58,
      tce_estimate: 14200,
      market_diff: -5.8,
      enrichment_data: null,
      created_at: "2024-03-13T08:00:00Z",
    },
    {
      id: "5",
      vessel_name: "MR Nordic Wind",
      imo_number: "9234567",
      cargo_type: "Clean Petroleum",
      cargo_quantity: 38000,
      cargo_unit: "MT",
      laycan_start: "2024-03-12",
      laycan_end: "2024-03-15",
      rate: 145,
      rate_currency: "WS",
      rate_unit: "",
      port_loading: "Amsterdam",
      port_discharge: "Med",
      charterer: "Shell",
      broker: "SSY",
      status: "confirmed",
      wake_score: 82,
      tce_estimate: 22100,
      market_diff: 8.4,
      enrichment_data: {
        rightship: { safety: 4.5, ghg: "A" },
      },
      created_at: "2024-03-08T11:00:00Z",
    },
  ];
}
