import { useState, useEffect } from "react";
import type { Contact } from "../types";
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
  X,
  Loader2,
} from "lucide-react";

export default function ReviewQueue() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionModal, setActionModal] = useState<{
    type: "deactivate" | "verify";
    contact: Contact;
  } | null>(null);
  const [isActioning, setIsActioning] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    fetchReviewQueue();
  }, []);

  async function fetchReviewQueue() {
    setLoading(true);
    try {
      const res = await fetch("/api/contacts/review", {
        headers: { "X-API-Key": "dev-key" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Contact[] = await res.json();
      setContacts(data);
      if (data.length > 0) setExpandedId(data[0].id);
    } catch (err: any) {
      console.error("Failed to fetch review queue:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!actionModal) return;
    setIsActioning(true);
    setActionError(null);
    const { type, contact } = actionModal;
    const updated = {
      ...contact,
      status: type === "deactivate" ? "inactive" : "active",
      needs_human_review: false,
      review_reason: null,
    };
    try {
      const res = await fetch("/api/contacts", {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-API-Key": "dev-key" },
        body: JSON.stringify(updated),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `HTTP ${res.status}`);
      }
      setContacts((prev) => prev.filter((c) => c.id !== contact.id));
      setActionModal(null);
    } catch (err: any) {
      setActionError(err.message || "Action failed.");
    } finally {
      setIsActioning(false);
    }
  }

  const displayContacts =
    contacts.length > 0
      ? contacts
      : ([
          {
            id: "review1",
            name: "Tom Cook",
            email: "tom@acme.com",
            title: "Director",
            organization: "Acme Corp",
            status: "unknown",
            review_reason:
              "Agent conflict: 'Director of Engineering' found on LinkedIn, but email bounced. Manual verification required.",
            district_website: "https://acme.com",
          },
        ] as Contact[]);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-[#6B7280]">
        <Loader2 size={16} className="animate-spin mr-2" />
        <span className="text-[13px] font-mono">Loading review queue…</span>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 pl-1">
        <h1 className="text-[32px] font-bold text-[#0B0B0B] tracking-tight mb-1 font-serif">
          Review Queue
        </h1>
        <p className="text-[12px] font-mono text-[#6B7280] uppercase tracking-widest font-semibold flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-[#3DF577] rounded-full inline-block"></span>{" "}
          <span>Pending Manual Checks</span>
        </p>
      </div>

      <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#e5e7eb]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-[#f9fafb] border border-[#e5e7eb] flex items-center justify-center text-[#0B0B0B]">
              <Sparkles size={16} />
            </div>
            <div>
              <h2 className="text-[16px] font-bold text-[#0B0B0B] tracking-tight">
                Manual Verifications
              </h2>
              <p className="text-[11px] font-mono text-[#6B7280]">
                Agentic escalation queue
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {displayContacts.map((contact) => {
            const isExpanded = expandedId === contact.id;
            return (
              <div
                key={contact.id}
                className={`rounded border transition-all duration-200 overflow-hidden ${isExpanded ? "border-[#0B0B0B] shadow-sm bg-white" : "border-[#e5e7eb] bg-[#f9fafb] hover:bg-white hover:border-[#0B0B0B]"}`}
              >
                <button
                  onClick={() => toggleExpand(contact.id)}
                  className="w-full text-left px-5 py-4 flex items-center justify-between focus:outline-none"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded bg-[#f9fafb] flex items-center justify-center text-[#0B0B0B] font-bold text-[13px] border border-[#e5e7eb] relative">
                      {contact.name
                        .split(" ")
                        .map((n: string) => n[0])
                        .join("")}
                      <div className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded border-2 border-white flex items-center justify-center bg-white">
                        <AlertCircle size={12} className="text-[#3DF577]" />
                      </div>
                    </div>
                    <div className="flex flex-col">
                      <h3 className="font-bold text-[#0B0B0B] text-[14px] tracking-tight">
                        {contact.name}
                      </h3>
                      <p className="text-[12px] text-[#6B7280] font-mono mt-0.5">
                        {contact.organization}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-5">
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold tracking-widest bg-white border border-[#0B0B0B] text-[#0B0B0B] shadow-sm">
                      NEEDS REVIEW
                    </span>
                    <div
                      className={`w-6 h-6 rounded flex items-center justify-center transition-colors border ${isExpanded ? "bg-[#0B0B0B] text-white border-[#0B0B0B]" : "bg-white text-[#6B7280] border-[#e5e7eb]"}`}
                    >
                      {isExpanded ? (
                        <ChevronUp size={14} />
                      ) : (
                        <ChevronDown size={14} />
                      )}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-5 py-5 border-t border-[#e5e7eb] grid grid-cols-1 lg:grid-cols-2 gap-6 bg-[#f9fafb]">
                    <div className="space-y-4">
                      <p className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1">
                        Target Profile Document
                      </p>
                      <div className="bg-white border border-[#e5e7eb] rounded p-4 shadow-sm">
                        <div className="space-y-3 font-mono text-[12px]">
                          <div className="flex justify-between items-center border-b border-[#e5e7eb] pb-2">
                            <span className="text-[#6B7280]">Title Field</span>
                            <span className="font-bold text-[#0B0B0B] bg-[#f9fafb] px-1.5 py-0.5 rounded border border-[#e5e7eb]">
                              {contact.title || "Unknown"}
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-b border-[#e5e7eb] pb-2">
                            <span className="text-[#6B7280]">
                              Email Address
                            </span>
                            <span className="font-bold text-[#0B0B0B]">
                              {contact.email}
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-[#6B7280]">System State</span>
                            <span className="font-bold text-[#0B0B0B] capitalize border border-[#e5e7eb] bg-[#f9fafb] px-1.5 py-0.5 rounded">
                              {contact.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col justify-between">
                      <div className="flex-1 space-y-4">
                        <p className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1">
                          Agent Diagnostic
                        </p>
                        <div className="bg-white font-mono border border-[#e5e7eb] text-[#0B0B0B] text-[12px] p-4 rounded shadow-sm border-l-2 border-l-[#0B0B0B]">
                          {contact.review_reason}
                        </div>
                      </div>

                      <div className="flex justify-end gap-3 pt-4 font-mono">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActionModal({ type: "deactivate", contact });
                          }}
                          className="px-4 py-2 bg-white border border-[#e5e7eb] rounded text-[11px] font-bold text-[#0B0B0B] hover:bg-[#f9fafb] transition-colors uppercase tracking-widest shadow-sm"
                        >
                          Deactivate Data
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActionModal({ type: "verify", contact });
                          }}
                          className="flex items-center gap-1.5 px-4 py-2 bg-[#3DF577] border border-transparent rounded text-[11px] font-bold text-[#0B0B0B] hover:bg-[#34d366] transition-colors shadow-sm uppercase tracking-widest"
                        >
                          <CheckCircle size={14} /> Verify & Update
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Modal */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-[16px] font-bold text-slate-900">
                {actionModal.type === "deactivate"
                  ? "Deactivate Contact"
                  : "Verify Contact"}
              </h3>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-400 hover:text-slate-700 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6">
              <p className="text-[13px] text-slate-600 leading-relaxed font-mono">
                {actionModal.type === "deactivate"
                  ? `Are you sure you want to deactivate ${actionModal.contact.name}? This will remove them from active agentic sync.`
                  : `Confirm that ${actionModal.contact.name}'s data is accurate and resolve the review flag. They will be returned to active agentic sync.`}
              </p>
            </div>

            {actionError && (
              <div className="px-6 pb-2 text-[12px] text-red-600 font-mono">
                {actionError}
              </div>
            )}
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3">
              <button
                onClick={() => {
                  setActionModal(null);
                  setActionError(null);
                }}
                disabled={isActioning}
                className="px-5 py-2.5 rounded text-[13px] font-bold text-slate-600 hover:bg-slate-200 transition-colors font-mono uppercase tracking-widest disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isActioning}
                className={`flex items-center gap-1.5 px-5 py-2.5 text-white rounded text-[13px] font-bold shadow-sm transition-colors font-mono uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed ${actionModal.type === "deactivate" ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"}`}
              >
                {isActioning && <Loader2 size={13} className="animate-spin" />}
                {isActioning ? "Saving…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
