import { useEffect, useRef, useState } from "react";

interface Task {
  id: string;
  title: string;
  description: string;
  type: string;
  status: string;
  complexity: string;
  estimated_tokens: number;
  actual_tokens: number | null;
  llm_id: string | null;
  parallel_group: string | null;
  dependencies: string[];
  test_ids: string[];
  error_context: string[];
}

interface TasksResponse {
  spec_id: string;
  run_id: string | null;
  tasks: Task[];
}

const COLUMNS = [
  { key: "pending", label: "Pending" },
  { key: "assigned", label: "Assigned" },
  { key: "running", label: "Running" },
  { key: "review", label: "Review" },
  { key: "passed", label: "Passed" },
  { key: "failed", label: "Failed" },
  { key: "committed", label: "Committed" },
  { key: "blocked", label: "Blocked" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--muted)",
  assigned: "#6c8ebf",
  running: "#f0a500",
  review: "#9b59b6",
  passed: "#27ae60",
  failed: "#e74c3c",
  committed: "#2ecc71",
  blocked: "#7f8c8d",
  retrying: "#e67e22",
};

function TaskCard({ task }: { task: Task }) {
  const color = STATUS_COLORS[task.status] || "var(--muted)";
  return (
    <div
      style={{
        background: "var(--surface)",
        border: `1px solid ${color}`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 6,
        padding: "8px 10px",
        fontSize: 12,
        cursor: "default",
      }}
      aria-label={`Task: ${task.title}, Status: ${task.status}`}
    >
      <div style={{ fontWeight: 600, marginBottom: 4, wordBreak: "break-word" }}>
        {task.title}
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: "var(--muted)", fontSize: 11 }}>{task.type}</span>
        {task.parallel_group && (
          <span
            title={`Parallel-Gruppe: ${task.parallel_group}`}
            style={{
              background: "#3498db22",
              color: "#3498db",
              borderRadius: 3,
              padding: "1px 5px",
              fontSize: 10,
            }}
          >
            ⋮⋮ {task.parallel_group}
          </span>
        )}
        {task.dependencies.length > 0 && (
          <span
            title={`Abhängig von: ${task.dependencies.join(", ")}`}
            style={{ color: "var(--muted)", fontSize: 11 }}
          >
            🔗 {task.dependencies.length}
          </span>
        )}
      </div>
      <div style={{ marginTop: 6, fontSize: 11 }}>
        {task.actual_tokens != null ? (
          <>
            <span style={{ textDecoration: "line-through", color: "var(--muted)" }}>
              ~{task.estimated_tokens.toLocaleString()}
            </span>{" "}
            <span style={{ color: "#3498db", fontWeight: 600 }}>
              {task.actual_tokens.toLocaleString()} tok
            </span>
          </>
        ) : (
          <span style={{ color: "var(--muted)" }}>~{task.estimated_tokens.toLocaleString()} tok</span>
        )}
      </div>
      {task.error_context.length > 0 && (
        <div
          style={{
            marginTop: 4,
            padding: "3px 6px",
            background: "#e74c3c22",
            borderRadius: 3,
            fontSize: 10,
            color: "#e74c3c",
            wordBreak: "break-word",
          }}
        >
          {task.error_context[task.error_context.length - 1]}
        </div>
      )}
    </div>
  );
}

export default function TaskKanbanBoard({ specId }: { specId: string }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasks = () => {
    fetch(`/api/specs/${specId}/tasks`)
      .then((r) => r.json())
      .then((d: TasksResponse) => {
        setTasks(d.tasks);
        setRunId(d.run_id);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(fetchTasks, 5000);
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const connectSSE = () => {
    if (eventSourceRef.current) return;
    const es = new EventSource(`/api/specs/${specId}/tasks/events`);
    eventSourceRef.current = es;

    es.addEventListener("task_update", (e) => {
      const payload = JSON.parse(e.data);
      setTasks((prev) => {
        const idx = prev.findIndex((t) => t.id === payload.task.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = payload.task;
          return next;
        }
        return [...prev, payload.task];
      });
    });

    es.addEventListener("run_started", (e) => {
      const payload = JSON.parse(e.data);
      setRunId(payload.run_id);
      fetchTasks();
    });

    es.addEventListener("run_completed", () => fetchTasks());

    es.onopen = () => {
      setSseConnected(true);
      stopPolling();
    };

    es.onerror = () => {
      setSseConnected(false);
      es.close();
      eventSourceRef.current = null;
      startPolling();
    };
  };

  useEffect(() => {
    fetchTasks();
    connectSSE();
    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      stopPolling();
    };
  }, [specId]);

  if (loading) return <div style={{ padding: 12, color: "var(--muted)", fontSize: 13 }}>Lade Tasks…</div>;
  if (tasks.length === 0)
    return (
      <div style={{ padding: 12, color: "var(--muted)", fontSize: 13 }}>
        Keine Tasks. Starte <code>sdd implement {specId}</code>.
      </div>
    );

  const tasksByStatus: Record<string, Task[]> = {};
  for (const col of COLUMNS) tasksByStatus[col.key] = [];
  for (const t of tasks) {
    if (tasksByStatus[t.status]) tasksByStatus[t.status].push(t);
    else tasksByStatus["blocked"] = [...(tasksByStatus["blocked"] || []), t];
  }

  const activeCols = COLUMNS.filter((c) => tasksByStatus[c.key].length > 0);

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 10,
          fontSize: 12,
          color: "var(--muted)",
        }}
      >
        <span>
          {tasks.length} Tasks
          {runId && <> · Run <code style={{ fontSize: 11 }}>{runId}</code></>}
        </span>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: sseConnected ? "#27ae60" : "#e74c3c",
            display: "inline-block",
          }}
          title={sseConnected ? "Live (SSE)" : "Polling (5s)"}
        />
      </div>
      <div
        role="list"
        aria-label="Task-Kanban-Board"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.max(activeCols.length, 1)}, minmax(140px, 1fr))`,
          gap: 12,
          overflowX: "auto",
        }}
      >
        {activeCols.map((col) => (
          <div
            key={col.key}
            role="listitem"
            aria-label={`Spalte ${col.label}`}
            tabIndex={0}
          >
            <div
              style={{
                fontWeight: 600,
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: 1,
                color: STATUS_COLORS[col.key] || "var(--muted)",
                marginBottom: 8,
                borderBottom: `2px solid ${STATUS_COLORS[col.key] || "var(--muted)"}`,
                paddingBottom: 4,
              }}
            >
              {col.label} <span style={{ fontWeight: 400 }}>({tasksByStatus[col.key].length})</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {tasksByStatus[col.key].map((t) => (
                <TaskCard key={t.id} task={t} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
