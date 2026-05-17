import { useEffect, useState } from "react";
import { api } from "../api";

interface Props {
  specId: string;
  onCreated: () => void;
  onCancel: () => void;
}

export default function ContractForm({ specId, onCreated, onCancel }: Props) {
  const [formats, setFormats] = useState<string[]>([]);
  const [format, setFormat] = useState("openapi");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getFormats().then((f) => { setFormats(f); setFormat(f[0] ?? "openapi"); });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.createContract({ spec_id: specId, format, title });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700 }}>Neuer Contract für {specId}</h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label>Format *</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            {formats.map((f) => <option key={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label>Titel (optional)</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z.B. login-api" />
        </div>
      </div>

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancel}>Abbrechen</button>
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Anlegen…" : "Contract anlegen"}
        </button>
      </div>
    </form>
  );
}
