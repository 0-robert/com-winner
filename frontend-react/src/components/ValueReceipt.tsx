import { DollarSign, Zap, FileText } from 'lucide-react';

export default function ValueReceipt() {
    // Mock data for the report
    const r = {
        contacts_processed: 1250,
        replacements_found: 42,
        flagged_for_review: 18,
        total_value_generated_usd: 105.00,
        total_api_cost_usd: 1.4582,
        net_roi_percentage: 7100,
        simulated_invoice_usd: 230.00
    };

    return (
        <div>
            <div className="mb-6 pl-1">
                <h1 className="text-[24px] font-bold text-slate-900 tracking-tight mb-1">
                    Value Receipt
                </h1>
                <p className="text-[12px] font-mono text-slate-500 uppercase tracking-widest font-semibold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-green-500"></span> <span>Outcome-based ROI</span>
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="col-span-1 md:col-span-3 overflow-hidden rounded bg-white p-6 shadow-sm border border-slate-200">
                    <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div>
                            <p className="text-slate-500 font-mono text-[11px] font-bold uppercase tracking-widest mb-2">Net ROI This Run</p>
                            <div className="text-5xl md:text-6xl font-black text-slate-800 tracking-tighter">
                                +{r.net_roi_percentage.toLocaleString()}%
                            </div>
                        </div>
                        <div className="flex gap-3 w-full md:w-auto">
                            <div className="flex-1 bg-slate-50 border border-slate-200 p-4 rounded flex flex-col justify-center min-w-[130px]">
                                <p className="text-slate-600 font-mono text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5"><DollarSign size={14} className="text-green-600" /> Value Gen</p>
                                <p className="text-2xl font-bold text-slate-800">${r.total_value_generated_usd.toFixed(2)}</p>
                            </div>
                            <div className="flex-1 bg-slate-50 border border-slate-200 p-4 rounded flex flex-col justify-center min-w-[130px]">
                                <p className="text-slate-600 font-mono text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5"><Zap size={14} className="text-orange-500" /> API Cost</p>
                                <p className="text-2xl font-bold text-slate-800">${r.total_api_cost_usd.toFixed(4)}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <KpiCard label="Rows Processed" value={r.contacts_processed} />
                <KpiCard label="Replacements" value={r.replacements_found} highlight />
                <KpiCard label="Flagged Details" value={r.flagged_for_review} />
            </div>

            <div className="bg-white rounded border border-slate-200 overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <h3 className="text-[14px] font-bold text-slate-800 flex items-center gap-2 tracking-tight">
                        <FileText size={16} className="text-slate-500" />
                        Outcome-Based Invoice
                    </h3>
                    <div className="bg-white text-slate-800 px-3 py-1.5 rounded border border-slate-200 font-mono font-bold text-[12px] shadow-sm">
                        TOTAL_USD: ${r.simulated_invoice_usd.toFixed(2)}
                    </div>
                </div>
                <div className="p-0">
                    <table className="w-full text-left text-[13px]">
                        <thead className="bg-white text-slate-500 text-[11px] uppercase tracking-widest font-mono font-bold">
                            <tr>
                                <th className="px-6 py-3 border-b border-slate-200">Service Request</th>
                                <th className="px-6 py-3 border-b border-slate-200 text-right">Qty</th>
                                <th className="px-6 py-3 border-b border-slate-200 text-right">Unit Price</th>
                                <th className="px-6 py-3 border-b border-slate-200 text-right text-slate-700">Total</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                            <tr className="hover:bg-slate-50 transition-colors group">
                                <td className="px-6 py-4 font-bold text-slate-700">Contact Verifications</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-500 tabular-nums">{r.contacts_processed}</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-500 tabular-nums">$0.10</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-800 font-bold tabular-nums">${(r.contacts_processed * 0.10).toFixed(2)}</td>
                            </tr>
                            <tr className="hover:bg-slate-50 transition-colors group">
                                <td className="px-6 py-4 font-bold text-slate-700">Replacements Discovered</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-500 tabular-nums">{r.replacements_found}</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-500 tabular-nums">$2.50</td>
                                <td className="px-6 py-4 text-right font-mono text-slate-800 font-bold tabular-nums">${(r.replacements_found * 2.50).toFixed(2)}</td>
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
        <div className={`p-6 rounded border ${highlight ? 'border-blue-200 bg-blue-50/50' : 'border-slate-200 bg-white'} flex flex-col items-center justify-center text-center shadow-sm`}>
            <p className={`text-4xl font-black mb-2 tracking-tighter ${highlight ? 'text-blue-700' : 'text-slate-800'}`}>{value}</p>
            <p className={`text-[10px] font-mono font-bold uppercase tracking-widest ${highlight ? 'text-blue-600' : 'text-slate-500'}`}>{label}</p>
        </div>
    );
}
