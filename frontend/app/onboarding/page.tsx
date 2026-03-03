"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Ship,
  Mail,
  Key,
  Check,
  ChevronRight,
  ChevronLeft,
  Loader2,
  User,
  Building,
  Globe,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";

interface OnboardingData {
  email: string;
  password: string;
  fullName: string;
  companyName: string;
  timezone: string;
  emailConnected: boolean;
  apiKeys: {
    rightship: string;
    marinetraffic: string;
    veson: string;
  };
}

const STEPS = [
  { id: 1, title: "Welcome", description: "Create your account" },
  { id: 2, title: "Company", description: "Set up organization" },
  { id: 3, title: "Email", description: "Connect email" },
  { id: 4, title: "API Keys", description: "Configure integrations" },
  { id: 5, title: "Ready", description: "Start chartering" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OnboardingData>({
    email: "",
    password: "",
    fullName: "",
    companyName: "",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    emailConnected: false,
    apiKeys: {
      rightship: "",
      marinetraffic: "",
      veson: "",
    },
  });

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      router.push("/wake");
    } catch (error) {
      console.error("Onboarding failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return data.email && data.password && data.fullName;
      case 2:
        return data.companyName;
      case 3:
        return true;
      case 4:
        return true;
      default:
        return true;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-2xl mb-4">
            <Ship className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">Welcome to OpenMaritime</h1>
          <p className="text-blue-200 mt-2">Your AI-powered maritime chartering platform</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8">
          {STEPS.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                  currentStep > step.id
                    ? "bg-green-500 border-green-500"
                    : currentStep === step.id
                    ? "bg-blue-500 border-blue-500"
                    : "border-gray-500 text-gray-400"
                }`}
              >
                {currentStep > step.id ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <span className="text-sm font-medium">{step.id}</span>
                )}
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={`w-16 h-0.5 mx-2 ${
                    currentStep > step.id ? "bg-green-500" : "bg-gray-500"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <Card className="bg-white/95 dark:bg-gray-800/95 backdrop-blur">
          <CardContent className="p-8">
            {/* Step 1: Welcome / Account */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Create your account
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    Get started with OpenMaritime
                  </p>
                </div>

                <div className="space-y-4">
                  <Input
                    label="Full Name"
                    placeholder="John Doe"
                    value={data.fullName}
                    onChange={(e) => setData({ ...data, fullName: e.target.value })}
                    icon={<User className="w-4 h-4" />}
                  />
                  <Input
                    label="Email"
                    type="email"
                    placeholder="john@company.com"
                    value={data.email}
                    onChange={(e) => setData({ ...data, email: e.target.value })}
                    icon={<Mail className="w-4 h-4" />}
                  />
                  <Input
                    label="Password"
                    type="password"
                    placeholder="Create a strong password"
                    value={data.password}
                    onChange={(e) => setData({ ...data, password: e.target.value })}
                  />
                </div>
              </div>
            )}

            {/* Step 2: Company */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Set up your company
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    This helps us customize your experience
                  </p>
                </div>

                <div className="space-y-4">
                  <Input
                    label="Company Name"
                    placeholder="Acme Shipping"
                    value={data.companyName}
                    onChange={(e) => setData({ ...data, companyName: e.target.value })}
                    icon={<Building className="w-4 h-4" />}
                  />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Timezone
                    </label>
                    <select
                      className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                      value={data.timezone}
                      onChange={(e) => setData({ ...data, timezone: e.target.value })}
                    >
                      <option value="UTC">UTC</option>
                      <option value="Europe/London">London (GMT)</option>
                      <option value="Europe/Oslo">Oslo (CET)</option>
                      <option value="Asia/Singapore">Singapore (SGT)</option>
                      <option value="Asia/Dubai">Dubai (GST)</option>
                      <option value="America/New_York">New York (EST)</option>
                      <option value="America/Houston">Houston (CST)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Email */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Connect your email
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    Automatically import fixtures from your inbox
                  </p>
                </div>

                <div className="space-y-4">
                  <button
                    onClick={() => setData({ ...data, emailConnected: true })}
                    className={`w-full p-4 rounded-lg border-2 transition-colors flex items-center gap-4 ${
                      data.emailConnected
                        ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                        : "border-gray-200 dark:border-gray-700 hover:border-blue-500"
                    }`}
                  >
                    <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                      <Mail className="w-6 h-6 text-red-600" />
                    </div>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-gray-900 dark:text-white">Connect Gmail</div>
                      <div className="text-sm text-gray-500">Import fixtures from Google Workspace</div>
                    </div>
                    {data.emailConnected && <Check className="w-5 h-5 text-green-500" />}
                  </button>

                  <button
                    className="w-full p-4 rounded-lg border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors flex items-center gap-4"
                  >
                    <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                      <Mail className="w-6 h-6 text-blue-600" />
                    </div>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-gray-900 dark:text-white">Connect IMAP</div>
                      <div className="text-sm text-gray-500">Use any email provider</div>
                    </div>
                  </button>

                  <button
                    className="w-full p-4 rounded-lg border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors flex items-center gap-4"
                    onClick={() => handleNext()}
                  >
                    <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
                      <span className="text-2xl">⏭️</span>
                    </div>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-gray-900 dark:text-white">Skip for now</div>
                      <div className="text-sm text-gray-500">Connect email later from settings</div>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: API Keys */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Configure integrations
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    Add API keys for enhanced data enrichment (optional)
                  </p>
                </div>

                <div className="space-y-4">
                  <Input
                    label="RightShip API Key"
                    type="password"
                    placeholder="Enter your RightShip API key"
                    value={data.apiKeys.rightship}
                    onChange={(e) => setData({ ...data, apiKeys: { ...data.apiKeys, rightship: e.target.value } })}
                    icon={<Key className="w-4 h-4" />}
                  />
                  <Input
                    label="MarineTraffic API Key"
                    type="password"
                    placeholder="Enter your MarineTraffic API key"
                    value={data.apiKeys.marinetraffic}
                    onChange={(e) => setData({ ...data, apiKeys: { ...data.apiKeys, marinetraffic: e.target.value } })}
                    icon={<Key className="w-4 h-4" />}
                  />
                  <Input
                    label="Veson IMOS Token"
                    type="password"
                    placeholder="Enter your Veson token"
                    value={data.apiKeys.veson}
                    onChange={(e) => setData({ ...data, apiKeys: { ...data.apiKeys, veson: e.target.value } })}
                    icon={<Key className="w-4 h-4" />}
                  />

                  <button
                    className="w-full text-center text-sm text-blue-600 hover:text-blue-700"
                    onClick={() => handleNext()}
                  >
                    Skip this step →
                  </button>
                </div>
              </div>
            )}

            {/* Step 5: Ready */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full mb-4">
                    <Sparkles className="w-10 h-10 text-green-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    You&apos;re all set!
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    Welcome to OpenMaritime, {data.fullName}!
                  </p>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-500" />
                    <span className="text-gray-700 dark:text-gray-300">Account created</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-500" />
                    <span className="text-gray-700 dark:text-gray-300">Company: {data.companyName}</span>
                  </div>
                  {data.emailConnected && (
                    <div className="flex items-center gap-2 text-sm">
                      <Check className="w-4 h-4 text-green-500" />
                      <span className="text-gray-700 dark:text-gray-300">Email connected</span>
                    </div>
                  )}
                </div>

                <Button
                  className="w-full"
                  size="lg"
                  onClick={handleSubmit}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Setting up...
                    </>
                  ) : (
                    <>
                      Launch Wake AI
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </>
                  )}
                </Button>
              </div>
            )}

            {/* Navigation */}
            {currentStep < 5 && (
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                <Button
                  variant="ghost"
                  onClick={handleBack}
                  disabled={currentStep === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Back
                </Button>
                <Button
                  onClick={handleNext}
                  disabled={!canProceed()}
                >
                  {currentStep === 4 ? "Finish" : "Continue"}
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-6 text-blue-200 text-sm">
          Already have an account?{" "}
          <button
            className="text-white font-medium hover:underline"
            onClick={() => router.push("/wake")}
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
}
