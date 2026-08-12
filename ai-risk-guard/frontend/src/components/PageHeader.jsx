export default function PageHeader({ eyebrow, title, subtitle, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
      <div className="min-w-0">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1 className="k-title">{title}</h1>
        {subtitle && <p className="k-sub">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-3 shrink-0">{children}</div>}
    </div>
  )
}