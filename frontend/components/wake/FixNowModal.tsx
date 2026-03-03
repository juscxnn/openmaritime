"use client";

import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Toggle } from "@/components/ui/Toggle";
import {
  Check,
  X,
  Mic,
  Ship,
  Anchor,
  Calendar,
  DollarSign,
  MapPin,
  Send,
  Loader2,
} from "lucide-react";

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
}

interface FixNowModalProps {
  fixture: Fixture | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (data: FixNowData) => Promise<void>;
}

interface FixNowData {
  fixture_id: string;
  rate: number;
  rate_currency: string;
  rate_unit: string;
  laycan_start: string;
  laycan_end: string;
  charterer: string;
  notes: string;
  notify_team: boolean;
  create_veson_voyage: boolean;
}

const CURRENCY_OPTIONS = [
  { value: "USD", label: "USD" },
  { value: "EUR", label: "EUR" },
  { value: "GBP", label: "GBP" },
];

const RATE_UNIT_OPTIONS = [
  { value: "/mt", label: "Per MT" },
  { value: "/ton", label: "Per Ton" },
  { value: "lumpsum", label: "Lumpsum" },
  { value: "ws", label: "Worldscale" },
];

export function FixNowModal({ fixture, isOpen, onClose, onConfirm }: FixNowModalProps) {
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [formData, setFormData] = useState<FixNowData>({
    fixture_id: "",
    rate: 0,
    rate_currency: "USD",
    rate_unit: "/mt",
    laycan_start: "",
    laycan_end: "",
    charterer: "",
    notes: "",
    notify_team: true,
    create_veson_voyage: true,
  });

  if (!fixture) return null;

  const handleOpen = () => {
    setFormData({
      fixture_id: fixture.id,
      rate: fixture.rate || 0,
      rate_currency: fixture.rate_currency || "USD",
      rate_unit: fixture.rate_unit || "/mt",
      laycan_start: fixture.laycan_start?.split("T")[0] || "",
      laycan_end: fixture.laycan_end?.split("T")[0] || "",
      charterer: fixture.charterer || "",
      notes: "",
      notify_team: true,
      create_veson_voyage: true,
    });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onConfirm(formData);
      onClose();
    } catch (error) {
      console.error("Failed to fix fixture:", error);
    } finally {
      setLoading(false);
    }
  };

  const startVoiceInput = () => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onstart = () => setListening(true);
      recognition.onend = () => setListening(false);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setFormData((prev) => ({ ...prev, notes: prev.notes + " " + transcript }));
      };

      recognition.start();
    } else {
      alert("Voice input not supported in this browser");
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      onOpenChange={(open) => open && handleOpen()}
      title="FIX NOW"
      size="lg"
    >
      <ModalContent>
        <div className="space-y-6">
          {/* Vessel Info Header */}
          <div className="flex items-center gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
              <Ship className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-gray-900 dark:text-white">
                {fixture.vessel_name}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {fixture.vessel_type} • {fixture.cargo_type} • {fixture.cargo_quantity.toLocaleString()} {fixture.cargo_unit}
              </div>
            </div>
            {fixture.wake_score !== null && (
              <div className="text-right">
                <div className="text-2xl font-bold text-green-600">{fixture.wake_score.toFixed(0)}</div>
                <div className="text-xs text-gray-500">Wake Score</div>
              </div>
            )}
          </div>

          {/* Route */}
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
            <MapPin className="w-4 h-4" />
            <span>{fixture.port_loading}</span>
            <span className="text-gray-400">→</span>
            <span>{fixture.port_discharge}</span>
          </div>

          {/* Rate */}
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Rate"
              type="number"
              value={formData.rate}
              onChange={(e) => setFormData({ ...formData, rate: parseFloat(e.target.value) || 0 })}
              icon={<DollarSign className="w-4 h-4" />}
            />
            <Select
              label="Currency"
              options={CURRENCY_OPTIONS}
              value={formData.rate_currency}
              onChange={(e) => setFormData({ ...formData, rate_currency: e.target.value })}
            />
            <Select
              label="Unit"
              options={RATE_UNIT_OPTIONS}
              value={formData.rate_unit}
              onChange={(e) => setFormData({ ...formData, rate_unit: e.target.value })}
            />
          </div>

          {/* Laycan */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Laycan Start"
              type="date"
              value={formData.laycan_start}
              onChange={(e) => setFormData({ ...formData, laycan_start: e.target.value })}
              icon={<Calendar className="w-4 h-4" />}
            />
            <Input
              label="Laycan End"
              type="date"
              value={formData.laycan_end}
              onChange={(e) => setFormData({ ...formData, laycan_end: e.target.value })}
              icon={<Calendar className="w-4 h-4" />}
            />
          </div>

          {/* Charterer */}
          <Input
            label="Charterer"
            value={formData.charterer}
            onChange={(e) => setFormData({ ...formData, charterer: e.target.value })}
            placeholder="Enter charterer name"
            icon={<Anchor className="w-4 h-4" />}
          />

          {/* Notes with Voice */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Notes
            </label>
            <div className="relative">
              <textarea
                className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Add notes or use voice input..."
              />
              <button
                type="button"
                onClick={startVoiceInput}
                className={`absolute right-3 top-3 p-2 rounded-full transition-colors ${
                  listening
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
              >
                {listening ? (
                  <Mic className="w-4 h-4" />
                ) : (
                  <Mic className="w-4 h-4" />
                )}
              </button>
            </div>
            {listening && (
              <p className="text-sm text-red-500 animate-pulse">Listening...</p>
            )}
          </div>

          {/* Actions */}
          <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="notify_team"
                  checked={formData.notify_team}
                  onChange={(e) => setFormData({ ...formData, notify_team: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="notify_team" className="text-sm text-gray-700 dark:text-gray-300">
                  Notify team
                </label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="create_veson"
                  checked={formData.create_veson_voyage}
                  onChange={(e) => setFormData({ ...formData, create_veson_voyage: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="create_veson" className="text-sm text-gray-700 dark:text-gray-300">
                  Create Veson voyage
                </label>
              </div>
            </div>
          </div>
        </div>
      </ModalContent>
      <ModalFooter>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            <X className="w-4 h-4 mr-2" />
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Fixing...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Confirm FIX NOW
              </>
            )}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
}
