import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Link } from 'react-router-dom';
import { Home, Sparkles, ClipboardList, BarChart2, Settings, Plus, Search, X } from 'lucide-react';

import AllContacts from './components/AllContacts';
import ReviewQueue from './components/ReviewQueue';
import ValueReceipt from './components/ValueReceipt';
import Dashboard from './components/Dashboard';
import SettingsPage from './components/Settings';

const mainMenu = [
  { name: 'Dashboard', path: '/dashboard', icon: <Home size={16} /> },
  { name: 'All Contacts', path: '/', icon: <ClipboardList size={16} /> },
  { name: 'Human Review', path: '/review', icon: <Sparkles size={16} />, badge: 'new' },
  { name: 'Value Receipt', path: '/receipt', icon: <BarChart2 size={16} /> },
  { name: 'Settings', path: '/settings', icon: <Settings size={16} /> },
];

const navBase = 'group flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-colors duration-150 border';
const navActive = 'bg-white text-[#0B0B0B] border-[#e5e7eb] shadow-sm';
const navInactive = 'text-[#6B7280] hover:bg-[#f9fafb] hover:text-[#0B0B0B] border-transparent';

function App() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newContact, setNewContact] = useState({
    name: '',
    email: '',
    title: '',
    organization: '',
    linkedin_url: '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const resetForm = () => {
    setNewContact({ name: '', email: '', title: '', organization: '', linkedin_url: '' });
    setSaveError(null);
  };

  const closeModal = () => {
    setIsAddModalOpen(false);
    resetForm();
  };

  const handleSaveContact = async () => {
    if (!newContact.name.trim() || !newContact.organization.trim()) {
      setSaveError('Name and Organization are required.');
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      const res = await fetch('/api/contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-key' },
        body: JSON.stringify({
          id: crypto.randomUUID(),
          name: newContact.name.trim(),
          email: newContact.email.trim(),
          title: newContact.title.trim(),
          organization: newContact.organization.trim(),
          linkedin_url: newContact.linkedin_url.trim() || null,
          status: 'unknown',
          needs_human_review: false,
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `HTTP ${res.status}`);
      }
      closeModal();
      window.location.reload();
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save contact.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Router>
      <div className="flex min-h-screen bg-white text-[#0B0B0B] font-sans selection:bg-[#3DF577]/20 selection:text-[#0B0B0B]">

        {/* ── Sidebar ─────────────────────────────────────────────────── */}
        <aside className="w-[232px] bg-white border-r border-[#e5e7eb] flex flex-col flex-shrink-0 h-screen sticky top-0 overflow-y-auto">

          {/* Logo */}
          <div className="flex items-center gap-3 px-4 pt-6 pb-5 border-b border-[#e5e7eb]">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-7 h-7 rounded-md bg-[#0B0B0B] flex items-center justify-center text-white font-bold text-[11px] shadow-sm shrink-0">
                <span className="font-mono tracking-tight text-white">PK</span>
              </div>
              <div>
                <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight leading-tight">ProspectKeeper</h2>
                <p className="text-[10px] font-mono text-[#6B7280] tracking-tight uppercase">agentic-crm-v1</p>
              </div>
            </Link>
          </div>

          {/* Nav */}
          <nav className="flex-1 px-3 py-4 space-y-0.5">
            {mainMenu.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `${navBase} ${isActive ? navActive : navInactive}`
                }
              >
                <span className="text-current opacity-70 group-hover:opacity-100 transition-opacity shrink-0">
                  {item.icon}
                </span>
                <span className="flex-1">{item.name}</span>
                {item.badge && (
                  <span className="bg-orange-100 text-orange-600 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded-full tracking-wide">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Background Sync widget */}
          <div className="px-3 pb-5">
            <div className="bg-white rounded-lg p-3.5 border border-[#e5e7eb]">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3DF577] opacity-60"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10b981]"></span>
                </span>
                <h3 className="text-[12px] font-semibold text-[#0B0B0B]">Background Sync</h3>
              </div>
              <p className="text-[11px] font-mono text-[#6B7280] leading-relaxed">Agentic workers are active.</p>
              <p className="text-[10px] font-mono text-[#9ca3af] mt-1.5">Last sync: just now</p>
            </div>
          </div>
        </aside>

        {/* ── Main ────────────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 min-h-screen p-7">
          <div className="max-w-[1100px] mx-auto">

            {/* Header */}
            <header className="mb-7 flex items-center justify-between bg-white rounded-xl px-4 py-3 shadow-sm border border-[#e5e7eb]">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-md flex items-center justify-center text-[#9ca3af]">
                  <Search size={14} />
                </div>
                <input
                  type="text"
                  placeholder="Search anything..."
                  className="bg-transparent border-none outline-none text-[13px] font-medium text-[#0B0B0B] placeholder:text-[#9ca3af] w-[260px]"
                />
              </div>
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => setIsAddModalOpen(true)}
                  className="flex items-center gap-1.5 bg-[#3DF577] text-[#0B0B0B] px-4 py-2 rounded-lg text-[13px] font-semibold hover:bg-[#34d366] active:scale-[0.97] transition-all duration-100 shadow-sm"
                >
                  <Plus size={14} /> Add contact
                </button>
                <div className="w-8 h-8 rounded-lg bg-[#f9fafb] border border-[#e5e7eb] flex items-center justify-center text-[#374151] font-bold text-[11px]">
                  RV
                </div>
              </div>
            </header>

            <Routes>
              <Route path="/" element={<AllContacts />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/receipt" element={<ValueReceipt />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </div>
        </main>
      </div>

      {/* ── Add Contact Modal ──────────────────────────────────────────── */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-[15px] font-bold text-slate-900">Add New Contact</h3>
              <button
                onClick={closeModal}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {saveError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-[12px] font-medium px-4 py-2.5 rounded-lg">
                  {saveError}
                </div>
              )}
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">
                  Full Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Jane Doe"
                  value={newContact.name}
                  onChange={(e) => setNewContact((p) => ({ ...p, name: e.target.value }))}
                  className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-[13px] focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">Email Address</label>
                <input
                  type="email"
                  placeholder="jane@example.com"
                  value={newContact.email}
                  onChange={(e) => setNewContact((p) => ({ ...p, email: e.target.value }))}
                  className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-[13px] focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">Job Title</label>
                  <input
                    type="text"
                    placeholder="e.g. Director of Sales"
                    value={newContact.title}
                    onChange={(e) => setNewContact((p) => ({ ...p, title: e.target.value }))}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-[13px] focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">
                    Organization <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Acme Corp"
                    value={newContact.organization}
                    onChange={(e) => setNewContact((p) => ({ ...p, organization: e.target.value }))}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-[13px] focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5 flex items-center gap-2">
                  LinkedIn URL
                  <span className="text-[9px] normal-case bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded-full">Optional</span>
                </label>
                <input
                  type="url"
                  placeholder="https://linkedin.com/in/..."
                  value={newContact.linkedin_url}
                  onChange={(e) => setNewContact((p) => ({ ...p, linkedin_url: e.target.value }))}
                  className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-[13px] focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-mono"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-[#e5e7eb] bg-[#f9fafb] flex justify-end gap-2.5">
              <button
                onClick={closeModal}
                disabled={isSaving}
                className="px-4 py-2 rounded-lg text-[13px] font-semibold text-[#6B7280] hover:bg-white hover:border-[#e5e7eb] border border-transparent active:scale-[0.97] transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveContact}
                disabled={isSaving}
                className="px-4 py-2 bg-[#3DF577] text-[#0B0B0B] rounded-lg text-[13px] font-semibold hover:bg-[#34d366] active:scale-[0.97] shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? 'Saving…' : 'Save Contact'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Router>
  );
}

export default App;
