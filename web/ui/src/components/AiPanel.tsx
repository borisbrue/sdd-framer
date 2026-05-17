import { useState } from "react";
import { api, AiUsageEntry } from "../api";
import MarkdownBody from "./MarkdownBody";

interface Props {
  specId: string;
  specContent: string;
  onApply?: (text: string) => void;
  onNavigate: (id: string) => void;
}

type Mode = "idle" | "improve" | "suggest";
type Provider = "claude" | "copilot";

const PROVIDER_LABEL: Record<Provider, string> = {
  claude:  "Claude (Anthropic)",
  copilot: "GitHub Copilot",
};

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  const cached = entry.cache_read_tokens > 0;
  const isCopilot = entry.provider === "copilot";
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {entry.input_tokens}↑ {entry.output_tokens}↓
      {cached && <span style={{ color: "var(--green)" }}> {entry.cache_read_tokens} cached</span>}
      {isCopilot
        ? <span style={{ color: "var(--muted)" }}> (Abo)</span>
        : <span> ${entry.cost_usd.toFixed(5)}</span>
      }
    </span>
  );
}

export default function AiPanel({ specId, specContent, onApply, onNavigate }: Props) {
  const [open, setOpen]         = useState(false);
  const [provider, setProvider] = useState<Provider>("claude");
  const [mode, setMode]         = useState<Mode>("idle");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState("");
  const [usage, setUsage]       = useState<AiUsageEntry | null>(null);
  const [error, setError]       = useState("");
  const [instructions, setInstructions] = useState("");

  async function run(op: Mode) {
    setLoading(true);
    setError("");
    setResult("");
    setUsage(null);
    try {
      let res;
      if (op === "improve") {
        const payload = { spec_id: specId, current_content: specContent, instructions };
        res = provider === "copilot"
          ? await api.copilotImproveSpec(payload)
          : await api.aiImproveSpec(payload);
      } else {
        const payload = { spec_id: specId, spec_content: specContent };
        res = provider === "copilot"
          ? await api.copilotSuggestContracts(payload)
          : await api.aiSuggestContracts(payload);
      }
      setResult(res.result);
      setUsage(res.usage);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{ fontSize: 12, padding: "4px 12px", color: "var(--accent)", borderColor: "var(--accent)" }}
      >
        ✦ KI-Assistent
      </button>
    );
  }

  const accentColor = provider === "copilot" ? "#4caf50" : "var(--accent)";

  return (
    <section className="card" style={{ borderColor: accentColor }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 12, color: accentColor, textTransform: "uppercase", letterSpacing: 1 }}>
          ✦ KI-Assistent
        </h3>
        <button onClick={() => setOpen(false)} style={{ fontSize: 12, padding: "2px 8px" }}>×</button>
      </div>

      {/* Provider selector */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12, background: "var(--bg)", borderRadius: 6, padding: 3 }}>
        {(["claude", "copilot"] as Provider[]).map(p => (
          <button
            key={p}
            onClick={() => { setProvider(p); setResult(""); setUsage(null); setError(""); }}
            style={{
              flex: 1,
              fontSize: 11,
              padding: "4px 8px",
              background: provider === p ? (p === "copilot" ? "#4caf50" : "var(--accent)") : "transparent",
              color: provider === p ? "#1e1e2e" : "var(--muted)",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {PROVIDER_LABEL[p]}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => setMode(mode === "improve" ? "idle" : "improve")}
          style={{ fontSize: 12, padding: "4px 12px", ...(mode === "improve" ? { background: accentColor, color: "#1e1e2e" } : {}) }}
        >
          Spec verbessern
        </button>
        <button
          onClick={() => { setMode("suggest"); run("suggest"); }}
          style={{ fontSize: 12, padding: "4px 12px", ...(mode === "suggest" ? { background: accentColor, color: "#1e1e2e" } : {}) }}
          disabled={loading}
        >
          Contracts vorschlagen
        </button>
      </div>

      {mode === "improve" && (
        <div style={{ marginBottom: 12 }}>
          <textarea
            value={instructions}
            onChange={e => setInstructions(e.target.value)}
            placeholder="Anweisungen, z.B. 'Füge Akzeptanzkriterien hinzu' oder 'Kürze den Text'"
            style={{ width: "100%", minHeight: 70, fontSize: 12, padding: 8, boxSizing: "border-box", background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, resize: "vertical" }}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button
              className="primary"
              onClick={() => run("improve")}
              disabled={loading || !instructions.trim()}
              style={{ fontSize: 12, padding: "4px 12px" }}
            >
              {loading ? "…" : "Ausführen"}
            </button>
          </div>
        </div>
      )}

      {loading && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          {provider === "copilot" ? "GitHub Copilot denkt nach…" : "Claude denkt nach…"}
        </p>
      )}
      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      {result && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>Ergebnis</span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {usage && <UsagePill entry={usage} />}
              {onApply && mode === "improve" && (
                <button
                  className="primary"
                  onClick={() => onApply(result)}
                  style={{ fontSize: 11, padding: "2px 10px" }}
                >
                  Übernehmen
                </button>
              )}
            </div>
          </div>
          <div style={{ background: "var(--bg)", borderRadius: 6, padding: 12, fontSize: 13 }}>
            <MarkdownBody markdown={result} onIdClick={onNavigate} />
          </div>
        </div>
      )}
    </section>
  );
}
