import { useState, useEffect, useRef } from 'react';
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

interface ContactRow {
    index: number;
    name: string;
    org: string;
    title: string;
    phase: 'running' | 'active' | 'inactive' | 'pending_confirmation' | 'flagged' | 'error' | 'unknown';
    cost_usd?: number;
    elapsed?: number;
    error?: string;
    replacement?: string | null;
}

interface BatchSummary {
    batch_id: string;
    processed: number;
    active: number;
    inactive: number;
    replacements: number;
    flagged: number;
    errors: number;
    total_cost_usd: number;
    total_value_usd: number;
    roi_pct: number;
    elapsed: number;
}

const API_KEY = 'dev-key';

function fmt(n: number, decimals = 0) {
    return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
    active:               { label: 'ACTIVE',      bg: '#ecfdf5', text: '#10b981', border: '#a7f3d0' },
    inactive:             { label: 'INACTIVE',    bg: '#fef2f2', text: '#ef4444', border: '#fecaca' },
    pending_confirmation: { label: 'EMAIL SENT',  bg: '#fffbeb', text: '#92400e', border: '#fde68a' },
    flagged:              { label: 'FLAGGED',     bg: '#f5f3ff', text: '#8b5cf6', border: '#ddd6fe' },
    error:                { label: 'ERROR',       bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
    unknown:              { label: 'UNKNOWN',     bg: '#f9fafb', text: '#6B7280', border: '#e5e7eb' },
    running:              { label: 'RUNNING',     bg: '#f9fafb', text: '#6B7280', border: '#e5e7eb' },
};

function StatusBadge({ phase }: { phase: ContactRow['phase'] }) {
    const cfg = STATUS_CONFIG[phase] ?? STATUS_CONFIG.unknown;
    return (
        <span
            className="text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase tracking-widest flex items-center gap-1 whitespace-nowrap"
            style={{ background: cfg.bg, color: cfg.text, borderColor: cfg.border }}
        >
            {phase === 'running' && <Loader2 size={9} className="animate-spin" />}
            {cfg.label}
        </span>
    );
}

export default function Dashboard() {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [receipts, setReceipts] = useState<BatchReceipt[]>([]);
    const [loading, setLoading] = useState(true);

    // ── batch run form ─────────────────────────────────────────────────────
    const [limit, setLimit] = useState(50);
    const [concurrency, setConcurrency] = useState(5);
    const [tier, setTier] = useState<'free' | 'paid'>('free');

    // ── streaming state ────────────────────────────────────────────────────
    type Phase = 'idle' | 'streaming' | 'complete' | 'error';
    const [phase, setPhase] = useState<Phase>('idle');
    const [runError, setRunError] = useState<string | null>(null);
    const [streamBatchId, setStreamBatchId] = useState<string | null>(null);
    const [streamTotal, setStreamTotal] = useState(0);
    const [streamDone, setStreamDone] = useState(0);
    const [contactRows, setContactRows] = useState<ContactRow[]>([]);
    const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
    const logRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        Promise.all([
            fetch('/api/contacts', { headers: { 'X-API-Key': API_KEY } }).then(r => r.json()).catch(() => []),
            fetch('/api/batch-receipts', { headers: { 'X-API-Key': API_KEY } }).then(r => r.json()).catch(() => []),
        ]).then(([c, r]) => {
            setContacts(Array.isArray(c) ? c : []);
            setReceipts(Array.isArray(r) ? r : []);
        }).catch(console.error).finally(() => setLoading(false));
    }, []);

    // auto-scroll log to bottom on new rows
    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [contactRows]);

    async function triggerRun() {
        setPhase('streaming');
        setRunError(null);
        setContactRows([]);
        setBatchSummary(null);
        setStreamTotal(0);
        setStreamDone(0);
        setStreamBatchId(null);

        function handleEvent(event: any) {
            switch (event.type) {
                case 'batch_start':
                    setStreamBatchId(event.batch_id);
                    setStreamTotal(event.total);
                    break;
                case 'contact_start':
                    setContactRows(prev => [...prev, {
                        index: event.index,
                        name: event.name,
                        org: event.org,
                        title: event.title,
                        phase: 'running',
                    }]);
                    break;
                case 'contact_done':
                    setStreamDone(d => d + 1);
                    setContactRows(prev => prev.map(r =>
                        r.index === event.index ? {
                            ...r,
                            phase: event.flagged ? 'flagged' : (event.status as ContactRow['phase']),
                            cost_usd: event.cost_usd,
                            elapsed: event.elapsed,
                            replacement: event.has_replacement ? event.replacement_name : null,
                        } : r
                    ));
                    break;
                case 'contact_error':
                    setStreamDone(d => d + 1);
                    setContactRows(prev => prev.map(r =>
                        r.index === event.index ? {
                            ...r,
                            phase: 'error',
                            error: event.error,
                            elapsed: event.elapsed,
                        } : r
                    ));
                    break;
                case 'batch_complete':
                    setBatchSummary(event);
                    setPhase('complete');
                    break;
                case 'error':
                    setRunError(event.message);
                    setPhase('error');
                    break;
            }
        }

        try {
            const res = await fetch('/api/batch/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
                body: JSON.stringify({ limit, concurrency, tier }),
            });
            if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);

            const reader = res.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop() ?? '';
                for (const part of parts) {
                    for (const line of part.split('\n')) {
                        if (!line.startsWith('data: ')) continue;
                        try { handleEvent(JSON.parse(line.slice(6))); } catch { /* skip malformed */ }
                    }
                }
            }
            setPhase(p => p === 'streaming' ? 'complete' : p);
        } catch (err: any) {
            if (err.name !== 'AbortError') {
                setRunError(err.message || 'Failed to run batch.');
                setPhase('error');
            }
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
        { label: 'Active', count: active, color: '#3DF577', bg: '#f9fafb', border: '#e5e7eb', countColor: '#0B0B0B', barColor: '#3DF577' },
        { label: 'Inactive', count: inactive, color: '#6B7280', bg: '#f9fafb', border: '#e5e7eb', countColor: '#0B0B0B', barColor: '#e5e7eb' },
        { label: 'Unknown', count: unknown, color: '#6B7280', bg: '#f9fafb', border: '#e5e7eb', countColor: '#0B0B0B', barColor: '#e5e7eb' },
        { label: 'Flagged', count: flagged, color: '#0B0B0B', bg: '#ffffff', border: '#0B0B0B', countColor: '#0B0B0B', barColor: '#0B0B0B' },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32 text-[#6B7280]">
                <RefreshCw size={16} className="animate-spin mr-2" />
                <span className="text-[13px] font-mono">Loading dashboard…</span>
            </div>
        );
    }

    const progressPct = streamTotal > 0 ? Math.round((streamDone / streamTotal) * 100) : 0;
    const isRunning = phase === 'streaming';

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
                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Total Contacts</span>
                            <Users size={14} className="text-[#9ca3af]" />
                        </div>
                        <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none mb-4">{fmt(total)}</p>
                    </div>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Active Rate</span>
                            <CheckCircle size={14} className="text-[#3DF577]" />
                        </div>
                        <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none mb-4">{activePercent}<span className="text-[18px] text-[#0B0B0B] font-mono">%</span></p>
                    </div>
                    <p className="text-[11px] font-mono text-[#6B7280]">{fmt(active)} of {fmt(total)} verified active</p>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Needs Review</span>
                            <AlertCircle size={14} className="text-[#8b5cf6]" />
                        </div>
                        <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none mb-4">{fmt(flagged)}</p>
                    </div>
                    <p className="text-[11px] font-mono text-[#6B7280]">flagged for human check</p>
                </div>

                <div className="bg-white rounded border border-[#e5e7eb] p-5 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Batch Runs</span>
                            <TrendingUp size={14} className="text-[#9ca3af]" />
                        </div>
                        <p className="text-[32px] font-bold text-[#0B0B0B] tracking-tight leading-none mb-4">{receipts.length}</p>
                    </div>
                    <p className="text-[11px] font-mono text-[#6B7280]">total agent runs</p>
                </div>
            </div>

            {/* ── Status Breakdown ── */}
            <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm mb-6">
                <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-4">Contact Status Breakdown</h2>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                    {statusGroups.map(g => (
                        <div key={g.label} className="rounded p-4 border flex flex-col justify-between" style={{ background: g.bg, borderColor: g.border }}>
                            <div>
                                <p className="text-[11px] font-mono font-bold uppercase tracking-widest mb-1" style={{ color: g.color }}>{g.label}</p>
                                <p className="text-[24px] font-bold leading-none mb-4" style={{ color: g.countColor }}>{g.count}</p>
                            </div>
                            <p className="text-[10px] font-mono text-[#9ca3af]">
                                {total > 0 ? Math.round((g.count / total) * 100) : 0}% of total
                            </p>
                        </div>
                    ))}
                </div>
                {total > 0 && (
                    <div className="flex h-2 rounded-full overflow-hidden gap-px">
                        {statusGroups.map(g => (
                            g.count > 0 && (
                                <div
                                    key={g.label}
                                    className="h-full transition-all"
                                    style={{ width: `${(g.count / total) * 100}%`, background: g.barColor }}
                                    title={`${g.label}: ${g.count}`}
                                />
                            )
                        ))}
                    </div>
                )}
            </div>

            {/* ── Run Agent ── */}
            <div className="bg-white rounded border border-[#e5e7eb] shadow-sm mb-6 overflow-hidden">
                {/* Header */}
                <div className="px-6 py-4 border-b border-[#e5e7eb] flex items-center justify-between">
                    <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight">Run Verification Agent</h2>
                    {isRunning && streamTotal > 0 && (
                        <span className="text-[11px] font-mono text-[#6B7280]">
                            {streamDone} / {streamTotal} &nbsp;·&nbsp; {progressPct}%
                        </span>
                    )}
                </div>

                {/* Form */}
                <div className="px-6 py-5">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                        <div>
                            <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Batch Limit</label>
                            <input
                                type="number" min={1} max={500} value={limit}
                                onChange={e => setLimit(Number(e.target.value))}
                                disabled={isRunning}
                                className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B] disabled:opacity-50"
                            />
                        </div>
                        <div>
                            <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Concurrency</label>
                            <input
                                type="number" min={1} max={20} value={concurrency}
                                onChange={e => setConcurrency(Number(e.target.value))}
                                disabled={isRunning}
                                className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B] disabled:opacity-50"
                            />
                        </div>
                        <div>
                            <label className="block text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest mb-1.5">Tier</label>
                            <select
                                value={tier}
                                onChange={e => setTier(e.target.value as 'free' | 'paid')}
                                disabled={isRunning}
                                className="w-full border border-[#e5e7eb] rounded px-3 py-2 text-[13px] font-mono text-[#0B0B0B] focus:outline-none focus:border-[#0B0B0B] bg-white disabled:opacity-50"
                            >
                                <option value="free">Free (email confirmation)</option>
                                <option value="paid">Paid (Claude AI)</option>
                            </select>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={triggerRun}
                            disabled={isRunning}
                            className="flex items-center gap-2 px-5 py-2.5 bg-[#3DF577] border border-transparent rounded text-[12px] font-mono font-bold text-[#0B0B0B] hover:bg-[#34d366] transition-colors shadow-sm uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                            {isRunning ? 'Running…' : phase === 'complete' ? 'Run Again' : 'Run Agent'}
                        </button>
                        {phase === 'error' && runError && (
                            <span className="text-[11px] font-mono text-[#ef4444]">{runError}</span>
                        )}
                    </div>
                </div>

                {/* ── Live Activity Feed ── */}
                {(isRunning || phase === 'complete' || phase === 'error') && (
                    <div className="border-t border-[#e5e7eb]">
                        {/* Progress bar */}
                        {streamTotal > 0 && (
                            <div className="h-1 bg-[#f3f4f6]">
                                <div
                                    className="h-full bg-[#3DF577] transition-all duration-500"
                                    style={{ width: `${progressPct}%` }}
                                />
                            </div>
                        )}

                        {/* Feed header */}
                        <div className="px-4 py-2.5 bg-[#f9fafb] border-b border-[#e5e7eb] flex items-center gap-2">
                            {isRunning
                                ? <><span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse flex-shrink-0" />
                                    <span className="text-[11px] font-mono font-bold text-[#065f46] uppercase tracking-widest">Live Agent Activity</span></>
                                : <><span className="w-1.5 h-1.5 rounded-full bg-[#9ca3af] flex-shrink-0" />
                                    <span className="text-[11px] font-mono font-bold text-[#6B7280] uppercase tracking-widest">Run Complete</span></>
                            }
                            {streamBatchId && (
                                <span className="ml-auto text-[10px] font-mono text-[#9ca3af] select-all">
                                    batch: {streamBatchId.slice(0, 8)}…
                                </span>
                            )}
                        </div>

                        {/* Empty states */}
                        {contactRows.length === 0 && isRunning && (
                            <div className="px-4 py-8 text-center text-[11px] font-mono text-[#9ca3af] flex items-center justify-center gap-2">
                                <Loader2 size={12} className="animate-spin" /> Loading contacts…
                            </div>
                        )}
                        {contactRows.length === 0 && !isRunning && (
                            <div className="px-4 py-8 text-center text-[11px] font-mono text-[#9ca3af]">
                                No contacts were eligible for verification.
                            </div>
                        )}

                        {/* Contact rows */}
                        {contactRows.length > 0 && (
                            <div ref={logRef} className="max-h-72 overflow-y-auto divide-y divide-[#f3f4f6]">
                                {contactRows.map(row => (
                                    <div key={row.index} className="px-4 py-2.5 flex items-start gap-3 hover:bg-[#fafafa]">
                                        <span className="text-[10px] font-mono text-[#9ca3af] w-10 flex-shrink-0 pt-0.5 tabular-nums">
                                            {String(row.index).padStart(2, '0')}/{String(streamTotal).padStart(2, '0')}
                                        </span>

                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-baseline gap-1.5 flex-wrap">
                                                <span className="text-[12px] font-semibold text-[#0B0B0B]">{row.name}</span>
                                                {row.title && <span className="text-[11px] font-mono text-[#9ca3af]">· {row.title}</span>}
                                                <span className="text-[11px] font-mono text-[#6B7280]">@ {row.org}</span>
                                            </div>
                                            {row.replacement && (
                                                <p className="text-[10px] font-mono text-[#8b5cf6] mt-0.5">
                                                    ↳ Replacement: {row.replacement}
                                                </p>
                                            )}
                                            {row.error && (
                                                <p className="text-[10px] font-mono text-[#dc2626] mt-0.5 truncate" title={row.error}>
                                                    ↳ {row.error}
                                                </p>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            {row.elapsed != null && row.phase !== 'running' && (
                                                <span className="text-[10px] font-mono text-[#9ca3af] tabular-nums">{row.elapsed}s</span>
                                            )}
                                            {row.cost_usd != null && row.cost_usd > 0 && (
                                                <span className="text-[10px] font-mono text-[#9ca3af] tabular-nums">${row.cost_usd.toFixed(4)}</span>
                                            )}
                                            <StatusBadge phase={row.phase} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Completion summary */}
                        {batchSummary && (
                            <div className="px-4 py-4 bg-[#f9fafb] border-t border-[#e5e7eb]">
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                                    <SummaryCell label="Processed" value={String(batchSummary.processed)} />
                                    <SummaryCell label="Active" value={String(batchSummary.active)} color="#10b981" />
                                    <SummaryCell label="Inactive" value={String(batchSummary.inactive)} color="#ef4444" />
                                    <SummaryCell label="Replacements" value={String(batchSummary.replacements)} color="#8b5cf6" />
                                    <SummaryCell label="Flagged" value={String(batchSummary.flagged)} color="#f59e0b" />
                                    <SummaryCell label="Errors" value={String(batchSummary.errors)} color={batchSummary.errors > 0 ? '#dc2626' : undefined} />
                                    <SummaryCell label="API Cost" value={`$${batchSummary.total_cost_usd.toFixed(4)}`} />
                                    <SummaryCell label="Elapsed" value={`${batchSummary.elapsed}s`} />
                                </div>
                                {batchSummary.processed > 0 && (
                                    <p className="text-[10px] font-mono text-[#9ca3af]">
                                        ROI: +{fmt(batchSummary.roi_pct)}% &nbsp;·&nbsp;
                                        Value generated: ${batchSummary.total_value_usd.toFixed(2)} &nbsp;·&nbsp;
                                        Refresh Value Receipt to see full breakdown.
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                )}
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
                            <tbody className="divide-y divide-[#e5e7eb]">
                                {receipts.map(r => (
                                    <tr key={r.id} className="border-b border-transparent hover:bg-[#f9fafb] transition-colors group">
                                        <td className="py-4 pr-4 font-mono text-[#6B7280]">
                                            {new Date(r.run_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                        </td>
                                        <td className="py-4 pr-4 font-bold text-[#0B0B0B]">{r.contacts_processed}</td>
                                        <td className="py-4 pr-4 font-bold" style={{ color: '#3DF577' }}>{r.contacts_verified_active}</td>
                                        <td className="py-4 pr-4 text-[#6B7280] font-bold">{r.contacts_marked_inactive}</td>
                                        <td className="py-4 pr-4 text-[#0B0B0B] font-bold">{r.replacements_found}</td>
                                        <td className="py-4 pr-4 font-mono text-[#6B7280]">${r.total_api_cost_usd?.toFixed(4)}</td>
                                        <td className="py-4 pr-4 font-mono text-[#0B0B0B]">${fmt(r.total_value_generated_usd, 2)}</td>
                                        <td className="py-4 pr-4">
                                            <span className="bg-white border border-[#3DF577] text-[#3DF577] text-[10px] font-mono font-bold px-2 py-0.5 rounded shadow-sm">
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

function SummaryCell({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <div className="bg-white rounded border border-[#e5e7eb] px-3 py-2">
            <p className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#9ca3af] mb-0.5">{label}</p>
            <p className="text-[14px] font-bold font-mono tabular-nums" style={{ color: color ?? '#0B0B0B' }}>{value}</p>
        </div>
    );
}
