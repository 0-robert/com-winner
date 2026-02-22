import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, RefreshCw, Play, Loader2 } from 'lucide-react';

interface ConfigStatus {
    anthropic_configured: boolean;
    supabase_configured: boolean;
    langfuse_configured: boolean;
    zerobounce_configured: boolean;
    resend_configured: boolean;
    batch_limit: number;
    batch_concurrency: number;
}

const API_KEY = 'dev-key';

const API_KEYS = [
    { key: 'anthropic_configured', label: 'Anthropic (Claude)', description: 'Required for AI verification (Tier 3)' },
    { key: 'supabase_configured', label: 'Supabase', description: 'Required — contact database' },
    { key: 'langfuse_configured', label: 'Langfuse', description: 'LLM observability & cost tracking' },
    { key: 'resend_configured', label: 'Resend', description: 'Outbound confirmation emails' },
] as const;

export default function Settings() {
    const [config, setConfig] = useState<ConfigStatus | null>(null);
    const [loading, setLoading] = useState(true);

    const [limit, setLimit] = useState(50);
    const [concurrency, setConcurrency] = useState(5);
    const [tier, setTier] = useState<'free' | 'paid'>('free');

    const [runStatus, setRunStatus] = useState<'idle' | 'starting' | 'started' | 'error'>('idle');
    const [runError, setRunError] = useState<string | null>(null);

    useEffect(() => {
        fetch('/api/config-status', { headers: { 'X-API-Key': API_KEY } })
            .then(r => r.json())
            .then((data: ConfigStatus) => {
                setConfig(data);
                setLimit(data.batch_limit);
                setConcurrency(data.batch_concurrency);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    async function triggerRun() {
        setRunStatus('starting');
        setRunError(null);
        try {
            const res = await fetch(
                `/api/batch/run?tier=${tier}&limit=${limit}&concurrency=${concurrency}`,
                { method: 'POST', headers: { 'X-API-Key': API_KEY } }
            );
            if (!res.ok) {
                const body = await res.text();
                throw new Error(body || `HTTP ${res.status}`);
            }
            setRunStatus('started');
        } catch (err: any) {
            setRunError(err.message || 'Failed to start batch run.');
            setRunStatus('error');
        }
    }

    return (
        <div>
            <div className="mb-6 pl-1">
                <h1 className="text-[32px] font-bold text-[#0B0B0B] tracking-tight mb-1 font-serif">Settings</h1>
                <p className="text-[12px] font-mono text-[#6B7280] uppercase tracking-widest font-semibold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#3DF577] rounded-full inline-block"></span>
                    <span>Configuration & Agent Control</span>
                </p>
            </div>

            <div className="space-y-5">

                {/* ── API Key Status ── */}
                <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm">
                    <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-1">API Key Status</h2>
                    <p className="text-[11px] font-mono text-[#6B7280] mb-5">Keys are read from the <code className="bg-[#f3f4f6] px-1 rounded">.env</code> file on the server. No values are exposed here.</p>

                    {loading ? (
                        <div className="flex items-center gap-2 text-[#6B7280] text-[12px] font-mono">
                            <RefreshCw size={12} className="animate-spin" /> Checking…
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {API_KEYS.map(({ key, label, description }) => {
                                const ok = config?.[key] ?? false;
                                return (
                                    <div key={key} className="flex items-center justify-between py-2.5 border-b border-[#f3f4f6] last:border-0">
                                        <div>
                                            <p className="text-[13px] font-semibold text-[#0B0B0B]">{label}</p>
                                            <p className="text-[11px] font-mono text-[#9ca3af]">{description}</p>
                                        </div>
                                        <div className={`flex items-center gap-1.5 text-[11px] font-mono font-bold uppercase tracking-widest px-2.5 py-1 rounded border ${ok ? 'bg-[#ecfdf5] border-[#a7f3d0] text-[#10b981]' : 'bg-[#fef2f2] border-[#fecaca] text-[#ef4444]'}`}>
                                            {ok ? <CheckCircle size={11} /> : <XCircle size={11} />}
                                            {ok ? 'Configured' : 'Missing'}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* ── Batch Run Config ── */}
                <div className="bg-white rounded border border-[#e5e7eb] p-6 shadow-sm">
                    <h2 className="text-[14px] font-bold text-[#0B0B0B] tracking-tight mb-1">Batch Run</h2>
                    <p className="text-[11px] font-mono text-[#6B7280] mb-5">Configure and trigger an agent verification run against your contact list.</p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">

                        {/* Tier */}
                        <div>
                            <label className="block text-[11px] font-semibold text-[#6B7280] uppercase tracking-widest mb-2">Verification Tier</label>
                            <div className="flex gap-2">
                                {(['free', 'paid'] as const).map(t => (
                                    <button
                                        key={t}
                                        onClick={() => setTier(t)}
                                        className={`flex-1 py-2 rounded border text-[12px] font-bold font-mono uppercase tracking-widest transition-all ${tier === t ? 'bg-[#0B0B0B] text-white border-[#0B0B0B]' : 'bg-white text-[#6B7280] border-[#e5e7eb] hover:border-[#0B0B0B]'}`}
                                    >
                                        {t}
                                    </button>
                                ))}
                            </div>
                            <p className="text-[10px] font-mono text-[#9ca3af] mt-1.5">
                                {tier === 'free' ? 'Email validation only — ~$0.004/contact' : 'Email + scrape + Claude AI — ~$0.01–$0.05/contact'}
                            </p>
                        </div>

                        {/* Limit */}
                        <div>
                            <label className="block text-[11px] font-semibold text-[#6B7280] uppercase tracking-widest mb-2">Contact Limit</label>
                            <input
                                type="number"
                                min={1}
                                max={500}
                                value={limit}
                                onChange={e => setLimit(Number(e.target.value))}
                                className="w-full px-3 py-2 border border-[#e5e7eb] rounded text-[13px] font-mono focus:outline-none focus:border-[#0B0B0B] focus:ring-1 focus:ring-[#0B0B0B]"
                            />
                            <p className="text-[10px] font-mono text-[#9ca3af] mt-1.5">Max contacts to process per run</p>
                        </div>

                        {/* Concurrency */}
                        <div>
                            <label className="block text-[11px] font-semibold text-[#6B7280] uppercase tracking-widest mb-2">Concurrency</label>
                            <input
                                type="number"
                                min={1}
                                max={20}
                                value={concurrency}
                                onChange={e => setConcurrency(Number(e.target.value))}
                                className="w-full px-3 py-2 border border-[#e5e7eb] rounded text-[13px] font-mono focus:outline-none focus:border-[#0B0B0B] focus:ring-1 focus:ring-[#0B0B0B]"
                            />
                            <p className="text-[10px] font-mono text-[#9ca3af] mt-1.5">Parallel verification workers</p>
                        </div>
                    </div>

                    {/* Status feedback */}
                    {runStatus === 'started' && (
                        <div className="mb-4 bg-[#ecfdf5] border border-[#a7f3d0] rounded px-4 py-3 text-[12px] font-mono text-[#10b981] flex items-center gap-2">
                            <CheckCircle size={13} />
                            Batch run started in the background. Check the Dashboard for results once complete.
                        </div>
                    )}
                    {runStatus === 'error' && (
                        <div className="mb-4 bg-[#fef2f2] border border-[#fecaca] rounded px-4 py-3 text-[12px] font-mono text-[#ef4444]">
                            {runError}
                        </div>
                    )}

                    <button
                        onClick={triggerRun}
                        disabled={runStatus === 'starting'}
                        className="flex items-center gap-2 px-5 py-2.5 bg-[#3DF577] text-[#0B0B0B] rounded text-[13px] font-bold hover:bg-[#34d366] active:scale-[0.97] shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {runStatus === 'starting' ? (
                            <><Loader2 size={14} className="animate-spin" /> Starting…</>
                        ) : (
                            <><Play size={14} /> Run Batch Now</>
                        )}
                    </button>
                </div>

            </div>
        </div>
    );
}
