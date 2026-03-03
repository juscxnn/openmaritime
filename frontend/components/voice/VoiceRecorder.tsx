"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { clsx } from "clsx";
import { Button } from "../ui/Button";

interface ExtractedFixture {
  vessel_name: string | null;
  cargo_type: string | null;
  cargo_quantity: number | null;
  rate: number | null;
  port_loading: string | null;
  port_discharge: string | null;
  laycan_start: string | null;
  laycan_end: string | null;
  charterer: string | null;
  broker: string | null;
}

interface VoiceRecorderProps {
  onFixtureExtracted?: (fixture: ExtractedFixture) => void;
  className?: string;
  apiUrl?: string;
}

export function VoiceRecorder({
  onFixtureExtracted,
  className,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001",
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [extractedFixture, setExtractedFixture] = useState<ExtractedFixture | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setError(null);
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        await processAudio();
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Failed to start recording:", err);
      setError("Failed to access microphone. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const processAudio = async () => {
    if (audioChunksRef.current.length === 0) {
      setError("No audio recorded");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Create audio blob
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });

      // Send to backend as FormData
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      const response = await fetch(`${apiUrl}/api/v1/voice/process`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setTranscript(data.transcription?.text || "");
        setExtractedFixture(data.fixture);
        
        if (onFixtureExtracted && data.fixture) {
          onFixtureExtracted(data.fixture);
        }
      } else {
        setError(data.error || "Failed to process audio");
      }
    } catch (err) {
      console.error("Processing error:", err);
      setError(err instanceof Error ? err.message : "Failed to process audio");
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const clearRecording = () => {
    setTranscript("");
    setExtractedFixture(null);
    setError(null);
    setRecordingTime(0);
  };

  return (
    <div className={clsx("bg-white rounded-lg border border-gray-200 p-4", className)}>
      <div className="flex flex-col items-center gap-4">
        {/* Recording Button */}
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
            className={clsx(
              "w-20 h-20 rounded-full flex items-center justify-center transition-all",
              "focus:outline-none focus:ring-4 focus:ring-offset-2",
              isRecording
                ? "bg-red-500 hover:bg-red-600 focus:ring-red-300 animate-pulse"
                : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-300",
              isProcessing && "opacity-50 cursor-not-allowed"
            )}
          >
            {isProcessing ? (
              <svg
                className="w-8 h-8 text-white animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : isRecording ? (
              <svg
                className="w-8 h-8 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : (
              <svg
                className="w-8 h-8 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            )}
          </button>

          {/* Recording indicator */}
          {isRecording && (
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-gray-700">
                Recording {formatTime(recordingTime)}
              </span>
            </div>
          )}

          {!isRecording && !isProcessing && (
            <span className="text-sm text-gray-500">Tap to record</span>
          )}

          {isProcessing && (
            <span className="text-sm text-gray-500">Processing...</span>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="w-full p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Transcript */}
        {transcript && (
          <div className="w-full">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Transcript</h4>
            <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
              {transcript}
            </p>
          </div>
        )}

        {/* Extracted Fixture */}
        {extractedFixture && (
          <div className="w-full">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-700">Extracted Fixture</h4>
              <Button variant="ghost" size="sm" onClick={clearRecording}>
                Clear
              </Button>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-2">
              {Object.entries(extractedFixture).map(([key, value]) => {
                if (value === null) return null;
                return (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-gray-600 capitalize">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VoiceRecorder;
