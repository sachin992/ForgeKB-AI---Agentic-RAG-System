const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export type Message = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations_json?: string;
  metadata_json?: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  role: "admin" | "user" | string;
};

export type RegisterResponse = {
  user_id: number;
  email: string;
  role: "admin" | "user" | string;
  message: string;
};

export type UserProfile = {
  id: number;
  email: string;
  role: "admin" | "user" | string;
};

export type AdminUser = {
  id: number;
  email: string;
  role: "admin" | "user" | string;
  created_at: string;
};

export type DataSource = {
  id: number;
  file_path: string;
  display_name: string;
  source_type: string;
  owner_user_id: number | null;
  visibility: string;
  metadata_json: string;
  status: "Pending" | "Indexing" | "Completed" | "Failed" | string;
  progress_percent: number;
  stage: string;
  telemetry_json: string;
  version: number;
  is_deleted: boolean;
  task_id: string;
  last_error: string;
  updated_at: string;
};

type ChatSseHandlers = {
  onSession?: (sessionId: number) => void;
  onToken?: (token: string) => void;
  onConfidence?: (payload: { avg_confidence: number; route_strategy?: string; context_count?: number }) => void;
  onCitations?: (citations: any[]) => void;
  onError?: (message: string) => void;
  onDone?: (payload?: { session_id?: number; message_id?: number }) => void;
};

export async function register(email: string, password: string, role: "admin" | "user" = "user") {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, role }),
  });
  if (!res.ok) throw new Error("Register failed");
  return (await res.json()) as RegisterResponse;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  return (await res.json()) as AuthResponse;
}

export async function me(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load profile");
  return res.json();
}

export async function adminListUsers(token: string): Promise<AdminUser[]> {
  const res = await fetch(`${API_BASE}/admin/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to list users");
  return res.json();
}

export async function adminUpdateUserRole(
  token: string,
  userId: number,
  role: "admin" | "user"
) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error("Failed to update user role");
  return res.json();
}

export async function adminOffboardUser(token: string, userId: number) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to offboard user");
  return res.json();
}

export async function loadSessions(token: string) {
  const res = await fetch(`${API_BASE}/history/sessions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load sessions");
  return res.json();
}

export async function loadMessages(token: string, sessionId: number) {
  const res = await fetch(`${API_BASE}/history/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

export async function deleteSession(token: string, sessionId: number) {
  const res = await fetch(`${API_BASE}/history/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

export async function sendChatStream(
  token: string,
  payload: { session_id?: number; message: string },
  onToken: (t: string) => void
) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) throw new Error("Chat failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onToken(decoder.decode(value, { stream: true }));
  }
}

export async function sendChatSSE(
  token: string,
  payload: { session_id?: number; message: string },
  handlers: ChatSseHandlers
) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) throw new Error("SSE chat failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatchEvent = (raw: string) => {
    const lines = raw.split("\n");
    let eventName = "message";
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    let payload: any = {};
    const data = dataLines.join("\n");
    if (data) {
      try {
        payload = JSON.parse(data);
      } catch {
        payload = { value: data };
      }
    }

    if (eventName === "session" && handlers.onSession && payload.session_id) handlers.onSession(payload.session_id);
    if (eventName === "token" && handlers.onToken) handlers.onToken(payload.token || "");
    if (eventName === "confidence" && handlers.onConfidence) handlers.onConfidence(payload);
    if (eventName === "citations" && handlers.onCitations) handlers.onCitations(payload.citations || []);
    if (eventName === "error" && handlers.onError) handlers.onError(payload.message || "Unknown error");
    if (eventName === "done" && handlers.onDone) handlers.onDone(payload);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      if (part.trim()) dispatchEvent(part);
    }
  }

  if (buffer.trim()) dispatchEvent(buffer);
}

export async function uploadAndIngest(token: string, file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/datasources/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error("Ingest failed");
  return res.json();
}

export async function uploadBulkAndIngest(token: string, files: File[]) {
  const form = new FormData();
  for (const file of files) form.append("files", file);

  const res = await fetch(`${API_BASE}/datasources/upload/bulk`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error("Bulk ingest failed");
  return res.json();
}

export async function listDataSources(token: string): Promise<DataSource[]> {
  const res = await fetch(`${API_BASE}/datasources`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to list data sources");
  return res.json();
}

export async function deleteDataSource(token: string, datasourceId: number) {
  const res = await fetch(`${API_BASE}/datasources/${datasourceId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

export async function retryDataSource(token: string, datasourceId: number) {
  const res = await fetch(`${API_BASE}/datasources/retry`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ datasource_id: datasourceId }),
  });
  if (!res.ok) throw new Error("Retry failed");
  return res.json();
}

export async function runEval(token: string) {
  const res = await fetch(`${API_BASE}/eval/run`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Evaluation failed");
  return res.json();
}

export async function sendFeedback(
  token: string,
  message_id: number,
  rating: number,
  comment: string
) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message_id, rating, comment }),
  });
  if (!res.ok) throw new Error("Feedback failed");
  return res.json();
}
