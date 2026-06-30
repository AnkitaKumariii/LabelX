import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProfile, updateProfile, getProfile } from '../services/api'

const HEALTH_CONDITIONS = [
  { id: 'diabetes',       label: 'Diabetes',           emoji: '🩸', desc: 'Flags hidden sugars & high GI ingredients' },
  { id: 'hypertension',   label: 'Hypertension / BP',  emoji: '❤️', desc: 'Flags sodium sources & BP-raising additives' },
  { id: 'celiac',         label: 'Celiac Disease',      emoji: '🌾', desc: 'Flags all gluten-containing ingredients' },
  { id: 'pku',            label: 'PKU',                 emoji: '⚗️',  desc: 'Strictly flags aspartame & phenylalanine' },
  { id: 'ibs',            label: 'IBS',                 emoji: '🫁', desc: 'Flags gut irritants & fermentable additives' },
  { id: 'gout',           label: 'Gout',                emoji: '🦵', desc: 'Flags purines and uric acid triggers' },
  { id: 'heart disease',  label: 'Heart Disease',       emoji: '💙', desc: 'Flags trans fats & cardiovascular risks' },
  { id: 'kidney disease', label: 'Kidney Disease',      emoji: '🫘', desc: 'Flags phosphorus, potassium, sodium excess' },
]

const ALLERGEN_PRESETS = ['Gluten', 'Dairy', 'Soy', 'Tree Nuts', 'Peanuts', 'Eggs', 'Fish', 'Shellfish', 'Sesame']

export default function ProfileSetup() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [form, setForm] = useState({
    name: '',
    expertise_level: 'beginner',
    health_conditions: [],
    allergies: [],
  })
  const [allergyInput, setAllergyInput] = useState('')

  // Load existing profile
  useEffect(() => {
    const savedId = localStorage.getItem('labelx_profile_id')
    if (savedId) {
      getProfile(savedId)
        .then(p => {
          setForm({
            name: p.name || '',
            expertise_level: p.expertise_level || 'beginner',
            health_conditions: p.health_conditions || [],
            allergies: p.allergies || [],
          })
        })
        .catch(() => {})
    }
  }, [])

  const toggleCondition = (id) => {
    setForm(f => ({
      ...f,
      health_conditions: f.health_conditions.includes(id)
        ? f.health_conditions.filter(c => c !== id)
        : [...f.health_conditions, id],
    }))
  }

  const addAllergen = (allergen) => {
    const trimmed = allergen.trim()
    if (!trimmed) return
    const lower = trimmed.toLowerCase()
    if (!form.allergies.includes(lower)) {
      setForm(f => ({ ...f, allergies: [...f.allergies, lower] }))
    }
    setAllergyInput('')
  }

  const removeAllergen = (allergen) => {
    setForm(f => ({ ...f, allergies: f.allergies.filter(a => a !== allergen) }))
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      const savedId = localStorage.getItem('labelx_profile_id')
      let profile
      if (savedId) {
        profile = await updateProfile(savedId, form)
      } else {
        profile = await createProfile(form)
      }
      localStorage.setItem('labelx_profile_id', profile.profile_id)
      navigate('/analyze')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen py-12 px-4 page-enter">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full text-sm text-brand-blue mb-6 border border-brand-blue/20">
            <span>✨</span> Set up your health profile
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl mb-4">
            Personalize Your <span className="gradient-text">Analysis</span>
          </h1>
          <p className="text-slate-500 text-lg max-w-md mx-auto">
            Your health profile helps our AI flag ingredients that specifically matter to you.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-4 mb-10">
          {[1, 2, 3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <button
                onClick={() => step > s && setStep(s)}
                className={`w-8 h-8 rounded-full text-sm font-bold flex items-center justify-center transition-all
                  ${step === s ? 'bg-brand-blue text-black scale-110' :
                    step > s ? 'bg-brand-green/30 text-brand-green border border-brand-green/40' :
                    'bg-slate-100 text-slate-400'}`}
              >
                {step > s ? '✓' : s}
              </button>
              {s < 3 && <div className={`w-12 h-0.5 rounded ${step > s ? 'bg-brand-blue/50' : 'bg-slate-100'}`} />}
            </div>
          ))}
        </div>

        {/* Step 1 — Name & Expertise */}
        {step === 1 && (
          <div className="glass rounded-2xl p-8 space-y-8 animate-slide-up">
            <div>
              <h2 className="font-display font-bold text-2xl mb-2">Basic Info</h2>
              <p className="text-slate-500 text-sm">Tell us who you are and your science background</p>
            </div>

            <div className="space-y-2">
              <label className="section-label">Your Name</label>
              <input
                id="input-name"
                type="text"
                placeholder="e.g. Priya, Alex…"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="input-field"
              />
            </div>

            <div className="space-y-3">
              <label className="section-label">Expertise Level</label>
              <div className="grid grid-cols-2 gap-4">
                {['beginner', 'expert'].map(level => (
                  <button
                    key={level}
                    id={`btn-expertise-${level}`}
                    onClick={() => setForm(f => ({ ...f, expertise_level: level }))}
                    className={`p-5 rounded-xl border text-left transition-all duration-200
                      ${form.expertise_level === level
                        ? 'border-brand-blue/60 bg-brand-blue/10 ring-1 ring-brand-blue/30'
                        : 'border-slate-200 glass hover:border-slate-300'}`}
                  >
                    <div className="text-2xl mb-2">{level === 'beginner' ? '🌱' : '🔬'}</div>
                    <div className="font-semibold capitalize">{level}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {level === 'beginner'
                        ? 'Plain language explanations'
                        : 'Technical details & E-numbers'}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <button
              id="btn-next-step1"
              onClick={() => setStep(2)}
              disabled={!form.name.trim()}
              className="btn-primary w-full"
            >
              Continue →
            </button>
          </div>
        )}

        {/* Step 2 — Health Conditions */}
        {step === 2 && (
          <div className="glass rounded-2xl p-8 space-y-8 animate-slide-up">
            <div>
              <h2 className="font-display font-bold text-2xl mb-2">Health Conditions</h2>
              <p className="text-slate-500 text-sm">Select any conditions — our AI will prioritize relevant warnings</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {HEALTH_CONDITIONS.map(cond => (
                <button
                  key={cond.id}
                  id={`btn-condition-${cond.id}`}
                  onClick={() => toggleCondition(cond.id)}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 group
                    ${form.health_conditions.includes(cond.id)
                      ? 'border-brand-brown/60 bg-brand-brown/10'
                      : 'border-slate-200 glass hover:border-slate-300'}`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl mt-0.5">{cond.emoji}</span>
                    <div className="min-w-0">
                      <div className="font-medium text-sm">{cond.label}</div>
                      <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{cond.desc}</div>
                    </div>
                    <div className={`shrink-0 ml-auto w-5 h-5 rounded-full border flex items-center justify-center
                      ${form.health_conditions.includes(cond.id)
                        ? 'bg-brand-brown border-brand-brown text-slate-900 text-xs'
                        : 'border-slate-300'}`}>
                      {form.health_conditions.includes(cond.id) && '✓'}
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="flex gap-4">
              <button id="btn-back-step2" onClick={() => setStep(1)} className="btn-secondary flex-1">← Back</button>
              <button id="btn-next-step2" onClick={() => setStep(3)} className="btn-primary flex-1">Continue →</button>
            </div>
          </div>
        )}

        {/* Step 3 — Allergies */}
        {step === 3 && (
          <div className="glass rounded-2xl p-8 space-y-8 animate-slide-up">
            <div>
              <h2 className="font-display font-bold text-2xl mb-2">Allergies</h2>
              <p className="text-slate-500 text-sm">Add any food allergies — these will always be flagged</p>
            </div>

            {/* Presets */}
            <div className="space-y-3">
              <label className="section-label">Common Allergens</label>
              <div className="flex flex-wrap gap-2">
                {ALLERGEN_PRESETS.map(a => (
                  <button
                    key={a}
                    id={`btn-allergen-preset-${a.toLowerCase()}`}
                    onClick={() => addAllergen(a)}
                    disabled={form.allergies.includes(a.toLowerCase())}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition-all
                      ${form.allergies.includes(a.toLowerCase())
                        ? 'border-brand-red/40 bg-brand-red/10 text-brand-red cursor-default'
                        : 'border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-900'}`}
                  >
                    {a} {form.allergies.includes(a.toLowerCase()) && '✓'}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom input */}
            <div className="space-y-2">
              <label className="section-label">Add Custom Allergen</label>
              <div className="flex gap-2">
                <input
                  id="input-allergen-custom"
                  type="text"
                  placeholder="e.g. Mustard, Lupin…"
                  value={allergyInput}
                  onChange={e => setAllergyInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addAllergen(allergyInput)}
                  className="input-field flex-1"
                />
                <button
                  id="btn-add-allergen"
                  onClick={() => addAllergen(allergyInput)}
                  className="btn-secondary px-4"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Active allergens */}
            {form.allergies.length > 0 && (
              <div className="space-y-2">
                <label className="section-label">Your Allergens</label>
                <div className="flex flex-wrap gap-2">
                  {form.allergies.map(a => (
                    <span key={a} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg badge-harmful text-sm font-medium border">
                      ⚠️ {a}
                      <button onClick={() => removeAllergen(a)} className="hover:text-slate-600 ml-1 text-xs">×</button>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 rounded-xl bg-brand-red/10 border border-brand-red/30 text-brand-red text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-4">
              <button id="btn-back-step3" onClick={() => setStep(2)} className="btn-secondary flex-1">← Back</button>
              <button
                id="btn-save-profile"
                onClick={handleSubmit}
                disabled={loading}
                className="btn-primary flex-1"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    Saving…
                  </span>
                ) : 'Save & Analyze →'}
              </button>
            </div>
          </div>
        )}

        {/* Profile summary at bottom */}
        {(form.health_conditions.length > 0 || form.allergies.length > 0) && (
          <div className="mt-6 glass rounded-xl p-4 flex flex-wrap gap-2">
            <span className="section-label self-center mr-1">Active:</span>
            {form.health_conditions.map(c => (
              <span key={c} className="px-2 py-1 rounded-lg bg-brand-brown/15 border border-brand-brown/25 text-xs text-amber-700 capitalize">{c}</span>
            ))}
            {form.allergies.map(a => (
              <span key={a} className="px-2 py-1 rounded-lg badge-harmful text-xs border capitalize">{a} allergy</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
