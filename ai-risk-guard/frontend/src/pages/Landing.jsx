import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

const MEDIA_VIDEO = '' // drop your cinematic *.mp4 here
const MEDIA_POSTER = '' // matching *.png poster

const navLinks = [
  { to: '/docs', label: 'How it works' },
  { to: '/docs', label: 'Features' },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/docs', label: 'Documentation' },
]

const menuLinks = [
  { to: '/docs', label: 'How it works' },
  { to: '/docs', label: 'Features' },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/docs', label: 'Documentation' },
]

function ShieldMark({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="var(--accent-bright)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

function GitHubMark() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
    </svg>
  )
}

export default function Landing() {
  const [menuOpen, setMenuOpen] = useState(false)
  const hamburgerRef = useRef(null)
  const menuRef = useRef(null)

  const closeMenu = () => setMenuOpen(false)

  useEffect(() => {
    if (menuOpen) {
      document.body.classList.add('hero-menu-open')
    }
    return () => document.body.classList.remove('hero-menu-open')
  }, [menuOpen])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        hamburgerRef.current?.focus()
        return
      }
      if (e.key === 'Tab' && menuOpen && menuRef.current) {
        const focusables = menuRef.current.querySelectorAll('a[href], button:not([disabled])')
        if (!focusables.length) return
        const first = focusables[0]
        const last = focusables[focusables.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // Auto-close once ≥901px
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 901px)')
    const onChange = () => {
      if (mq.matches) setMenuOpen(false)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return (
    <section className="hero" id="top">
      {/* Media layer */}
      <div className="hero__media" aria-hidden="true">
        {MEDIA_VIDEO ? (
          <video autoPlay muted loop playsInline preload="auto" poster={MEDIA_POSTER || undefined}>
            <source src={MEDIA_VIDEO} type="video/mp4" />
          </video>
        ) : MEDIA_POSTER ? (
          <div className="hero__poster" style={{ backgroundImage: `url(${MEDIA_POSTER})` }} />
        ) : (
          <div className="hero__poster hero__poster--placeholder" />
        )}
      </div>
      <div className="hero__scrim" aria-hidden="true" />

      {/* Row 1 — Navbar */}
      <nav className="hero__nav" aria-label="Site">
        <a className="hero__nav-logo" href="#top">
          <ShieldMark className="hero__logo-mark" />
          <span className="hero__logo-text">AI Risk Guard</span>
        </a>

        <div className="hero__nav-cluster">
          <div className="hero__nav-links">
            {navLinks.map((link) => (
              <Link key={link.label} to={link.to} className="hero__nav-link">
                {link.label}
              </Link>
            ))}
          </div>
          <button
            ref={hamburgerRef}
            type="button"
            className="hero__hamburger"
            aria-expanded={menuOpen}
            aria-controls="mobileMenu"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </nav>

      {/* Row 2 — Right access panel */}
      <div className="hero__body">
        <div className="hero__panel">
          <span className="hero__chip">[ Autonomous Security ]</span>

          <h1 className="hero__title">
            AI Risk <span className="hero__title-accent">Guard</span>
          </h1>

          <p className="hero__tagline">
            Automatic detection, validation, and patching on every pull request.
          </p>

          <div className="hero__form">
            <a href="/auth/login" className="hero__btn hero__btn--accent hero__btn-icon">
              <GitHubMark />
              Sign in with GitHub
            </a>
          </div>

          <a className="hero__referral" href="#invite">
            Need an invite?
          </a>
        </div>
      </div>

      {/* Row 3 — Legal footer */}
      <footer className="hero__footer">
        By using AI Risk Guard you accept our{' '}
        <a href="#privacy-notice">Privacy Notice</a>,{' '}
        <a href="#terms-of-service">Terms of Service</a>, and the GitHub App
        permission model.
      </footer>

      {/* Mobile menu overlay */}
      <div
        id="mobileMenu"
        ref={menuRef}
        className={`hero__menu ${menuOpen ? 'is-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Site menu"
        aria-hidden={!menuOpen}
        tabIndex={-1}
        onClick={(e) => {
          if (e.target === menuRef.current) setMenuOpen(false)
        }}
        {...(menuOpen ? {} : { inert: '' })}
      >
        {menuLinks.map((link, i) => (
          <Link
            key={link.label}
            to={link.to}
            className="hero__menu-link"
            style={{ '--stagger-d': `${0.18 + i * 0.07}s` }}
            onClick={closeMenu}
            tabIndex={menuOpen ? 0 : -1}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </section>
  )
}