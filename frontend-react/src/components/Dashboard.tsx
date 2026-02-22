import { useState, useEffect } from 'react';
import { Users, CheckCircle, AlertCircle, RefreshCw, TrendingUp, Clock, Play, Loader2 } from 'lucide-react';
import type { Contact } from '../types';

interface BatchReceipt {
    id: string;
    batch_id: string;
    contacts_processed: number;
    contacts_verified_active: number;
    contacts_marked_inactive: number;
    replacements_found: number;
    flagged_for_review: number;
    total_api_cost_usd: number;
    total_tokens_used: number;
    total_labor_hours_saved: number;
    total_value_generated_usd: number;
    simulated_invoice_usd: number;
    net_roi_percentage: number;
    run_at: string;
}

const API_KEY = 'dev-key';

function fmt(n: number, decimals = 0) {
    return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}

export default function Dashboard() {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [receipts, setReceipts] = useState<BatchReceipt[]>([]);
    const [loading, setLoading] = useState(true);
    const [limit, setLimit] = useState(50);
    const [concurrency, setConcurrency] = useState(5);
    const [tier, setTier] = useState<'free' | 'paid'>('free');
    const [runStatus, setRunStatus] = useState<'idle' | 'starting' | 'started' | 'error'>('idle');
    const [runError, setRunError] = useState<string | null>(null);
    const [runMeta, setRunMeta] = useState<{ batch_id: string; tier: string; limit: number } | null>(null);

    useEffect(() => {
        Promise.all([
            fetch('/api/contacts', { headers: { 'X-API-Key': API_KEY } }).then(r => r.json()).catch(() => []),
            fetch('/api/batch-receipts', { headers: { 'X-API-Key': API_KEY } }).then(r => r.json()).catch(() => []),
        ]).then(([c, r]) => {
            setContacts(Array.isArray(c) ? c : []);
            setReceipts(Array.isArray(r) ? r : []);
        }).catch(console.error).finally(() => setLoading(false));
    }, []);

    async function triggerRun() {
        setRunStatus('starting');
        setRunError(null);
        setRunMeta(null);
        console.log('[Dashboard] Triggering batch run', { limit, concurrency, tier });
        try {
            const res = await fetch('/api/batch/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
                body: JSON.stringify({ limit, concurrency, tier }),
            });
            if (!res.ok) {
                const body = await res.text();
                console.error('[Dashboard] Batch run HTTP error', res.status, body);
                throw new Error(body || `HTTP ${res.status}`);
            }
            const data = await res.json();
            console.log('[Dashboard] Batch run started:', data);
            setRunMeta({ batch_id: data.batch_id, tier: data.tier, limit: data.limit });
            setRunStatus('started');
        } catch (err: any) {
            console.error('[Dashboard] triggerRun error:', err);
            setRunStatus('error');
            setRunError(err.message || 'Failed to start batch run.');
        }
    }

    // ── KPIs ──────────────────────────────────────────────────────────────
    const total = contacts.length;
    const active = contacts.filter(c => c.status === 'active').length;
    const inactive = contacts.filter(c => c.status === 'inactive').length;
    const unknown = contacts.filter(c => c.status === 'unknown').length;
    const flagged = contacts.filter(c => c.needs_human_review).length;
    const activePercent = total > 0 ? Math.round((active / total) * 100) : 0;

    const statusGroups = [
        { label: 'Active', count: active, color: '#10b981', bg: '#ecfdf5', border: '#a7f3d0' },
        { label: 'Inactive', count: inactive, color: '#ef4444', bg: '#fef2f2', border: '#fecaca' },
        { label: 'Unknown', count: unknown, color: '#f59e0b', bg: '#fffbeb', border: '#fde68a' },
        { label: 'Flagged', count: flagged, color: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe' },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32 text-[#6B7280]">
                <RefreshCw size={16} className="animate-spin mr-2" />
                <span className="text-[13px] font-mono">Loading dashboard…</span>
            </div>
        );
    }

    return (
        <div>
            <div className="mb-6 pl-1">
                <h1 className="text-[32px] font-bold text-[#0B0B0B] tracking-tight mb-1 font-serif">Dashboard</h1>
                <p className="text-[12px] font-mono text-[#6B7280] uppercase tracking-widest font-semibold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#3DF577] rounded-full inline-block"></span>
                    <span>Contact Health Overview</span>
                </p>
            </div>

            {/* ── KPI Cards ── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Total Contacts</span>
                        <Users size={14} className="text-[#9ca3af]" />
                    </div>
                    <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none">{fmt(total)}</p>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Active Rate</span>
                        <CheckCircle size={14} className="text-[#10b981]" />
                    </div>
                    <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none">{activePercent}<span className="text-[18px] text-[#6B7280]">%</span></p>
                    <p className="text-[11px] font-mono text-[#9ca3af] mt-1">{fmt(active)} of {fmt(total)} verified active</p>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Needs Review</span>
                        <AlertCircle size={14} className="text-[#8b5cf6]" />
                    </div>
                    <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none">{fmt(flagged)}</p>
                    <p className="text-[11px] font-mono text-[#9ca3af] mt-1">flagged for human check</p>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Batch Runs</span>
                        <TrendingUp size={14} className="text-[#9ca3af]" />
                    </div>
                    <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none">{receipts.length}</p>
                    <p className="text-[11px] font-mono text-[#9ca3af] mt-1">total agent runs</p>
                </div>
            </div>

            {/* ── Status Breakdown ── */}
            <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm mb-6">
                <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-4">Contact Status Breakdown</h2>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                    {statusGroups.map(g => (
                        <div key={g.label} className="rounded p-4 border" style={{ background: g.bg, borderColor: g.border }}>
                            <p className="text-[11px] font-mono font-bold uppercase tracking-widest mb-1" style={{ color: g.color }}>{g.label}</p>
                            <p className="text-[24px] font-bold text-[#0B0B0B] leading-none">{g.count}</p>
                            <p className="text-[10px] font-mono text-[#9ca3af] mt-1">
                                {total > 0 ? Math.round((g.count / total) * 100) : 0}% of total
                            </p>
                        </div>
                    ))}
                </div>
                {/* Bar */}
                {total > 0 && (
                    <div className="flex h-2 rounded-full overflow-hidden gap-px">
                        {statusGroups.map(g => (
                            g.count > 0 && (
                                <div
                                    key={g.label}
                                    className="h-full transition-all"
                                    style={{ width: `${(g.count / total) * 100}%`, background: g.color }}
                                    title={`${g.label}: ${g.count}`}
                                />
                            )
                        ))}
                    </div>
                )}
            </div>

            {/* ── Run Agent ── */}
            <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm mb-6">
                <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-4">Run Verification Agent</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                    <div>
                        <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Batch Limit</label>
                        <input
                            type="number"
                            min={1}
                            max={500}
                            value={limit}
                            onChange={e => setLimit(Number(e.target.value))}
                            className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B]"
                        />
                    </div>
                    <div>
                        <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Concurrency</label>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={concurrency}
                            onChange={e => setConcurrency(Number(e.target.value))}
                            className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B]"
                        />
                    </div>
                    <div>
                        <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Tier</label>
                        <select
                            value={tier}
                            onChange={e => setTier(e.target.value as 'free' | 'paid')}
                            className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B] bg-white"
                        >
                            <option value="free">Free (scrape only)</option>
                            <option value="paid">Paid (Claude AI)</option>
                        </select>
                    </div>
                </div>
                <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={triggerRun}
                            disabled={runStatus === 'starting' || runStatus === 'started'}
                            className="flex items-center gap-2 px-5 py-2.5 bg-[#3DF577] border border-transparent rounded text-[12px] font-mono font-bold text-[#0B0B0B] hover:bg-[#34d366] transition-colors shadow-sm uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {runStatus === 'starting' ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                            {runStatus === 'starting' ? 'Starting…' : 'Run Agent'}
                        </button>
                        {runStatus === 'error' && runError && (
                            <span className="text-[11px] font-mono text-[#ef4444]">{runError}</span>
                        )}
                    </div>

                    {runStatus === 'started' && runMeta && (
                        <div className="flex items-start gap-3 bg-[#ecfdf5] border border-[#a7f3d0] rounded px-4 py-3">
                            <span className="mt-0.5 w-2 h-2 rounded-full bg-[#10b981] animate-pulse flex-shrink-0" />
                            <div>
                                <p className="text-[12px] font-mono font-bold text-[#065f46]">
                                    Agent started — check Value Receipt for results.
                                </p>
                                <p className="text-[11px] font-mono text-[#047857] mt-0.5">
                                    batch_id: <span className="select-all">{runMeta.batch_id}</span>
                                    &nbsp;·&nbsp;tier: {runMeta.tier}
                                    &nbsp;·&nbsp;up to {runMeta.limit} contacts
                                </p>
                                <p className="text-[10px] font-mono text-[#6ee7b7] mt-1">
                                    Running in background — watch your server logs for per-agent progress.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Recent Batch Runs ── */}
            <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm">
                <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-4">Recent Batch Runs</h2>

                {receipts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-[#9ca3af]">
                        <Clock size={28} className="mb-3 opacity-40" />
                        <p className="text-[13px] font-medium text-[#6B7280]">No batch runs yet</p>
                        <p className="text-[11px] font-mono mt-1">Use the "Run Agent" button above to trigger your first run</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-[12px]">
                            <thead>
                                <tr className="border-b border-[#e5e7eb]">
                                    {['Run At', 'Processed', 'Active', 'Inactive', 'Replacements', 'API Cost', 'Value', 'ROI'].map(h => (
                                        <th key={h} className="text-left pb-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-[#6B7280] font-bold">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {receipts.map(r => (
                                    <tr key={r.id} className="border-b border-[#f3f4f6] hover:bg-[#f9fafb]">
                                        <td className="py-3 pr-4 font-mono text-[#6B7280]">
                                            {new Date(r.run_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                        </td>
                                        <td className="py-3 pr-4 font-bold text-[#0B0B0B]">{r.contacts_processed}</td>
                                        <td className="py-3 pr-4 text-[#10b981] font-bold">{r.contacts_verified_active}</td>
                                        <td className="py-3 pr-4 text-[#ef4444] font-bold">{r.contacts_marked_inactive}</td>
                                        <td className="py-3 pr-4 text-[#8b5cf6] font-bold">{r.replacements_found}</td>
                                        <td className="py-3 pr-4 font-mono text-[#6B7280]">${r.total_api_cost_usd?.toFixed(4)}</td>
                                        <td className="py-3 pr-4 font-mono text-[#0B0B0B]">${fmt(r.total_value_generated_usd, 2)}</td>
                                        <td className="py-3 pr-4">
                                            <span className="bg-[#ecfdf5] text-[#10b981] border border-[#a7f3d0] text-[10px] font-mono font-bold px-2 py-0.5 rounded">
                                                +{fmt(r.net_roi_percentage)}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
