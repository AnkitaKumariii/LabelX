const RATING_CONFIG = {
  safe:    { label: 'Safe',    emoji: '', cls: 'badge-safe',    dot: 'bg-brand-green' },
  caution: { label: 'Caution', emoji: '', cls: 'badge-caution', dot: 'bg-brand-yellow' },
  harmful: { label: 'Harmful', emoji: '', cls: 'badge-harmful', dot: 'bg-brand-red' },
  other: { label: 'Other', emoji: '', cls: 'badge-other', dot: 'bg-slate-300' },
}

export default function IngredientBadge({ ingredient, expanded = false, onClick }) {
  const cfg = RATING_CONFIG[ingredient.safety_rating] || RATING_CONFIG.other

  return (
    <button
      id={`badge-${ingredient.name.toLowerCase().replace(/\s+/g, '-')}`}
      onClick={onClick}
      className={`
        group relative inline-flex flex-col text-left w-full rounded-xl border px-4 py-3
        transition-all duration-200 hover:scale-[1.01] hover:shadow-lg cursor-pointer
        ${cfg.cls} ${expanded ? 'ring-1 ring-slate-200' : ''}
      `}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base">{cfg.emoji}</span>
          <span className="font-semibold text-sm truncate">{ingredient.name}</span>
          {ingredient.banned_in?.length > 0 && (
            <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
               {ingredient.banned_in.length} countries
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${cfg.cls}`}>
            {cfg.label}
          </span>
          <svg className={`w-4 h-4 opacity-50 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
               fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-200 space-y-2 animate-fade-in">
          <p className="text-sm text-slate-600 leading-relaxed">{ingredient.explanation}</p>

          {ingredient.personalized_note && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-brand-blue/8 border border-brand-blue/20">
              <span className="text-brand-blue text-sm mt-0.5"></span>
              <p className="text-sm text-brand-blue/90 leading-relaxed">{ingredient.personalized_note}</p>
            </div>
          )}

          <div className="flex flex-wrap gap-3 text-xs text-slate-500">
            {ingredient.daily_limit_mg && (
              <span>Daily limit: <strong className="text-slate-600">{ingredient.daily_limit_mg} mg/kg bw</strong></span>
            )}
            {ingredient.source && (
              <span>Source: <strong className="text-slate-500 capitalize">{ingredient.source}</strong></span>
            )}
            {ingredient.banned_in?.length > 0 && (
              <span>Banned in: <strong className="text-brand-red/80">{ingredient.banned_in.join(', ')}</strong></span>
            )}
          </div>
        </div>
      )}
    </button>
  )
}
