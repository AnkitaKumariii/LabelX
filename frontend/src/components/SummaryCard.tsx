export default function SummaryCard({ title, value, color = 'cyan' }) {
  const colorMap = {
    cyan:   'text-brand-blue',
    green:  'text-emerald-600',
    yellow: 'text-amber-600',
    red:    'text-rose-600',
    purple: 'text-purple-600',
    white:  'text-slate-700',
  }

  const textColor = colorMap[color] || colorMap.cyan

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm flex flex-col justify-center transition-shadow hover:shadow-md">
      <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-500 mb-2">{title}</p>
      <p className={`font-display font-bold text-3xl ${textColor}`}>
        {value}
      </p>
    </div>
  )
}
