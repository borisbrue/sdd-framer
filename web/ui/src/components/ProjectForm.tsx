import { useState } from "react";
import { api } from "../api";

interface Props {
  onCreated: (id: string) => void;
  onCancel: () => void;
}

export default function ProjectForm({ onCreated, onCancel }: Props) {
  const [name, setName]               = useState("");
  const [owner, setOwner]             = useState("");
  const [status, setStatus]           = useState("active");
  const [description, setDescription] = useState("");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.createProject({ name, owner, status, description });
      onCreated(res.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700 }}>Neues Projekt</h3>

      <div>
        <label>Name *</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="z.B. Checkout-Backend" autoFocus required />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label>Owner</label>
          <input value={owner} onChange={e => setOwner(e.target.value)} placeholder="Name oder Team" />
        </div>
        <div>
          <label>Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="planning">planning</option>
            <option value="active">active</option>
            <option value="archived">archived</option>
          </select>
        </div>
      </div>

      <div>
        <label>Beschreibung</label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Worum geht es in diesem Projekt?"
          style={{ width: "100%", minHeight: 60, fontSize: 13, padding: 8, boxSizing: "border-box", background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, resize: "vertical" }}
        />
      </div>

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancel}>Abbrechen</button>
        <button type="submit" className="primary" disabled={loading || !name.trim()}>
          {loading ? "Anlegen…" : "Projekt anlegen"}
        </button>
      </div>
    </form>
  );
}
