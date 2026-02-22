import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const FEATURES = [
  {
    num: '01',
    title: 'Autonomous Agents',
    desc: 'AI agents run continuously in the background, verifying every contact against live data sources without any human input.',
    accent: '#2563eb',
  },
  {
    num: '02',
    title: 'Risk Scoring',
    desc: 'Each contact receives a 0–100 risk score based on email validity, company changes, role drift, and engagement signals.',
    accent: '#2563eb',
  },
  {
    num: '03',
    title: 'Freshness Tracking',
    desc: 'See exactly when each record was last verified. Never trust stale data — every field has a verification timestamp.',
    accent: '#2563eb',
  },
  {
    num: '04',
    title: 'Human Review Queue',
    desc: 'Flagged records surface automatically for human review. Your team only touches what the agents can\'t resolve alone.',
    accent: '#2563eb',
  },
  {
    num: '05',
    title: 'Email Enrichment',
    desc: 'Verify deliverability, catch catch-all domains, and enrich with LinkedIn and company data in a single pipeline.',
    accent: '#2563eb',
  },
  {
    num: '06',
    title: 'Real-time Sync',
    desc: 'Background sync keeps your database current as agents work. A live status panel shows exactly what\'s happening.',
    accent: '#2563eb',
  },
]

export default function Features() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.feat-header', {
        scrollTrigger: { trigger: '.feat-header', start: 'top 88%' },
        opacity: 0,
        y: 24,
        duration: 0.7,
        ease: 'power2.out',
      })

      ScrollTrigger.batch('.feat-card', {
        onEnter: (els) => gsap.fromTo(els,
          { opacity: 0, y: 30 },
          { opacity: 1, y: 0, duration: 0.6, stagger: 0.08, ease: 'power2.out' }
        ),
        start: 'top 90%',
      })
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section id="features" ref={sectionRef} className="py-28 px-8 bg-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="feat-header max-w-2xl mb-16">
          <div
            className="text-xs font-semibold text-[#2563eb] tracking-widest uppercase mb-4"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Why ProspectKeeper
          </div>
          <h2
            className="font-bold text-[#111827] mb-5"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(32px, 4vw, 52px)', lineHeight: '1.1' }}
          >
            Built for teams that{' '}
            <span className="italic">can't afford bad data.</span>
          </h2>
          <p
            className="text-[#6b7280] text-base leading-relaxed"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Every feature serves one principle: your CRM should be accurate, automatically, without anyone lifting a finger.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e5e7eb]">
          {FEATURES.map((f) => (
            <div
              key={f.num}
              className="feat-card bg-white p-8 group hover:bg-[#f9fafb] transition-colors duration-150"
            >
              <div
                className="text-xs font-semibold text-[#d1d5db] mb-5 tracking-widest"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {f.num}
              </div>
              <h3
                className="font-semibold text-[#111827] mb-3 text-lg group-hover:text-[#2563eb] transition-colors duration-150"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {f.title}
              </h3>
              <p
                className="text-sm text-[#6b7280] leading-relaxed"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {f.desc}
              </p>
              <div className="mt-6">
                <span
                  className="text-xs text-[#2563eb] font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-150"
                  style={{ fontFamily: 'var(--font-sans)' }}
                >
                  Learn more →
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
