import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const STATS = [
  { value: 94, suffix: '%', label: 'Contact accuracy after first agent run', sub: 'Average across all accounts' },
  { value: 30, suffix: '%', label: 'Stale records eliminated automatically', sub: 'Within 48 hours of setup' },
  { value: 5, suffix: '×', label: 'Faster prospecting with clean data', sub: 'Based on rep feedback' },
  { value: 24, suffix: '/7', label: 'Background agents running', sub: 'No configuration required' },
]

export default function Stats() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.stats-head', {
        scrollTrigger: { trigger: '.stats-head', start: 'top 88%' },
        opacity: 0, y: 20, duration: 0.6, ease: 'power2.out',
      })

      document.querySelectorAll<HTMLElement>('.stat-val').forEach((el) => {
        const target = parseInt(el.getAttribute('data-value') || '0', 10)
        gsap.fromTo(
          el,
          { textContent: '0' },
          {
            scrollTrigger: { trigger: el, start: 'top 88%' },
            textContent: target,
            duration: 1.8,
            ease: 'power2.out',
            snap: { textContent: 1 },
          }
        )
      })

      gsap.from('.stat-item', {
        scrollTrigger: { trigger: sectionRef.current, start: 'top 82%' },
        opacity: 0, y: 24, stagger: 0.12, duration: 0.6, ease: 'power2.out',
      })
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} className="py-28 px-8 bg-white border-t border-[#f3f4f6]">
      <div className="max-w-6xl mx-auto">
        <div className="stats-head text-center mb-16">
          <div
            className="text-xs font-semibold text-[#9ca3af] tracking-widest uppercase mb-3"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            By the Numbers
          </div>
          <h2
            className="font-bold text-[#111827]"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(28px, 3.5vw, 44px)' }}
          >
            Results that speak for themselves.
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-0 md:divide-x md:divide-[#f3f4f6]">
          {STATS.map((s) => (
            <div key={s.label} className="stat-item text-center md:px-8">
              <div
                className="flex items-baseline justify-center gap-1 mb-2"
                style={{ fontFamily: 'var(--font-serif)' }}
              >
                <span
                  className="stat-val text-5xl font-bold text-[#111827]"
                  data-value={s.value}
                >
                  0
                </span>
                <span className="text-2xl font-bold text-[#2563eb]">{s.suffix}</span>
              </div>
              <p
                className="text-sm font-medium text-[#374151] mb-1 leading-snug"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {s.label}
              </p>
              <p
                className="text-xs text-[#9ca3af]"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                {s.sub}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
