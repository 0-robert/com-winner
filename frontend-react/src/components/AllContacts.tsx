import { useState } from "react";
import { supabase } from "../lib/supabase";
import type { Contact } from "../types";
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
} from "lucide-react";

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

export default function AllContacts() {
  const [activeTab, setActiveTab] = useState("All Contacts");
  const [selectedNotesContact, setSelectedNotesContact] =
    useState<Contact | null>(null);
  const [selectedMoreContact, setSelectedMoreContact] =
    useState<Contact | null>(null);
  const [selectedProfileContact, setSelectedProfileContact] =
    useState<Contact | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([
    {
      id: "1",
      name: "Keanu Czirjak",
      title: "SWE Apprentice",
      email: "keanu@example.com",
      organization: "Arm",
      status: "active",
      needs_human_review: false,
      linkedin_url: "https://www.linkedin.com/in/keanuczirjak/",
    },
    {
      id: "2",
      name: "Keanu Czirjak",
      title: "SWE Apprentice",
      email: "keanu2@example.com",
      organization: "Arm",
      status: "unknown",
      needs_human_review: true,
      linkedin_url: "https://www.linkedin.com/in/keanuczirjak/",
    },
    {
      id: "3",
      name: "Keanu Czirjak",
      title: "SWE Apprentice",
      email: "keanu3@example.com",
      organization: "Arm",
      status: "active",
      needs_human_review: false,
      linkedin_url: "https://www.linkedin.com/in/keanuczirjak/",
    },
    {
      id: "4",
      name: "Keanu Czirjak",
      title: "SWE Apprentice",
      email: "keanu4@example.com",
      organization: "Arm",
      status: "inactive",
      needs_human_review: false,
      linkedin_url: "https://www.linkedin.com/in/keanuczirjak/",
    },
    {
      id: "5",
      name: "Keanu Czirjak",
      title: "SWE Apprentice",
      email: "keanu5@example.com",
      organization: "Arm",
      status: "opted_out",
      needs_human_review: false,
      linkedin_url: "https://www.linkedin.com/in/keanuczirjak/",
    },
  ] as Contact[]);

  // ── Email sending state ──────────────────────────────────────────────
  const [emailSendingOne, setEmailSendingOne] = useState<string | null>(null); // contact ID being emailed
  const [emailSendingAll, setEmailSendingAll] = useState(false);
  const [emailAllResult, setEmailAllResult] = useState<{
    total_sent: number;
    total_failed: number;
  } | null>(null);

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
        `Send info-review emails to all ${contacts.filter((c: Contact) => c.status !== "opted_out").length} eligible contacts?`,
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

  const tabs = ["All Contacts", "Review Required", "Departed"];

  return (
    <div>
      <div className="mb-6 pl-1">
        <h1 className="text-[24px] font-bold text-slate-900 tracking-tight mb-1">
          Manage Contacts
        </h1>
        <p className="text-[12px] font-mono text-slate-500 uppercase tracking-widest font-semibold flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-blue-500"></span> Agentic Database
        </p>
      </div>

      <div className="bg-white rounded border border-slate-200 p-6 shadow-sm">
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
              onClick={async () => {
                try {
                  const { data } = await supabase
                    .from("contacts")
                    .select("*")
                    .order("name");
                  setContacts(data || []);
                } catch (err) {
                  console.error(err);
                }
              }}
              className="px-4 py-1.5 bg-blue-600 text-white rounded text-[12px] font-bold shadow-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw size={14} />
              Fetch Real Contacts
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
          <div className="col-span-4">Client</div>
          <div className="col-span-3">Task</div>
          <div className="col-span-2">Notes</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">More</div>
        </div>

        {/* Rows Space */}
        <div className="space-y-1 relative pt-2">
          {contacts.map((contact) => (
            <div key={contact.id} className="group relative">
              {/* Hover floating effect container */}
              <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center bg-white rounded border border-transparent transition-colors hover:bg-slate-50">
                <div className="col-span-4 flex items-center gap-3">
                  <div className="w-3.5 h-3.5 rounded-sm border border-slate-300 pointer-events-none group-hover:border-blue-400 bg-white"></div>
                  <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px]">
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

                <div className="col-span-3 flex flex-col justify-center min-w-0">
                  <span className="text-[12px] font-bold text-slate-800 truncate">
                    {contact.organization}
                  </span>
                  <div className="flex flex-col">
                    <span className="text-[11px] font-mono text-slate-500 truncate">
                      {contact.title || "Unknown Role"}
                    </span>
                    {contact.experience && contact.experience[0]?.dateRange && (
                      <span className="text-[9px] font-mono text-blue-600 font-bold uppercase tracking-tight mt-0.5">
                        Tenure:{" "}
                        {contact.experience[0].dateRange
                          .split("·")[1]
                          ?.trim() || contact.experience[0].dateRange}
                      </span>
                    )}
                  </div>
                </div>

                <div className="col-span-2 flex items-center">
                  <button
                    onClick={() => setSelectedNotesContact(contact)}
                    className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-400 hover:text-blue-600 hover:border-blue-200 transition-colors bg-white shadow-sm"
                  >
                    <FileText size={12} />
                  </button>
                </div>

                <div className="col-span-2 flex items-center">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider inline-flex items-center gap-1 border uppercase shadow-sm ${
                      contact.needs_human_review
                        ? STATUS_CONFIG.unknown.badge
                        : STATUS_CONFIG[
                            contact.status as keyof typeof STATUS_CONFIG
                          ]?.badge || STATUS_CONFIG.inactive.badge
                    }`}
                  >
                    {contact.status === "active" && <CheckCircle2 size={10} />}
                    {contact.needs_human_review ? "REVIEW" : contact.status}
                  </span>
                </div>

                <div className="col-span-1 flex items-center justify-end">
                  <button
                    onClick={() => setSelectedMoreContact(contact)}
                    className="text-slate-400 hover:text-slate-800 transition-colors p-1 rounded hover:bg-slate-200"
                  >
                    <MoreVertical size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Notes Modal */}
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
                  {selectedNotesContact?.name} (
                  {selectedNotesContact?.organization})
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
                {selectedNotesContact?.needs_human_review ? (
                  <>
                    <span className="text-orange-600 font-bold">
                      [!] FLAG: NEEDS REVIEW
                    </span>
                    <br />
                    <br />
                    - ZeroBounce returned valid email.
                    <br />
                    - Could not locate on district website.
                    <br />
                    - LinkedIn profile is private or not exact match.
                    <br />- Claude analysis: "Uncertain if still at{" "}
                    {selectedNotesContact?.organization}. Proceed with caution."
                    <br />
                  </>
                ) : (
                  <>
                    <span className="text-green-600 font-bold">
                      [✓] VERIFIED ACTIVE
                    </span>
                    <br />
                    <br />
                    - ZeroBounce returned valid email.
                    <br />- Found on {selectedNotesContact?.organization} staff
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

      {/* More Options Modal */}
      {selectedMoreContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px]">
                  {selectedMoreContact?.name
                    ?.split(" ")
                    .map((n: string) => n[0])
                    .join("")}
                </div>
                <h3 className="text-[14px] font-bold text-slate-900">
                  {selectedMoreContact?.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedMoreContact(null)}
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
                    alert("No LinkedIn URL found for this contact.");
                    return;
                  }
                  try {
                    // Opt for a basic loading alert or toast in a real app
                    console.log("Starting agentic sync...");
                    const btn = document.getElementById(
                      `sync-btn-${selectedMoreContact.id}`,
                    );
                    if (btn)
                      btn.innerHTML =
                        '<span class="text-[13px] font-semibold text-slate-700">Syncing...</span>';

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
                      }),
                    });
                    const data = await res.json();
                    console.log("Scrape successful:", data);

                    // Update the contact in the local state array
                    if (data.success) {
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
                              }
                            : c,
                        ),
                      );
                    }

                    setSelectedMoreContact(null);
                    if (btn)
                      btn.innerHTML =
                        '<span class="text-[13px] font-semibold text-slate-700">Force Agentic Sync</span>';
                  } catch (err) {
                    console.error(err);
                    alert("Scrape failed. Check console.");
                  }
                }}
                id={`sync-btn-${selectedMoreContact.id}`}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors"
              >
                <RefreshCw size={16} className="text-slate-400" />
                <span className="text-[13px] font-semibold text-slate-700">
                  Force Agentic Sync
                </span>
              </button>
              <button
                onClick={() => setSelectedMoreContact(null)}
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
            <div className="p-2 border-t border-slate-100 bg-slate-50/50">
              <button
                onClick={() => setSelectedMoreContact(null)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-50 rounded text-left transition-colors group"
              >
                <Trash
                  size={16}
                  className="text-red-400 group-hover:text-red-600 transition-colors"
                />
                <span className="text-[13px] font-semibold text-red-600">
                  Delete Contact
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Profile Detail Modal */}
      {selectedProfileContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200 flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold border border-blue-700 text-[18px] shadow-sm">
                  {selectedProfileContact?.name
                    ?.split(" ")
                    .map((n: string) => n[0])
                    .join("")}
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-slate-900 leading-tight">
                    {selectedProfileContact?.name}
                  </h3>
                  <p className="text-[12px] font-mono text-slate-500 font-semibold">
                    {selectedProfileContact?.organization} —{" "}
                    {selectedProfileContact?.title}
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
                      {selectedProfileContact.status === "active"
                        ? "Contact is verified active. Tenure analysis shows stable progression. High relevance for current campaign."
                        : "Contact status is unknown. Last scraped role may have shifted. Suggest manual oversight before outreach."}
                    </p>
                    <div className="mt-4 pt-4 border-t border-blue-500/50 flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-blue-200">
                        Confidence Score
                      </span>
                      <span className="text-[16px] font-bold">
                        {selectedProfileContact.status === "active"
                          ? "98%"
                          : "45%"}
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
    </div>
  );
}
