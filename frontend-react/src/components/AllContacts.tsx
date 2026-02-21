import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { Contact } from '../types';
import { MoreVertical, FileText, CheckCircle2, X, ExternalLink, RefreshCw, Edit, Trash } from 'lucide-react';

const STATUS_CONFIG = {
    active: { label: 'CONFIRMED ACTIVE', badge: 'bg-green-50 text-green-700 border-green-200' },
    unknown: { label: 'NEEDS REVIEW', badge: 'bg-orange-50 text-orange-700 border-orange-200' },
    inactive: { label: 'DEPARTED / INACTIVE', badge: 'bg-slate-100 text-slate-600 border-slate-200' },
    opted_out: { label: 'OPTED OUT', badge: 'bg-red-50 text-red-700 border-red-200' },
} as const;

export default function AllContacts() {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [activeTab, setActiveTab] = useState('All Contacts');
    const [selectedNotesContact, setSelectedNotesContact] = useState<Contact | null>(null);
    const [selectedMoreContact, setSelectedMoreContact] = useState<Contact | null>(null);

    useEffect(() => {
        fetchContacts();
    }, []);

    async function fetchContacts() {
        try {
            const { data } = await supabase.from('contacts').select('*').order('name');
            setContacts(data || []);
        } catch (err) {
            console.error(err);
        }
    }

    const displayContacts = contacts.length > 0 ? contacts : [
        { id: '1', name: 'Courtney Henry', title: 'VP of Engineering', email: 'courtney@example.com', organization: 'Prodify', status: 'active', needs_human_review: false },
        { id: '2', name: 'Tom Cook', title: 'Director', email: 'tom@example.com', organization: 'Acme Corp', status: 'unknown', needs_human_review: true },
        { id: '3', name: 'Jane Doe', title: 'Head of Growth', email: 'jane@example.com', organization: 'Stark Ind', status: 'active', needs_human_review: false },
        { id: '4', name: 'John Smith', title: 'Sales Executive', email: 'john@smith.com', organization: 'Globex', status: 'inactive', needs_human_review: false },
        { id: '5', name: 'Alice Johnson', title: 'CMO', email: 'alice@company.com', organization: 'Initech', status: 'opted_out', needs_human_review: false },
    ] as Contact[];

    const tabs = ['All Contacts', 'Review Required', 'Departed'];

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

                {/* Tabs & Controls */}
                <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">
                    <div className="flex gap-2">
                        {tabs.map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`px-4 py-1.5 rounded text-[12px] font-bold transition-all border ${activeTab === tab ? 'bg-white border-blue-600 text-blue-700 shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-800'}`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                </div>

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
                    {displayContacts.map((contact) => (
                        <div key={contact.id} className="group relative">
                            {/* Hover floating effect container */}
                            <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center bg-white rounded border border-transparent transition-colors hover:bg-slate-50">

                                <div className="col-span-4 flex items-center gap-3">
                                    <div className="w-3.5 h-3.5 rounded-sm border border-slate-300 pointer-events-none group-hover:border-blue-400 bg-white"></div>
                                    <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px]">
                                        {contact.name.split(' ').map((n: string) => n[0]).join('')}
                                    </div>
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-[13px] font-bold text-slate-900 truncate">
                                            {contact.name}
                                        </span>
                                        <span className="text-[11px] font-mono text-slate-500 truncate">{contact.email}</span>
                                    </div>
                                </div>

                                <div className="col-span-3 flex flex-col justify-center min-w-0">
                                    <span className="text-[12px] font-bold text-slate-800 truncate">{contact.organization}</span>
                                    <span className="text-[11px] font-mono text-slate-500 truncate">{contact.title || 'Unknown Role'}</span>
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
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider inline-flex items-center gap-1 border uppercase shadow-sm ${contact.needs_human_review ? STATUS_CONFIG.unknown.badge : STATUS_CONFIG[contact.status as keyof typeof STATUS_CONFIG]?.badge || STATUS_CONFIG.inactive.badge
                                        }`}>
                                        {contact.status === 'active' && <CheckCircle2 size={10} />}
                                        {contact.needs_human_review ? 'REVIEW' : contact.status}
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
            {
                selectedNotesContact && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
                        <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                                <div>
                                    <h3 className="text-[16px] font-bold text-slate-900 flex items-center gap-2">
                                        <FileText size={16} className="text-slate-400" />
                                        Agentic Notes
                                    </h3>
                                    <p className="text-[11px] font-mono text-slate-500 mt-1">{selectedNotesContact?.name} ({selectedNotesContact?.organization})</p>
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
                                            <span className="text-orange-600 font-bold">[!] FLAG: NEEDS REVIEW</span><br /><br />
                                            - ZeroBounce returned valid email.<br />
                                            - Could not locate on district website.<br />
                                            - LinkedIn profile is private or not exact match.<br />
                                            - Claude analysis: "Uncertain if still at {selectedNotesContact?.organization}. Proceed with caution."<br />
                                        </>
                                    ) : (
                                        <>
                                            <span className="text-green-600 font-bold">[✓] VERIFIED ACTIVE</span><br /><br />
                                            - ZeroBounce returned valid email.<br />
                                            - Found on {selectedNotesContact?.organization} staff page.<br />
                                            - No conflicting data on LinkedIn.<br />
                                            - Claude analysis: "High confidence still active."<br />
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
                )
            }

            {/* More Options Modal */}
            {
                selectedMoreContact && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
                        <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200 text-[11px]">
                                        {selectedMoreContact?.name?.split(' ').map((n: string) => n[0]).join('')}
                                    </div>
                                    <h3 className="text-[14px] font-bold text-slate-900">{selectedMoreContact?.name}</h3>
                                </div>
                                <button
                                    onClick={() => setSelectedMoreContact(null)}
                                    className="text-slate-400 hover:text-slate-700 transition-colors p-1"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="p-2">
                                <button onClick={() => setSelectedMoreContact(null)} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors">
                                    <ExternalLink size={16} className="text-slate-400" />
                                    <span className="text-[13px] font-semibold text-slate-700">View LinkedIn Profile</span>
                                </button>
                                <button onClick={() => setSelectedMoreContact(null)} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors">
                                    <RefreshCw size={16} className="text-slate-400" />
                                    <span className="text-[13px] font-semibold text-slate-700">Force Agentic Sync</span>
                                </button>
                                <button onClick={() => setSelectedMoreContact(null)} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 rounded text-left transition-colors">
                                    <Edit size={16} className="text-slate-400" />
                                    <span className="text-[13px] font-semibold text-slate-700">Edit Contact Data</span>
                                </button>
                            </div>
                            <div className="p-2 border-t border-slate-100 bg-slate-50/50">
                                <button onClick={() => setSelectedMoreContact(null)} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-50 rounded text-left transition-colors group">
                                    <Trash size={16} className="text-red-400 group-hover:text-red-600 transition-colors" />
                                    <span className="text-[13px] font-semibold text-red-600">Delete Contact</span>
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
