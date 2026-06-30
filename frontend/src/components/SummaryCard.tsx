export default function SummaryCard({ icon, title, value, subtitle, color = 'cyan', size = 'normal' }) {
  const colorMap = {
    cyan:   { text: 'text-brand-blue',   bg: 'bg-brand-blue/10',   border: 'border-brand-blue/20',   glow: 'shadow-brand-blue/10' },
    green:  { text: 'text-brand-green',  bg: 'bg-brand-green/10',  border: 'border-brand-green/20',  glow: 'shadow-brand-green/10' },
    yellow: { text: 'text-brand-yellow', bg: 'bg-brand-yellow/10', border: 'border-brand-yellow/20', glow: 'shadow-brand-yellow/10' },
    red:    { text: 'text-brand-red',    bg: 'bg-brand-red/10',    border: 'border-brand-red/20',    glow: 'shadow-brand-red/10' },
    purple: { text: 'text-purple-600',   bg: 'bg-purple-500/10',   border: 'border-purple-500/20',   glow: 'shadow-purple-500/10' },
    white:  { text: 'text-slate-600',    bg: 'bg-slate-100',       border: 'border-slate-200',       glow: '' },
  }

  const c = colorMap[color] || colorMap.cyan

  return (
    <div className={`glass rounded-2xl p-5 border ${c.border} hover:shadow-lg ${c.glow} transition-all duration-300 hover:-translate-y-0.5`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="section-label mb-2">{title}</p>
          <p className={`font-display font-bold leading-none ${size === 'large' ? 'text-4xl' : 'text-3xl'} ${c.text}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-slate-500 text-xs mt-2 leading-relaxed">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className={`${c.bg} ${c.border} border rounded-xl p-3 shrink-0`}>
            <span className="text-xl">{icon}</span>
          </div>
        )}
      </div>
    </div>
  )
}
