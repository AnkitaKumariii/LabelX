import { useEffect, useRef } from 'react'

function scoreToColor(score) {
  if (score >= 70) return { stroke: '#00ff88', text: '#00ff88', label: 'Excellent' }
  if (score >= 50) return { stroke: '#ffcc00', text: '#ffcc00', label: 'Moderate' }
  if (score >= 30) return { stroke: '#ff8c00', text: '#ff8c00', label: 'Poor' }
  return { stroke: '#ff3366', text: '#ff3366', label: 'Dangerous' }
}

export default function HealthGauge({ score = 0, animated = true }) {
  const circleRef = useRef(null)
  const scoreRef = useRef(null)

  const { stroke, text, label } = scoreToColor(score)
  const radius = 90
  const circumference = Math.PI * radius   // Semi-circle arc length
  const offset = circumference - (score / 100) * circumference

  useEffect(() => {
    if (!animated || !circleRef.current) return

    // Animate the dash offset
    const el = circleRef.current
    el.style.transition = 'none'
    el.style.strokeDashoffset = `${circumference}`

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.transition = 'stroke-dashoffset 1.8s cubic-bezier(0.4, 0, 0.2, 1)'
        el.style.strokeDashoffset = `${offset}`
      })
    })

    // Animate count-up number
    if (!scoreRef.current) return
    const start = performance.now()
    const duration = 1800
    const animate = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      scoreRef.current.textContent = Math.round(eased * score)
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
  }, [score, animated])

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: 220, height: 130 }}>
        <svg width="220" height="130" viewBox="0 0 220 130">
          {/* Track */}
          <path
            d="M 15 115 A 95 95 0 0 1 205 115"
            fill="none"
            stroke="rgba(0,0,0,0.06)"
            strokeWidth="14"
            strokeLinecap="round"
          />
          {/* Fill */}
          <path
            ref={circleRef}
            d="M 15 115 A 95 95 0 0 1 205 115"
            fill="none"
            stroke={stroke}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={animated ? circumference : offset}
            style={{ filter: `drop-shadow(0 0 8px ${stroke}80)` }}
          />
          {/* Tick marks */}
          {[0, 25, 50, 75, 100].map((tick) => {
            const angle = -180 + (tick / 100) * 180
            const rad = (angle * Math.PI) / 180
            const x1 = 110 + 85 * Math.cos(rad)
            const y1 = 115 + 85 * Math.sin(rad)
            const x2 = 110 + 74 * Math.cos(rad)
            const y2 = 115 + 74 * Math.sin(rad)
            return (
              <line key={tick} x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke="rgba(0,0,0,0.15)" strokeWidth="1.5" />
            )
          })}
        </svg>

        {/* Center score */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <span
            ref={scoreRef}
            className="font-display font-black text-5xl leading-none"
            style={{ color: text }}
          >
            {animated ? 0 : score}
          </span>
          <span className="text-slate-500 text-xs mt-1 font-medium">/ 100</span>
        </div>
      </div>

      {/* Label */}
      <div className="mt-2 flex flex-col items-center gap-1">
        <span className="font-bold text-lg" style={{ color: text }}>{label}</span>
        <span className="text-slate-500 text-xs">Health Score</span>
      </div>

      {/* Scale labels */}
      <div className="flex justify-between w-48 mt-1 text-[10px] text-slate-400 font-medium">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  )
}
