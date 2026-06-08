// Hub-Verbindungslogik (CON-0149, CON-0150) – reine Funktionen, kein React.

export type ConnectionState = "online" | "offline" | "unknown";
export type ServerStatus = "running" | "stopped" | "starting" | "stopping" | "error";

export const OFFLINE_THRESHOLD = 2;

/**
 * Zustandsmaschine für Hub-Verbindungsüberwachung mit Entprellung (EC-10).
 * Erst nach OFFLINE_THRESHOLD aufeinanderfolgenden Fehlern → offline.
 */
export class ConnectionMonitor {
  private _failureCount = 0;
  private _state: ConnectionState = "unknown";

  get state(): ConnectionState { return this._state; }

  recordSuccess(): ConnectionState {
    this._failureCount = 0;
    this._state = "online";
    return this._state;
  }

  recordFailure(): ConnectionState {
    this._failureCount += 1;
    if (this._failureCount >= OFFLINE_THRESHOLD) {
      this._state = "offline";
    }
    return this._state;
  }
}

/** Schaltfläche "Starten" darf nur aktiv sein wenn Hub online, kein Pending, Status stopped. */
export function canStart(status: ServerStatus, online: boolean, pending: boolean): boolean {
  return online && !pending && status === "stopped";
}

/** Schaltfläche "Stoppen" darf nur aktiv sein wenn Hub online, kein Pending, Status running. */
export function canStop(status: ServerStatus, online: boolean, pending: boolean): boolean {
  return online && !pending && status === "running";
}

/** Optimistischer Status nach Aktionsauslösung (FR-07). */
export function optimisticStatus(action: "start" | "stop"): ServerStatus {
  return action === "start" ? "starting" : "stopping";
}

/** Übergangs-Status → beide Aktionsschaltflächen deaktiviert (EC-03). */
export function isTransitionState(status: ServerStatus): boolean {
  return status === "starting" || status === "stopping";
}
