import { Link, NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import ThemeToggle from './ThemeToggle'

const defaultAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2394a3b8'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E"

const publicLinks = [
  { to: '/docs', label: 'Getting Started' },
  { to: '/status', label: 'Status' },
]

const appLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/repositories', label: 'Repositories' },
  { to: '/scans', label: 'Pull Requests' },
  { to: '/findings', label: 'Findings' },
  { to: '/policy', label: 'Policy' },
  { to: '/metrics', label: 'Metrics' },
  { to: '/settings', label: 'Settings' },
  { to: '/docs', label: 'Docs' },
  { to: '/status', label: 'Status' },
]

export default function Navbar({ auth }) {
  const location = useLocation()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const stripRef = useRef(null)
  const activeRef = useRef(null)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const links = auth?.authenticated ? appLinks : publicLinks

  useEffect(() => {
    const strip = stripRef.current
    const active = activeRef.current
    if (!strip || !active) return
    const target = active.offsetLeft - (strip.clientWidth - active.clientWidth) / 2
    strip.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
  }, [location.pathname, links])

  const setActiveRef = (el, isActive) => {
    if (isActive) activeRef.current = el
  }

  return (
    <nav
      className="sticky top-0 z-50 transition-all duration-300"
      style={{
        backgroundColor: scrolled ? 'var(--nav-bg)' : 'transparent',
        borderBottom: scrolled ? '1px solid var(--line)' : '1px solid transparent',
        backdropFilter: scrolled ? 'blur(28px) saturate(140%)' : 'none',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="var(--accent-bright)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
            <span className="font-light tracking-[0.16em] text-base whitespace-nowrap">
              AI RISK <span style={{ color: 'var(--accent)' }}>GUARD</span>
            </span>
          </Link>

          {/* Scrollable nav strip — active tab always centered with a glow box */}
          <div
            ref={stripRef}
            className="hidden lg:flex flex-1 items-center gap-0.5 overflow-x-auto navbar-scroll mx-4 py-1 scroll-smooth font-mono uppercase tracking-[0.12em] text-[11px]"
          >
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                ref={(el) => setActiveRef(el, el?.getAttribute('aria-current') === 'page')}
                className="shrink-0 px-3 py-1.5 transition-all duration-200"
                style={({ isActive }) => ({
                  color: isActive ? 'var(--text-main)' : 'var(--text-muted)',
                  backgroundColor: isActive ? 'var(--highlight)' : 'transparent',
                  border: isActive ? '1px solid var(--line-strong)' : '1px solid transparent',
                })}
              >
                {l.label.toUpperCase()}
              </NavLink>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />

            {auth?.authenticated ? (
              <div className="flex items-center gap-2">
                <img
                  src={auth.user?.avatar_url || defaultAvatar}
                  alt={auth.user?.login}
                  className="w-9 h-9"
                  onError={(e) => { if (e.target.src !== defaultAvatar) e.target.src = defaultAvatar }}
                />
                <a
                  href="/auth/logout"
                  title="Logout"
                  className="hidden sm:flex items-center gap-2 px-3 py-2 font-mono text-[11px] tracking-[0.12em] uppercase transition-all hover:scale-105"
                  style={{ backgroundColor: 'var(--fill-ghost)', border: '1px solid var(--border)', color: 'var(--text-main)' }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                  Logout
                </a>
              </div>
            ) : (
              <Link
                to="/login"
                className="hidden md:flex items-center gap-2 px-4 py-2 font-mono text-xs uppercase tracking-[0.2em] transition-all hover:scale-105"
                style={{
                  background: 'var(--accent-gradient)',
                  border: '1px solid transparent',
                  color: '#fff',
                }}
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                Login
              </Link>
            )}

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden w-10 h-10 flex items-center justify-center"
              style={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }}
              aria-label="Toggle menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                {mobileOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="md:hidden overflow-hidden border-t"
          style={{ backgroundColor: 'var(--nav-bg)', borderColor: 'var(--border)', borderTop: '1px solid var(--line)' }}
        >
          <div className="px-4 py-3 space-y-1 font-mono text-[11px] uppercase tracking-[0.14em]">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className="block px-4 py-2.5 transition-all"
                style={({ isActive }) => ({
                  color: isActive ? 'var(--text-main)' : 'var(--text-muted)',
                  backgroundColor: isActive ? 'var(--highlight)' : 'transparent',
                  border: isActive ? '1px solid var(--line-strong)' : '1px solid transparent',
                })}
              >
                {l.label.toUpperCase()}
              </NavLink>
            ))}
            {auth?.authenticated ? (
              <a
                href="/auth/logout"
                className="flex items-center justify-center gap-2 px-4 py-2.5 transition-all"
                style={{ color: 'var(--text-main)', backgroundColor: 'var(--bg)' }}
              >
                Logout
              </a>
            ) : (
              <Link
                to="/login"
                className="flex items-center justify-center gap-2 px-4 py-2.5 transition-all"
                style={{ background: 'var(--accent-gradient)', color: '#fff' }}
              >
                Login with GitHub
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}