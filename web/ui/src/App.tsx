import { useCallback, useEffect, useRef, useState } from "react";
import { api, AiUsage, Contract, PatternUsage, Spec, Test } from "./api";
import AiUsageView from "./components/AiUsageView";
import PatternsView from "./components/PatternsView";
import ContractDetail from "./components/ContractDetail";
import DevConsole from "./components/DevConsole";
import HoldoutDetail from "./components/HoldoutDetail";
import HubPanel from "./components/HubPanel";
import OrchestrateMonitorPage from "./components/OrchestrateMonitorPage";
import ServerInfoPanel from "./components/ServerInfoPanel";
import SettingsPage from "./components/SettingsPage";
import SpecDetail from "./components/SpecDetail";
import SpecForm from "./components/SpecForm";
import SpecList from "./components/SpecList";
import StatusBar from "./components/StatusBar";
import TestDetail from "./components/TestDetail";
import { useTheme } from "./hooks/useTheme";

type Selection = { type: "spec" | "contract" | "test" | "holdout"; id: string } | null;

function idType(id: string): "spec" | "contract" | "test" | "holdout" | "adr" {
  const prefix = id.split("-")[0];
  if (prefix === "SPEC") return "spec";
  if (prefix === "CON")  return "contract";
  if (prefix === "TST")  return "test";
  if (prefix === "HOL")  return "holdout";
  return "adr";
}

export default function App() {
  const { theme, setTheme } = useTheme();
  const [specs, setSpecs]         = useState<Spec[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [tests, setTests]         = useState<Test[]>([]);
  const [selected, setSelected]   = useState<Selection>(null);
  const [history, setHistory]     = useState<Selection[]>([]);
  const [showSpecForm, setShowSpecForm]     = useState(false);
  const [showAiUsage, setShowAiUsage]       = useState(false);
  const [showPatterns, setShowPatterns]     = useState(false);
  const [patterns, setPatterns]             = useState<PatternUsage[]>([]);
  const [showSettings, setShowSettings]     = useState(false);
  const [showServerInfo, setShowServerInfo] = useState(false);
  const [showConsole, setShowConsole]       = useState(false);
  const [showHub, setShowHub]               = useState(false);
  const [showDagMonitor, setShowDagMonitor] = useState(false);
  const [hubUrl, setHubUrl]                 = useState("");
  const [aiUsage, setAiUsage]     = useState<AiUsage | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");

  const mainRef = useRef<HTMLElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [s, c, t] = await Promise.all([
        api.getSpecs(), api.getContracts(), api.getTests(),
      ]);
      setSpecs(s);
      setContracts(c);
      setTests(t);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Verbindungsfehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    api.serverInfo().then(info => { if (info.hubUrl) setHubUrl(info.hubUrl); }).catch(() => {});
  }, []);

  function navigate(id: string) {
    const type = idType(id);
    if (type === "adr") return;

    const next: Selection = { type, id };
    setHistory(h => selected ? [...h, selected] : h);
    setSelected(next);
    setShowAiUsage(false);
    setShowSettings(false);
    mainRef.current?.scrollTo(0, 0);
  }

  function goBack() {
    const prev = history[history.length - 1] ?? null;
    setHistory(h => h.slice(0, -1));
    setSelected(prev);
  }

  function selectSpec(id: string) {
    setHistory([]);
    setSelected({ type: "spec", id });
    setShowAiUsage(false);
    setShowSettings(false);
    mainRef.current?.scrollTo(0, 0);
  }

  const selectedSpecId = selected?.type === "spec" ? selected.id : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StatusBar
        onShowAiUsage={() => { api.aiUsage().then(setAiUsage); setShowAiUsage(v => !v); setShowSettings(false); setShowServerInfo(false); setShowHub(false); setShowPatterns(false); }}
        onShowSettings={() => { setShowSettings(v => !v); setShowAiUsage(false); setShowServerInfo(false); setShowHub(false); setShowPatterns(false); }}
        onShowServerInfo={() => setShowServerInfo(v => !v)}
        onToggleConsole={() => setShowConsole(v => !v)}
        onShowHub={() => { setShowHub(v => !v); setShowAiUsage(false); setShowSettings(false); setShowDagMonitor(false); setShowPatterns(false); }}
        hubActive={showHub}
        onShowDagMonitor={() => { setShowDagMonitor(v => !v); setShowHub(false); setShowAiUsage(false); setShowSettings(false); setShowPatterns(false); }}
        dagMonitorActive={showDagMonitor}
        onShowPatterns={() => { api.patterns().then(setPatterns); setShowPatterns(v => !v); setShowAiUsage(false); setShowSettings(false); setShowHub(false); setShowDagMonitor(false); }}
        patternsActive={showPatterns}
      />
      {showConsole && <DevConsole onClose={() => setShowConsole(false)} />}

      {showServerInfo && <ServerInfoPanel onClose={() => setShowServerInfo(false)} />}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <aside style={{
          width: 300, minWidth: 240,
          borderRight: "1px solid var(--border)",
          display: "flex", flexDirection: "column", overflow: "hidden",
        }}>
          <div style={{ padding: "10px 10px 8px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
              Specs ({specs.length})
            </span>
            <button onClick={() => setShowSpecForm(v => !v)} style={{ padding: "3px 8px", fontSize: 11 }}>
              {showSpecForm ? "×" : "+ Spec"}
            </button>
          </div>

          <div style={{ overflowY: "auto", flex: 1, padding: 8, paddingBottom: showConsole ? 280 : 8 }}>
            {showSpecForm && (
              <SpecForm
                onCreated={(id) => { setShowSpecForm(false); refresh().then(() => selectSpec(id)); }}
                onCancel={() => setShowSpecForm(false)}
              />
            )}

            {loading && <p style={{ color: "var(--muted)", padding: 8, fontSize: 13 }}>Laden…</p>}
            {error   && <p style={{ color: "var(--red)", padding: 8, fontSize: 13 }}>{error}</p>}
            {!loading && !error && (
              <SpecList
                specs={specs}
                selected={selectedSpecId}
                onSelect={selectSpec}
              />
            )}
          </div>
        </aside>

        {/* Main */}
        <main ref={mainRef} style={{ flex: 1, overflowY: "auto", padding: 20, paddingBottom: showConsole ? 280 : 20, display: "flex", flexDirection: "column", gap: 0 }}>
          {(selected || history.length > 0) && !showAiUsage && !showPatterns && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 12, color: "var(--muted)" }}>
              {history.length > 0 && (
                <button onClick={goBack} style={{ padding: "3px 10px", fontSize: 12 }}>← Zurück</button>
              )}
              {history.map((h, i) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{ color: "var(--accent)", cursor: "pointer", fontFamily: "monospace" }}
                    onClick={() => {
                      setSelected(h);
                      setHistory(prev => prev.slice(0, i));
                    }}
                  >{h?.id}</span>
                  <span>›</span>
                </span>
              ))}
              <span style={{ fontFamily: "monospace", color: "var(--text)" }}>{selected?.id}</span>
            </div>
          )}

          {showAiUsage && aiUsage && (
            <AiUsageView usage={aiUsage} onClose={() => setShowAiUsage(false)} />
          )}

          {showPatterns && (
            <PatternsView patterns={patterns} onClose={() => setShowPatterns(false)} />
          )}

          {showSettings && (
            <SettingsPage
              currentTheme={theme}
              onThemeChange={setTheme}
              onClose={() => setShowSettings(false)}
            />
          )}

          {showHub && (
            <HubPanel hubUrl={hubUrl} />
          )}

          {showDagMonitor && (
            <OrchestrateMonitorPage onNavigate={navigate} />
          )}

          {!showAiUsage && !showPatterns && !showSettings && !showHub && !showDagMonitor && !selected && <EmptyState onNewSpec={() => setShowSpecForm(true)} />}

          {!showAiUsage && !showPatterns && !showSettings && !showHub && !showDagMonitor && selected?.type === "spec" && (
            <SpecDetail
              key={selected.id}
              specId={selected.id}
              contracts={contracts}
              tests={tests}
              onNavigate={navigate}
              onRefresh={refresh}
            />
          )}

          {!showAiUsage && !showPatterns && !showSettings && !showHub && !showDagMonitor && selected?.type === "contract" && (
            <ContractDetail
              key={selected.id}
              contractId={selected.id}
              onNavigate={navigate}
            />
          )}

          {!showAiUsage && !showPatterns && !showSettings && !showHub && !showDagMonitor && selected?.type === "test" && (
            <TestDetail
              key={selected.id}
              testId={selected.id}
              onNavigate={navigate}
            />
          )}

          {!showAiUsage && !showPatterns && !showSettings && !showHub && !showDagMonitor && selected?.type === "holdout" && (
            <HoldoutDetail
              key={selected.id}
              holdoutId={selected.id}
              onNavigate={navigate}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function EmptyState({ onNewSpec }: { onNewSpec: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, color: "var(--muted)" }}>
      <div style={{ fontSize: 48 }}>📋</div>
      <p style={{ fontSize: 16 }}>Wähle eine Spec aus der Liste</p>
      <p style={{ fontSize: 13 }}>oder lege eine neue an.</p>
      <button className="primary" onClick={onNewSpec}>+ Neue Spec</button>
    </div>
  );
}
