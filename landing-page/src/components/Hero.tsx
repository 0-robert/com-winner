import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const LOGOS = [
  'Salesforce', 'HubSpot', 'Pipedrive', 'Outreach', 'Apollo',
  'ZoomInfo', 'Clearbit', 'Clay', 'Lemlist', 'Instantly',
]

export default function Hero() {
  const heroRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ delay: 0.3 })

      tl.from('.hero-eyebrow', {
        opacity: 0,
        y: 10,
        duration: 0.5,
        ease: 'power2.out',
      })
        .from('.hero-line-1', {
          opacity: 0,
          y: 24,
          duration: 0.7,
          ease: 'power3.out',
        }, '-=0.2')
        .from('.hero-line-2', {
          opacity: 0,
          y: 24,
          duration: 0.7,
          ease: 'power3.out',
        }, '-=0.45')
        .from('.hero-sub', {
          opacity: 0,
          y: 16,
          duration: 0.6,
          ease: 'power2.out',
        }, '-=0.35')
        .from('.hero-cta', {
          opacity: 0,
          y: 12,
          stagger: 0.08,
          duration: 0.5,
          ease: 'power2.out',
        }, '-=0.3')
        .from('.hero-stats', {
          opacity: 0,
          y: 10,
          duration: 0.5,
          ease: 'power2.out',
        }, '-=0.2')

      // Parallax effects
      gsap.to('.hero-stats-container', {
        y: -47, // Increased from -40
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      })

      gsap.to('.hero-crm-mockup', {
        y: -94, // Increased from -80
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      })

    }, heroRef)

    return () => ctx.revert()
  }, [])

  return (
    <section ref={heroRef} className="relative pt-16 overflow-hidden bg-white">
      {/* Very subtle grid */}
      <div className="absolute inset-0 grid-bg pointer-events-none" />

      {/* Faint radial wash */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 70% 50% at 50% -10%, rgba(37,99,235,0.04) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-8 pt-24 pb-20 text-center">
        {/* Eyebrow */}
        <div
          className="hero-eyebrow inline-flex items-center gap-2 mb-8 text-xs font-medium text-[#6b7280] tracking-widest uppercase"
          style={{ fontFamily: 'var(--font-sans)' }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#059669]" />
          Agentic CRM — always accurate, automatically
        </div>

        {/* Headline — Playfair Display, mixed italic treatment */}
        <h1 className="mb-6" style={{ lineHeight: '1.08' }}>
          <span
            className="hero-line-1 block text-[#111827] font-bold"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(52px, 8vw, 96px)' }}
          >
            The CRM that
          </span>
          <span
            className="hero-line-2 block italic text-[#2563eb] font-bold"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(52px, 8vw, 96px)' }}
          >
            cleans itself.
          </span>
        </h1>

        {/* Subtitle */}
        <p
          className="hero-sub text-[#6b7280] text-lg leading-relaxed max-w-xl mx-auto mb-10"
          style={{ fontFamily: 'var(--font-sans)' }}
        >
          AI agents verify, enrich, and risk-score every contact 24/7.
          No manual cleanup. No stale data. Just a CRM you can trust.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-16">
          <a
            href="#how-it-works"
            className="hero-cta inline-flex items-center justify-center gap-2 bg-[#2563eb] hover:bg-[#1d4ed8] text-white font-medium px-7 py-3.5 rounded-lg text-sm transition-colors duration-150"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            See How It Works <span>→</span>
          </a>
          <a
            href="#demo"
            className="hero-cta inline-flex items-center justify-center gap-2 border border-[#e5e7eb] hover:border-[#d1d5db] text-[#374151] font-medium px-7 py-3.5 rounded-lg text-sm transition-colors duration-150 bg-white"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            View Live Demo <span>→</span>
          </a>
        </div>

        {/* Stats */}
        <div className="hero-stats hero-stats-container flex items-center justify-center gap-6 mt-12 relative z-20">
          {[
            { value: '94%', label: 'Contact accuracy' },
            { value: '30%', label: 'Stale data removed' },
            { value: '24/7', label: 'Background agents' },
          ].map((s, i, arr) => (
            <div key={s.label} className="flex items-center gap-6">
              <div className="px-8 py-5 flex flex-col items-center justify-center min-w-[200px] text-center">
                <div
                  className="text-3xl font-bold text-[#111827] mb-1.5"
                  style={{ fontFamily: 'var(--font-serif)' }}
                >
                  {s.value}
                </div>
                <div
                  className="text-[10px] text-[#2563eb] uppercase tracking-widest font-semibold"
                  style={{ fontFamily: 'var(--font-sans)' }}
                >
                  {s.label}
                </div>
              </div>
              {i < arr.length - 1 && <div className="w-px h-12 bg-[#e5e7eb]" />}
            </div>
          ))}
        </div>
      </div>

      {/* Product screenshot preview area */}
      <div className="relative max-w-5xl mx-auto px-8 hero-crm-mockup mt-10">
        {/* Gradient fade at edges */}
        <div
          className="absolute inset-y-0 left-0 w-32 z-10 pointer-events-none"
          style={{ background: 'linear-gradient(90deg, white, transparent)' }}
        />
        <div
          className="absolute inset-y-0 right-0 w-32 z-10 pointer-events-none"
          style={{ background: 'linear-gradient(-90deg, white, transparent)' }}
        />
        {/* Gradient bottom fade */}
        <div
          className="absolute bottom-0 left-0 right-0 h-24 z-10 pointer-events-none"
          style={{ background: 'linear-gradient(0deg, white, transparent)' }}
        />

        {/* CRM screenshot mockup */}
        <div
          className="rounded-xl overflow-hidden border border-[#e5e7eb]"
          style={{ boxShadow: '0 4px 6px -1px rgba(0,0,0,0.04), 0 20px 60px -10px rgba(0,0,0,0.08)' }}
        >
          {/* Window chrome */}
          <div className="bg-[#f9fafb] border-b border-[#e5e7eb] px-4 py-2.5 flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-[#fca5a5]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#fde68a]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#6ee7b7]" />
            <div className="flex-1 flex justify-center">
              <div className="bg-white border border-[#e5e7eb] rounded px-3 py-1 text-xs text-[#9ca3af] flex items-center gap-1">
                <span>🔒</span> app.prospectkeeper.com
              </div>
            </div>
          </div>

          {/* CRM content */}
          <div className="bg-white p-4">
            {/* Mini header */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold text-[#111827]" style={{ fontFamily: 'var(--font-sans)' }}>Manage Contacts</div>
                <div className="text-xs text-[#9ca3af] flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-[#2563eb]" /> Agentic Database
                </div>
              </div>
              <div className="flex gap-2">
                <button className="text-xs border border-[#e5e7eb] px-3 py-1.5 rounded text-[#6b7280]">Review Required</button>
                <button className="text-xs bg-[#2563eb] text-white px-3 py-1.5 rounded">+ Add Contact</button>
              </div>
            </div>

            {/* Table header */}
            <div className="grid border-b border-[#f3f4f6] pb-1.5 mb-1" style={{ gridTemplateColumns: '2fr 2fr 1fr 1.2fr 0.7fr' }}>
              {['CLIENT', 'ORG / ROLE', 'STATUS', 'FRESHNESS', 'RISK'].map((h) => (
                <div key={h} className="text-[9px] font-semibold text-[#9ca3af] tracking-widest px-2">{h}</div>
              ))}
            </div>

            {/* Rows */}
            {[
              { i: 'RL', name: 'Robby Linson', email: 'robbylinson@gmail.com', org: 'Trinity College Dublin', role: 'Student', s: 'UNKNOWN', sc: '#d97706', sf: '#fffbeb', fresh: 'NEVER', fc: '#9ca3af', risk: '—' },
              { i: 'AP', name: 'Alex Pivovarov', email: 'alexpivovarov156@gmail.com', org: 'Univ. of Liverpool', role: 'Student', s: 'REVIEW', sc: '#d97706', sf: '#fffbeb', fresh: 'FRESH', fc: '#059669', risk: '47' },
              { i: 'JD', name: 'John Doe', email: 'test@catch-all-domain.com', org: 'Fake School District', role: 'Director', s: 'UNKNOWN', sc: '#d97706', sf: '#fffbeb', fresh: 'NEVER', fc: '#9ca3af', risk: '—' },
              { i: 'SC', name: 'Sarah Chen', email: 'sarah.chen@techcorp.io', org: 'TechCorp Inc.', role: 'VP Sales', s: 'VERIFIED', sc: '#059669', sf: '#f0fdf4', fresh: 'FRESH', fc: '#059669', risk: '5' },
            ].map((row) => (
              <div key={row.email} className="grid py-2 border-b border-[#f9fafb] hover:bg-[#f9fafb] transition-colors" style={{ gridTemplateColumns: '2fr 2fr 1fr 1.2fr 0.7fr' }}>
                <div className="flex items-center gap-2 px-2">
                  <div className="w-6 h-6 rounded bg-[#f3f4f6] flex items-center justify-center flex-shrink-0">
                    <span className="text-[8px] font-bold text-[#6b7280]">{row.i}</span>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-[#111827]">{row.name}</div>
                    <div className="text-[9px] text-[#9ca3af]">{row.email}</div>
                  </div>
                </div>
                <div className="px-2 flex items-center">
                  <div>
                    <div className="text-xs text-[#374151]">{row.org}</div>
                    <div className="text-[9px] text-[#9ca3af]">{row.role}</div>
                  </div>
                </div>
                <div className="px-2 flex items-center">
                  <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded border" style={{ color: row.sc, background: row.sf, borderColor: `${row.sc}40` }}>{row.s}</span>
                </div>
                <div className="px-2 flex items-center">
                  <span className="text-[9px] font-semibold" style={{ color: row.fc }}>{row.fresh}</span>
                </div>
                <div className="px-2 flex items-center">
                  <span className="text-xs font-bold" style={{ color: row.risk === '—' ? '#9ca3af' : parseInt(row.risk) > 40 ? '#dc2626' : '#059669' }}>{row.risk}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Logo strip */}
      <div className="mt-16 border-t border-[#f3f4f6] py-8 overflow-hidden">
        <div className="text-center mb-4">
          <span className="text-xs text-[#9ca3af] uppercase tracking-widest font-medium" style={{ fontFamily: 'var(--font-sans)' }}>
            Designed to replace your current CRM stack
          </span>
        </div>
        <div className="relative overflow-hidden">
          <div className="marquee-track flex gap-16 whitespace-nowrap items-center">
            {[...LOGOS, ...LOGOS].map((logo, i) => (
              <span
                key={i}
                className="text-sm font-medium text-[#d1d5db] flex-shrink-0 tracking-wide"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {logo}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
