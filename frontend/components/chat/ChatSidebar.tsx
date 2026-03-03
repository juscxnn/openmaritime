"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  X,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  Volume2,
  VolumeX,
  Mic,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Square,
  Paperclip,
  MoreHorizontal,
  Copy,
  Check,
  Zap,
  Waves,
  Anchor,
  Calculator,
  Mail,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  thinking?: string;
  sources?: ChatSource[];
  feedback?: "up" | "down" | null;
  toolCalls?: ToolCall[];
}

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "error";
  result?: string;
}

interface ChatSource {
  type: "fixture" | "email" | "pdf" | "market_data" | "rag";
  id: string;
  title: string;
  relevance: number;
  snippet?: string;
}

interface ChatProps {
  isOpen: boolean;
  onClose: () => void;
  fixtureId?: string;
  fixtureName?: string;
}

export function ChatSidebar({ isOpen, onClose, fixtureId, fixtureName }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [contextFixture, setContextFixture] = useState<{ id: string; name: string } | null>(
    fixtureId && fixtureName ? { id: fixtureId, name: fixtureName } : null
  );
  const [showThinking, setShowThinking] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamingRef = useRef<string>("");

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: `Welcome to Wake AI! 🚢\n\nI'm your maritime chartering assistant. I can help you with:\n\n• **Analyze fixtures** - Get AI insights on any vessel or charter\n• **FIX NOW** - Quickly confirm fixtures with all details\n• **Laytime calculations** - Calculate demurrage/despatch\n• **Market intelligence** - Compare rates, find opportunities\n• **RAG queries** - Ask questions about your data\n\n${fixtureName ? `Currently viewing: **${fixtureName}**` : "Select a fixture to get contextual insights."}`,
          timestamp: new Date(),
        },
      ]);
    }
  }, [isOpen, fixtureName]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (fixtureId && fixtureName) {
      setContextFixture({ id: fixtureId, name: fixtureName });
      if (messages.length > 0) {
        setMessages((prev) => [
          ...prev,
          {
            id: `ctx-${Date.now()}`,
            role: "system",
            content: `Context switched to: **${fixtureName}**`,
            timestamp: new Date(),
          },
        ]);
      }
    }
  }, [fixtureId, fixtureName]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const thinkingMessage: Message = {
      id: `thinking-${Date.now()}`,
      role: "assistant",
      content: "",
      thinking: "",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, thinkingMessage]);

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: messages.concat(userMessage).map((m) => ({
            role: m.role,
            content: m.content,
          })),
          context_fixture_id: contextFixture?.id,
          stream: true,
        }),
      });

      if (!response.ok) throw new Error("Chat failed");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let finalContent = "";
      let currentThinking = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") continue;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === "thinking") {
                currentThinking += parsed.content;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === thinkingMessage.id
                      ? { ...m, thinking: currentThinking }
                      : m
                  )
                );
              } else if (parsed.type === "content") {
                finalContent += parsed.content;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === thinkingMessage.id
                      ? { ...m, content: finalContent, thinking: currentThinking }
                      : m
                  )
                );
              } else if (parsed.type === "source") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === thinkingMessage.id
                      ? { ...m, sources: [...(m.sources || []), parsed.source] }
                      : m
                  )
                );
              } else if (parsed.type === "tool_call") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === thinkingMessage.id
                      ? {
                          ...m,
                          toolCalls: [
                            ...(m.toolCalls || []),
                            {
                              id: parsed.tool.id,
                              name: parsed.tool.name,
                              arguments: parsed.tool.arguments,
                              status: "running",
                            },
                          ],
                        }
                      : m
                  )
                );
              } else if (parsed.type === "tool_result") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === thinkingMessage.id
                      ? {
                          ...m,
                          toolCalls: (m.toolCalls || []).map((t) =>
                            t.id === parsed.tool_id
                              ? { ...t, status: "completed", result: parsed.result }
                              : t
                          ),
                        }
                      : m
                  )
                );
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === thinkingMessage.id
            ? { ...m, toolCalls: m.toolCalls?.map((t) => ({ ...t, status: "completed" })) }
            : m
        )
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === thinkingMessage.id
            ? { ...m, content: "Sorry, I encountered an error. Please try again." }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = (messageId: string, feedback: "up" | "down") => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, feedback: m.feedback === feedback ? null : feedback }
          : m
      )
    );

    const message = messages.find((m) => m.id === messageId);
    if (message) {
      fetch("http://localhost:8000/api/v1/chat/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          message_content: message.content,
          feedback,
          context_fixture_id: contextFixture?.id,
        }),
      }).catch(console.error);
    }
  };

  const startVoiceInput = () => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      // @ts-ignore
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join("");
        setInput((prev) => prev + transcript);
      };

      recognition.start();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className={`${
        isFullscreen
          ? "fixed inset-0 z-50"
          : "fixed right-0 top-0 bottom-0 w-full max-w-md"
      } bg-white dark:bg-gray-800 shadow-2xl flex flex-col transition-all`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Wake AI</h3>
            <p className="text-xs text-gray-500">
              {contextFixture ? `Context: ${contextFixture.name}` : "General chat"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsFullscreen(!isFullscreen)}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setIsMuted(!isMuted)}>
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </Button>
          <Button size="sm" variant="ghost" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Context Banner */}
      {contextFixture && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800">
          <div className="flex items-center gap-2 text-sm">
            <Anchor className="w-4 h-4 text-blue-600" />
            <span className="text-blue-900 dark:text-blue-200">
              Analyzing: <strong>{contextFixture.name}</strong>
            </span>
            <button
              onClick={() => setContextFixture(null)}
              className="ml-auto text-blue-500 hover:text-blue-700"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === "user"
                  ? "bg-gray-200 dark:bg-gray-700"
                  : "bg-gradient-to-br from-blue-500 to-purple-600"
              }`}
            >
              {message.role === "user" ? (
                <User className="w-4 h-4 text-gray-600 dark:text-gray-300" />
              ) : (
                <Bot className="w-4 h-4 text-white" />
              )}
            </div>
            <div
              className={`flex-1 max-w-[80%] ${message.role === "user" ? "text-right" : ""}`}
            >
              {/* Thinking */}
              {message.thinking && showThinking && message.role === "assistant" && (
                <div className="mb-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <Zap className="w-3 h-3 text-yellow-500" />
                    Thinking...
                  </div>
                  <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                    {message.thinking}
                  </pre>
                </div>
              )}

              {/* Content */}
              <div
                className={`p-3 rounded-lg ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                }`}
              >
                <div className="whitespace-pre-wrap text-sm">{message.content}</div>
              </div>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {message.sources.map((source, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {source.type === "fixture" && <Waves className="w-3 h-3 mr-1" />}
                      {source.type === "email" && <Mail className="w-3 h-3 mr-1" />}
                      {source.type === "rag" && <Bot className="w-3 h-3 mr-1" />}
                      {source.title}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Tool Calls */}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div className="mt-2 space-y-1">
                  {message.toolCalls.map((tool) => (
                    <div
                      key={tool.id}
                      className={`flex items-center gap-2 p-2 rounded text-xs ${
                        tool.status === "running"
                          ? "bg-yellow-50 dark:bg-yellow-900/20"
                          : tool.status === "completed"
                          ? "bg-green-50 dark:bg-green-900/20"
                          : "bg-red-50 dark:bg-red-900/20"
                      }`}
                    >
                      {tool.status === "running" && (
                        <Loader2 className="w-3 h-3 animate-spin text-yellow-500" />
                      )}
                      {tool.status === "completed" && (
                        <Check className="w-3 h-3 text-green-500" />
                      )}
                      <span className="font-medium">{tool.name}</span>
                      {tool.result && (
                        <span className="text-gray-500 truncate">{tool.result}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Feedback & Actions */}
              {message.role === "assistant" && message.id.startsWith("thinking") && (
                <div className="flex items-center gap-1 mt-2">
                  <button
                    onClick={() => handleFeedback(message.id, "up")}
                    className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                      message.feedback === "up" ? "text-green-500" : "text-gray-400"
                    }`}
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleFeedback(message.id, "down")}
                    className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                      message.feedback === "down" ? "text-red-500" : "text-gray-400"
                    }`}
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                  <button className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400">
                    <Copy className="w-4 h-4" />
                  </button>
                  <button className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Timestamp */}
              <div className="text-xs text-gray-400 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        {loading && !messages[messages.length - 1]?.thinking && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                contextFixture
                  ? `Ask about ${contextFixture.name}...`
                  : "Ask anything about fixtures, rates, market..."
              }
              className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={1}
              disabled={loading}
            />
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={startVoiceInput}
            disabled={loading}
            className={isListening ? "bg-red-100 text-red-600" : ""}
          >
            <Mic className={`w-5 h-5 ${isListening ? "animate-pulse" : ""}`} />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={loading || !input.trim()}
            onClick={handleSend}
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">Enter</kbd>
            <span>send</span>
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded ml-2">Shift+Enter</kbd>
            <span>new line</span>
          </div>
          <span>Powered by Wake AI</span>
        </div>
      </div>
    </div>
  );
}
