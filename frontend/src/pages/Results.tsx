import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import HealthGauge from '../components/HealthGauge'
import IngredientBadge from '../components/IngredientBadge'
import SummaryCard from '../components/SummaryCard'

const FILTERS = ['all', 'harmful', 'caution', 'safe', 'unknown']

export default function Results() {
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [filter, setFilter] = useState('all')
  const [expanded, setExpanded] = useState({})
  const [sortBy, setSortBy] = useState('severity')

  useEffect(() => {
    const raw = sessionStorage.getItem('labelx_last_report')
    if (raw) {
      try { setReport(JSON.parse(raw)) }
      catch { navigate('/analyze') }
    } else {
      navigate('/analyze')
    }
  }, [])

  if (!report) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-slate-500">Loading results…</div>
    </div>
  )

  const summary = report.summary || {}
  const ingredients = report.ingredients || []
  const score = summary.health_score ?? 0

  const SEVERITY_ORDER = { harmful: 0, caution: 1, unknown: 2, safe: 3 }
  const sorted = [...ingredients].sort((a, b) =>
    sortBy === 'severity'
      ? (SEVERITY_ORDER[a.safety_rating] ?? 4) - (SEVERITY_ORDER[b.safety_rating] ?? 4)
      : a.name.localeCompare(b.name)
  )

  const filtered = filter === 'all' ? sorted : sorted.filter(i => i.safety_rating === filter)

  const toggleExpand = (name) => setExpanded(prev => ({ ...prev, [name]: !prev[name] }))

  const handleDownload = () => {
    const content = JSON.stringify(report, null, 2)
    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `labelx-report-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const scoreColor =
    score >= 70 ? 'text-brand-green' :
    score >= 50 ? 'text-brand-yellow' :
    score >= 30 ? 'text-orange-400' : 'text-brand-red'

  return (
    <div className="min-h-screen py-12 px-4 page-enter">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="section-label mb-2">Analysis Complete</div>
            <h1 className="font-display font-bold text-3xl sm:text-4xl">
              Safety <span className="gradient-text">Report</span>
            </h1>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button id="btn-new-analysis" onClick={() => navigate('/analyze')} className="btn-secondary">
              ← New Analysis
            </button>
            <button id="btn-download-report" onClick={handleDownload} className="btn-secondary">
              ⬇️ Download JSON
            </button>
          </div>
        </div>

        {/* Disclaimer */}
        {report.disclaimer && (
          <div className="glass rounded-xl p-4 border border-brand-yellow/30 bg-brand-yellow/5 flex items-start gap-3">
            <span className="text-xl shrink-0">⚠️</span>
            <p className="text-sm text-brand-yellow/80 leading-relaxed">{report.disclaimer}</p>
          </div>
        )}

        {/* Top Section: Score + Summary Cards */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Gauge */}
          <div className="glass rounded-2xl p-6 flex flex-col items-center justify-center lg:col-span-1">
            <HealthGauge score={score} animated />
            {report.expertise_level && (
              <div className="mt-4 px-3 py-1.5 glass rounded-full text-xs text-slate-500 border border-slate-200 capitalize">
                {report.expertise_level} mode
              </div>
            )}
          </div>

          {/* Stats grid */}
          <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-2 gap-4">
            <SummaryCard
              icon="🟢" title="Safe Ingredients"
              value={summary.safe_count ?? 0}
              color="green"
            />
            <SummaryCard
              icon="🟡" title="Caution Items"
              value={summary.caution_count ?? 0}
              color="yellow"
            />
            <SummaryCard
              icon="🔴" title="Harmful Items"
              value={summary.harmful_count ?? 0}
              color="red"
            />
            <SummaryCard
              icon="⚪" title="Unknown Items"
              value={summary.unknown_count ?? 0}
              color="white"
            />
          </div>
        </div>

        {/* Personalized Summary */}
        <div className="glass rounded-2xl p-6 space-y-4">
          <h2 className="font-display font-semibold text-lg flex items-center gap-2">
            <span>💡</span> Personalized Summary
          </h2>
          <p className="text-slate-600 leading-relaxed text-sm sm:text-base">
            {summary.personalized_summary || 'No summary available.'}
          </p>

          {/* Warning pills */}
          {summary.top_warnings?.length > 0 && (
            <div className="space-y-2">
              <p className="section-label">Top Warnings</p>
              <div className="flex flex-wrap gap-2">
                {summary.top_warnings.map((w, i) => (
                  <span key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg badge-caution text-xs border">
                    ⚠️ {w}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Allergen alerts */}
          {summary.allergen_alerts?.length > 0 && (
            <div className="space-y-2">
              <p className="section-label">Allergen Alerts</p>
              <div className="flex flex-wrap gap-2">
                {summary.allergen_alerts.map((a, i) => (
                  <span key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg badge-harmful text-xs border font-semibold">
                    🚨 {a}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Ingredients Section */}
        <div className="glass rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h2 className="font-display font-semibold text-lg">
              Ingredient Breakdown
              <span className="ml-2 text-sm font-normal text-slate-500">({ingredients.length} total)</span>
            </h2>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Sort:</span>
              <div className="glass rounded-lg p-0.5 flex">
                {['severity', 'name'].map(s => (
                  <button
                    key={s}
                    id={`btn-sort-${s}`}
                    onClick={() => setSortBy(s)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all
                      ${sortBy === s ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-600'}`}
                  >
                    {s === 'severity' ? '🚦 Severity' : '🔤 Name'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-2 flex-wrap">
            {FILTERS.map(f => {
              const count = f === 'all' ? ingredients.length :
                ingredients.filter(i => i.safety_rating === f).length
              const colorMap = {
                all: 'border-slate-300 text-slate-500 data-[active]:bg-slate-100 data-[active]:text-slate-900',
                safe: 'border-brand-green/30 text-brand-green data-[active]:bg-brand-green/15',
                caution: 'border-brand-yellow/30 text-brand-yellow data-[active]:bg-brand-yellow/15',
                harmful: 'border-brand-red/30 text-brand-red data-[active]:bg-brand-red/15',
                unknown: 'border-slate-200 text-slate-500 data-[active]:bg-slate-100',
              }
              return (
                <button
                  key={f}
                  id={`btn-filter-${f}`}
                  data-active={filter === f ? true : undefined}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border capitalize transition-all duration-200
                    ${colorMap[f]} ${filter === f ? 'opacity-100' : 'opacity-60 hover:opacity-80'}`}
                >
                  {f} ({count})
                </button>
              )
            })}
          </div>

          {/* Badge list */}
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {filtered.length === 0 ? (
              <div className="text-center py-10 text-slate-400">
                No {filter} ingredients found
              </div>
            ) : (
              filtered.map(ingredient => (
                <IngredientBadge
                  key={ingredient.name}
                  ingredient={ingredient}
                  expanded={!!expanded[ingredient.name]}
                  onClick={() => toggleExpand(ingredient.name)}
                />
              ))
            )}
          </div>
        </div>

        {/* Expand All */}
        <div className="flex justify-center gap-4">
          <button
            id="btn-expand-all"
            onClick={() => {
              const obj = {}
              ingredients.forEach(i => obj[i.name] = true)
              setExpanded(obj)
            }}
            className="btn-secondary text-sm"
          >
            Expand All
          </button>
          <button
            id="btn-collapse-all"
            onClick={() => setExpanded({})}
            className="btn-secondary text-sm"
          >
            Collapse All
          </button>
        </div>
      </div>
    </div>
  )
}
