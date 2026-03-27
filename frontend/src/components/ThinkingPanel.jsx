const STEP_ICONS = {
  brain_start: "🧠",
  brain_done: "🧠",
  geocoding: "📍",
  geocoding_done: "📍",
  agents_dispatch: "🛰️",
  agent_done: "✅",
  agent_error: "❌",
  comparing: "⚖️",
  done: "🏁",
};

const AGENT_LABELS = {
  snow_cover: "Snow Cover",
  glacier_extent: "Glacier Extent",
  temperature: "Temperature",
  precipitation: "Precipitation",
  vegetation: "Vegetation",
};

function StepItem({ step, isLatest }) {
  const icon = STEP_ICONS[step.step] || "⏳";

  return (
    <div className={`thinking-step ${isLatest ? "latest" : ""} step-${step.step}`}>
      <span className="step-icon">{icon}</span>
      <div className="step-content">
        <p className="step-message">{step.message}</p>
        <p className="step-detail">{step.detail}</p>

        {step.claims && (
          <div className="step-claims">
            {step.claims.map((c) => (
              <span key={c.id} className={`step-claim-tag severity-${c.severity}`}>
                {c.type.replace("_", " ")}: {c.text.slice(0, 60)}...
              </span>
            ))}
          </div>
        )}

        {step.agents && (
          <div className="step-agents">
            {step.agents.map((a) => (
              <span key={a} className="step-agent-tag">
                {AGENT_LABELS[a] || a}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ThinkingPanel({ steps }) {
  if (!steps || steps.length === 0) return null;

  // Count completed agents
  const agentsDone = steps.filter((s) => s.step === "agent_done").length;
  const agentsTotal = steps.find((s) => s.step === "agents_dispatch")?.agents?.length || 0;
  const isDone = steps.some((s) => s.step === "done");

  return (
    <div className="thinking-panel">
      <div className="thinking-header">
        <h2>
          {isDone ? "Analysis Complete" : "Analyzing..."}
        </h2>
        {agentsTotal > 0 && !isDone && (
          <span className="agent-progress">
            Agents: {agentsDone}/{agentsTotal}
          </span>
        )}
      </div>

      <div className="thinking-steps">
        {steps.map((step, i) => (
          <StepItem
            key={i}
            step={step}
            isLatest={i === steps.length - 1 && !isDone}
          />
        ))}
      </div>

      {!isDone && (
        <div className="thinking-loader">
          <div className="loader-dots">
            <span /><span /><span />
          </div>
        </div>
      )}
    </div>
  );
}
