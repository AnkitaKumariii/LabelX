import { Link, useLocation } from 'react-router-dom'

const steps = [
  { path: '/profile', label: '01', title: 'Profile' },
  { path: '/analyze', label: '02', title: 'Analyze' },
  { path: '/results', label: '03', title: 'Results' },
]

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-50 glass border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/profile" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-blue to-brand-black flex items-center justify-center shadow-lg shadow-brand-brown/30 group-hover:shadow-brand-blue/40 transition-shadow">
            <span className="text-white font-bold text-sm">LX</span>
          </div>
          <span className="font-display font-bold text-lg tracking-tight">
            Label<span className="gradient-text">X</span>
          </span>
        </Link>

        {/* Step Indicator */}
        <nav className="hidden sm:flex items-center gap-1">
          {steps.map((step, i) => {
            const isActive = pathname === step.path
            const isPast = steps.findIndex(s => s.path === pathname) > i
            return (
              <Link
                key={step.path}
                to={step.path}
                id={`nav-step-${i + 1}`}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                  ${isActive
                    ? 'bg-brand-brown/10 text-brand-blue border border-brand-brown/20'
                    : isPast
                    ? 'text-slate-500 hover:text-slate-800'
                    : 'text-slate-400 hover:text-slate-600'
                  }`}
              >
                <span className={`w-5 h-5 rounded-full text-xs flex items-center justify-center font-bold
                  ${isActive ? 'bg-brand-blue text-slate-900' : isPast ? 'bg-slate-200 text-slate-700' : 'bg-slate-100 text-slate-400'}`}>
                  {isPast ? '✓' : step.label}
                </span>
                {step.title}
              </Link>
            )
          })}
        </nav>

        {/* Profile indicator */}
        <div className="flex items-center gap-2">
          {localStorage.getItem('labelx_google_id') && (
            <div className="flex items-center gap-2 px-3 py-1.5 glass rounded-full text-xs text-slate-500">
              <div className="w-2 h-2 rounded-full bg-brand-green animate-pulse-slow" />
              Profile Active
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
