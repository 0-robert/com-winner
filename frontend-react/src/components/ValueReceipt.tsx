import { useEffect, useState } from 'react';
import { DollarSign, Zap, FileText, Activity, ExternalLink, RefreshCw } from 'lucide-react';

interface GenerationSummary {
    name: string | null;
    model: string | null;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    start_time: string | null;
}

interface LangfuseStats {
    total_calls: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    total_cost_usd: number;
    avg_cost_per_call: number;
    recent: GenerationSummary[];
    langfuse_dashboard_url: string;
}

// Static receipt data (batch-level metrics)
const r = {
    contacts_processed: 1250,
    replacements_found: 42,
    flagged_for_review: 18,
    total_value_generated_usd: 105.00,
    net_roi_percentage: 7100,
    simulated_invoice_usd: 230.00,
};

export default function ValueReceipt() {
    const [stats, setStats] = useState<LangfuseStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = () => {
        setLoading(true);
        setError(null);
        fetch('/api/langfuse-stats', { headers: { 'X-API-Key': 'dev-key' } })
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then((data: LangfuseStats & { not_configured?: boolean }) => {
                // Stub returns not_configured=true until Langfuse is wired
                if (data.not_configured) {
                    setStats(null);
                } else {
                    setStats(data);
                }
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    };

    useEffect(() => { fetchStats(); }, []);

    const apiCost = stats?.total_cost_usd ?? r.total_value_generated_usd;

    return (
        <div>
            <div className="mb-6 pl-1">
                <h1 className="text-[32px] font-bold text-[#0B0B0B] tracking-tight mb-1 font-serif">
                    Value Receipt
                </h1>
                <p className="text-[12px] font-mono text-[#6B7280] uppercase tracking-widest font-semibold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#3DF577] rounded-full inline-block"></span> <span>Outcome-based ROI</span>
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="col-span-1 md:col-span-3 overflow-hidden rounded bg-white p-6 shadow-sm border border-[#e5e7eb]">
                    <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div>
                            <p className="text-[#6B7280] font-mono text-[11px] font-bold uppercase tracking-widest mb-2">Net ROI This Run</p>
                            <div className="text-5xl md:text-6xl font-black text-[#0B0B0B] tracking-tighter">
                                +{r.net_roi_percentage.toLocaleString()}%
                            </div>
                        </div>
                        <div className="flex gap-3 w-full md:w-auto">
                            <div className="flex-1 bg-[#f9fafb] border border-[#e5e7eb] p-4 rounded flex flex-col justify-center min-w-[130px]">
                                <p className="text-[#6B7280] font-mono text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5"><DollarSign size={14} className="text-[#3DF577]" /> Value Gen</p>
                                <p className="text-2xl font-bold text-[#0B0B0B]">${r.total_value_generated_usd.toFixed(2)}</p>
                            </div>
                            <div className="flex-1 bg-[#f9fafb] border border-[#e5e7eb] p-4 rounded flex flex-col justify-center min-w-[160px]">
                                <p className="text-[#6B7280] font-mono text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5"><Zap size={14} className="text-[#0B0B0B]" /> API Cost</p>
                                <p className="text-xl font-bold text-[#0B0B0B] tabular-nums">
                                    {stats ? `$${stats.total_cost_usd.toFixed(4)}` : loading ? <span className="text-[#9ca3af] text-base">Loading…</span> : `$${apiCost.toFixed(4)}`}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <KpiCard label="Rows Processed" value={r.contacts_processed} />
                <KpiCard label="Replacements" value={r.replacements_found} highlight />
                <KpiCard label="Flagged Details" value={r.flagged_for_review} />
            </div>

            {/* ── Langfuse Claude API Usage ──────────────────────────────── */}
            <div className="mb-6 bg-white rounded border border-[#e5e7eb] overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-[#e5e7eb] flex justify-between items-center bg-[#f9fafb]">
                    <h3 className="text-[14px] font-bold text-[#0B0B0B] flex items-center gap-2 tracking-tight">
                        <Activity size={16} className="text-[#0B0B0B]" />
                        Claude API Usage
                        <span className="text-[10px] font-mono font-normal text-[#6B7280] bg-white border border-[#e5e7eb] px-1.5 py-0.5 rounded">via Langfuse</span>
                    </h3>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={fetchStats}
                            disabled={loading}
                            className="text-[#6B7280] hover:text-[#0B0B0B] transition-colors disabled:opacity-40"
                            title="Refresh"
                        >
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </button>
                        {stats && (
                            <a
                                href={stats.langfuse_dashboard_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] font-mono text-[#0B0B0B] hover:text-black flex items-center gap-1 transition-colors underline underline-offset-2"
                            >
                                Open Dashboard <ExternalLink size={11} />
                            </a>
                        )}
                    </div>
                </div>

                {loading && (
                    <div className="px-6 py-8 text-center text-[#9ca3af] font-mono text-[12px]">
                        Fetching stats...
                    </div>
                )}

                {!loading && !error && !stats && (
                    <div className="px-6 py-8 text-center text-[#9ca3af] font-mono text-[12px]">
                        Langfuse not configured — stats will appear here once connected.
                    </div>
                )}

                {error && (
                    <div className="px-6 py-4 text-[12px] font-mono text-red-500 bg-red-50 border-b border-red-100">
                        Could not load Langfuse stats: {error}. Is the backend running?
                    </div>
                )}

                {stats && (
                    <>
                        {/* Token + cost summary grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-[#e5e7eb] border-b border-[#e5e7eb]">
                            <StatCell label="Total API Calls" value={stats.total_calls.toLocaleString()} />
                            <StatCell label="Input Tokens" value={stats.total_input_tokens.toLocaleString()} />
                            <StatCell label="Output Tokens" value={stats.total_output_tokens.toLocaleString()} />
                            <StatCell label="Est. Total Cost" value={`$${stats.total_cost_usd.toFixed(4)}`} highlight />
                        </div>

                        {/* Recent generations table */}
                        {stats.recent.length > 0 && (
                            <div>
                                <p className="px-6 pt-4 pb-2 text-[10px] font-mono font-bold uppercase tracking-widest text-[#9ca3af]">
                                    Recent Generations
                                </p>
                                <table className="w-full text-left text-[12px]">
                                    <thead className="bg-[#f9fafb] text-[#6B7280] text-[10px] uppercase tracking-widest font-mono font-bold">
                                        <tr>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t">Name</th>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t">Model</th>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t text-right">In</th>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t text-right">Out</th>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t text-right">Cost</th>
                                            <th className="px-6 py-2 border-b border-[#e5e7eb] border-t text-right">Time</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#e5e7eb]">
                                        {stats.recent.map((g, i) => (
                                            <tr key={i} className="hover:bg-[#f9fafb] transition-colors">
                                                <td className="px-6 py-2.5 font-mono text-[#6B7280]">{g.name ?? '—'}</td>
                                                <td className="px-6 py-2.5 text-[#6B7280]">{g.model ?? '—'}</td>
                                                <td className="px-6 py-2.5 text-right font-mono tabular-nums text-[#6B7280]">{g.input_tokens.toLocaleString()}</td>
                                                <td className="px-6 py-2.5 text-right font-mono tabular-nums text-[#6B7280]">{g.output_tokens.toLocaleString()}</td>
                                                <td className="px-6 py-2.5 text-right font-mono tabular-nums text-[#0B0B0B] font-semibold">${g.cost_usd.toFixed(5)}</td>
                                                <td className="px-6 py-2.5 text-right font-mono text-[#9ca3af] text-[10px]">
                                                    {g.start_time ? new Date(g.start_time).toLocaleTimeString() : '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* ── Simulated Invoice ─────────────────────────────────────── */}
            <div className="bg-white rounded border border-[#e5e7eb] overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-[#e5e7eb] flex justify-between items-center bg-[#f9fafb]">
                    <h3 className="text-[14px] font-bold text-[#0B0B0B] flex items-center gap-2 tracking-tight">
                        <FileText size={16} className="text-[#6B7280]" />
                        Outcome-Based Invoice
                    </h3>
                    <div className="bg-white text-[#0B0B0B] px-3 py-1.5 rounded-lg border border-[#0B0B0B] font-mono font-bold text-[12px] shadow-sm">
                        Amount Due: ${r.simulated_invoice_usd.toFixed(2)}
                    </div>
                </div>
                <div className="p-0">
                    <table className="w-full text-left text-[13px]">
                        <thead className="bg-white text-[#6B7280] text-[11px] uppercase tracking-widest font-mono font-bold">
                            <tr>
                                <th className="px-6 py-3 border-b border-[#e5e7eb]">Service Request</th>
                                <th className="px-6 py-3 border-b border-[#e5e7eb] text-right">Qty</th>
                                <th className="px-6 py-3 border-b border-[#e5e7eb] text-right">Unit Price</th>
                                <th className="px-6 py-3 border-b border-[#e5e7eb] text-right text-[#0B0B0B]">Total</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#e5e7eb] bg-white">
                            <tr className="hover:bg-[#f9fafb] transition-colors group">
                                <td className="px-6 py-4 font-bold text-[#0B0B0B]">Contact Verifications</td>
                                <td className="px-6 py-4 text-right font-mono text-[#6B7280] tabular-nums">{r.contacts_processed}</td>
                                <td className="px-6 py-4 text-right font-mono text-[#6B7280] tabular-nums">$0.10</td>
                                <td className="px-6 py-4 text-right font-mono text-[#0B0B0B] font-bold tabular-nums">${(r.contacts_processed * 0.10).toFixed(2)}</td>
                            </tr>
                            <tr className="hover:bg-[#f9fafb] transition-colors group">
                                <td className="px-6 py-4 font-bold text-[#0B0B0B]">Replacements Discovered</td>
                                <td className="px-6 py-4 text-right font-mono text-[#6B7280] tabular-nums">{r.replacements_found}</td>
                                <td className="px-6 py-4 text-right font-mono text-[#6B7280] tabular-nums">$2.50</td>
                                <td className="px-6 py-4 text-right font-mono text-[#0B0B0B] font-bold tabular-nums">${(r.replacements_found * 2.50).toFixed(2)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function KpiCard({ label, value, highlight = false }: { label: string, value: number, highlight?: boolean }) {
    return (
        <div className={`p-6 rounded border ${highlight ? 'border-[#0B0B0B] bg-white' : 'border-[#e5e7eb] bg-[#f9fafb]'} flex flex-col items-center justify-center text-center shadow-sm`}>
            <p className={`text-4xl font-black mb-2 tracking-tighter text-[#0B0B0B]`}>{value}</p>
            <p className={`text-[10px] font-mono font-bold uppercase tracking-widest ${highlight ? 'text-[#0B0B0B]' : 'text-[#6B7280]'}`}>{label}</p>
        </div>
    );
}

function StatCell({ label, value, highlight = false }: { label: string, value: string, highlight?: boolean }) {
    return (
        <div className="px-6 py-4 flex flex-col gap-0.5">
            <p className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#9ca3af]">{label}</p>
            <p className={`text-xl font-black tracking-tight ${highlight ? 'text-[#3DF577]' : 'text-[#0B0B0B]'}`}>{value}</p>
        </div>
    );
}
