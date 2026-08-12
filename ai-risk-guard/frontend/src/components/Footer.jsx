export default function Footer() {
  return (
    <footer className="mt-12 py-8" style={{ borderTop: '1px solid var(--line)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <svg
              viewBox="0 0 24 24"
              className="w-5 h-5"
              fill="none"
              stroke="var(--accent-bright)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
            <span className="font-mono text-xs tracking-[0.14em]" style={{ color: 'var(--text-muted)' }}>
              AI Risk Guard &copy; {new Date().getFullYear()}
            </span>
          </div>
          <div className="flex gap-6 font-mono text-[11px] uppercase tracking-[0.12em]" style={{ color: 'var(--text-muted)' }}>
            <span>Autonomous Security Platform</span>
            <span>Python &middot; Gemini &middot; React</span>
          </div>
        </div>
      </div>
    </footer>
  )
}