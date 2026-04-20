import { useCallback, useState } from "react";
import { analyzeRepo } from "./api.js";
import IntroScreen from "./components/IntroScreen.jsx";
import Workspace from "./components/Workspace.jsx";

export default function App() {
  const [screen, setScreen] = useState("intro");
  const [githubUrl, setGithubUrl] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runAnalyze = useCallback(async (url, refresh = false) => {
    setError("");
    setLoading(true);
    try {
      const data = await analyzeRepo(url, refresh);
      setGithubUrl(url);
      setAnalysis(data);
      setScreen("workspace");
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  const back = useCallback(() => {
    setScreen("intro");
    setAnalysis(null);
    setError("");
  }, []);

  return (
    <>
      {screen === "intro" && (
        <IntroScreen
          onAnalyze={(url) => runAnalyze(url, false)}
          loading={loading}
          error={error}
        />
      )}
      {screen === "workspace" && analysis && (
        <Workspace
          githubUrl={githubUrl}
          analysis={analysis}
          onBack={back}
          onReanalyze={() => runAnalyze(githubUrl, true)}
          analyzeError={error}
          onDismissError={() => setError("")}
        />
      )}
    </>
  );
}
