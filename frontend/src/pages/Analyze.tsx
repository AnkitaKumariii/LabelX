import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import AgentProgress from '../components/AgentProgress'
import { streamAnalysis, streamImageAnalysis } from '../services/api'

const SAMPLE_INGREDIENTS = `Water, Sugar, High Fructose Corn Syrup, Citric Acid, Natural Flavors, Sodium Benzoate (Preservative), Red 40, Yellow 5, Blue 1, Caramel Color, Phosphoric Acid, Potassium Sorbate`

export default function Analyze() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const [text, setText] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [isDragging, setIsDragging] = useState(false)

  const [analyzing, setAnalyzing] = useState(false)
  const [events, setEvents] = useState([])
  const [currentAgent, setCurrentAgent] = useState(null)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)

  const profileId = localStorage.getItem('labelx_google_id')

  const addEvent = useCallback((event) => {
    setEvents(prev => [...prev.slice(-99), event])
    if (event.progress !== undefined) setProgress(event.progress)
    if (event.agent) setCurrentAgent(event.agent)
  }, [])

  const handleImageDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer?.files?.[0] || e.target?.files?.[0]
    if (!file || !file.type.startsWith('image/')) return
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
  }

  const handleAnalyze = async () => {
    if (!profileId) {
      setError('Please set up your health profile first.')
      return
    }

    setAnalyzing(true)
    setEvents([])
    setProgress(0)
    setCurrentAgent(null)
    setError(null)

    try {
      let stream
      if (imageFile) {
        stream = streamImageAnalysis(profileId, imageFile)
      } else {
        const ingredients = text
          .split(/[,\n;]/)
          .map(s => s.trim())
          .filter(Boolean)
        if (ingredients.length === 0) {
          setError('Please enter at least one ingredient or upload an image.')
          setAnalyzing(false)
          return
        }
        stream = streamAnalysis(profileId, ingredients, text)
      }

      for await (const event of stream) {
        addEvent(event)

        if (event.type === 'complete') {
          // Store report and navigate
          sessionStorage.setItem('labelx_last_report', JSON.stringify(event.report))
          sessionStorage.setItem('labelx_last_analysis_id', event.analysis_id || '')
          setProgress(100)
          setTimeout(() => navigate('/results'), 600)
          break
        }
        if (event.type === 'error') {
          setError(event.message || 'Analysis failed.')
          break
        }
        if (event.type === 'timeout') {
          setError('Analysis timed out. Please try again.')
          break
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to start analysis.')
      addEvent({ type: 'error', message: err.message })
    } finally {
      setAnalyzing(false)
    }
  }

  if (!profileId) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="glass rounded-2xl p-10 text-center max-w-md">
          <div className="text-5xl mb-4"></div>
          <h2 className="font-display font-bold text-2xl mb-3">Profile Required</h2>
          <p className="text-slate-500 mb-6">Set up your health profile first to get personalized analysis.</p>
          <button onClick={() => navigate('/profile')} className="btn-primary w-full">
            Set Up Profile →
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen py-12 px-4 page-enter">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full text-sm text-brand-brown/80 mb-6 border border-brand-brown/20">
            <span></span> Multi-agent AI analysis
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl mb-4">
            Analyze <span className="gradient-text">Ingredients</span>
          </h1>
          <p className="text-slate-500 text-lg">Paste ingredient text or upload a product photo</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Text Input Panel */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <h2 className="font-display font-semibold text-lg">
              Paste Ingredient List
            </h2>
            <div className="space-y-3">
              <textarea
                id="textarea-ingredients"
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Paste ingredient list here…
e.g. Water, Sugar, High Fructose Corn Syrup, Citric Acid, Natural Flavors, Sodium Benzoate…"
                rows={10}
                className="textarea-field"
                disabled={analyzing}
              />
              <button
                id="btn-use-sample"
                onClick={() => setText(SAMPLE_INGREDIENTS)}
                className="text-xs text-brand-blue/70 hover:text-brand-blue underline underline-offset-2 transition-colors"
                disabled={analyzing}
              >
                Use sample ingredients →
              </button>
            </div>
          </div>

          {/* Image Upload Panel */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <h2 className="font-display font-semibold text-lg">
              Upload Product Photo
            </h2>
            <div
              id="upload-zone"
              className={`upload-zone rounded-xl p-8 text-center cursor-pointer transition-all duration-200 h-[280px] flex flex-col justify-center
                ${isDragging ? 'drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleImageDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageDrop}
              />
              {imagePreview ? (
                <div className="space-y-3">
                  <img
                    src={imagePreview}
                    alt="Product"
                    className="max-h-48 mx-auto rounded-xl object-contain border border-slate-200"
                  />
                  <p className="text-sm text-slate-500 line-clamp-1">{imageFile?.name}</p>
                  <button
                    id="btn-remove-image"
                    onClick={e => { e.stopPropagation(); setImageFile(null); setImagePreview(null) }}
                    className="text-xs text-brand-red/70 hover:text-brand-red underline"
                  >
                    Remove image
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-5xl animate-float"></div>
                  <p className="text-slate-500 text-sm">Drag & drop or click to upload</p>
                  <p className="text-slate-400 text-xs">PNG, JPG, WEBP — max 10MB</p>
                  <p className="text-brand-blue/60 text-xs">OCR will extract ingredient text automatically</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Analyze Button */}
        <div className="text-center">
          <button
            id="btn-analyze"
            onClick={handleAnalyze}
            disabled={analyzing || (!text.trim() && !imageFile)}
            className="btn-primary px-12 py-4 text-lg"
          >
            {analyzing ? (
              <span className="flex items-center justify-center gap-3">
                <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Analyzing…
              </span>
            ) : (
              'Analyze Ingredients'
            )}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="glass rounded-xl p-4 border border-brand-red/30 bg-brand-red/5 text-brand-red text-sm text-center">
            {error}
          </div>
        )}

        {/* Live Agent Progress */}
        {analyzing && (
          <div className="glass rounded-2xl p-6 space-y-4 animate-fade-in">
            <h3 className="font-display font-semibold text-lg flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-blue animate-pulse" />
              Live Agent Progress
            </h3>
            <AgentProgress events={events} currentAgent={currentAgent} progress={progress} />
          </div>
        )}
      </div>
    </div>
  )
}
