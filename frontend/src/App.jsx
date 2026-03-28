import { useState } from "react";
import ArticleInput from "./components/ArticleInput";
import LocationInfo from "./components/LocationInfo";
import AnnotatedArticle from "./components/AnnotatedArticle";
import VerdictPanel from "./components/VerdictPanel";
import ThinkingPanel from "./components/ThinkingPanel";
import FactCheckPopup from "./components/FactCheckPopup";
import { analyzeWithStream } from "./api";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [articleText, setArticleText] = useState("");
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [activeVerdict, setActiveVerdict] = useState(null);

  async function handleAnalyze(text) {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setActiveVerdict(null);
    setArticleText(text);
    setThinkingSteps([]);

    try {
      await analyzeWithStream(
        text,
        (step) => {
          setThinkingSteps((prev) => [...prev, step]);
        },
        (result) => {
          setAnalysis(result);
          setLoading(false);
        },
        (errMsg) => {
          setError(errMsg);
          setLoading(false);
        }
      );
    } catch (err) {
      setError(err.message || "Analysis failed");
      setLoading(false);
    }
  }

  function handleReset() {
    setAnalysis(null);
    setThinkingSteps([]);
    setError(null);
    setActiveVerdict(null);
  }

  return (
    <div className={`app ${activeVerdict ? "has-sidebar" : ""}`}>
      <div className="main-column">
        <header className="app-header">
          <h1>AlpineCheck</h1>
          <p>AI-powered fact-checking for Alpine climate claims using satellite data</p>
        </header>

        <main className="app-main">
          {!loading && !analysis ? (
            <>
              <ArticleInput onAnalyze={handleAnalyze} loading={loading} />
              {error && <div className="error-banner">{error}</div>}
            </>
          ) : (
            <div className="results">
              {!analysis && <ThinkingPanel steps={thinkingSteps} />}

              {error && <div className="error-banner">{error}</div>}

              {analysis && (
                <>
                  <LocationInfo extraction={analysis.extraction} />
                  <AnnotatedArticle
                    articleText={articleText}
                    verdicts={analysis.verdicts}
                    activeVerdict={activeVerdict}
                    onVerdictClick={setActiveVerdict}
                  />
                  <VerdictPanel
                    verdicts={analysis.verdicts}
                    satelliteData={analysis.satellite_data}
                  />

                  <div style={{ marginTop: "2rem", textAlign: "center" }}>
                    <button className="btn-back" onClick={handleReset}>
                      &larr; Analyze another article
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </main>
      </div>

      {activeVerdict && (
        <aside className="sidebar-column">
          <FactCheckPopup
            verdict={activeVerdict}
            onClose={() => setActiveVerdict(null)}
          />
        </aside>
      )}
    </div>
  );
}
