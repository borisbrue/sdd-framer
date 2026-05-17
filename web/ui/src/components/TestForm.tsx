import { useState } from "react";
import { api, Contract } from "../api";

const LEVELS = ["unit", "integration", "contract", "acceptance", "performance", "property"];

interface Props {
  specId: string;
  contracts: Contract[];
  onCreated: () => void;
  onCancel: () => void;
}

export default function TestForm({ specId, contracts, onCreated, onCancel }: Props) {
  const [contractId, setContractId] = useState(contracts[0]?.id ?? "");
  const [level, setLevel] = useState("contract");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.createTest({ spec_id: specId, contract_id: contractId, level, title });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700 }}>Neuer Test für {specId}</h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <div>
          <label>Contract *</label>
          <select value={contractId} onChange={(e) => setContractId(e.target.value)}>
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>{c.id} {c.title}</option>
            ))}
          </select>
        </div>
        <div>
          <label>Level *</label>
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            {LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
        </div>
        <div>
          <label>Titel (optional)</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z.B. login-happy-path" />
        </div>
      </div>

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancel}>Abbrechen</button>
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Anlegen…" : "Test anlegen"}
        </button>
      </div>
    </form>
  );
}
