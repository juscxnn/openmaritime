"use client";

import { useState, useEffect } from "react";
import {
  Settings,
  User,
  Key,
  Mail,
  Shield,
  CreditCard,
  Trash2,
  Plus,
  Copy,
  Check,
  ExternalLink,
  AlertTriangle,
  DollarSign,
  Activity,
  RefreshCw,
  Plug,
  CheckCircle,
  XCircle,
  Users,
  FileText,
  Search,
  Filter,
  Download,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Toggle } from "@/components/ui/Toggle";
import { Spinner } from "@/components/ui/Spinner";
import { Select } from "@/components/ui/Select";
import { useAppStore } from "@/lib/store";

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used: string | null;
}

interface EmailConfig {
  connected: boolean;
  email: string | null;
  last_sync: string | null;
}

interface CostData {
  total_cost: number;
  api_calls: Record<string, number>;
  api_costs: Record<string, number>;
  period_start: string;
}

interface Integration {
  plugin_name: string;
  display_name: string;
  description: string;
  category: string;
  icon: string;
  api_key_required: boolean;
  is_enabled: boolean;
  api_key_configured: boolean;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    connected: false,
    email: null,
    last_sync: null,
  });
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [costData, setCostData] = useState<CostData>({
    total_cost: 0,
    api_calls: {},
    api_costs: {},
    period_start: new Date().toISOString(),
  });
  
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [integrationApiKey, setIntegrationApiKey] = useState("");
  const [showIntegrationModal, setShowIntegrationModal] = useState(false);
  const [savingIntegration, setSavingIntegration] = useState(false);
  
  const [newApiKeyName, setNewApiKeyName] = useState("");
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { costTracking, getCostSummary } = useAppStore();

  useEffect(() => {
    fetchUserProfile();
    fetchApiKeys();
    fetchEmailConfig();
    fetchCostData();
    fetchIntegrations();
  }, []);

  async function fetchUserProfile() {
    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/me");
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      } else {
        // Mock user
        setProfile({
          id: "user-1",
          email: "demo@openmaritime.io",
          full_name: "Demo User",
          is_active: true,
        });
      }
    } catch (err) {
      setProfile({
        id: "user-1",
        email: "demo@openmaritime.io",
        full_name: "Demo User",
        is_active: true,
      });
    }
  }

  async function fetchApiKeys() {
    // Mock API keys
    setApiKeys([
      {
        id: "key-1",
        name: "Production API",
        key_prefix: "om_live_****",
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
        last_used: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      },
      {
        id: "key-2",
        name: "Development",
        key_prefix: "om_test_****",
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
        last_used: null,
      },
    ]);
  }

  async function fetchEmailConfig() {
    // Mock email config
    setEmailConfig({
      connected: true,
      email: "charterer@company.com",
      last_sync: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    });
  }

  async function fetchCostData() {
    // Use store data or mock
    const summary = getCostSummary();
    if (summary.total_cost > 0) {
      setCostData(summary);
    } else {
      setCostData({
        total_cost: 127.50,
        api_calls: {
          rightship: 245,
          marinetraffic: 892,
          signalocean: 156,
        },
        api_costs: {
          rightship: 49.00,
          marinetraffic: 44.60,
          signalocean: 33.90,
        },
        period_start: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
      });
    }
  }

  async function fetchIntegrations() {
    try {
      const res = await fetch("http://localhost:8000/api/v1/marketplace/user/configs");
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data);
      } else {
        setIntegrations(MOCK_INTEGRATIONS);
      }
    } catch (err) {
      setIntegrations(MOCK_INTEGRATIONS);
    }
  }

  async function saveIntegrationConfig(integration: Integration, apiKey: string, enabled: boolean) {
    setSavingIntegration(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/marketplace/${integration.plugin_name}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, is_enabled: enabled }),
      });
      if (res.ok) {
        await fetchIntegrations();
        setShowIntegrationModal(false);
        setIntegrationApiKey("");
      }
    } catch (err) {
      console.error("Failed to save integration config:", err);
    }
    setSavingIntegration(false);
  }

  const MOCK_INTEGRATIONS = [
    {
      plugin_name: "rightship",
      display_name: "RightShip",
      description: "Safety scores, GHG ratings, and inspection data for vessels",
      category: "Vessel Data",
      icon: "shield",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "marinetraffic",
      display_name: "MarineTraffic",
      description: "AIS positions, ETA, and vessel tracking",
      category: "AIS & Position",
      icon: "map-pin",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "signalocean",
      display_name: "Signal Ocean",
      description: "Market data, voyages, vessel positions, freight rates",
      category: "Market Data",
      icon: "trending-up",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "veson",
      display_name: "Veson IMOS",
      description: "Bi-directional voyage sync with IMOS",
      category: "Voyage Management",
      icon: "ship",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "idwal",
      display_name: "Idwal",
      description: "Vessel grading (0-100), technical assessment",
      category: "Vessel Data",
      icon: "award",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "zeronorth",
      display_name: "ZeroNorth",
      description: "Bunker optimization, voyage planning, CO2 emissions",
      category: "Operations",
      icon: "anchor",
      api_key_required: true,
      is_enabled: false,
      api_key_configured: false,
    },
    {
      plugin_name: "whisper",
      display_name: "Whisper Voice",
      description: "Local voice-to-fixture transcription using Whisper",
      category: "AI/ML",
      icon: "mic",
      api_key_required: false,
      is_enabled: true,
      api_key_configured: true,
    },
    {
      plugin_name: "laytime",
      display_name: "Laytime Engine",
      description: "Built-in NOR, SOF, and demurrage calculation",
      category: "Calculations",
      icon: "calculator",
      api_key_required: false,
      is_enabled: true,
      api_key_configured: true,
    },
  ];

  async function handleCreateApiKey() {
    if (!newApiKeyName) return;
    
    // Mock API key creation
    const newKey: ApiKey = {
      id: `key-${Date.now()}`,
      name: newApiKeyName,
      key_prefix: "om_live_****",
      created_at: new Date().toISOString(),
      last_used: null,
    };
    
    setApiKeys([...apiKeys, newKey]);
    setNewApiKey("om_live_" + Math.random().toString(36).substring(2, 15));
    setNewApiKeyName("");
  }

  async function handleDeleteApiKey(keyId: string) {
    setApiKeys(apiKeys.filter((k) => k.id !== keyId));
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleConnectGmail() {
    // OAuth flow would go here
    alert("Gmail OAuth connection would be initiated here");
  }

  async function handleDisconnectEmail() {
    setEmailConfig({
      connected: false,
      email: null,
      last_sync: null,
    });
  }

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "integrations", label: "Integrations", icon: Plug },
    { id: "api-keys", label: "API Keys", icon: Key },
    { id: "email", label: "Email Sync", icon: Mail },
    { id: "sso", label: "SSO", icon: Shield },
    { id: "team", label: "Team", icon: Users },
    { id: "audit", label: "Audit Log", icon: FileText },
    { id: "costs", label: "Cost Tracking", icon: DollarSign },
  ];

  return (
    <Navbar>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Settings className="w-7 h-7 text-blue-600" />
            Settings
          </h1>
          <p className="text-gray-500 mt-1">
            Manage your account and integrations
          </p>
        </div>

        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-56 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1">
            {activeTab === "profile" && (
              <Card>
                <CardHeader>
                  <CardTitle>User Profile</CardTitle>
                  <CardDescription>
                    Manage your personal information
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                      <User className="w-8 h-8 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {profile?.full_name || "User"}
                      </h3>
                      <p className="text-sm text-gray-500">{profile?.email}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Full Name"
                      value={profile?.full_name || ""}
                      onChange={(e) =>
                        setProfile(profile ? { ...profile, full_name: e.target.value } : null)
                      }
                    />
                    <Input
                      label="Email"
                      value={profile?.email || ""}
                      disabled
                    />
                  </div>

                  <div className="flex justify-end">
                    <Button>Save Changes</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "integrations" && (
              <Card>
                <CardHeader>
                  <CardTitle>Integrations</CardTitle>
                  <CardDescription>
                    Connect external services and API providers
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {integrations.map((integration) => (
                      <div
                        key={integration.plugin_name}
                        className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                            <Plug className="w-5 h-5 text-gray-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">
                              {integration.display_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {integration.description}
                            </div>
                            <div className="text-xs text-gray-400 mt-1">
                              {integration.category}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {integration.api_key_required ? (
                            integration.api_key_configured ? (
                              <Badge variant="success">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Connected
                              </Badge>
                            ) : (
                              <Badge variant="warning">
                                <XCircle className="w-3 h-3 mr-1" />
                                API Key Required
                              </Badge>
                            )
                          ) : (
                            <Badge variant="success">Built-in</Badge>
                          )}
                          <Button
                            variant={integration.api_key_configured ? "outline" : "primary"}
                            size="sm"
                            onClick={() => {
                              setSelectedIntegration(integration);
                              setShowIntegrationModal(true);
                            }}
                          >
                            {integration.api_key_configured ? "Configure" : "Set Up"}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "api-keys" && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>API Keys</CardTitle>
                      <CardDescription>
                        Manage API keys for programmatic access
                      </CardDescription>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => setShowApiKeyModal(true)}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Create Key
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {apiKeys.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <Key className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p>No API keys yet</p>
                      <p className="text-sm">Create an API key to get started</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {apiKeys.map((key) => (
                        <div
                          key={key.id}
                          className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                        >
                          <div>
                            <div className="font-medium text-gray-900">{key.name}</div>
                            <div className="text-sm text-gray-500">
                              {key.key_prefix} • Created{" "}
                              {new Date(key.created_at).toLocaleDateString()}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {key.last_used && (
                              <span className="text-xs text-gray-500">
                                Last used: {new Date(key.last_used).toLocaleDateString()}
                              </span>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteApiKey(key.id)}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {activeTab === "email" && (
              <Card>
                <CardHeader>
                  <CardTitle>Email Sync</CardTitle>
                  <CardDescription>
                    Connect your email to automatically import fixtures
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                        <Mail className="w-6 h-6 text-red-600" />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">Gmail</div>
                        <div className="text-sm text-gray-500">
                          {emailConfig.connected
                            ? emailConfig.email
                            : "Connect your Gmail account"}
                        </div>
                      </div>
                    </div>
                    {emailConfig.connected ? (
                      <div className="flex items-center gap-3">
                        <Badge variant="success">Connected</Badge>
                        <Button variant="outline" size="sm" onClick={handleDisconnectEmail}>
                          Disconnect
                        </Button>
                      </div>
                    ) : (
                      <Button onClick={handleConnectGmail}>
                        <ExternalLink className="w-4 h-4 mr-1" />
                        Connect
                      </Button>
                    )}
                  </div>

                  {emailConfig.connected && emailConfig.last_sync && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <RefreshCw className="w-4 h-4" />
                        Last synced: {new Date(emailConfig.last_sync).toLocaleString()}
                      </div>
                    </div>
                  )}

                  <div className="border-t border-gray-200 pt-6">
                    <h4 className="font-medium text-gray-900 mb-4">Sync Settings</h4>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-700">Auto-tagging</div>
                          <div className="text-sm text-gray-500">
                            Automatically tag emails as fixture/charter/market
                          </div>
                        </div>
                        <Toggle checked={true} onChange={() => {}} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-700">Extract Fixtures</div>
                          <div className="text-sm text-gray-500">
                            Automatically extract fixture details from emails
                          </div>
                        </div>
                        <Toggle checked={true} onChange={() => {}} />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "sso" && (
              <Card>
                <CardHeader>
                  <CardTitle>Single Sign-On (SSO)</CardTitle>
                  <CardDescription>
                    Configure enterprise authentication
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-gray-500 mb-4">
                      SSO is not configured for your organization
                    </p>
                    <Button variant="outline">
                      <ExternalLink className="w-4 h-4 mr-1" />
                      Learn about SSO
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "team" && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Team Members</CardTitle>
                      <CardDescription>
                        Manage your team and their permissions
                      </CardDescription>
                    </div>
                    <Button size="sm">
                      <Plus className="w-4 h-4 mr-1" />
                      Invite Member
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <User className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">Demo User</div>
                          <div className="text-sm text-gray-500">demo@openmaritime.io</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="success">Admin</Badge>
                        <Button variant="ghost" size="sm">
                          Edit
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "audit" && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Audit Log</CardTitle>
                      <CardDescription>
                        Track all actions and changes in your account
                      </CardDescription>
                    </div>
                    <Button variant="outline" size="sm">
                      <Download className="w-4 h-4 mr-1" />
                      Export
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 flex gap-2">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search audit logs..."
                        className="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-300 text-sm"
                      />
                    </div>
                    <Select
                      options={[
                        { value: "all", label: "All Actions" },
                        { value: "fixture.create", label: "Fixture Created" },
                        { value: "fixture.update", label: "Fixture Updated" },
                        { value: "auth.login", label: "Login" },
                        { value: "plugin.call", label: "Plugin Call" },
                      ]}
                      value="all"
                      onChange={() => {}}
                      className="w-40"
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                            <Check className="w-4 h-4 text-green-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">Fixture created</div>
                            <div className="text-sm text-gray-500">MT Pacific Grace - Singapore to Chiba</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500">Demo User</div>
                          <div className="text-xs text-gray-400">2 hours ago</div>
                        </div>
                      </div>
                    </div>
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <User className="w-4 h-4 text-blue-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">User login</div>
                            <div className="text-sm text-gray-500">demo@openmaritime.io</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500">Demo User</div>
                          <div className="text-xs text-gray-400">5 hours ago</div>
                        </div>
                      </div>
                    </div>
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                            <Plug className="w-4 h-4 text-purple-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">RightShip enrichment</div>
                            <div className="text-sm text-gray-500">IMO: 9753161</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500">System</div>
                          <div className="text-xs text-gray-400">1 day ago</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "costs" && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Cost Summary</CardTitle>
                    <CardDescription>
                      Track your API usage and costs this billing period
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                      <div className="bg-blue-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-blue-600">
                          ${costData.total_cost.toFixed(2)}
                        </div>
                        <div className="text-sm text-blue-700">Total Cost</div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-600">
                          {Object.values(costData.api_calls).reduce((a, b) => a + b, 0)}
                        </div>
                        <div className="text-sm text-green-700">API Calls</div>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-purple-600">
                          {new Date(costData.period_start).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })}
                        </div>
                        <div className="text-sm text-purple-700">Period Start</div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {Object.entries(costData.api_costs).map(([api, cost]) => (
                        <div
                          key={api}
                          className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            <Activity className="w-4 h-4 text-gray-400" />
                            <span className="font-medium text-gray-700 capitalize">
                              {api}
                            </span>
                          </div>
                          <div className="text-right">
                            <div className="font-medium text-gray-900">
                              ${cost.toFixed(2)}
                            </div>
                            <div className="text-xs text-gray-500">
                              {costData.api_calls[api]} calls
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Usage Alerts</CardTitle>
                    <CardDescription>
                      Get notified when usage exceeds thresholds
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-700">
                            Monthly Budget Alert
                          </div>
                          <div className="text-sm text-gray-500">
                            Notify when spending reaches $100
                          </div>
                        </div>
                        <Toggle checked={true} onChange={() => {}} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-700">
                            API Limit Warning
                          </div>
                          <div className="text-sm text-gray-500">
                            Alert at 80% of plan limits
                          </div>
                        </div>
                        <Toggle checked={true} onChange={() => {}} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        {/* Create API Key Modal */}
        <Modal
          isOpen={showApiKeyModal}
          onClose={() => {
            setShowApiKeyModal(false);
            setNewApiKey(null);
            setNewApiKeyName("");
          }}
          title={newApiKey ? "API Key Created" : "Create API Key"}
          size="md"
        >
          {newApiKey ? (
            <div className="space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-yellow-900">
                      Save this key now
                    </p>
                    <p className="text-sm text-yellow-700 mt-1">
                      This is the only time you&apos;ll see this key. Copy it and store
                      it securely.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <code className="flex-1 bg-gray-100 px-4 py-3 rounded-lg font-mono text-sm">
                  {newApiKey}
                </code>
                <Button
                  variant="outline"
                  onClick={() => copyToClipboard(newApiKey)}
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={() => {
                    setShowApiKeyModal(false);
                    setNewApiKey(null);
                  }}
                >
                  Done
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <Input
                label="Key Name"
                placeholder="e.g., Production API"
                value={newApiKeyName}
                onChange={(e) => setNewApiKeyName(e.target.value)}
              />

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowApiKeyModal(false);
                    setNewApiKeyName("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateApiKey}
                  disabled={!newApiKeyName}
                >
                  Create Key
                </Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Integration Config Modal */}
        <Modal
          isOpen={showIntegrationModal}
          onClose={() => {
            setShowIntegrationModal(false);
            setSelectedIntegration(null);
            setIntegrationApiKey("");
          }}
          title={`Configure ${selectedIntegration?.display_name || "Integration"}`}
          size="md"
        >
          <div className="space-y-4">
            {selectedIntegration && (
              <>
                <p className="text-sm text-gray-600">
                  {selectedIntegration.description}
                </p>
                
                {selectedIntegration.api_key_required && (
                  <Input
                    label="API Key"
                    type="password"
                    placeholder="Enter your API key"
                    value={integrationApiKey}
                    onChange={(e) => setIntegrationApiKey(e.target.value)}
                  />
                )}

                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-700">Enable Integration</span>
                  <Toggle
                    checked={selectedIntegration.is_enabled}
                    onChange={() => {
                      if (selectedIntegration) {
                        setSelectedIntegration({
                          ...selectedIntegration,
                          is_enabled: !selectedIntegration.is_enabled,
                        });
                      }
                    }}
                  />
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowIntegrationModal(false);
                      setSelectedIntegration(null);
                      setIntegrationApiKey("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => {
                      if (selectedIntegration) {
                        saveIntegrationConfig(
                          selectedIntegration,
                          integrationApiKey,
                          selectedIntegration.is_enabled
                        );
                      }
                    }}
                    disabled={selectedIntegration.api_key_required && !integrationApiKey}
                  >
                    {savingIntegration ? "Saving..." : "Save Configuration"}
                  </Button>
                </div>
              </>
            )}
          </div>
        </Modal>
      </div>
    </Navbar>
  );
}
