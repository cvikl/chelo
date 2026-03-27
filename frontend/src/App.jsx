import { useState } from "react";
import ArticleInput from "./components/ArticleInput";
import LocationInfo from "./components/LocationInfo";
import ClaimsList from "./components/ClaimsList";
import VerdictPanel from "./components/VerdictPanel";
import { fullAnalyze } from "./api";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  async function handleAnalyze(articleText) {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const result = await fullAnalyze(articleText);
      setAnalysis(result);
    } catch (err) {
      setError(err.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>AlpineCheck</h1>
        <p>AI-powered fact-checking for Alpine climate claims using satellite data</p>
      </header>

      <main className="app-main">
        <ArticleInput onAnalyze={handleAnalyze} loading={loading} />

        {error && <div className="error-banner">{error}</div>}

        {analysis && (
          <div className="results">
            <LocationInfo extraction={analysis.extraction} />
            <ClaimsList claims={analysis.extraction.claims} />
            <VerdictPanel
              verdicts={analysis.verdicts}
              satelliteData={analysis.satellite_data}
            />
          </div>
        )}
      </main>
    </div>
  );
}
