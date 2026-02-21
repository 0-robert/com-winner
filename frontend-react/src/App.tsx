import { useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
} from "react-router-dom";
import {
  Home,
  Sparkles,
  ClipboardList,
  BarChart2,
  Settings,
  Plus,
  Search,
  X,
} from "lucide-react";

import AllContacts from "./components/AllContacts";
import ReviewQueue from "./components/ReviewQueue";
import ValueReceipt from "./components/ValueReceipt";

function App() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newContact, setNewContact] = useState({
    name: "",
    email: "",
    title: "",
    organization: "",
    linkedin_url: "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const resetForm = () => {
    setNewContact({
      name: "",
      email: "",
      title: "",
      organization: "",
      linkedin_url: "",
    });
    setSaveError(null);
  };

  const closeModal = () => {
    setIsAddModalOpen(false);
    resetForm();
  };

  const handleSaveContact = async () => {
    if (!newContact.name.trim() || !newContact.organization.trim()) {
      setSaveError("Name and Organization are required.");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      const res = await fetch("/api/contacts", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": "dev-key" },
        body: JSON.stringify({
          id: crypto.randomUUID(),
          name: newContact.name.trim(),
          email: newContact.email.trim(),
          title: newContact.title.trim(),
          organization: newContact.organization.trim(),
          linkedin_url: newContact.linkedin_url.trim() || null,
          status: "unknown",
          needs_human_review: false,
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `HTTP ${res.status}`);
      }
      closeModal();
      // Refresh the page so the contacts list picks up the new entry
      window.location.reload();
    } catch (err: any) {
      setSaveError(err.message || "Failed to save contact.");
    } finally {
      setIsSaving(false);
    }
  };

  const mainMenu = [
    { name: "Dashboard", path: "#dashboard", icon: <Home size={18} /> },
    { name: "All Contacts", path: "/", icon: <ClipboardList size={18} /> },
    {
      name: "Human Review",
      path: "/review",
      icon: <Sparkles size={18} />,
      badge: "new",
    },
    { name: "Value Receipt", path: "/receipt", icon: <BarChart2 size={18} /> },
    { name: "Settings", path: "#settings", icon: <Settings size={18} /> },
  ];

  return (
    <Router>
      <div className="min-h-screen bg-[#f8f9fc] flex text-slate-800 font-sans selection:bg-blue-100 selection:text-blue-900">
        {/* Sidebar */}
        <aside className="w-[260px] bg-transparent flex flex-col pt-8 pl-6 pr-4 flex-shrink-0 h-screen sticky top-0">
          <div className="mb-10 flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-sm border border-blue-700">
              <span className="font-mono">PK</span>
            </div>
            <div>
              <h2 className="text-[16px] font-bold text-slate-900 tracking-tight leading-tight">
                ProspectKeeper
              </h2>
              <p className="text-[11px] font-mono text-slate-500 tracking-tight font-semibold uppercase">
                agentic-crm-v1
              </p>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto space-y-8">
            <div className="space-y-1.5">
              {mainMenu.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.path}
                  className={({ isActive }) =>
                    `group flex items-center gap-3 px-3 py-2.5 rounded border ${
                      isActive && item.path !== "#"
                        ? "bg-white text-slate-900 shadow-sm border-slate-200"
                        : "text-slate-500 hover:bg-white/60 hover:text-slate-800 border-transparent"
                    }`
                  }
                >
                  <div
                    className={`transition-colors ${item.path !== "#" ? "group-hover:text-slate-700" : ""}`}
                  >
                    {item.icon}
                  </div>
                  <span className="flex-1 text-[13px] font-semibold">
                    {item.name}
                  </span>
                  {item.badge && (
                    <span className="bg-orange-100 text-orange-700 text-[10px] uppercase font-bold px-1.5 py-0.5 rounded shadow-sm">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>

            <div className="pt-6 border-t border-slate-200/60">
              <div className="bg-white rounded p-4 border border-slate-200">
                <h3 className="text-[12px] font-bold text-slate-800 mb-1">
                  Background Sync
                </h3>
                <p className="text-[11px] font-mono text-slate-500 leading-relaxed">
                  Agentic workers are active.
                </p>
              </div>
            </div>
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 bg-[#f8f9fc] min-h-screen relative p-8">
          <div className="max-w-[1200px] mx-auto relative z-10">
            <header className="mb-8 flex items-center justify-between bg-white rounded p-4 shadow-sm border border-slate-200">
              <div className="flex items-center gap-3 pl-4">
                <div className="w-7 h-7 rounded flex items-center justify-center text-slate-400 bg-slate-50 border border-slate-200">
                  <Search size={14} />
                </div>
                <input
                  type="text"
                  placeholder="Search anything..."
                  className="bg-transparent border-none outline-none text-[13px] font-medium text-slate-700 placeholder:text-slate-400 w-[300px]"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsAddModalOpen(true)}
                  className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded text-[12px] font-bold hover:bg-blue-700 transition-colors shadow-sm"
                >
                  <Plus size={14} /> Add new contact
                </button>
                <div className="w-9 h-9 rounded bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 font-bold text-[12px]">
                  RV
                </div>
              </div>
            </header>

            <Routes>
              <Route path="/" element={<AllContacts />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/receipt" element={<ValueReceipt />} />
            </Routes>
          </div>
        </main>
      </div>

      {/* Add Contact Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-[16px] font-bold text-slate-900">
                Add New Contact
              </h3>
              <button
                onClick={closeModal}
                className="text-slate-400 hover:text-slate-700 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {saveError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-[12px] font-medium px-4 py-2.5 rounded">
                  {saveError}
                </div>
              )}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Full Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Jane Doe"
                  value={newContact.name}
                  onChange={(e) =>
                    setNewContact((p) => ({ ...p, name: e.target.value }))
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
                  placeholder="jane@example.com"
                  value={newContact.email}
                  onChange={(e) =>
                    setNewContact((p) => ({ ...p, email: e.target.value }))
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
                    placeholder="e.g. Director of Sales"
                    value={newContact.title}
                    onChange={(e) =>
                      setNewContact((p) => ({ ...p, title: e.target.value }))
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
                    placeholder="e.g. Acme Corp"
                    value={newContact.organization}
                    onChange={(e) =>
                      setNewContact((p) => ({
                        ...p,
                        organization: e.target.value,
                      }))
                    }
                    className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 flex items-center gap-2">
                  LinkedIn URL{" "}
                  <span className="text-[9px] bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded">
                    Optional
                  </span>
                </label>
                <input
                  type="url"
                  placeholder="https://linkedin.com/in/..."
                  value={newContact.linkedin_url}
                  onChange={(e) =>
                    setNewContact((p) => ({
                      ...p,
                      linkedin_url: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded text-[13px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono shadow-sm"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3">
              <button
                onClick={closeModal}
                disabled={isSaving}
                className="px-5 py-2.5 rounded text-[13px] font-bold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveContact}
                disabled={isSaving}
                className="px-5 py-2.5 bg-blue-600 text-white rounded text-[13px] font-bold hover:bg-blue-700 shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? "Saving…" : "Save Contact"}
              </button>
            </div>
          </div>
        </div>
      )}
    </Router>
  );
}

export default App;
