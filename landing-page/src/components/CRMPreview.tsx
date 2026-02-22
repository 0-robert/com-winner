import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const CONTACTS = [
  { i: 'RL', name: 'Robby Linson', email: 'robbylinson@gmail.com', org: 'Trinity College Dublin', role: 'Student', status: 'UNKNOWN', sc: '#d97706', sf: '#fffbeb', fresh: 'NEVER', fc: '#9ca3af', risk: null },
  { i: 'AP', name: 'Alex Pivovarov', email: 'alexpivovarov156@gmail.com', org: 'KGB lacky', role: 'Student', status: 'REVIEW', sc: '#d97706', sf: '#fffbeb', fresh: 'FRESH', fc: '#059669', risk: 47 },
  { i: 'JD', name: 'John Doe', email: 'test@catch-all-domain.com', org: 'Fake School District', role: 'Director of Special Ed...', status: 'UNKNOWN', sc: '#d97706', sf: '#fffbeb', fresh: 'NEVER', fc: '#9ca3af', risk: null },
  { i: 'SC', name: 'Sarah Chen', email: 'sarah.chen@techcorp.io', org: 'TechCorp Inc.', role: 'VP Sales', status: 'VERIFIED', sc: '#059669', sf: '#f0fdf4', fresh: 'FRESH', fc: '#059669', risk: 5 },
]

export default function CRMPreview() {
  const sectionRef = useRef<HTMLElement>(null)
  const browserRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.crm-label', {
        scrollTrigger: { trigger: '.crm-label', start: 'top 88%' },
        opacity: 0, y: 20, duration: 0.6, ease: 'power2.out',
      })
      gsap.from(browserRef.current, {
        scrollTrigger: { trigger: browserRef.current, start: 'top 82%' },
        opacity: 0, y: 40, scale: 0.98, duration: 0.9, ease: 'power3.out',
      })
      gsap.from('.crm-row-item', {
        scrollTrigger: { trigger: browserRef.current, start: 'top 78%' },
        opacity: 0, x: -16, stagger: 0.1, duration: 0.45, delay: 0.35, ease: 'power2.out',
      })
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section id="demo" ref={sectionRef} className="py-28 px-8 bg-[#f9fafb]">
      <div className="max-w-6xl mx-auto">
        {/* Label */}
        <div className="crm-label max-w-2xl mx-auto text-center mb-14">
          <div
            className="text-xs font-semibold text-[#2563eb] tracking-widest uppercase mb-4"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            The Interface
          </div>
          <h2
            className="font-bold text-[#111827] mb-4"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(28px, 4vw, 48px)', lineHeight: '1.1' }}
          >
            Clean data.{' '}
            <span className="italic">Beautiful interface.</span>
          </h2>
          <p
            className="text-[#6b7280] text-base"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Everything your team needs to trust their data, in one focused view.
          </p>
        </div>

        {/* Browser */}
        <div
          ref={browserRef}
          className="rounded-xl overflow-hidden border border-[#e5e7eb] bg-white"
          style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 20px 60px rgba(0,0,0,0.06)' }}
        >
          {/* Chrome */}
          <div className="bg-[#f9fafb] border-b border-[#e5e7eb] px-4 py-2.5 flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#fca5a5]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#fde68a]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#6ee7b7]" />
            </div>
            <div className="flex-1 flex justify-center">
              <div className="bg-white border border-[#e5e7eb] rounded px-3 py-1 text-xs text-[#9ca3af] flex items-center gap-1.5">
                <span>🔒</span> app.prospectkeeper.com
              </div>
            </div>
          </div>

          {/* App layout */}
          <div className="flex min-h-0">
            {/* Sidebar */}
            <div className="w-52 bg-white border-r border-[#f3f4f6] flex-shrink-0 hidden md:flex flex-col p-4">
              <div className="flex items-center gap-2 mb-8 px-1">
                <div className="w-7 h-7 rounded-lg bg-[#111827] flex items-center justify-center">
                  <span className="text-white text-xs font-bold" style={{ fontFamily: 'var(--font-serif)' }}>PK</span>
                </div>
                <div>
                  <div className="text-[#111827] text-xs font-semibold" style={{ fontFamily: 'var(--font-sans)' }}>ProspectKeeper</div>
                  <div className="text-[#9ca3af] text-[9px]">AGENTIC-CRM-V1</div>
                </div>
              </div>

              {[
                { icon: '⊞', label: 'Dashboard' },
                { icon: '☰', label: 'All Contacts', active: true },
                { icon: '⟳', label: 'Human Review', badge: 'NEW' },
                { icon: '◈', label: 'Value Receipt' },
                { icon: '⚙', label: 'Settings' },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md mb-0.5 text-xs cursor-pointer transition-colors ${item.active ? 'bg-[#eff6ff] text-[#2563eb]' : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#374151]'}`}
                  style={{ fontFamily: 'var(--font-sans)' }}
                >
                  <span className="text-sm">{item.icon}</span>
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="text-[8px] bg-[#2563eb] text-white px-1.5 py-0.5 rounded-full font-semibold">{item.badge}</span>
                  )}
                </div>
              ))}

              <div className="mt-auto">
                <div className="bg-[#f9fafb] border border-[#f3f4f6] rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#059669] shadow-[0_0_4px_#059669]" />
                    <span className="text-[#059669] text-[10px] font-semibold">Background Sync</span>
                  </div>
                  <div className="text-[#9ca3af] text-[9px]">Agentic workers are active.</div>
                  <div className="text-[#d1d5db] text-[9px]">Last sync: just now</div>
                </div>
              </div>
            </div>

            {/* Main */}
            <div className="flex-1 p-6 min-w-0">
              <div className="flex items-center justify-between mb-5">
                <div className="flex-1 max-w-md bg-[#f9fafb] border border-[#e5e7eb] rounded-lg px-3 py-2 flex items-center gap-2">
                  <span className="text-[#9ca3af] text-sm">⌕</span>
                  <span className="text-[#9ca3af] text-sm" style={{ fontFamily: 'var(--font-sans)' }}>Search anything...</span>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center gap-1 transition-colors" style={{ fontFamily: 'var(--font-sans)' }}>
                    + Add contact
                  </button>
                  <div className="w-8 h-8 rounded-lg bg-[#f3f4f6] border border-[#e5e7eb] flex items-center justify-center text-xs font-semibold text-[#374151]">RV</div>
                </div>
              </div>

              <div className="mb-5">
                <h1 className="text-xl font-bold text-[#111827] mb-1" style={{ fontFamily: 'var(--font-sans)' }}>Manage Contacts</h1>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#2563eb]" />
                  <span className="text-[#9ca3af] text-xs tracking-widest uppercase" style={{ fontFamily: 'var(--font-sans)' }}>Agentic Database</span>
                </div>
              </div>

              {/* Table card */}
              <div className="border border-[#e5e7eb] rounded-xl overflow-hidden">
                {/* Tabs */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#f3f4f6] bg-white">
                  <div className="flex gap-2">
                    {['All Contacts', 'Review Required', 'Departed'].map((tab, i) => (
                      <button
                        key={tab}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${i === 0 ? 'bg-[#eff6ff] text-[#2563eb] border border-[#bfdbfe]' : 'text-[#6b7280] border border-transparent hover:border-[#e5e7eb]'}`}
                        style={{ fontFamily: 'var(--font-sans)' }}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button className="text-xs border border-[#e5e7eb] px-3 py-1.5 rounded-md text-[#374151] hover:bg-[#f9fafb] transition-colors flex items-center gap-1" style={{ fontFamily: 'var(--font-sans)' }}>
                      ✉ Email All
                    </button>
                    <button className="text-xs bg-[#2563eb] text-white px-3 py-1.5 rounded-md flex items-center gap-1 hover:bg-[#1d4ed8] transition-colors" style={{ fontFamily: 'var(--font-sans)' }}>
                      ↻ Refresh
                    </button>
                  </div>
                </div>

                {/* Column headers */}
                <div className="grid px-4 py-2 bg-[#f9fafb] border-b border-[#f3f4f6]" style={{ gridTemplateColumns: '2fr 2fr 1fr 1.2fr 0.8fr 0.4fr' }}>
                  {['CLIENT', 'ORG / ROLE', 'STATUS', 'FRESHNESS', 'RISK', ''].map((h) => (
                    <div key={h} className="text-[10px] font-semibold text-[#9ca3af] tracking-widest" style={{ fontFamily: 'var(--font-sans)' }}>{h}</div>
                  ))}
                </div>

                {/* Rows */}
                {CONTACTS.map((c) => (
                  <div
                    key={c.email}
                    className="crm-row-item grid px-4 py-3.5 border-b border-[#f9fafb] last:border-0 hover:bg-[#f9fafb] transition-colors group cursor-pointer"
                    style={{ gridTemplateColumns: '2fr 2fr 1fr 1.2fr 0.8fr 0.4fr' }}
                  >
                    <div className="flex items-center gap-3">
                      <input type="checkbox" className="opacity-0 group-hover:opacity-100 w-3.5 h-3.5 rounded accent-[#2563eb] flex-shrink-0" />
                      <div className="w-8 h-8 rounded-lg bg-[#f3f4f6] border border-[#e5e7eb] flex items-center justify-center flex-shrink-0">
                        <span className="text-[#6b7280] text-[9px] font-bold">{c.i}</span>
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-[#111827]" style={{ fontFamily: 'var(--font-sans)' }}>{c.name}</div>
                        <div className="text-[10px] text-[#9ca3af]">{c.email}</div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      <div>
                        <div className="text-xs font-medium text-[#374151]">{c.org}</div>
                        <div className="text-[10px] text-[#9ca3af]">{c.role}</div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      <span className="text-[9px] font-bold px-2 py-1 rounded border" style={{ color: c.sc, background: c.sf, borderColor: `${c.sc}40` }}>{c.status}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.fc }} />
                      <span className="text-[10px] font-semibold" style={{ color: c.fc }}>{c.fresh}</span>
                    </div>
                    <div className="flex items-center">
                      {c.risk !== null ? (
                        <span
                          className="text-sm font-bold"
                          style={{ color: c.risk > 70 ? '#dc2626' : c.risk > 30 ? '#d97706' : '#059669', fontFamily: 'var(--font-serif)' }}
                        >
                          {c.risk}
                        </span>
                      ) : (
                        <span className="text-[#d1d5db] text-xs">—</span>
                      )}
                    </div>
                    <div className="flex items-center justify-end">
                      <span className="text-[#9ca3af] opacity-0 group-hover:opacity-100 transition-opacity text-sm">⋮</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <p
          className="text-center text-[#9ca3af] text-sm mt-5"
          style={{ fontFamily: 'var(--font-sans)' }}
        >
          Agents are running in the background — data updates automatically
        </p>
      </div>
    </section>
  )
}
