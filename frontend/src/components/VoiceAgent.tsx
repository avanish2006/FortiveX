"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, PhoneOff, Send, VolumeX } from "lucide-react";
import { clsx } from "clsx";
import toast from "react-hot-toast";
import BANTScoreCard from "./BANTScoreCard";
import SentimentBadge from "./SentimentBadge";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AgentState {
  bant_score: number;
  sentiment_score: number;
  sentiment_label: string;
  intent: string;
  suggested_action: string | null;
  appointment_booked: boolean;
  crm_updated: boolean;
  status: string;
  lead_name: string | null;
  lead_email: string | null;
  lead_company: string | null;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "hi", label: "हिंदी" },
  { code: "zh", label: "中文" },
  { code: "ja", label: "日本語" },
  { code: "ar", label: "العربية" },
];

export default function VoiceAgent() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [textInput, setTextInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [sessionId] = useState(() => `session_${Date.now()}`);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [messages]);

  const stopPlayback = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
      setIsSpeaking(false);
    }
  }, []);

  const addMessage = useCallback((role: "user" | "assistant", content: string) => {
    setMessages((prev) => [...prev, { role, content, timestamp: new Date() }]);
  }, []);

  const playAudio = useCallback(async (b64: string) => {
    try {
      stopPlayback();
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudioRef.current = audio;
      setIsSpeaking(true);
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setIsSpeaking(false);
        currentAudioRef.current = null;
      };
      await audio.play();
    } catch (e) {
      setIsSpeaking(false);
      console.error("Audio playback error", e);
    }
  }, [stopPlayback]);

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/ws/voice/${sessionId}?language=${language}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      toast.success("Connected to SalesPilot AI");
    };

    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "processing") {
        setIsProcessing(true);
        return;
      }

      setIsProcessing(false);

      if (data.type === "greeting" || data.type === "response") {
        if (data.transcript) addMessage("user", data.transcript);
        if (data.response) addMessage("assistant", data.response);
        if (data.state) setAgentState(data.state);
        if (data.audio_b64) await playAudio(data.audio_b64);
      } else if (data.type === "empty_audio") {
        toast("Could not hear audio, please try again.");
      }
    };

    ws.onerror = () => {
      toast.error("Connection error — check if backend is running");
      setIsConnected(false);
      setIsProcessing(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsRecording(false);
      setIsProcessing(false);
      stopPlayback();
    };
  }, [sessionId, language, addMessage, playAudio, stopPlayback]);

  const disconnect = useCallback(() => {
    stopPlayback();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_call" }));
    }
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setIsRecording(false);
  }, [stopPlayback]);

  const startRecording = useCallback(async () => {
    if (!isConnected) {
      toast.error("Connect first before recording");
      return;
    }
    // Interrupt AI speech immediately when user starts talking
    stopPlayback();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const arrayBuffer = await audioBlob.arrayBuffer();
        if (wsRef.current?.readyState === WebSocket.OPEN && arrayBuffer.byteLength > 0) {
          wsRef.current.send(arrayBuffer);
          setIsProcessing(true);
        }
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      toast.error("Microphone access denied");
    }
  }, [isConnected, stopPlayback]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const sendText = useCallback(() => {
    if (!textInput.trim() || !isConnected) return;
    stopPlayback();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: textInput.trim() }));
      setIsProcessing(true);
      setTextInput("");
    }
  }, [textInput, isConnected, stopPlayback]);

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Voice Agent</h1>
            <p className="text-xs text-gray-500">Session: {sessionId}</p>
          </div>
          <div className="flex items-center gap-3">
            {isSpeaking && (
              <button
                onClick={stopPlayback}
                className="btn-secondary flex items-center gap-1.5 text-xs py-2"
                title="Interrupt AI voice"
              >
                <VolumeX className="w-4 h-4 text-yellow-400" /> Interrupt
              </button>
            )}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="input text-sm w-36"
              disabled={isConnected}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
            {isConnected ? (
              <button
                onClick={disconnect}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <PhoneOff className="w-4 h-4" /> End Call
              </button>
            ) : (
              <button onClick={connect} className="btn-primary flex items-center gap-2">
                <Mic className="w-4 h-4" /> Start Call
              </button>
            )}
          </div>
        </div>

        {/* Status bar */}
        {isConnected && (
          <div className="bg-green-900/30 border-b border-green-800/50 px-6 py-2 flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-green-400">Connected — SalesPilot AI is listening</span>
            {isProcessing && (
              <span className="ml-2 text-xs text-brand-400 animate-pulse">Processing...</span>
            )}
          </div>
        )}

        {/* Transcript */}
        <div ref={transcriptRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 bg-brand-900/50 rounded-full flex items-center justify-center mb-4">
                <Mic className="w-10 h-10 text-brand-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-300">SalesPilot AI</h2>
              <p className="text-gray-500 mt-2 max-w-sm">
                Click <strong>Start Call</strong> then hold the microphone button to speak, or type
                below.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={clsx("flex", msg.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={clsx(
                  "max-w-[75%] px-4 py-3 rounded-2xl text-sm",
                  msg.role === "user"
                    ? "bg-brand-600 text-white rounded-br-sm"
                    : "bg-gray-800 text-gray-100 rounded-bl-sm"
                )}
              >
                <p>{msg.content}</p>
                <p
                  className={clsx(
                    "text-[10px] mt-1",
                    msg.role === "user" ? "text-blue-200" : "text-gray-500"
                  )}
                >
                  {msg.role === "user" ? "You" : "SalesPilot AI"} ·{" "}
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="flex justify-start">
              <div className="bg-gray-800 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-1.5">
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="border-t border-gray-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <button
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onMouseLeave={() => isRecording && stopRecording()}
              onTouchStart={startRecording}
              onTouchEnd={stopRecording}
              disabled={!isConnected || isProcessing}
              className={clsx(
                "w-12 h-12 rounded-full flex items-center justify-center transition-all shrink-0",
                isRecording
                  ? "bg-red-600 shadow-lg shadow-red-600/50 scale-110"
                  : isConnected
                  ? "bg-brand-600 hover:bg-brand-700"
                  : "bg-gray-800 cursor-not-allowed"
              )}
              title="Hold to speak"
            >
              {isRecording ? (
                <div className="flex items-end gap-0.5 h-5">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="waveform-bar"
                      style={{ animationDelay: `${i * 0.1}s` }}
                    />
                  ))}
                </div>
              ) : (
                <Mic className="w-5 h-5 text-white" />
              )}
            </button>

            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendText()}
              placeholder={isConnected ? "Or type a message..." : "Connect to start..."}
              disabled={!isConnected}
              className="input flex-1"
            />

            <button
              onClick={sendText}
              disabled={!isConnected || !textInput.trim()}
              className="btn-primary px-3 py-3"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2 text-center">
            Hold the mic button to speak · Release to send
          </p>
        </div>
      </div>

      {/* Right panel — Agent state */}
      <div className="w-72 border-l border-gray-800 bg-gray-900 flex flex-col shrink-0 overflow-y-auto">
        <div className="px-4 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">Agent Insights</h2>
        </div>

        <div className="p-4 space-y-4">
          <BANTScoreCard score={agentState?.bant_score ?? 0} />

          <div className="card">
            <p className="text-xs text-gray-500 mb-2">Sentiment</p>
            <SentimentBadge
              label={agentState?.sentiment_label ?? "neutral"}
              score={agentState?.sentiment_score ?? 0}
            />
          </div>

          <div className="card">
            <p className="text-xs text-gray-500 mb-1">Current Intent</p>
            <p className="text-sm font-medium text-brand-400 capitalize">
              {agentState?.intent ?? "—"}
            </p>
          </div>

          {agentState?.suggested_action && (
            <div className="card border-brand-700 bg-brand-900/20">
              <p className="text-xs text-brand-400 mb-1">Suggested Action</p>
              <p className="text-sm text-brand-300">{agentState.suggested_action}</p>
            </div>
          )}

          {(agentState?.lead_name || agentState?.lead_email) && (
            <div className="card">
              <p className="text-xs text-gray-500 mb-2">Lead Info</p>
              {agentState.lead_name && (
                <p className="text-sm text-white font-medium">{agentState.lead_name}</p>
              )}
              {agentState.lead_company && (
                <p className="text-xs text-gray-400">{agentState.lead_company}</p>
              )}
              {agentState.lead_email && (
                <p className="text-xs text-gray-500">{agentState.lead_email}</p>
              )}
            </div>
          )}

          <div className="space-y-2">
            {agentState?.appointment_booked && (
              <div className="flex items-center gap-2 px-3 py-2 bg-green-900/30 border border-green-800/50 rounded-lg">
                <span className="text-green-400 text-xs">Appointment Booked</span>
              </div>
            )}
            {agentState?.crm_updated && (
              <div className="flex items-center gap-2 px-3 py-2 bg-blue-900/30 border border-blue-800/50 rounded-lg">
                <span className="text-blue-400 text-xs">CRM Updated</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
