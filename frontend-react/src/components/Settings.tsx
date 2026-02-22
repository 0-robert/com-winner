import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, RefreshCw } from 'lucide-react';

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

    useEffect(() => {
        fetch('/api/config-status', { headers: { 'X-API-Key': API_KEY } })
            .then(r => r.json())
            .then((data: ConfigStatus) => setConfig(data))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div>
            <div className="mb-6 pl-1">
                <h1 className="text-[32px] font-bold text-[#0B0B0B] tracking-tight mb-1 font-serif">Settings</h1>
                <p className="text-[12px] font-mono text-[#6B7280] uppercase tracking-widest font-semibold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#3DF577] rounded-full inline-block"></span>
                    <span>Configuration & Agent Control</span>
                </p>
            </div>

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
        </div>
    );
}
