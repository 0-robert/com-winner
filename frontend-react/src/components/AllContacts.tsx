import { useState, useEffect } from "react";
import type { Contact, ChangeSummary } from "../types";
import {
  MoreVertical,
  FileText,
  CheckCircle2,
  X,
  ExternalLink,
  RefreshCw,
  Edit,
  Trash,
  Mail,
  Send,
  Loader2,
  ChevronDown,
  ChevronRight,
  Wand2,
} from "lucide-react";
import AgentWorkbench from "./AgentWorkbench";

// ── Freshness helpers ────────────────────────────────────────────────────────

type FreshnessLevel = "fresh" | "idle" | "stale" | "never";

function getFreshness(contact: Contact): FreshnessLevel {
  if (!contact.last_scraped_at) return "never";
  const days =
    (Date.now() - new Date(contact.last_scraped_at).getTime()) / 86_400_000;
  if (days < 30) return "fresh";
  if (days < 90) return "idle";
  return "stale";
}

function latestScrapeChangedData(contact: Contact): boolean {
  if (!contact.last_scraped_at || !contact.last_changed_at) return false;
  const diff = Math.abs(
    new Date(contact.last_scraped_at).getTime() -
      new Date(contact.last_changed_at).getTime(),
  );
  return diff < 5 * 60 * 1000;
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return "just now";
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const days = Math.floor(ms / 86_400_000);
  if (days < 1) return "today";
  if (days === 1) return "1d ago";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

const FRESHNESS_CONFIG: Record<
  FreshnessLevel,
  { dot: string; badge: string; label: string }
> = {
  fresh: {
    dot: "bg-green-500",
    badge: "bg-green-50 text-green-700 border-green-200",
    label: "FRESH",
  },
  idle: {
    dot: "bg-amber-400",
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    label: "IDLE",
  },
  stale: {
    dot: "bg-orange-500",
    badge: "bg-orange-50 text-orange-700 border-orange-200",
    label: "STALE",
  },
  never: {
    dot: "bg-slate-300",
    badge: "bg-slate-50 text-slate-500 border-slate-200",
    label: "NEVER",
  },
};

function getConfidenceScore(contact: Contact): string {
  const f = getFreshness(contact);
  const base: Record<FreshnessLevel, number> = {
    fresh: 92,
    idle: 68,
    stale: 42,
    never: 15,
  };
  let score = base[f];
  if (contact.status === "active") score = Math.min(score + 5, 97);
  if (contact.status === "inactive") score = Math.min(score + 4, 95);
  if (contact.needs_human_review) score = Math.max(score - 8, 10);
  return `${score}%`;
}

function getInsightText(contact: Contact): string {
  const f = getFreshness(contact);
  const changed = latestScrapeChangedData(contact);
  if (f === "never")
    return "No LinkedIn data synced yet. Run agent sync to verify current status before outreach.";
  if (contact.status === "inactive")
    return "Contact marked inactive. If a replacement was found, prioritise that contact instead.";
  if (contact.status === "active" && f === "fresh")
    return "Contact verified active. LinkedIn data is current — high confidence for outreach.";
  if (contact.status === "active")
    return "Contact marked active but LinkedIn data is ageing — re-sync before outreach.";
  if (f === "fresh" && changed)
    return "LinkedIn profile changed since last check. Review the diff below before outreach.";
  if (f === "fresh")
    return "LinkedIn data is current. Status unresolved — agent sync complete, manual review may help.";
  return "LinkedIn data is ageing. Re-sync to get the latest role before outreach.";
}

// ── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  active: {
    label: "CONFIRMED ACTIVE",
    badge: "bg-green-50 text-green-700 border-green-200",
  },
  unknown: {
    label: "NEEDS REVIEW",
    badge: "bg-orange-50 text-orange-700 border-orange-200",
  },
  inactive: {
    label: "DEPARTED / INACTIVE",
    badge: "bg-slate-100 text-slate-600 border-slate-200",
  },
  opted_out: {
    label: "OPTED OUT",
    badge: "bg-red-50 text-red-700 border-red-200",
  },
} as const;

// ══════════════════════════════════════════════════════════════════════════════
//  COMPONENT
// ══════════════════════════════════════════════════════════════════════════════

export default function AllContacts() {
  // ── Core state ─────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState("All Contacts");
  const [selectedNotesContact, setSelectedNotesContact] =
    useState<Contact | null>(null);
  const [selectedMoreContact, setSelectedMoreContact] =
    useState<Contact | null>(null);
  const [selectedProfileContact, setSelectedProfileContact] =
    useState<Contact | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  // ── Change detection state ─────────────────────────────────────────────
  const [expandedChange, setExpandedChange] = useState<string | null>(null);
  const [changeDetails, setChangeDetails] = useState<
    Record<string, ChangeSummary | null>
  >({});

  // ── Email sending state ────────────────────────────────────────────────
  const [emailSendingOne, setEmailSendingOne] = useState<string | null>(null);
  const [emailSendingAll, setEmailSendingAll] = useState(false);
  const [emailAllResult, setEmailAllResult] = useState<{
    total_sent: number;
    total_failed: number;
  } | null>(null);

  // ── Agent workbench state ──────────────────────────────────────────────
  const [agentContact, setAgentContact] = useState<Contact | null>(null);

  // ── Edit / Delete state ────────────────────────────────────────────────
  const [editContact, setEditContact] = useState<Contact | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    email: "",
    title: "",
    organization: "",
    linkedin_url: "",
  });
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // ── Fetch contacts from API ────────────────────────────────────────────
  const fetchContacts = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await fetch("/api/contacts", {
        headers: { "X-API-Key": "dev-key" },
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data: Contact[] = await res.json();
      setContacts(data);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Failed to load contacts.",
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleChangeDetail = async (contactId: string) => {
    if (expandedChange === contactId) {
      setExpandedChange(null);
      return;
    }
    setExpandedChange(contactId);
    if (changeDetails[contactId] !== undefined) return;
    try {
      const res = await fetch(`/api/contacts/${contactId}/linkedin-change`, {
        headers: { "X-API-Key": "dev-key" },
      });
      const data: ChangeSummary = await res.json();
      setChangeDetails((prev) => ({
        ...prev,
        [contactId]: Object.keys(data).length ? data : null,
      }));
    } catch {
      setChangeDetails((prev) => ({ ...prev, [contactId]: null }));
    }
  };

  useEffect(() => {
    fetchContacts();
  }, []);

  // ── Email helpers ──────────────────────────────────────────────────────
  const sendEmailToOne = async (contact: Contact) => {
    if (contact.status === "opted_out") {
      alert("Contact has opted out — cannot send email.");
      return;
    }
    setEmailSendingOne(contact.id);
    try {
      const res = await fetch("/api/email/send-one", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": "dev-key" },
        body: JSON.stringify({ contact_id: contact.id }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to send email");
        return;
      }
      if (data.success) {
        alert(`Email sent to ${data.email}`);
      } else {
        alert(`Email failed: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      alert("Network error sending email. Is the API running?");
    } finally {
      setEmailSendingOne(null);
    }
  };

  const sendEmailToAll = async () => {
    if (
      !confirm(
        `Send info-review emails to all ${contacts.filter((c) => c.status !== "opted_out").length} eligible contacts?`,
      )
    )
      return;
    setEmailSendingAll(true);
    setEmailAllResult(null);
    try {
      const res = await fetch("/api/email/send-all", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": "dev-key" },
        body: JSON.stringify({ limit: 500, concurrency: 5 }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to send emails");
        return;
      }
      setEmailAllResult({
        total_sent: data.total_sent,
        total_failed: data.total_failed,
      });
    } catch (err) {
      console.error(err);
      alert("Network error sending emails. Is the API running?");
    } finally {
      setEmailSendingAll(false);
    }
  };

  // ── Tabs ───────────────────────────────────────────────────────────────
  const tabs = ["All Contacts", "Review Required", "Departed"];

  // ── Delete handler ─────────────────────────────────────────────────────
  const deleteContact = async (contact: Contact) => {
    if (!confirm(`Delete ${contact.name}? This cannot be undone.`)) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/contacts/${contact.id}`, {
        method: "DELETE",
        headers: { "X-API-Key": "dev-key" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setContacts((prev) => prev.filter((c) => c.id !== contact.id));
      setSelectedMoreContact(null);
      setSyncError(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setIsDeleting(false);
    }
  };

  // ── Edit handlers ──────────────────────────────────────────────────────
  const openEditModal = (contact: Contact) => {
    setEditContact(contact);
    setEditForm({
      name: contact.name || "",
      email: contact.email || "",
      title: contact.title || "",
      organization: contact.organization || "",
      linkedin_url: contact.linkedin_url || "",
    });
    setEditError(null);
    setSelectedMoreContact(null);
  };

  const saveEdit = async () => {
    if (!editContact) return;
    if (!editForm.name.trim() || !editForm.organization.trim()) {
      setEditError("Name and Organization are required.");
      return;
    }
    setIsSavingEdit(true);
    setEditError(null);
    try {
      const res = await fetch("/api/contacts", {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-API-Key": "dev-key" },
        body: JSON.stringify({
          ...editContact,
          name: editForm.name.trim(),
          email: editForm.email.trim(),
          title: editForm.title.trim(),
          organization: editForm.organization.trim(),
          linkedin_url: editForm.linkedin_url.trim() || null,
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `HTTP ${res.status}`);
      }
      const updated: Contact = await res.json();
      setContacts((prev) =>
        prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)),
      );
      setEditContact(null);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setIsSavingEdit(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div>
      <div className="mb-6 pl-1">
        <h1 className="text-[24px] font-bold text-slate-900 tracking-tight mb-1">
          Manage Contacts
        </h1>
        <p className="text-[12px] font-mono text-slate-500 uppercase tracking-widest font-semibold flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full inline-block"></span> Agentic Database
        </p>
      </div>

      <div className="bg-white rounded border border-slate-200 p-6 shadow-sm">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded text-[12px] font-bold transition-all border ${activeTab === tab ? "bg-white border-blue-600 text-blue-700 shadow-sm" : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-800"}`}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={sendEmailToAll}
              disabled={emailSendingAll}
              className="px-4 py-1.5 bg-emerald-600 text-white rounded text-[12px] font-bold shadow-sm hover:bg-emerald-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {emailSendingAll ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              {emailSendingAll ? "Sending..." : "Email All Contacts"}
            </button>
            <button
              onClick={fetchContacts}
              disabled={loading}
              className="px-4 py-1.5 bg-blue-600 text-white rounded text-[12px] font-bold shadow-sm hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-60"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              {loading ? "Loading..." : "Refresh Contacts"}
            </button>
          </div>
        </div>

        {/* Email-all result banner */}
        {emailAllResult && (
          <div className="mb-4 p-3 rounded border border-emerald-200 bg-emerald-50 flex items-center justify-between">
            <p className="text-[12px] font-semibold text-emerald-800">
              Sent {emailAllResult.total_sent} email
              {emailAllResult.total_sent !== 1 ? "s" : ""}
              {emailAllResult.total_failed > 0 && (
                <span className="text-red-600 ml-2">
                  ({emailAllResult.total_failed} failed)
                </span>
              )}
            </p>
            <button
              onClick={() => setEmailAllResult(null)}
              className="text-emerald-600 hover:text-emerald-800"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 px-4 pb-3 text-[11px] font-mono font-bold text-slate-500 uppercase tracking-widest border-b border-slate-100">
          <div className="col-span-3">Client</div>
          <div className="col-span-2">Org / Role</div>
          <div className="col-span-1">Notes</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-3">Freshness</div>
          <div className="col-span-1 text-right">More</div>
        </div>

        {/* Rows */}
        <div className="space-y-1 relative pt-2">
          {loadError && (
            <div className="py-6 text-center text-red-600 text-[12px] font-mono bg-red-50 rounded border border-red-200">
              {loadError} —{" "}
              <button
                onClick={fetchContacts}
                className="underline hover:no-underline"
              >
                retry
              </button>
            </div>
          )}
          {!loadError && contacts.length === 0 && !loading && (
            <div className="py-12 text-center text-slate-400 text-[13px] font-mono">
              No contacts found.
            </div>
          )}
          {loading && contacts.length === 0 && (
            <div className="space-y-0.5 pt-1">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="grid grid-cols-12 gap-4 px-4 py-3 items-center animate-pulse">
                  <div className="col-span-3 flex items-center gap-3">
                    <div className="w-3.5 h-3.5 rounded-sm bg-slate-200 shrink-0"></div>
                    <div className="w-8 h-8 rounded bg-slate-200 shrink-0"></div>
                    <div className="flex flex-col gap-1.5 min-w-0 flex-1">
                      <div className="h-2.5 bg-slate-200 rounded w-3/4"></div>
                      <div className="h-2 bg-slate-100 rounded w-1/2"></div>
                    </div>
                  </div>
                  <div className="col-span-2 space-y-1.5">
                    <div className="h-2.5 bg-slate-200 rounded w-4/5"></div>
                    <div className="h-2 bg-slate-100 rounded w-3/5"></div>
                  </div>
                  <div className="col-span-1"><div className="w-7 h-7 bg-slate-100 rounded"></div></div>
                  <div className="col-span-2"><div className="h-5 bg-slate-100 rounded w-20"></div></div>
                  <div className="col-span-3"><div className="h-5 bg-slate-100 rounded w-14"></div></div>
                  <div className="col-span-1"></div>
                </div>
              ))}
            </div>
          )}
          {contacts.map((contact) => {
            const freshness = getFreshness(contact);
            const fc = FRESHNESS_CONFIG[freshness];
            const isExpanded = expandedChange === contact.id;
            const detail = changeDetails[contact.id];

            return (
              <div key={contact.id} className="group relative transition-colors duration-150 rounded border border-transparent hover:border-slate-100 hover:bg-slate-50/70">
                <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center rounded">
                  {/* Client */}
                  <div className="col-span-3 flex items-center gap-3">
                    <div className="w-3.5 h-3.5 rounded-sm border border-slate-300 pointer-events-none group-hover:border-blue-400 bg-white flex-shrink-0"></div>
                    <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px] flex-shrink-0">
                      {contact.name
                        .split(" ")
                        .map((n: string) => n[0])
                        .join("")}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[13px] font-bold text-slate-900 truncate">
                        {contact.name}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500 truncate">
                        {contact.email}
                      </span>
                    </div>
                  </div>

                  {/* Org / Role */}
                  <div className="col-span-2 flex flex-col justify-center min-w-0">
                    <span className="text-[12px] font-bold text-slate-800 truncate">
                      {contact.organization}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500 truncate">
                      {contact.title || "Unknown Role"}
                    </span>
                  </div>

                  {/* Notes */}
                  <div className="col-span-1 flex items-center">
                    <button
                      onClick={() => setSelectedNotesContact(contact)}
                      className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-400 hover:text-blue-600 hover:border-blue-200 transition-colors bg-white shadow-sm"
                    >
                      <FileText size={12} />
                    </button>
                  </div>

                  {/* Status */}
                  <div className="col-span-2 flex items-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider inline-flex items-center gap-1 border uppercase shadow-sm ${contact.needs_human_review ? STATUS_CONFIG.unknown.badge : STATUS_CONFIG[contact.status as keyof typeof STATUS_CONFIG]?.badge || STATUS_CONFIG.inactive.badge}`}
                    >
                      {contact.status === "active" && (
                        <CheckCircle2 size={10} />
                      )}
                      {contact.needs_human_review ? "REVIEW" : contact.status}
                    </span>
                  </div>

                  {/* Freshness */}
                  <div className="col-span-3 flex items-center gap-2">
                    <div className="relative group/tip">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider inline-flex items-center gap-1.5 border uppercase shadow-sm cursor-default ${fc.badge}`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${fc.dot}`}
                        />
                        {fc.label}
                      </span>
                      {freshness !== "never" && (
                        <div className="absolute bottom-full left-0 mb-1.5 z-20 opacity-0 group-hover/tip:opacity-100 pointer-events-none transition-opacity duration-150">
                          <div className="bg-slate-900 text-white text-[11px] font-mono rounded px-2.5 py-1.5 whitespace-nowrap shadow-lg">
                            <div>
                              Scraped {timeAgo(contact.last_scraped_at)}
                            </div>
                            <div>
                              Changed {timeAgo(contact.last_changed_at)}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {latestScrapeChangedData(contact) && (
                      <button
                        onClick={() => toggleChangeDetail(contact.id)}
                        className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 transition-colors"
                        title="Show what changed"
                      >
                        <span>CHANGED</span>
                        {isExpanded ? (
                          <ChevronDown size={10} />
                        ) : (
                          <ChevronRight size={10} />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="col-span-1 flex items-center justify-end gap-0.5">
                    <button
                      onClick={() => setAgentContact(contact)}
                      className="text-slate-400 hover:text-purple-600 transition-colors p-1 rounded hover:bg-purple-50"
                      title="Run AI verification agent"
                    >
                      <Wand2 size={14} />
                    </button>
                    <button
                      onClick={() => setSelectedMoreContact(contact)}
                      className="text-slate-400 hover:text-slate-800 transition-colors p-1 rounded hover:bg-slate-200"
                    >
                      <MoreVertical size={16} />
                    </button>
                  </div>
                </div>

                {/* Expanded change detail */}
                {isExpanded && latestScrapeChangedData(contact) && (
                  <div className="mx-4 mb-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded text-[11px] font-mono text-slate-600 space-y-1">
                    {detail === undefined && (
                      <span className="text-slate-400">Loading...</span>
                    )}
                    {detail === null && (
                      <span className="text-slate-400">
                        No change data available.
                      </span>
                    )}
                    {detail &&
                      Object.entries({
                        title: { from: detail.title_from, to: detail.title_to },
                        org: { from: detail.org_from, to: detail.org_to },
                        headline: {
                          from: detail.headline_from,
                          to: detail.headline_to,
                        },
                      }).map(([key, { from, to }]) =>
                        from || to ? (
                          <div key={key} className="flex items-center gap-2">
                            <span className="text-slate-400 w-16 flex-shrink-0 capitalize">
                              {key}
                            </span>
                            <span className="text-red-500 line-through truncate max-w-[140px]">
                              {from || "—"}
                            </span>
                            <span className="text-slate-400">→</span>
                            <span className="text-green-600 font-semibold truncate max-w-[140px]">
                              {to || "—"}
                            </span>
                          </div>
                        ) : null,
                      )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Notes Modal ──────────────────────────────────────────────────── */}
      {selectedNotesContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="text-[16px] font-bold text-slate-900 flex items-center gap-2">
                  <FileText size={16} className="text-slate-400" />
                  Agentic Notes
                </h3>
                <p className="text-[11px] font-mono text-slate-500 mt-1">
                  {selectedNotesContact.name} (
                  {selectedNotesContact.organization})
                </p>
              </div>
              <button
                onClick={() => setSelectedNotesContact(null)}
                className="text-slate-400 hover:text-slate-700 transition-colors p-1"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 bg-slate-50/30">
              <div className="bg-white border border-slate-200 rounded p-4 font-mono text-[12px] text-slate-600 leading-relaxed shadow-sm min-h-[150px]">
                {selectedNotesContact.needs_human_review ? (
                  <>
                    <span className="text-orange-600 font-bold">
                      [!] FLAG: NEEDS REVIEW
                    </span>
                    <br />
                    <br />
                    - Could not locate on district website.
                    <br />
                    - LinkedIn profile is private or not exact match.
                    <br />- Claude analysis: "Uncertain if still at{" "}
                    {selectedNotesContact.organization}. Proceed with caution."
                    <br />
                  </>
                ) : (
                  <>
                    <span className="text-green-600 font-bold">
                      [✓] VERIFIED ACTIVE
                    </span>
                    <br />
                    <br />- Found on {selectedNotesContact.organization} staff
                    page.
                    <br />
                    - No conflicting data on LinkedIn.
                    <br />
                    - Claude analysis: "High confidence still active."
                    <br />
                  </>
                )}
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
              <button
                onClick={() => setSelectedNotesContact(null)}
                className="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 rounded text-[13px] font-bold hover:bg-slate-50 shadow-sm transition-colors"
              >
                Close Notes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── More Options Modal ───────────────────────────────────────────── */}
      {selectedMoreContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px]">
                  {selectedMoreContact.name
                    ?.split(" ")
                    .map((n: string) => n[0])
                    .join("")}
                </div>
                <h3 className="text-[14px] font-bold text-slate-900">
                  {selectedMoreContact.name}
                </h3>
              </div>
              <button
                onClick={() => {
                  setSelectedMoreContact(null);
                  setSyncError(null);
                }}
                className="text-slate-400 hover:text-slate-700 transition-colors p-1"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-2">
              <button
                onClick={() => {
                  setSelectedProfileContact(selectedMoreContact);
                  setSelectedMoreContact(null);
                }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors"
              >
                <ExternalLink size={16} className="text-slate-400" />
                <span className="text-[13px] font-semibold text-slate-700">
                  View Scraped profile
                </span>
              </button>
              <button
                onClick={() => {
                  if (selectedMoreContact?.linkedin_url) {
                    window.open(selectedMoreContact.linkedin_url, "_blank");
                  }
                  setSelectedMoreContact(null);
                }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors"
              >
                <ExternalLink size={16} className="text-slate-400" />
                <span className="text-[13px] font-semibold text-slate-700">
                  Open LinkedIn
                </span>
              </button>
              <button
                onClick={async () => {
                  if (!selectedMoreContact?.linkedin_url) {
                    setSyncError("No LinkedIn URL on file for this contact.");
                    return;
                  }
                  setSyncError(null);
                  try {
                    const res = await fetch("/api/scrape", {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        "X-API-Key": "dev-key",
                      },
                      body: JSON.stringify({
                        linkedin_url: selectedMoreContact.linkedin_url,
                        contact_name: selectedMoreContact.name,
                        organization: selectedMoreContact.organization,
                        contact_id: selectedMoreContact.id,
                      }),
                    });
                    const data = await res.json();
                    console.log("Scrape successful:", data);

                    if (data.success) {
                      await fetchContacts();
                      setContacts((prev) =>
                        prev.map((c) =>
                          c.id === selectedMoreContact.id
                            ? {
                                ...c,
                                title: data.current_title || c.title,
                                organization:
                                  data.current_organization || c.organization,
                                status: data.still_at_organization
                                  ? "active"
                                  : "unknown",
                                needs_human_review: !data.still_at_organization,
                                experience: data.experience,
                                education: data.education,
                                skills: data.skills,
                                employment_confidence:
                                  data.employment_confidence,
                              }
                            : c,
                        ),
                      );
                    }
                    setSelectedMoreContact(null);
                  } catch (err) {
                    setSyncError(
                      err instanceof Error
                        ? err.message
                        : "Sync failed — check that the LinkedIn API is running.",
                    );
                  }
                }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors"
              >
                <RefreshCw size={16} className="text-slate-400" />
                <span className="text-[13px] font-semibold text-slate-700">
                  Force Agentic Sync
                </span>
              </button>
              <button
                onClick={() => openEditModal(selectedMoreContact)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors"
              >
                <Edit size={16} className="text-slate-400" />
                <span className="text-[13px] font-semibold text-slate-700">
                  Edit Contact Data
                </span>
              </button>
              <button
                onClick={async () => {
                  if (!selectedMoreContact) return;
                  await sendEmailToOne(selectedMoreContact);
                  setSelectedMoreContact(null);
                }}
                disabled={emailSendingOne === selectedMoreContact?.id}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-emerald-50 rounded text-left transition-colors disabled:opacity-50"
              >
                {emailSendingOne === selectedMoreContact?.id ? (
                  <Loader2
                    size={16}
                    className="text-emerald-500 animate-spin"
                  />
                ) : (
                  <Mail size={16} className="text-emerald-500" />
                )}
                <span className="text-[13px] font-semibold text-emerald-700">
                  {emailSendingOne === selectedMoreContact?.id
                    ? "Sending..."
                    : "Send Info-Review Email"}
                </span>
              </button>
            </div>
            {syncError && (
              <div className="mx-2 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded text-[11px] font-mono text-red-600">
                {syncError}
              </div>
            )}
            <div className="p-2 border-t border-slate-100 bg-slate-50/50">
              <button
                onClick={() => deleteContact(selectedMoreContact)}
                disabled={isDeleting}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-50 rounded text-left transition-colors group disabled:opacity-50"
              >
                {isDeleting ? (
                  <Loader2 size={16} className="text-red-400 animate-spin" />
                ) : (
                  <Trash
                    size={16}
                    className="text-red-400 group-hover:text-red-600 transition-colors"
                  />
                )}
                <span className="text-[13px] font-semibold text-red-600">
                  {isDeleting ? "Deleting..." : "Delete Contact"}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Profile Detail Modal ─────────────────────────────────────────── */}
      {selectedProfileContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200 flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold border border-blue-700 text-[18px] shadow-sm">
                  {selectedProfileContact.name
                    ?.split(" ")
                    .map((n: string) => n[0])
                    .join("")}
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-slate-900 leading-tight">
                    {selectedProfileContact.name}
                  </h3>
                  <p className="text-[12px] font-mono text-slate-500 font-semibold">
                    {selectedProfileContact.organization} —{" "}
                    {selectedProfileContact.title}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedProfileContact(null)}
                className="text-slate-400 hover:text-slate-700 transition-colors p-2 hover:bg-slate-100 rounded-full"
              >
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30">
              <div className="grid grid-cols-12 gap-8">
                {/* Left Column: Experience */}
                <div className="col-span-8 space-y-6">
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
                    <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                      <h4 className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                        Experience History
                      </h4>
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded border border-blue-100">
                        AGENT VERIFIED
                      </span>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {selectedProfileContact.experience &&
                      selectedProfileContact.experience.length > 0 ? (
                        selectedProfileContact.experience.map((exp, idx) => (
                          <div
                            key={idx}
                            className="p-4 hover:bg-slate-50/50 transition-colors"
                          >
                            <div className="flex justify-between items-start mb-1">
                              <h5 className="text-[13px] font-bold text-slate-900">
                                {exp.title}
                              </h5>
                              {exp.isCurrent && (
                                <span className="px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-bold rounded border border-green-100">
                                  CURRENT
                                </span>
                              )}
                            </div>
                            <p className="text-[12px] text-slate-600 mb-1">
                              {exp.company}
                            </p>
                            <p className="text-[11px] font-mono text-slate-400 mb-3">
                              {exp.dateRange}
                            </p>
                            {exp.description && (
                              <div className="bg-slate-50 rounded p-3 text-[11px] text-slate-500 leading-relaxed border border-slate-100">
                                {exp.description.split("\b").map((line, i) => (
                                  <div key={i} className="mb-1 last:mb-0">
                                    {line}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="p-8 text-center text-slate-400 text-[13px]">
                          No experience data synced yet. Run agent sync to fetch
                          history.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Education section */}
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
                    <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                      <h4 className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                        Education
                      </h4>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {selectedProfileContact.education &&
                      selectedProfileContact.education.length > 0 ? (
                        selectedProfileContact.education.map((edu, idx) => (
                          <div key={idx} className="p-4">
                            <h5 className="text-[13px] font-bold text-slate-900">
                              {edu.institution}
                            </h5>
                            <p className="text-[12px] text-slate-600">
                              {edu.degree}
                            </p>
                            <p className="text-[11px] font-mono text-slate-400">
                              {edu.dateRange}
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="p-6 text-center text-slate-400 text-[13px]">
                          No education data found.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right Column: Meta/Skills */}
                <div className="col-span-4 space-y-6">
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm p-4">
                    <h4 className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-4">
                      Skills
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedProfileContact.skills &&
                      selectedProfileContact.skills.length > 0 ? (
                        selectedProfileContact.skills.map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-slate-50 text-slate-600 text-[11px] font-semibold rounded border border-slate-200"
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <p className="text-slate-400 text-[12px]">
                          No skills found.
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="bg-blue-600 rounded-lg shadow-md p-5 text-white">
                    <h4 className="text-[10px] font-mono font-bold text-blue-100 uppercase tracking-widest mb-3 italic">
                      Autonomous Insights
                    </h4>
                    <p className="text-[13px] font-medium leading-relaxed opacity-95">
                      {getInsightText(selectedProfileContact)}
                    </p>
                    <div className="mt-4 pt-4 border-t border-blue-500/50 flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-blue-200">
                        Confidence Score
                      </span>
                      <span className="text-[16px] font-bold">
                        {selectedProfileContact.employment_confidence != null
                          ? `${Math.round(selectedProfileContact.employment_confidence * 100)}%`
                          : getConfidenceScore(selectedProfileContact)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-100 bg-white flex justify-end gap-3">
              <button
                onClick={() => setSelectedProfileContact(null)}
                className="px-5 py-2 bg-white border border-slate-200 text-slate-700 rounded text-[13px] font-bold hover:bg-slate-50 shadow-sm transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  if (selectedProfileContact.linkedin_url)
                    window.open(selectedProfileContact.linkedin_url, "_blank");
                }}
                className="px-5 py-2 bg-blue-600 text-white rounded text-[13px] font-bold hover:bg-blue-700 shadow-sm transition-colors flex items-center gap-2"
              >
                <ExternalLink size={14} />
                Verify on LinkedIn
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit Contact Modal ───────────────────────────────────────────── */}
      {editContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-[16px] font-bold text-slate-900">
                Edit Contact
              </h3>
              <button
                onClick={() => setEditContact(null)}
                className="text-slate-400 hover:text-slate-700 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {editError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-[12px] font-medium px-4 py-2.5 rounded">
                  {editError}
                </div>
              )}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Full Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, name: e.target.value }))
                  }
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, email: e.target.value }))
                  }
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                    Job Title
                  </label>
                  <input
                    type="text"
                    value={editForm.title}
                    onChange={(e) =>
                      setEditForm((p) => ({ ...p, title: e.target.value }))
                    }
                    className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                    Organization <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={editForm.organization}
                    onChange={(e) =>
                      setEditForm((p) => ({
                        ...p,
                        organization: e.target.value,
                      }))
                    }
                    className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
                  />
                </div>
              </div>
              <div>
                <label className="flex items-center gap-2 text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  LinkedIn URL{" "}
                  <span className="text-[9px] bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded">
                    Optional
                  </span>
                </label>
                <input
                  type="url"
                  value={editForm.linkedin_url}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, linkedin_url: e.target.value }))
                  }
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono shadow-sm"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3">
              <button
                onClick={() => setEditContact(null)}
                disabled={isSavingEdit}
                className="px-5 py-2.5 rounded text-[13px] font-bold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={isSavingEdit}
                className="px-5 py-2.5 bg-blue-600 text-white rounded text-[13px] font-bold hover:bg-blue-700 shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSavingEdit ? "Saving\u2026" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Agent Workbench modal ───────────────────────────────────────── */}
      {agentContact && (
        <AgentWorkbench
          contact={agentContact}
          onClose={() => setAgentContact(null)}
        />
      )}
    </div>
  );
}
