import { useState } from "react";
import { api, Contract, TestSuggestionItem, AiUsageEntry } from "../api";
import { useNotify } from "./NotificationContext";

/** Extracts sections 1, 2, and 4 (Kontext, Zielsetzung, FRs) — all the LLM needs for test suggestions. */
function extractSpecContext(body: string): string {
  const lines = body.split("\n");
  const result: string[] = [];
  let capture = false;
  for (const line of lines) {
    const m = line.match(/^## (\d+)\./);
    if (m) capture = ["1", "2", "4"].includes(m[1]);
    if (capture) result.push(line);
  }
  return result.length > 0 ? result.join("\n") : body.slice(0, 2000);
}

const TEST_LEVELS = ["unit", "integration", "contract", "acceptance", "performance", "property"];

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {entry.provider === "claude-cli"
        ? "claude-cli"
        : `${entry.input_tokens}↑ ${entry.output_tokens}↓ $${(entry.cost_usd ?? 0).toFixed(5)}`}
    </span>
  );
}

interface Props {
  specId: string;
  specContent: string;
  contracts: Contract[];
  onCreated: () => void;
}

export default function TestSuggestPanel({ specId, specContent, contracts, onCreated }: Props) {
  const notify = useNotify();
  const [phase, setPhase]             = useState<"idle" | "generating" | "preview">("idle");
  const [suggestions, setSuggestions] = useState<TestSuggestionItem[]>([]);
  const [usage, setUsage]             = useState<AiUsageEntry | null>(null);
  const [creating, setCreating]       = useState<Record<number, boolean>>({});
  const [createPhase, setCreatePhase] = useState<Record<number, string>>({});
  const [created, setCreated]         = useState<Record<number, boolean>>({});
  const [levels, setLevels]           = useState<Record<number, string>>({});
  const [contractIds, setContractIds] = useState<Record<number, string>>({});
  const [error, setError]             = useState("");

  if (contracts.length === 0) return null;

  const handleGenerate = async () => {
    setPhase("generating");
    setError("");
    try {
      const res = await api.aiSuggestTestsStructured({
        spec_id: specId,
        spec_content: extractSpecContext(specContent),
        contracts: contracts.map(c => ({ id: c.id, title: c.title, format: c.format })),
      });
      setSuggestions(res.suggestions);
      setLevels(Object.fromEntries(res.suggestions.map((s, i) => [i, s.level])));
      setContractIds(Object.fromEntries(res.suggestions.map((s, i) => [i, s.contract_id])));
      setUsage(res.usage);
      setCreated({});
      setPhase(res.suggestions.length > 0 ? "preview" : "idle");
      if (res.suggestions.length === 0) setError("Keine Vorschläge generiert.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Generieren.");
      setPhase("idle");
    }
  };

  const handleCreate = async (i: number, s: TestSuggestionItem) => {
    const contractId = contractIds[i] ?? s.contract_id;
    if (!contractId) { notify("Kein Contract ausgewählt", "error"); return; }
    setCreating(prev => ({ ...prev, [i]: true }));
    setCreatePhase(prev => ({ ...prev, [i]: "Anlegen…" }));
    try {
      const result = await api.createTest({ spec_id: specId, contract_id: contractId, level: levels[i] ?? s.level, title: s.title });
      setCreatePhase(prev => ({ ...prev, [i]: "Befülle mit KI…" }));
      const contract = contracts.find(c => c.id === contractId);
      await api.aiFillTest({
        test_id: result.id,
        spec_context: extractSpecContext(specContent),
        contract_description: contract ? `${contract.title} [${contract.format}]: ${s.description}` : s.description,
      });
      setCreated(prev => ({ ...prev, [i]: true }));
      notify(`✓ Test „${s.title}" angelegt und befüllt`, "success");
      onCreated();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Anlegen", "error");
    } finally {
      setCreating(prev => ({ ...prev, [i]: false }));
      setCreatePhase(prev => ({ ...prev, [i]: "" }));
    }
  };

  const handleClose = () => {
    setPhase("idle");
    setSuggestions([]);
    setCreated({});
    setError("");
  };

  if (phase === "idle") {
    return (
      <div style={{ marginTop: 10 }}>
        <button
          onClick={handleGenerate}
          style={{ fontSize: 11, padding: "3px 12px", color: "var(--accent)", borderColor: "var(--accent)" }}
        >
          ✦ KI-Vorschläge für Tests
        </button>
        {error && <p style={{ fontSize: 11, color: "var(--red)", marginTop: 6 }}>{error}</p>}
      </div>
    );
  }

  if (phase === "generating") {
    return (
      <div style={{ marginTop: 10, fontSize: 12, color: "var(--muted)" }}>
        ✦ Analysiert Spec und Contracts…
      </div>
    );
  }

  const allCreated = suggestions.length > 0 && suggestions.every((_, i) => created[i]);

  return (
    <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
          ✦ KI-Vorschläge ({suggestions.length})
        </span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {usage && <UsagePill entry={usage} />}
          <button onClick={handleGenerate} style={{ fontSize: 11, padding: "2px 8px" }}>↺ Neu</button>
          <button onClick={handleClose} style={{ fontSize: 11, padding: "2px 8px" }}>× Schließen</button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {suggestions.map((s, i) => (
          <div key={i} className="card" style={{
            display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12,
            opacity: created[i] ? 0.55 : 1,
            borderColor: created[i] ? "var(--green)" : "var(--border)",
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{s.title}</span>
                <select
                  value={levels[i] ?? s.level}
                  onChange={e => setLevels(prev => ({ ...prev, [i]: e.target.value }))}
                  disabled={created[i]}
                  style={{ fontSize: 11, padding: "1px 4px", background: "var(--surface)", color: "var(--muted)", border: "1px solid var(--border)", borderRadius: 4 }}
                >
                  {TEST_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
                <select
                  value={contractIds[i] ?? s.contract_id}
                  onChange={e => setContractIds(prev => ({ ...prev, [i]: e.target.value }))}
                  disabled={created[i]}
                  style={{ fontSize: 11, padding: "1px 4px", background: "var(--surface)", color: "var(--muted)", border: "1px solid var(--border)", borderRadius: 4 }}
                >
                  {contracts.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}
                </select>
              </div>
              <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>{s.description}</p>
            </div>
            <button
              onClick={() => handleCreate(i, s)}
              disabled={creating[i] || created[i]}
              className={created[i] ? undefined : "primary"}
              style={{
                fontSize: 11, padding: "3px 12px", flexShrink: 0, whiteSpace: "nowrap",
                color: created[i] ? "var(--green)" : undefined,
                borderColor: created[i] ? "var(--green)" : undefined,
              }}
            >
              {created[i] ? "✓ Angelegt" : creating[i] ? (createPhase[i] || "…") : "+ Anlegen"}
            </button>
          </div>
        ))}
      </div>

      {allCreated && (
        <p style={{ fontSize: 12, color: "var(--green)", marginTop: 10 }}>✓ Alle Tests angelegt.</p>
      )}
    </div>
  );
}
