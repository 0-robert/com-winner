import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export default function CTA() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.cta-content > *', {
        scrollTrigger: { trigger: sectionRef.current, start: 'top 80%' },
        opacity: 0,
        y: 28,
        stagger: 0.12,
        duration: 0.7,
        ease: 'power2.out',
      })
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section id="cta" ref={sectionRef} className="bg-[#111827] text-white">
      <div className="max-w-4xl mx-auto px-8 py-28 text-center">
        <div className="cta-content">
          {/* Eyebrow */}
          <div
            className="inline-flex items-center gap-2 mb-8 text-xs font-medium text-[#6b7280] uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#059669] shadow-[0_0_6px_#059669]" />
            Early access — limited spots available
          </div>

          {/* Headline */}
          <h2
            className="font-bold mb-5"
            style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(36px, 5vw, 72px)', lineHeight: '1.08' }}
          >
            Stop trusting{' '}
            <span className="italic text-[#60a5fa]">stale data.</span>
          </h2>

          {/* Subtitle */}
          <p
            className="text-[#9ca3af] text-lg max-w-xl mx-auto mb-10 leading-relaxed"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Book a 20-minute demo and watch ProspectKeeper clean your actual
            CRM data in real time. No pitch decks. Just live agents working.
          </p>

          {/* Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12">
            <a
              href="mailto:hello@prospectkeeper.com"
              className="inline-flex items-center justify-center gap-2 bg-white text-[#111827] font-semibold px-8 py-3.5 rounded-lg text-sm hover:bg-[#f9fafb] transition-colors"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              Book a Demo <span>→</span>
            </a>
            <a
              href="#demo"
              className="inline-flex items-center justify-center gap-2 border border-[#374151] text-white font-medium px-8 py-3.5 rounded-lg text-sm hover:border-[#4b5563] transition-colors"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              View Demo
            </a>
          </div>

          {/* Trust line */}
          <div
            className="flex flex-wrap justify-center gap-8 text-xs text-[#4b5563]"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            {['No credit card required', 'Works with your existing CRM', 'Setup in under 10 minutes'].map((t) => (
              <span key={t} className="flex items-center gap-1.5">
                <span className="w-3 h-px bg-[#374151]" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-[#1f2937]">
        <div className="max-w-6xl mx-auto px-8 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-white/10 flex items-center justify-center">
              <span className="text-white text-[10px] font-bold" style={{ fontFamily: 'var(--font-serif)' }}>PK</span>
            </div>
            <span className="text-[#4b5563] text-sm" style={{ fontFamily: 'var(--font-sans)' }}>ProspectKeeper</span>
          </div>
          <p className="text-[#374151] text-xs" style={{ fontFamily: 'var(--font-sans)' }}>
            © 2026 ProspectKeeper. All rights reserved.
          </p>
          <div className="flex gap-6">
            {['Privacy', 'Terms', 'Contact'].map((l) => (
              <a key={l} href="#" className="text-[#374151] hover:text-[#9ca3af] text-xs transition-colors" style={{ fontFamily: 'var(--font-sans)' }}>{l}</a>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
