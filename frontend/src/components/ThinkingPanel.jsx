import { useState, useEffect } from "react";

export default function ThinkingPanel({ steps }) {
  const [displayStep, setDisplayStep] = useState(null);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    if (!locked && steps.length > 0) {
      const latestStep = steps[steps.length - 1];
      if (displayStep !== latestStep) {
        setDisplayStep(latestStep);
        setLocked(true);
        setTimeout(() => setLocked(false), 1000);
      }
    }
  }, [steps, locked, displayStep]);

  const current = displayStep || steps[0];

  const getProgress = (stepType) => {
    switch (stepType) {
      case "brain_start": return 15;
      case "brain_done": return 30;
      case "geocoding": return 40;
      case "geocoding_done": return 55;
      case "agents_dispatch": return 70;
      case "agent_done": return 85;
      case "agent_error": return 85;
      case "comparing": return 95;
      case "done": return 100;
      default: return 5;
    }
  };

  const progressPercent = current ? getProgress(current.step) : 0;

  return (
    <div className="thinking-panel">
      <div className="thinking-header">
        <h2>Analyzing Article...</h2>
      </div>

      <div className="progress-container">
        <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
        {current && <span className="progress-text">{progressPercent}%</span>}
      </div>

      <div className="status-text">
        {current ? (
          current.message
        ) : (
          <div className="loader-dots loader-right">
            <span /><span /><span />
          </div>
        )}
      </div>
    </div>
  );
}
