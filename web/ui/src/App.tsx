import { useCallback, useEffect, useRef, useState } from "react";
import { api, AiUsage, Contract, Project, Spec, Test } from "./api";
import AiUsageView from "./components/AiUsageView";
import ContractDetail from "./components/ContractDetail";
import ProjectForm from "./components/ProjectForm";
import ProjectList from "./components/ProjectList";
import SettingsPage from "./components/SettingsPage";
import SpecDetail from "./components/SpecDetail";
import SpecForm from "./components/SpecForm";
import StatusBar from "./components/StatusBar";
import TestDetail from "./components/TestDetail";
import { useTheme } from "./hooks/useTheme";

type Selection = { type: "spec" | "contract" | "test"; id: string } | null;

function idType(id: string): "spec" | "contract" | "test" | "adr" {
  const prefix = id.split("-")[0];
  if (prefix === "SPEC") return "spec";
  if (prefix === "CON")  return "contract";
  if (prefix === "TST")  return "test";
  return "adr";
}

export default function App() {
  const { theme, setTheme } = useTheme();
  const [projects, setProjects]   = useState<Project[]>([]);
  const [specs, setSpecs]         = useState<Spec[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [tests, setTests]         = useState<Test[]>([]);
  const [selected, setSelected]   = useState<Selection>(null);
  const [history, setHistory]     = useState<Selection[]>([]);
  const [showSpecForm, setShowSpecForm]         = useState(false);
  const [showProjectForm, setShowProjectForm]   = useState(false);
  const [showAiUsage, setShowAiUsage]           = useState(false);
  const [showSettings, setShowSettings]         = useState(false);
  const [aiUsage, setAiUsage]     = useState<AiUsage | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");

  const mainRef = useRef<HTMLElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [p, s, c, t] = await Promise.all([
        api.getProjects(), api.getSpecs(), api.getContracts(), api.getTests(),
      ]);
      setProjects(p);
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

  // Determine default project for new spec (from currently selected spec's project)
  const defaultProjectId = selectedSpecId
    ? (specs.find(s => s.id === selectedSpecId)?.project ?? "")
    : "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StatusBar
        onShowAiUsage={() => { api.aiUsage().then(setAiUsage); setShowAiUsage(v => !v); setShowSettings(false); }}
        onShowSettings={() => { setShowSettings(v => !v); setShowAiUsage(false); }}
      />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <aside style={{
          width: 300, minWidth: 240,
          borderRight: "1px solid var(--border)",
          display: "flex", flexDirection: "column", overflow: "hidden",
        }}>
          {/* Sidebar header */}
          <div style={{ padding: "10px 10px 8px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
              Projekte ({projects.length})
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <button onClick={() => { setShowProjectForm(v => !v); setShowSpecForm(false); }} style={{ padding: "3px 8px", fontSize: 11 }}>
                {showProjectForm ? "×" : "+ Projekt"}
              </button>
              <button onClick={() => { setShowSpecForm(v => !v); setShowProjectForm(false); }} style={{ padding: "3px 8px", fontSize: 11 }}>
                {showSpecForm ? "×" : "+ Spec"}
              </button>
            </div>
          </div>

          {/* Forms */}
          <div style={{ overflowY: "auto", flex: 1, padding: 8 }}>
            {showProjectForm && (
              <ProjectForm
                onCreated={() => { setShowProjectForm(false); refresh(); }}
                onCancel={() => setShowProjectForm(false)}
              />
            )}
            {showSpecForm && (
              <SpecForm
                projects={projects}
                defaultProjectId={defaultProjectId}
                onCreated={(id) => { setShowSpecForm(false); refresh().then(() => selectSpec(id)); }}
                onCancel={() => setShowSpecForm(false)}
              />
            )}

            {loading && <p style={{ color: "var(--muted)", padding: 8, fontSize: 13 }}>Laden…</p>}
            {error   && <p style={{ color: "var(--red)", padding: 8, fontSize: 13 }}>{error}</p>}
            {!loading && !error && (
              <ProjectList
                projects={projects}
                specs={specs}
                selected={selectedSpecId}
                onSelect={selectSpec}
              />
            )}
          </div>
        </aside>

        {/* Main */}
        <main ref={mainRef} style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 0 }}>
          {/* Breadcrumb */}
          {(selected || history.length > 0) && !showAiUsage && (
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

          {/* KI-Nutzungsübersicht */}
          {showAiUsage && aiUsage && (
            <AiUsageView usage={aiUsage} onClose={() => setShowAiUsage(false)} />
          )}

          {/* Einstellungen */}
          {showSettings && (
            <SettingsPage
              currentTheme={theme}
              onThemeChange={setTheme}
              onClose={() => setShowSettings(false)}
            />
          )}

          {/* Detail-Ansicht */}
          {!showAiUsage && !showSettings && !selected && <EmptyState onNewProject={() => setShowProjectForm(true)} onNewSpec={() => setShowSpecForm(true)} />}

          {!showAiUsage && !showSettings && selected?.type === "spec" && (
            <SpecDetail
              key={selected.id}
              specId={selected.id}
              contracts={contracts}
              tests={tests}
              onNavigate={navigate}
              onRefresh={refresh}
            />
          )}

          {!showAiUsage && !showSettings && selected?.type === "contract" && (
            <ContractDetail
              key={selected.id}
              contractId={selected.id}
              onNavigate={navigate}
            />
          )}

          {!showAiUsage && !showSettings && selected?.type === "test" && (
            <TestDetail
              key={selected.id}
              testId={selected.id}
              onNavigate={navigate}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function EmptyState({ onNewProject, onNewSpec }: { onNewProject: () => void; onNewSpec: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, color: "var(--muted)" }}>
      <div style={{ fontSize: 48 }}>📋</div>
      <p style={{ fontSize: 16 }}>Wähle eine Spec aus der Liste</p>
      <p style={{ fontSize: 13 }}>oder lege etwas Neues an.</p>
      <div style={{ display: "flex", gap: 12 }}>
        <button className="primary" onClick={onNewProject}>+ Neues Projekt</button>
        <button onClick={onNewSpec}>+ Neue Spec</button>
      </div>
    </div>
  );
}
