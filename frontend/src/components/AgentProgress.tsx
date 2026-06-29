const AGENTS = [
  { key: 'supervisor', label: 'Supervisor',     icon: '🧠', desc: 'Orchestrating workflow' },
  { key: 'research',   label: 'Research Agent', icon: '🔬', desc: 'Searching ingredient database' },
  { key: 'analysis',   label: 'Analysis Agent', icon: '📊', desc: 'Generating personalized report' },
  { key: 'critic',     label: 'Critic Agent',   icon: '✅', desc: 'Validating report quality' },
]

export default function AgentProgress({ events = [], currentAgent = null, progress = 0 }) {
  const activeAgents = new Set(
    events.filter(e => e.type === 'agent_start').map(e =>
      e.agent?.toLowerCase().replace(' agent', '').replace('research', 'research')
            .replace('analysis', 'analysis').replace('critic', 'critic')
            .replace('supervisor', 'supervisor')
    )
  )

  const doneAgents = new Set(
    events.filter(e => e.type === 'research_done').length > 0 ? ['research'] : []
  )
  if (events.some(e => e.type === 'analysis_done')) doneAgents.add('analysis')
  if (events.some(e => e.type === 'critic_result' && e.passed)) doneAgents.add('critic')

  const latestMessage = events.length > 0 ? events[events.length - 1] : null

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Analysis Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-purple to-brand-cyan transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Agent steps */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {AGENTS.map((agent) => {
          const isActive = currentAgent?.toLowerCase().includes(agent.key)
          const isDone = doneAgents.has(agent.key)

          return (
            <div
              key={agent.key}
              id={`agent-step-${agent.key}`}
              className={`
                relative p-3 rounded-xl border transition-all duration-300
                ${isDone ? 'agent-step-done' : isActive ? 'agent-step-active' : 'agent-step-idle'}
              `}
            >
              {isActive && (
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-brand-cyan animate-pulse" />
              )}
              {isDone && (
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-brand-green" />
              )}
              <div className="text-xl mb-2">{agent.icon}</div>
              <div className="text-xs font-semibold text-slate-800">{agent.label}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{agent.desc}</div>
            </div>
          )
        })}
      </div>

      {/* Live event feed */}
      <div className="glass rounded-xl p-4 max-h-40 overflow-y-auto space-y-1.5 font-mono text-xs">
        {events.length === 0 ? (
          <p className="text-slate-400 text-center py-2">Waiting for events…</p>
        ) : (
          [...events].reverse().slice(0, 20).map((event, i) => (
            <div key={i} className={`flex items-start gap-2 ${i === 0 ? 'text-slate-800' : 'text-slate-500'}`}>
              <span className="shrink-0 mt-px">
                {event.type === 'error' ? '❌' :
                 event.type === 'complete' ? '🎉' :
                 event.type === 'critic_result' ? (event.passed ? '✅' : '⚠️') :
                 event.type === 'research_fallback' ? '🌐' : '›'}
              </span>
              <span className="leading-relaxed break-all">
                {event.message || event.type}
                {event.ingredient && ` — ${event.ingredient}`}
                {event.safety_rating && (
                  <span className={`ml-1 font-bold ${
                    event.safety_rating === 'safe' ? 'text-brand-green' :
                    event.safety_rating === 'harmful' ? 'text-brand-red' :
                    event.safety_rating === 'caution' ? 'text-brand-yellow' : 'text-slate-400'
                  }`}>({event.safety_rating})</span>
                )}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
