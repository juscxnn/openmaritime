"use client";

import { useState, useEffect, useMemo } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Store,
  Shield,
  MapPin,
  TrendingUp,
  Anchor,
  Calculator,
  Mic,
  Database,
  Clock,
  Ship,
  Award,
  Compass,
  Search,
  Check,
  X,
  Key,
  ExternalLink,
  Settings2,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Toggle } from "@/components/ui/Toggle";
import { Spinner } from "@/components/ui/Spinner";

interface Plugin {
  name: string;
  display_name: string;
  description: string;
  category: string;
  icon: string;
  api_key_required: boolean;
  api_key_env: string;
  hooks_available: string[];
  is_builtin: boolean;
  is_enabled?: boolean;
  api_key_configured?: boolean;
}

const columnHelper = createColumnHelper<Plugin>();

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "Vessel Data": Shield,
  "AIS & Position": MapPin,
  "Market Data": TrendingUp,
  "Voyage Management": Ship,
  "Operations": Anchor,
  Calculations: Calculator,
  "AI/ML": Mic,
  "Port Data": Database,
};

const CATEGORY_COLORS: Record<string, string> = {
  "Vessel Data": "bg-blue-100 text-blue-700",
  "AIS & Position": "bg-green-100 text-green-700",
  "Market Data": "bg-purple-100 text-purple-700",
  "Voyage Management": "bg-cyan-100 text-cyan-700",
  Operations: "bg-orange-100 text-orange-700",
  Calculations: "bg-gray-100 text-gray-700",
  "AI/ML": "bg-pink-100 text-pink-700",
  "Port Data": "bg-teal-100 text-teal-700",
};

function getCategoryIcon(category: string) {
  return CATEGORY_ICONS[category] || Store;
}

function getCategoryColor(category: string) {
  return CATEGORY_COLORS[category] || "bg-gray-100 text-gray-700";
}

const columns = [
  columnHelper.accessor("display_name", {
    header: "Plugin",
    cell: (info) => {
      const plugin = info.row.original;
      const IconComponent = getCategoryIcon(plugin.category);
      
      return (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
            <IconComponent className="w-5 h-5 text-gray-600" />
          </div>
          <div>
            <div className="font-medium text-gray-900">{plugin.display_name}</div>
            <div className="text-xs text-gray-500">{plugin.name}</div>
          </div>
        </div>
      );
    },
  }),
  columnHelper.accessor("description", {
    header: "Description",
    cell: (info) => (
      <div className="text-sm text-gray-600 max-w-md">{info.getValue()}</div>
    ),
  }),
  columnHelper.accessor("category", {
    header: "Category",
    cell: (info) => {
      const category = info.getValue();
      return (
        <Badge className={getCategoryColor(category)}>{category}</Badge>
      );
    },
  }),
  columnHelper.accessor("hooks_available", {
    header: "Hooks",
    cell: (info) => (
      <div className="flex flex-wrap gap-1">
        {info.getValue().map((hook) => (
          <Badge key={hook} variant="outline">
            {hook.replace("on_", "")}
          </Badge>
        ))}
      </div>
    ),
  }),
  columnHelper.accessor("api_key_required", {
    header: "API Key",
    cell: (info) => (
      info.getValue() ? (
        <div className="flex items-center gap-1 text-sm text-gray-500">
          <Key className="w-3 h-3" />
          Required
        </div>
      ) : (
        <span className="text-sm text-green-600">Built-in</span>
      )
    ),
  }),
  columnHelper.display({
    id: "status",
    header: "Status",
    cell: (info) => {
      const plugin = info.row.original;
      if (plugin.api_key_required && !plugin.api_key_configured) {
        return <Badge variant="warning">Setup Required</Badge>;
      }
      return plugin.is_enabled ? (
        <Badge variant="success">Enabled</Badge>
      ) : (
        <Badge variant="default">Disabled</Badge>
      );
    },
  }),
  columnHelper.display({
    id: "actions",
    header: "Actions",
    cell: (info) => {
      const plugin = info.row.original;
      return (
        <div className="flex items-center gap-2">
          {plugin.api_key_required && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => openConfigModal(plugin)}
            >
              <Settings2 className="w-3 h-3 mr-1" />
              Configure
            </Button>
          )}
          <Toggle
            checked={plugin.is_enabled || false}
            onChange={(checked) => handleToggle(plugin, checked)}
          />
        </div>
      );
    },
  }),
];

function handleToggle(plugin: Plugin, enabled: boolean) {
  console.log(`${enabled ? "Enable" : "Disable"} plugin:`, plugin.name);
  // API call would go here
}

function openConfigModal(plugin: Plugin) {
  console.log("Open config for:", plugin.name);
}

export default function MarketplacePage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [configModal, setConfigModal] = useState<Plugin | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [configuring, setConfiguring] = useState(false);

  useEffect(() => {
    async function fetchPlugins() {
      try {
        const res = await fetch("http://localhost:8000/api/v1/marketplace");
        if (res.ok) {
          const data = await res.json();
          // Add mock enabled/configured state
          setPlugins(
            data.map((p: Plugin) => ({
              ...p,
              is_enabled: p.is_builtin,
              api_key_configured: false,
            }))
          );
        }
      } catch (err) {
        console.log("Using mock plugins");
        setPlugins(getMockPlugins());
      } finally {
        setLoading(false);
      }
    }
    fetchPlugins();
  }, []);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    plugins.forEach((p) => cats.add(p.category));
    return Array.from(cats);
  }, [plugins]);

  const filteredPlugins = useMemo(() => {
    let result = plugins;
    
    if (selectedCategory !== "all") {
      result = result.filter((p) => p.category === selectedCategory);
    }
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.display_name.toLowerCase().includes(query) ||
          p.description.toLowerCase().includes(query) ||
          p.name.toLowerCase().includes(query)
      );
    }
    
    return result;
  }, [plugins, selectedCategory, searchQuery]);

  const table = useReactTable({
    data: filteredPlugins,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  async function handleConfigurePlugin() {
    if (!configModal || !apiKeyInput) return;
    
    setConfiguring(true);
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/marketplace/${configModal.name}/config`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: apiKeyInput }),
        }
      );
      
      if (res.ok) {
        setPlugins((prev) =>
          prev.map((p) =>
            p.name === configModal.name
              ? { ...p, api_key_configured: true, is_enabled: true }
              : p
          )
        );
        setConfigModal(null);
        setApiKeyInput("");
      }
    } catch (err) {
      console.error("Failed to configure plugin:", err);
    } finally {
      setConfiguring(false);
    }
  }

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
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <Store className="w-7 h-7 text-blue-600" />
              Plugin Marketplace
            </h1>
            <p className="text-gray-500 mt-1">
              Extend OpenMaritime with data providers and integrations
            </p>
          </div>
        </div>

        {/* Category Filters */}
        <Card>
          <CardContent className="py-4">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedCategory("all")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedCategory === "all"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  All ({plugins.length})
                </button>
                {categories.map((cat) => {
                  const count = plugins.filter((p) => p.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setSelectedCategory(cat)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedCategory === cat
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {cat} ({count})
                    </button>
                  );
                })}
              </div>
              <div className="w-full md:w-64">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search plugins..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-900">{plugins.length}</div>
              <div className="text-sm text-gray-500">Available Plugins</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-green-600">
                {plugins.filter((p) => p.is_enabled).length}
              </div>
              <div className="text-sm text-gray-500">Enabled</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-blue-600">
                {categories.length}
              </div>
              <div className="text-sm text-gray-500">Categories</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-orange-600">
                {plugins.filter((p) => p.api_key_required && !p.api_key_configured).length}
              </div>
              <div className="text-sm text-gray-500">Setup Required</div>
            </CardContent>
          </Card>
        </div>

        {/* Plugins Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-6 py-4">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* API Key Config Modal */}
        <Modal
          isOpen={!!configModal}
          onClose={() => {
            setConfigModal(null);
            setApiKeyInput("");
          }}
          title={`Configure ${configModal?.display_name}`}
          size="md"
        >
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Key className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    API Key Required
                  </p>
                  <p className="text-sm text-blue-700 mt-1">
                    Enter your {configModal?.display_name} API key to enable this plugin.
                    You can find your API key in your {configModal?.display_name} dashboard.
                  </p>
                </div>
              </div>
            </div>

            <Input
              label={`${configModal?.display_name} API Key`}
              type="password"
              placeholder="Enter your API key"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
            />

            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setConfigModal(null);
                  setApiKeyInput("");
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfigurePlugin}
                disabled={!apiKeyInput || configuring}
              >
                {configuring ? <Spinner size="sm" className="mr-2" /> : null}
                Save Configuration
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </Navbar>
  );
}

function getMockPlugins(): Plugin[] {
  return [
    {
      name: "rightship",
      display_name: "RightShip",
      description: "Safety scores, GHG ratings, and inspection data for vessels",
      category: "Vessel Data",
      icon: "shield",
      api_key_required: true,
      api_key_env: "RIGHTSHIP_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: true,
      api_key_configured: true,
    },
    {
      name: "marinetraffic",
      display_name: "MarineTraffic",
      description: "AIS positions, ETA, and vessel tracking",
      category: "AIS & Position",
      icon: "map-pin",
      api_key_required: true,
      api_key_env: "MARINETRAFFIC_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "veson",
      display_name: "Veson IMOS",
      description: "Bi-directional voyage sync with IMOS",
      category: "Voyage Management",
      icon: "ship",
      api_key_required: true,
      api_key_env: "VESON_API_TOKEN",
      hooks_available: ["on_fixture_enrich", "on_fix_now"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "signalocean",
      display_name: "Signal Ocean",
      description: "Market data, voyages, and vessel positions",
      category: "Market Data",
      icon: "trending-up",
      api_key_required: true,
      api_key_env: "SIGNAL_OCEAN_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "idwal",
      display_name: "Idwal",
      description: "Vessel grading and technical assessment (0-100)",
      category: "Vessel Data",
      icon: "award",
      api_key_required: true,
      api_key_env: "IDWAL_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "zeronorth",
      display_name: "ZeroNorth",
      description: "Bunker optimization and voyage planning",
      category: "Operations",
      icon: "anchor",
      api_key_required: true,
      api_key_env: "ZERONORTH_API_KEY",
      hooks_available: ["on_fixture_enrich", "on_rank"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "laytime",
      display_name: "Laytime Engine",
      description: "Built-in NOR, SOF, and demurrage calculation",
      category: "Calculations",
      icon: "calculator",
      api_key_required: false,
      api_key_env: "",
      hooks_available: ["on_laytime_calculate"],
      is_builtin: true,
      is_enabled: true,
      api_key_configured: true,
    },
    {
      name: "whisper",
      display_name: "Whisper Voice",
      description: "Local voice-to-fixture transcription using Whisper",
      category: "AI/ML",
      icon: "mic",
      api_key_required: false,
      api_key_env: "",
      hooks_available: ["on_voice_note"],
      is_builtin: true,
      is_enabled: true,
      api_key_configured: true,
    },
    {
      name: "orbitmi",
      display_name: "OrbitMI",
      description: "Vessel efficiency scores, CII data, market comps",
      category: "Vessel Data",
      icon: "compass",
      api_key_required: true,
      api_key_env: "ORBITMI_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "abaixa",
      display_name: "Abaixa",
      description: "Terminal data, congestion, and port information",
      category: "Port Data",
      icon: "database",
      api_key_required: true,
      api_key_env: "ABAIXA_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      name: "portcall",
      display_name: "PortCall AI",
      description: "ETA predictions and port congestion forecasting",
      category: "Operations",
      icon: "clock",
      api_key_required: true,
      api_key_env: "PORTCALL_API_KEY",
      hooks_available: ["on_fixture_enrich"],
      is_builtin: true,
      is_enabled: false,
      api_key_configured: false,
    },
  ];
}
