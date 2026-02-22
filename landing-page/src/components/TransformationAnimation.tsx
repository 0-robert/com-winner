import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const SCENE_DATA = [
  {
    label: '01',
    title: 'Your CRM Is Lying to You',
    desc: 'Stale entries, wrong titles, dead emails. Traditional CRMs rot silently while your team works from bad data.',
    accent: '#d97706',
  },
  {
    label: '02',
    title: 'Intelligent Agents Deploy',
    desc: 'ProspectKeeper sends autonomous AI agents to scan every contact, identify data drift, and flag bad entries.',
    accent: '#2563eb',
  },
  {
    label: '03',
    title: 'Multi-Tier Precision Repair',
    desc: 'Agents fire red-beam validation across LinkedIn, email APIs, and company data — simultaneously, in parallel.',
    accent: '#dc2626',
  },
  {
    label: '04',
    title: 'Clean, Verified, Trusted Data',
    desc: 'Every record is verified, freshness-stamped, and risk-scored. Your CRM is finally a source of truth.',
    accent: '#059669',
  },
]

const CRM_ROWS = [
  { initials: 'RL', name: 'Robby Linson', email: 'robbylinson@gmail.com', org: 'Trinity College Dublin', role: 'Student' },
  { initials: 'AP', name: 'Alex Pivovarov', email: 'alexpivovarov156@gmail.com', org: 'Univ. of Liverpool', role: 'Student' },
  { initials: 'JD', name: 'John Doe', email: 'test@catch-all-domain.com', org: 'Fake School District', role: 'Director' },
  { initials: 'SC', name: 'Sarah Chen', email: 'sarah.chen@techcorp.io', org: 'TechCorp Inc.', role: 'VP Sales' },
]

export default function TransformationAnimation() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const stickyRef = useRef<HTMLDivElement>(null)
  const [sceneIndex, setSceneIndex] = useState(0)

  // ── DEBUG: call window.__debugAgents() in the console after the full animation ──
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__debugAgents = () => {
      const ids = ['agent-1', 'agent-2', 'agent-3']
      console.group('🔍 AGENT OVERFLOW DEBUG')

      ids.forEach((id) => {
        const el = document.getElementById(id)
        if (!el) { console.warn(`#${id} not found`); return }
        const rect = el.getBoundingClientRect()
        const attr = el.getAttribute('transform')
        const cssTransform = getComputedStyle(el).transform
        console.group(`#${id}`)
        console.log('BoundingClientRect:', { x: rect.x, y: rect.y, width: rect.width, height: rect.height, left: rect.left, right: rect.right })
        console.log('SVG transform attr:', attr)
        console.log('Computed CSS transform:', cssTransform)
        console.groupEnd()
      })

      // Card / SVG bounds
      const svgEl = document.querySelector('[data-anim="svg"]')
      const cardEl = document.querySelector('[data-anim="card"]')
      console.log('SVG rect:', svgEl?.getBoundingClientRect())
      console.log('Card rect:', cardEl?.getBoundingClientRect())

      // Walk ancestors from SVG, log any non-visible overflow or filter
      console.group('Ancestors (overflow ≠ visible | has filter):')
      let el: Element | null = svgEl
      while (el && el !== document.documentElement) {
        const cs = getComputedStyle(el as Element)
        const ov = cs.overflow; const ox = cs.overflowX; const oy = cs.overflowY
        const filt = cs.filter
        const hasClip = ov !== 'visible' || ox !== 'visible' || oy !== 'visible'
        const hasFilt = filt && filt !== 'none'
        if (hasClip || hasFilt) {
          const r = (el as Element).getBoundingClientRect()
          console.log({
            tag: el.tagName,
            id: (el as HTMLElement).id || '(none)',
            class: (el as HTMLElement).className?.toString().slice(0, 80),
            overflow: `${ov} / ${ox} / ${oy}`,
            filter: filt,
            rect: { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width }
          })
        }
        el = el.parentElement
      }
      console.groupEnd()
      console.groupEnd()
    }
    console.log('🔍 Debug ready — call window.__debugAgents() after animation completes')
    return () => { delete (window as unknown as Record<string, unknown>).__debugAgents }
  }, [])
  // ── END DEBUG ──

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: sectionRef.current,
          pin: stickyRef.current,
          pinSpacing: true,
          start: 'top top',
          end: '+=3600',
          scrub: 1.5,
          onUpdate: (self) => {
            const p = self.progress
            const next = p < 0.25 ? 0 : p < 0.5 ? 1 : p < 0.75 ? 2 : 3
            setSceneIndex((prev) => (prev !== next ? next : prev))
          },
        },
      })

      // Scene 1 → 2: Rust dims, agents fly in
      tl
        .to('#rust-frame', { opacity: 0.4, duration: 2 }, 0)
        .to('#rust-squiggles', { opacity: 0.3, duration: 2 }, 0)
        // Explicit absolute SVG coords — fromTo overrides any SVG transform attr
        .fromTo('#agent-1', { x: -220, y: 250, opacity: 0 }, { x: -60, y: 250, opacity: 1, duration: 2.5, ease: 'power3.out' }, 1)
        .fromTo('#agent-2', { x: 1080, y:  60, opacity: 0 }, { x: 920, y: 140, opacity: 1, duration: 2.5, ease: 'power3.out' }, 1.5)
        .fromTo('#agent-3', { x: 1080, y: 410, opacity: 0 }, { x: 920, y: 330, opacity: 1, duration: 2.5, ease: 'power3.out' }, 2)
        .fromTo('.scan-highlight', { opacity: 0, scaleX: 0 }, { opacity: 0.35, scaleX: 1, stagger: 0.3, duration: 1, ease: 'power2.out' }, 2.5)

      // Scene 2 → 3: Laser beams
      tl
        .to('#rust-frame', { opacity: 0, duration: 1.5 }, 5)
        .to('#beams-group', { opacity: 1, duration: 0.3 }, 5)
        .fromTo('#beam-1', { attr: { x2: -60, y2: 250 } }, { attr: { x2: 522, y2: 178 }, duration: 1.2, ease: 'power2.out' }, 5)
        .fromTo('#beam-1-glow', { attr: { x2: -60, y2: 250 } }, { attr: { x2: 522, y2: 178 }, duration: 1.2, ease: 'power2.out' }, 5)
        .fromTo('#beam-2', { attr: { x2: 920, y2: 140 } }, { attr: { x2: 638, y2: 248 }, duration: 1.2, ease: 'power2.out' }, 5.6)
        .fromTo('#beam-2-glow', { attr: { x2: 920, y2: 140 } }, { attr: { x2: 638, y2: 248 }, duration: 1.2, ease: 'power2.out' }, 5.6)
        .fromTo('#beam-3', { attr: { x2: 920, y2: 330 } }, { attr: { x2: 522, y2: 318 }, duration: 1.2, ease: 'power2.out' }, 6.2)
        .fromTo('#beam-3-glow', { attr: { x2: 920, y2: 330 } }, { attr: { x2: 522, y2: 318 }, duration: 1.2, ease: 'power2.out' }, 6.2)
        .fromTo('.beam-particle', { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, stagger: 0.1, duration: 0.4, ease: 'back.out(2)' }, 6.5)

      // Scene 3 → 4: Clean up
      tl
        .to('#beams-group', { opacity: 0, duration: 1.5 }, 8.5)
        .to('.beam-particle', { opacity: 0, stagger: 0.05, duration: 0.5 }, 8.5)
        .to('#agent-1', { opacity: 0.15, scale: 0.85, duration: 1.5 }, 8.5)
        .to('#agent-2', { opacity: 0.15, scale: 0.85, duration: 1.5 }, 8.5)
        .to('#agent-3', { opacity: 0.15, scale: 0.85, duration: 1.5 }, 8.5)
        .to('#rust-squiggles', { opacity: 0, duration: 1 }, 8.5)
        .to('.scan-highlight', { opacity: 0, duration: 0.8 }, 8.5)
        .fromTo('#clean-frame', { opacity: 0 }, { opacity: 1, duration: 2, ease: 'power2.out' }, 9)
        .fromTo('.clean-row', { opacity: 0, y: 6 }, { opacity: 1, y: 0, stagger: 0.2, duration: 0.8, ease: 'power2.out' }, 9.5)
        .to('.corrupt-row', { opacity: 0, duration: 1 }, 9.5)
        .fromTo('.sparkle', { opacity: 0, scale: 0, rotation: -20 }, { opacity: 1, scale: 1, rotation: 0, stagger: 0.08, duration: 0.5, ease: 'back.out(2)' }, 10.5)
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  const scene = SCENE_DATA[sceneIndex]

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative bg-[#f9fafb]"
      style={{ overflowX: 'clip' }}
    >
      <div
        ref={stickyRef}
        className="h-screen flex flex-col items-center justify-center overflow-hidden"
      >
        {/* Section header */}
        <div className="text-center mb-8 px-6 max-w-2xl mx-auto">
          <div
            className="inline-flex items-center gap-2 mb-3 text-xs font-medium uppercase tracking-widest transition-colors duration-700"
            style={{ color: scene.accent, fontFamily: 'var(--font-sans)' }}
          >
            <span className="w-5 h-px" style={{ background: scene.accent }} />
            Step {scene.label}
            <span className="w-5 h-px" style={{ background: scene.accent }} />
          </div>
          <h2
            className="font-bold text-[#111827] mb-3 transition-all duration-700"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(28px, 4vw, 48px)', lineHeight: '1.12' }}
          >
            {scene.title}
          </h2>
          <p
            className="text-[#6b7280] text-sm leading-relaxed transition-all duration-700"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            {scene.desc}
          </p>
        </div>

        {/* Scene progress */}
        <div className="flex gap-1.5 mb-8">
          {SCENE_DATA.map((s, i) => (
            <div
              key={i}
              className="h-0.5 rounded-full transition-all duration-700"
              style={{
                width: i === sceneIndex ? '28px' : '10px',
                background: i === sceneIndex ? s.accent : '#d1d5db',
              }}
            />
          ))}
        </div>

        {/* Animation card — filter removed; drop-shadow would clip overflow:visible SVG children */}
        <div className="w-full max-w-4xl px-6">
          <div
            data-anim="card"
            className="rounded-xl border border-[#e5e7eb]"
            style={{ boxShadow: '0 8px 40px rgba(0,0,0,0.08)' }}
          >
            {/* Window chrome — light theme */}
            <div className="bg-[#f9fafb] px-4 py-2.5 flex items-center gap-2 border-b border-[#e5e7eb] rounded-t-xl">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#fca5a5]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#fde68a]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#6ee7b7]" />
              </div>
              <div className="flex-1 flex justify-center">
                <div className="bg-white border border-[#e5e7eb] rounded px-3 py-0.5 text-[10px] text-[#9ca3af] flex items-center gap-1">
                  🔒 app.prospectkeeper.com
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-[#059669] shadow-[0_0_4px_#059669]" />
                <span className="text-[9px] text-[#059669]" style={{ fontFamily: 'var(--font-sans)' }}>agents active</span>
              </div>
            </div>

            {/* SVG — overflow visible so agents animate outside the card */}
            <svg
              data-anim="svg"
              viewBox="0 0 860 380"
              xmlns="http://www.w3.org/2000/svg"
              className="w-full bg-white"
              style={{ overflow: 'visible', display: 'block', borderRadius: '0 0 12px 12px' }}
            >
              <defs>
                <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <linearGradient id="rust-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#92400e" />
                  <stop offset="100%" stopColor="#d97706" />
                </linearGradient>
              </defs>

              {/* Table background */}
              <rect x="80" y="20" width="700" height="340" rx="8" fill="white" stroke="#e5e7eb" strokeWidth="1" />

              {/* Rust frame (Scene 1) */}
              <g id="rust-frame">
                <rect x="80" y="20" width="700" height="340" rx="8" fill="none"
                  stroke="url(#rust-grad)" strokeWidth="2" strokeDasharray="10 5" />
                <path d="M80 100 L70 112 L67 126" stroke="#b45309" strokeWidth="1.5" fill="none" opacity="0.7" />
                <path d="M780 60 L792 75 L789 90" stroke="#b45309" strokeWidth="1.5" fill="none" opacity="0.7" />
                <path d="M80 290 L69 302 L71 318" stroke="#d97706" strokeWidth="1.5" fill="none" opacity="0.5" />
                <path d="M780 310 L792 324 L789 340" stroke="#d97706" strokeWidth="1.5" fill="none" opacity="0.5" />
              </g>

              {/* Clean frame (Scene 4) */}
              <g id="clean-frame" opacity="0">
                <rect x="80" y="20" width="700" height="340" rx="8" fill="none"
                  stroke="#2563eb" strokeWidth="1.5" filter="url(#glow-blue)" />
              </g>

              {/* Tab bar */}
              <rect x="80" y="20" width="700" height="44" rx="8" fill="#f3f4f6" />
              <rect x="80" y="48" width="700" height="16" fill="#f3f4f6" />
              <rect x="100" y="30" width="110" height="22" rx="4" fill="white" stroke="#bfdbfe" strokeWidth="1.5" />
              <text x="155" y="46" fill="#2563eb" fontSize="9.5" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">All Contacts</text>
              <text x="250" y="46" fill="#9ca3af" fontSize="9.5" textAnchor="middle" fontFamily="DM Sans,sans-serif">Review Required</text>
              <text x="340" y="46" fill="#9ca3af" fontSize="9.5" textAnchor="middle" fontFamily="DM Sans,sans-serif">Departed</text>
              <rect x="595" y="29" width="76" height="22" rx="4" fill="#dcfce7" />
              <text x="633" y="45" fill="#059669" fontSize="8.5" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">Email All</text>
              <rect x="680" y="29" width="88" height="22" rx="4" fill="#eff6ff" />
              <text x="724" y="45" fill="#2563eb" fontSize="8.5" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">Refresh</text>

              {/* Column headers */}
              <rect x="80" y="64" width="700" height="34" fill="#f9fafb" />
              <text x="145" y="86" fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif" fontWeight="600" letterSpacing="1.5">CLIENT</text>
              <text x="318" y="86" fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif" fontWeight="600" letterSpacing="1.5">ORG / ROLE</text>
              <text x="486" y="86" fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif" fontWeight="600" letterSpacing="1.5">STATUS</text>
              <text x="600" y="86" fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif" fontWeight="600" letterSpacing="1.5">FRESHNESS</text>
              <text x="748" y="86" fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif" fontWeight="600" letterSpacing="1.5">RISK</text>

              {/* Column dividers */}
              {[305, 470, 585, 700, 760].map((x) => (
                <line key={x} x1={x} y1="64" x2={x} y2="360" stroke="#e5e7eb" strokeWidth="1" />
              ))}

              {/* Row dividers */}
              {[148, 210, 272, 334].map((y) => (
                <line key={y} x1="80" x2="780" y1={y} y2={y} stroke="#f3f4f6" strokeWidth="1" />
              ))}

              {/* === CORRUPTED ROWS === */}
              {CRM_ROWS.map((row, i) => {
                const ry = 98 + i * 62
                const my = ry + 25
                return (
                  <g key={`c-${i}`} className="corrupt-row">
                    <rect x="94" y={ry + 5} width="28" height="28" rx="4" fill="#f3f4f6" />
                    <text x="108" y={ry + 24} fill="#6b7280" fontSize="8" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">{row.initials}</text>
                    {/* Wavy name lines */}
                    <path d={`M132 ${my - 8} Q140 ${my - 13} 148 ${my - 8} Q156 ${my - 3} 164 ${my - 8} Q172 ${my - 13} 180 ${my - 8} Q188 ${my - 3} 196 ${my - 8} Q204 ${my - 13} 212 ${my - 8}`} stroke="#d97706" strokeWidth="1.6" fill="none" />
                    <path d={`M132 ${my + 4} Q138 ${my + 1} 144 ${my + 4} Q150 ${my + 7} 156 ${my + 4} Q162 ${my + 1} 168 ${my + 4} Q174 ${my + 7} 180 ${my + 4}`} stroke="#92400e" strokeWidth="1" fill="none" opacity="0.6" />
                    {/* Wavy org lines */}
                    <path d={`M315 ${my - 8} Q323 ${my - 13} 331 ${my - 8} Q339 ${my - 3} 347 ${my - 8} Q355 ${my - 13} 363 ${my - 8} Q371 ${my - 3} 379 ${my - 8} Q387 ${my - 13} 395 ${my - 8}`} stroke="#d97706" strokeWidth="1.6" fill="none" />
                    <path d={`M315 ${my + 4} Q321 ${my + 1} 327 ${my + 4} Q333 ${my + 7} 339 ${my + 4} Q345 ${my + 1} 351 ${my + 4}`} stroke="#92400e" strokeWidth="1" fill="none" opacity="0.6" />
                    {/* Status badge */}
                    <rect x="486" y={my - 11} width="75" height="20" rx="4" fill="none" stroke="#dc2626" strokeWidth="1.2" strokeDasharray="3 2" />
                    <text x="524" y={my + 4} fill="#ef4444" fontSize="8" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">UNKNOWN</text>
                    {/* Freshness badge */}
                    <rect x="595" y={my - 11} width="78" height="20" rx="4" fill="#f9fafb" stroke="#92400e" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="609" cy={my - 1} r="2.5" fill="#d1d5db" />
                    <text x="640" y={my + 4} fill="#92400e" fontSize="8" textAnchor="middle" fontFamily="DM Sans,sans-serif">NEVER</text>
                    <text x="772" y={my + 4} fill="#ef4444" fontSize="14" textAnchor="middle" opacity="0.7">×</text>
                  </g>
                )
              })}

              {/* Rust squiggles */}
              <g id="rust-squiggles">
                {[123, 185, 247, 309].map((y, i) => (
                  <g key={i}>
                    <path d={`M132 ${y} Q136 ${y - 4} 140 ${y} Q144 ${y + 4} 148 ${y} Q152 ${y - 4} 156 ${y}`} stroke="#ef4444" strokeWidth="1.5" fill="none" opacity="0.8" />
                    <path d={`M315 ${y} Q319 ${y - 4} 323 ${y} Q327 ${y + 4} 331 ${y} Q335 ${y - 4} 339 ${y}`} stroke="#dc2626" strokeWidth="1.5" fill="none" opacity="0.7" />
                  </g>
                ))}
              </g>

              {/* Scan highlights */}
              <rect className="scan-highlight" x="86" y="98" width="120" height="50" rx="2" fill="#dbeafe" opacity="0" />
              <rect className="scan-highlight" x="476" y="98" width="90" height="50" rx="2" fill="#d1fae5" opacity="0" />
              <rect className="scan-highlight" x="585" y="160" width="90" height="50" rx="2" fill="#dbeafe" opacity="0" />
              <rect className="scan-highlight" x="305" y="222" width="150" height="50" rx="2" fill="#d1fae5" opacity="0" />

              {/* === CLEAN ROWS === */}
              {[
                { initials: 'RL', name: 'Robby Linson', email: 'robbylinson@gmail.com', org: 'Trinity College Dublin', role: 'Student', status: 'VERIFIED', sc: '#059669', sf: '#d1fae5', fresh: 'FRESH', fc: '#059669', risk: 12, rc: '#059669' },
                { initials: 'AP', name: 'Alex Pivovarov', email: 'alexpivovarov156@gmail.com', org: 'Univ. of Liverpool', role: 'Student', status: 'REVIEW', sc: '#d97706', sf: '#fef3c7', fresh: 'FRESH', fc: '#059669', risk: 47, rc: '#d97706' },
                { initials: 'JD', name: 'John Doe', email: 'test@catch-all-domain.com', org: 'Fake School District', role: 'Director', status: 'VERIFIED', sc: '#059669', sf: '#d1fae5', fresh: 'STALE', fc: '#dc2626', risk: 83, rc: '#dc2626' },
                { initials: 'SC', name: 'Sarah Chen', email: 'sarah.chen@techcorp.io', org: 'TechCorp Inc.', role: 'VP Sales', status: 'VERIFIED', sc: '#059669', sf: '#d1fae5', fresh: 'FRESH', fc: '#059669', risk: 5, rc: '#059669' },
              ].map((row, i) => {
                const ry = 98 + i * 62
                const my = ry + 25
                return (
                  <g key={`clean-${i}`} className="clean-row" opacity="0">
                    <rect x="94" y={ry + 5} width="28" height="28" rx="4" fill="#eff6ff" />
                    <text x="108" y={ry + 24} fill="#2563eb" fontSize="8" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600">{row.initials}</text>
                    <text x="132" y={my - 4} fill="#111827" fontSize="10" fontFamily="DM Sans,sans-serif" fontWeight="600">{row.name}</text>
                    <text x="132" y={my + 10} fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif">{row.email}</text>
                    <text x="315" y={my - 4} fill="#374151" fontSize="10" fontFamily="DM Sans,sans-serif" fontWeight="500">{row.org}</text>
                    <text x="315" y={my + 10} fill="#9ca3af" fontSize="8.5" fontFamily="DM Sans,sans-serif">{row.role}</text>
                    <rect x="486" y={my - 11} width="75" height="20" rx="4" fill={row.sf} />
                    <text x="524" y={my + 4} fill={row.sc} fontSize="8" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="700">{row.status}</text>
                    <circle cx="605" cy={my - 1} r="3" fill={row.fc} />
                    <text x="630" y={my + 4} fill={row.fc} fontSize="8" fontFamily="DM Sans,sans-serif" fontWeight="600">{row.fresh}</text>
                    <text x="772" y={my + 5} fill={row.rc} fontSize="11" textAnchor="middle" fontFamily="Playfair Display,serif" fontWeight="700">{row.risk}</text>
                  </g>
                )
              })}

              {/* === AGENTS — positioned outside table edges, overflow visible === */}
              <g id="agent-1" transform="translate(-60, 250)" opacity="0">
                <circle r="38" cx="0" cy="0" fill="none" stroke="#2563eb" strokeWidth="0.5" opacity="0.3" />
                <circle r="28" cx="0" cy="0" fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.5" />
                <circle r="18" cx="0" cy="0" fill="#2563eb" stroke="#3b82f6" strokeWidth="2" filter="url(#glow-blue)" />
                <circle cx="-4" cy="-2" r="3" fill="#bfdbfe" /><circle cx="4" cy="-2" r="3" fill="#bfdbfe" />
                <circle cx="-4" cy="-2" r="1" fill="#1e40af" /><circle cx="4" cy="-2" r="1" fill="#1e40af" />
                <path d="M-3 4 Q0 7 3 4" stroke="#bfdbfe" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                <text x="0" y="30" fill="#2563eb" fontSize="6" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600" opacity="0.8">A-1</text>
              </g>
              <g id="agent-2" transform="translate(920, 140)" opacity="0">
                <circle r="38" cx="0" cy="0" fill="none" stroke="#2563eb" strokeWidth="0.5" opacity="0.3" />
                <circle r="28" cx="0" cy="0" fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.5" />
                <circle r="18" cx="0" cy="0" fill="#2563eb" stroke="#3b82f6" strokeWidth="2" filter="url(#glow-blue)" />
                <circle cx="-4" cy="-2" r="3" fill="#bfdbfe" /><circle cx="4" cy="-2" r="3" fill="#bfdbfe" />
                <circle cx="-4" cy="-2" r="1" fill="#1e40af" /><circle cx="4" cy="-2" r="1" fill="#1e40af" />
                <path d="M-3 4 Q0 7 3 4" stroke="#bfdbfe" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                <text x="0" y="30" fill="#2563eb" fontSize="6" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600" opacity="0.8">A-2</text>
              </g>
              <g id="agent-3" transform="translate(920, 330)" opacity="0">
                <circle r="38" cx="0" cy="0" fill="none" stroke="#2563eb" strokeWidth="0.5" opacity="0.3" />
                <circle r="28" cx="0" cy="0" fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.5" />
                <circle r="18" cx="0" cy="0" fill="#2563eb" stroke="#3b82f6" strokeWidth="2" filter="url(#glow-blue)" />
                <circle cx="-4" cy="-2" r="3" fill="#bfdbfe" /><circle cx="4" cy="-2" r="3" fill="#bfdbfe" />
                <circle cx="-4" cy="-2" r="1" fill="#1e40af" /><circle cx="4" cy="-2" r="1" fill="#1e40af" />
                <path d="M-3 4 Q0 7 3 4" stroke="#bfdbfe" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                <text x="0" y="30" fill="#2563eb" fontSize="6" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontWeight="600" opacity="0.8">A-3</text>
              </g>

              {/* === LASER BEAMS === */}
              <g id="beams-group" opacity="0">
                <line id="beam-1-glow" x1="-60" y1="250" x2="-60" y2="250" stroke="#ef4444" strokeWidth="8" opacity="0.3" strokeLinecap="round" filter="url(#glow-red)" />
                <line id="beam-1" x1="-60" y1="250" x2="-60" y2="250" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" />
                <line id="beam-2-glow" x1="920" y1="140" x2="920" y2="140" stroke="#ef4444" strokeWidth="8" opacity="0.3" strokeLinecap="round" filter="url(#glow-red)" />
                <line id="beam-2" x1="920" y1="140" x2="920" y2="140" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" />
                <line id="beam-3-glow" x1="920" y1="330" x2="920" y2="330" stroke="#ef4444" strokeWidth="8" opacity="0.3" strokeLinecap="round" filter="url(#glow-red)" />
                <line id="beam-3" x1="920" y1="330" x2="920" y2="330" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" />
                {[{ cx: 200, cy: 210 }, { cx: 300, cy: 200 }, { cx: 400, cy: 190 }, { cx: 640, cy: 195 }, { cx: 720, cy: 185 }, { cx: 750, cy: 240 }, { cx: 790, cy: 325 }, { cx: 720, cy: 320 }, { cx: 640, cy: 316 }].map((p, i) => (
                  <circle key={i} className="beam-particle" cx={p.cx} cy={p.cy} r="3" fill="#ef4444" opacity="0" filter="url(#glow-red)" />
                ))}
              </g>

              {/* === SPARKLES === */}
              {[
                { x: 165, y: 110, s: 9, c: '#fde68a' }, { x: 270, y: 125, s: 6, c: '#60a5fa' },
                { x: 524, y: 106, s: 8, c: '#34d399' }, { x: 636, y: 108, s: 7, c: '#fde68a' },
                { x: 165, y: 172, s: 6, c: '#60a5fa' }, { x: 524, y: 296, s: 8, c: '#34d399' },
                { x: 636, y: 296, s: 6, c: '#fde68a' }, { x: 772, y: 110, s: 7, c: '#34d399' },
                { x: 772, y: 300, s: 6, c: '#fca5a5' },
              ].map((s, i) => (
                <g key={i} className="sparkle" transform={`translate(${s.x},${s.y})`} opacity="0">
                  <path d={`M0 ${-s.s} L${s.s * 0.2} ${-s.s * 0.2} L${s.s} 0 L${s.s * 0.2} ${s.s * 0.2} L0 ${s.s} L${-s.s * 0.2} ${s.s * 0.2} L${-s.s} 0 L${-s.s * 0.2} ${-s.s * 0.2}Z`} fill={s.c} />
                </g>
              ))}
            </svg>
          </div>
        </div>
      </div>
    </section>
  )
}
