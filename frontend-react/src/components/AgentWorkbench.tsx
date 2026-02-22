import { useState, useRef, useEffect } from "react";
import type { Contact } from "../types";
import {
  X,
  Brain,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Wand2,
  Clock,
} from "lucide-react";

// ── Event types ───────────────────────────────────────────────────────────────

interface AgentEvent {
  type:
  | "start"
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "final"
  | "error"
  | "done";
  // start
  contact?: { name: string; organization: string; title: string; status: string };
  // thinking / final / error
  text?: string;
  message?: string;
  // tool_call / tool_result
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  result?: Record<string, unknown>;
}

// ── Tool display labels ───────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, { label: string; description: string }> = {
  lookup_contact: {
    label: "Lookup Contact",
    description: "Fetching full contact record from database",
  },
  scrape_district_website: {
    label: "Scrape Website",
    description: "Checking org's public site for staff listing",
  },
  scrape_linkedin: {
    label: "LinkedIn Check",
    description: "Verifying current employment via LinkedIn",
  },
  send_confirmation_email: {
    label: "Send Email",
    description: "Sending verification email directly to contact",
  },
  update_contact: {
    label: "Update Record",
    description: "Persisting verified verdict to database",
  },
  flag_for_review: {
    label: "Flag for Review",
    description: "Escalating to human review queue",
  },
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  contact: Contact;
  onClose: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function AgentWorkbench({ contact, onClose }: Props) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const runAgent = async () => {
    setEvents([]);
    setRunning(true);
    setDone(false);
    setElapsed(0);
    startTimeRef.current = Date.now();

    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    try {
      const response = await fetch(`/api/agent/verify/${contact.id}`, {
        method: "POST",
        headers: { "X-API-Key": "dev-key" },
      });

      if (!response.ok || !response.body) {
        setEvents([
          { type: "error", message: `HTTP ${response.status} — ${response.statusText}` },
        ]);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE lines
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const event: AgentEvent = JSON.parse(jsonStr);
            setEvents((prev) => [...prev, event]);
            if (event.type === "done") {
              setDone(true);
              setRunning(false);
              if (timerRef.current) clearInterval(timerRef.current);
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setEvents((prev) => [...prev, { type: "error", message: msg }]);
    } finally {
      setRunning(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  // Derive final verdict from events
  const toolCallCount = events.filter((e) => e.type === "tool_call").length;
  const finalEvent = events.find((e) => e.type === "final");
  const updateEvent = events.find(
    (e) => e.type === "tool_result" && e.name === "update_contact"
  );
  const flagEvent = events.find(
    (e) => e.type === "tool_result" && e.name === "flag_for_review"
  );

  const verdictStyle =
    updateEvent?.result?.status === "active"
      ? "bg-green-50 border-green-200 text-green-800"
      : updateEvent?.result?.status === "inactive"
        ? "bg-[#f9fafb] border-[#e5e7eb] text-[#0B0B0B]"
        : flagEvent
          ? "bg-[#f9fafb] border-[#e5e7eb] text-[#0B0B0B]"
          : "bg-[#f9fafb] border-[#e5e7eb] text-[#6B7280]";

  const verdictLabel =
    updateEvent?.result?.status === "active"
      ? "Verified Active"
      : updateEvent?.result?.status === "inactive"
        ? "Marked Inactive"
        : flagEvent
          ? "Flagged for Human Review"
          : "Agent Complete";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B0B0B]/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded border border-[#e5e7eb] w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 shadow-sm">

        {/* ── Header ── */}
        <div className="px-6 py-4 border-b border-[#e5e7eb] flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-[#f9fafb] border border-[#e5e7eb] flex items-center justify-center">
              <Wand2 size={16} className="text-[#0B0B0B]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#0B0B0B] tracking-tight">
                AI Verification Agent
              </h3>
              <p className="text-[11px] font-mono text-[#6B7280]">
                {contact.name} · {contact.organization}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {running && (
              <span className="text-[11px] font-mono text-[#9ca3af] flex items-center gap-1">
                <Clock size={11} />
                {elapsed}s
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded text-[#9ca3af] hover:text-[#0B0B0B] hover:bg-[#f9fafb] transition-colors focus:outline-none"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* ── Timeline ── */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2 min-h-0 bg-white">

          {/* Empty state */}
          {events.length === 0 && !running && (
            <div className="flex flex-col items-center justify-center py-16 text-[#9ca3af]">
              <Wand2 size={32} className="mb-3 opacity-30 text-[#0B0B0B]" />
              <p className="text-[13px] font-bold text-[#0B0B0B]">Ready to verify</p>
              <p className="text-[11px] font-mono mt-1 text-center text-[#6B7280]">
                Claude will autonomously choose tools and iterate until it reaches a verdict
              </p>
            </div>
          )}

          {events.map((event, i) => {
            // skip "start" and "done" — handled separately
            if (event.type === "start" || event.type === "done") return null;

            if (event.type === "thinking") {
              return (
                <div key={i} className="flex gap-2.5 items-start">
                  <div className="w-5 h-5 rounded bg-[#f9fafb] border border-[#e5e7eb] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Brain size={10} className="text-[#6B7280]" />
                  </div>
                  <p className="text-[12px] text-[#6B7280] italic leading-relaxed">
                    {event.text}
                  </p>
                </div>
              );
            }

            if (event.type === "tool_call") {
              const tool =
                TOOL_LABELS[event.name ?? ""] ?? {
                  label: event.name ?? "Unknown tool",
                  description: "",
                };
              return (
                <div
                  key={i}
                  className="ml-7 bg-[#f9fafb] border border-[#e5e7eb] rounded px-3 py-2.5 flex items-start gap-2"
                >
                  <Wrench size={12} className="text-[#0B0B0B] flex-shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold text-[#0B0B0B] uppercase tracking-wider">
                        {tool.label}
                      </span>
                    </div>
                    <p className="text-[11px] font-mono text-[#6B7280] mt-0.5">{tool.description}</p>
                    {event.input && Object.keys(event.input).length > 0 && (
                      <pre className="text-[10px] font-mono text-[#6B7280] mt-1.5 overflow-x-auto whitespace-pre-wrap break-all bg-white border border-[#e5e7eb] rounded p-1.5">
                        {JSON.stringify(event.input, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              );
            }

            if (event.type === "tool_result") {
              const isError =
                event.result?.error != null || event.result?.success === false;
              return (
                <div
                  key={i}
                  className={`ml-7 rounded px-3 py-2.5 flex items-start gap-2 border ${isError
                      ? "bg-red-50 border-red-200"
                      : "bg-[#f9fafb] border-[#e5e7eb]"
                    }`}
                >
                  <CheckCircle2
                    size={12}
                    className={`flex-shrink-0 mt-0.5 ${isError ? "text-red-500" : "text-[#3DF577]"}`}
                  />
                  <div className="min-w-0 flex-1">
                    <span
                      className={`text-[11px] font-bold uppercase tracking-wider ${isError ? "text-red-700" : "text-[#0B0B0B]"}`}
                    >
                      {isError ? "Error" : "Result"}
                    </span>
                    <pre
                      className={`text-[10px] font-mono mt-1 overflow-x-auto whitespace-pre-wrap break-all rounded p-1.5 border ${isError
                          ? "text-red-600 bg-red-100/50 border-transparent"
                          : "text-[#6B7280] bg-white border-[#e5e7eb]"
                        }`}
                    >
                      {JSON.stringify(event.result, null, 2)}
                    </pre>
                  </div>
                </div>
              );
            }

            if (event.type === "error") {
              return (
                <div key={i} className="flex gap-2.5 items-start">
                  <AlertTriangle
                    size={14}
                    className="text-red-500 flex-shrink-0 mt-0.5"
                  />
                  <p className="text-[12px] text-red-600 font-bold">
                    {event.message}
                  </p>
                </div>
              );
            }

            return null;
          })}

          {/* Final verdict card */}
          {done && (finalEvent || updateEvent || flagEvent) && (
            <div className={`mt-3 rounded border px-4 py-3 ${verdictStyle}`}>
              <p className="text-[11px] font-bold uppercase tracking-wider mb-1">
                {verdictLabel}
              </p>
              {finalEvent?.text && (
                <p className="text-[12px] font-mono leading-relaxed text-[#6B7280]">{finalEvent.text}</p>
              )}
            </div>
          )}

          {/* Completion banner */}
          {done && (
            <div className="mt-2 flex items-center gap-2 text-[11px] font-mono text-[#9ca3af] justify-center py-1">
              <CheckCircle2 size={12} className="text-[#3DF577]" />
              Agent completed in {elapsed}s · {toolCallCount} tool call
              {toolCallCount !== 1 ? "s" : ""}
            </div>
          )}

          {/* Live spinner */}
          {running && (
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#0B0B0B] justify-center py-2 animate-pulse">
              <Loader2 size={12} className="animate-spin text-[#3DF577]" />
              Agent is thinking...
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Footer ── */}
        <div className="px-6 py-4 border-t border-[#e5e7eb] bg-[#f9fafb] flex items-center justify-between flex-shrink-0">
          <p className="text-[11px] font-mono text-[#9ca3af]">
            {toolCallCount > 0
              ? `${toolCallCount} tool call${toolCallCount !== 1 ? "s" : ""}`
              : "No tool calls yet"}
          </p>
          <div className="flex gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-[13px] font-semibold text-[#6B7280] hover:bg-white border border-transparent hover:border-[#e5e7eb] active:scale-[0.97] transition-all"
            >
              Close
            </button>
            <button
              onClick={runAgent}
              disabled={running}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#3DF577] text-[#0B0B0B] rounded text-[13px] font-bold hover:bg-[#34d366] active:scale-[0.97] shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest font-mono border border-transparent"
            >
              {running ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Wand2 size={13} />
                  Run Agent
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
