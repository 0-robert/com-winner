import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'

export default function Navbar() {
  const navRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.nav-item', {
        opacity: 0,
        y: -12,
        stagger: 0.07,
        duration: 0.5,
        ease: 'power2.out',
        delay: 0.2,
      })
    }, navRef)

    const handleScroll = () => {
      if (!navRef.current) return
      navRef.current.style.background = 'white'
      navRef.current.style.borderBottomColor = window.scrollY > 40
        ? '#e5e7eb'
        : 'transparent'
    }
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      ctx.revert()
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  return (
    <nav
      ref={navRef}
      className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-transparent transition-colors duration-300"
    >
      <div className="max-w-7xl mx-auto px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="nav-item flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-[#111827] flex items-center justify-center">
            <span className="text-white font-bold text-xs" style={{ fontFamily: 'var(--font-serif)' }}>PK</span>
          </div>
          <span className="text-[#111827] font-semibold text-base tracking-tight" style={{ fontFamily: 'var(--font-sans)' }}>
            ProspectKeeper
          </span>
        </a>

        {/* Center links */}
        <div className="hidden md:flex items-center gap-8">
          {['How It Works', 'Features', 'Pricing'].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
              className="nav-item text-[#6b7280] hover:text-[#111827] transition-colors duration-150 text-sm font-medium"
              style={{ fontFamily: 'var(--font-sans)' }}
            >
              {item}
            </a>
          ))}
        </div>

        {/* Right CTAs */}
        <div className="flex items-center gap-3">
          <a
            href="#"
            className="nav-item hidden md:block text-[#6b7280] hover:text-[#111827] text-sm transition-colors"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Sign in
          </a>
          <a
            href="#cta"
            className="nav-item inline-flex items-center gap-1.5 border border-[#111827] text-[#111827] hover:bg-[#111827] hover:text-white text-sm font-medium px-4 py-2 rounded-lg transition-all duration-200"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            Book a Demo <span className="text-xs">→</span>
          </a>
        </div>
      </div>
    </nav>
  )
}
