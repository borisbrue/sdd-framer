import { useState } from "react";
import { api } from "../api";

interface Props {
  onCreated: (id: string) => void;
  onCancel: () => void;
}

export default function SpecForm({ onCreated, onCancel }: Props) {
  const [title, setTitle]       = useState("");
  const [owner, setOwner]       = useState("");
  const [priority, setPriority] = useState("medium");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.createSpec({ title, owner, priority });
      onCreated(res.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700 }}>Neue Spec</h3>

      <div>
        <label>Titel *</label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="z.B. User Registrierung"
          autoFocus
          required
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label>Owner</label>
          <input value={owner} onChange={e => setOwner(e.target.value)} placeholder="Name oder Team" />
        </div>
        <div>
          <label>Priorität</label>
          <select value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </div>
      </div>

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancel}>Abbrechen</button>
        <button type="submit" className="primary" disabled={loading || !title.trim()}>
          {loading ? "Anlegen…" : "Spec anlegen"}
        </button>
      </div>
    </form>
  );
}
