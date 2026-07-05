import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Layout, Progress, Tag, Typography } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    deleteSession,
  DataSource,
  Message,
  deleteDataSource,
  listDataSources,
  loadMessages,
  loadSessions,
  me,
  retryDataSource,
  runEval,
  sendChatSSE,
  sendFeedback,
  uploadAndIngest,
} from "../../lib/api";
import { useAppStore } from "../../lib/store";

type Session = { id: number; title: string; updated_at: string };

export function AppPage() {
  const navigate = useNavigate();
  const token = useAppStore((s) => s.token);
  const role = useAppStore((s) => s.role);
  const email = useAppStore((s) => s.email);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setToken = useAppStore((s) => s.setToken);
  const setProfile = useAppStore((s) => s.setProfile);
  const clearProfile = useAppStore((s) => s.clearProfile);
  const activeSessionId = useAppStore((s) => s.activeSessionId);
  const setActiveSessionId = useAppStore((s) => s.setActiveSessionId);

  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [evalResult, setEvalResult] = useState<any>(null);
  const [liveConfidence, setLiveConfidence] = useState<number | null>(null);

  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    me(token)
      .then((p) => {
        setProfile({ userId: p.id, email: p.email, role: p.role });
        localStorage.setItem("auth_role", p.role || "user");
        localStorage.setItem("auth_email", p.email || "");
        localStorage.setItem("auth_user_id", String(p.id || ""));
      })
      .catch(() => {
        setStatus("Profile fetch failed");
      });

    loadSessions(token)
      .then(setSessions)
      .catch(() => setStatus("Failed to load sessions"));
  }, [token, navigate, setProfile]);

  const dsQuery = useQuery({
    queryKey: ["datasources", token],
    queryFn: () => listDataSources(token),
    enabled: !!token && role !== "admin",
    refetchInterval: 2500,
  });

  const retryMutation = useMutation({
    mutationFn: (id: number) => retryDataSource(token, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasources", token] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDataSource(token, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasources", token] }),
  });

  const canChat = useMemo(() => token.length > 0 && query.trim().length > 0, [token, query]);

  function parseCitations(citationsJson?: string): Array<{ anchor: string; source: string; snippet: string }> {
    if (!citationsJson) return [];
    try {
      return JSON.parse(citationsJson);
    } catch {
      return [];
    }
  }

  async function openSession(sessionId: number) {
    if (!token) return;
    const rows = await loadMessages(token, sessionId);
    setMessages(rows);
    setActiveSessionId(sessionId);
    setStatus(`Loaded session ${sessionId}`);
  }

  async function removeSession(sessionId: number) {
    if (!token) return;
    await deleteSession(token, sessionId);
    const rows = await loadSessions(token);
    setSessions(rows);
    if (activeSessionId === sessionId) {
      setActiveSessionId(undefined);
      setMessages([]);
    }
    setStatus(`Deleted session ${sessionId}`);
  }

  function newChat() {
    setActiveSessionId(undefined);
    setMessages([]);
    setStatus("New chat ready");
  }

  function logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_role");
    localStorage.removeItem("auth_email");
    localStorage.removeItem("auth_user_id");
    setToken("");
    clearProfile();
    setActiveSessionId(undefined);
    navigate("/login", { replace: true });
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!token || role === "admin" || !e.target.files?.[0]) return;
    const out = await uploadAndIngest(token, e.target.files[0]);
    setStatus(`Queued indexing for data source ${out.id}`);
    queryClient.invalidateQueries({ queryKey: ["datasources", token] });
  }

  async function onRunEval() {
    if (!token) return;
    const out = await runEval(token);
    setEvalResult(out);
  }

  async function ask() {
    if (!canChat || !token) return;

    const prompt = query;
    setQuery("");
    setTyping(true);

    const next: Message[] = [
      ...messages,
      { role: "user", content: prompt },
      { role: "assistant", content: "" },
    ];
    setMessages(next);

    let streamOk = true;
    try {
      await sendChatSSE(
        token,
        { session_id: activeSessionId, message: prompt },
        {
          onSession: (sid) => {
            if (!activeSessionId) setActiveSessionId(sid);
          },
          onToken: (t) => {
            setMessages((prev) => {
              const clone = [...prev];
              const last = clone[clone.length - 1];
              if (last?.role === "assistant") {
                last.content += t;
              }
              return clone;
            });
          },
          onConfidence: (payload) => {
            setLiveConfidence(payload.avg_confidence ?? null);
            setStatus(`route=${payload.route_strategy || "balanced"}, confidence=${payload.avg_confidence ?? 0}`);
          },
          onCitations: (citations) => {
            setMessages((prev) => {
              const clone = [...prev];
              const last = clone[clone.length - 1];
              if (last?.role === "assistant") {
                last.citations_json = JSON.stringify(citations || []);
              }
              return clone;
            });
          },
          onError: (message) => {
            setStatus(message);
          },
        }
      );
    } catch {
      streamOk = false;
      setStatus("Streaming failed");
    } finally {
      setTyping(false);
    }

    if (streamOk) setStatus("Answer complete");

    const newSessions = await loadSessions(token);
    setSessions(newSessions);
    if (!activeSessionId && newSessions[0]?.id) {
      setActiveSessionId(newSessions[0].id);
    }
  }

  return (
    <Layout className="app-shell">
      <Layout.Sider width={330} theme="light" className="left-rail">
        <div className="sidebar-main">
          <div className="brand-box">
            <Typography.Title level={3}>ForgeKB AI</Typography.Title>
            <p className="muted">{role === "admin" ? "Admin Console" : "User Workspace"}</p>
            <p className="small">{email || ""}</p>
          </div>
          <Button type="primary" block onClick={newChat}>New Chat</Button>
          {role === "admin" ? (
            <Button block onClick={() => navigate("/admin/users")} style={{ marginTop: 8 }}>
              User Management
            </Button>
          ) : null}
          {role === "admin" ? (
            <Button block onClick={() => navigate("/admin/knowledge-base")} style={{ marginTop: 8 }}>
              Knowledge Dashboard
            </Button>
          ) : null}
          <Button block onClick={toggleTheme} style={{ marginTop: 8 }}>
            Theme: {theme === "dark" ? "Dark" : "Light"}
          </Button>

          {role !== "admin" ? (
            <div className="panel">
              <h3>My Upload</h3>
              <input type="file" onChange={onUpload} />
            </div>
          ) : null}

          {role !== "admin" ? (
            <div className="panel">
              <h3>My Files</h3>
              {dsQuery.data?.map((d: DataSource) => (
                <div key={d.id} className="msg">
                  <div><strong>{d.display_name || d.file_path.split("/").pop()}</strong></div>
                  <div className="small">Status: <Tag>{d.status}</Tag> Version: {d.version}</div>
                  <div className="small">Stage: {d.stage}</div>
                  <Progress percent={d.progress_percent} size="small" status={d.status === "Failed" ? "exception" : "active"} />
                  {d.last_error ? <div className="small">Error: {d.last_error}</div> : null}
                  <div className="row">
                    <Button onClick={() => retryMutation.mutate(d.id)}>Retry</Button>
                    <Button danger onClick={() => deleteMutation.mutate(d.id)}>Delete</Button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          <div className="panel">
            <h3>Evaluation</h3>
            <Button onClick={onRunEval} block>Run Eval</Button>
            {evalResult ? (
              <div className="small" style={{ marginTop: 8 }}>
                total={evalResult.total}, faithfulness={evalResult.faithfulness}, relevancy={evalResult.answer_relevancy}
              </div>
            ) : null}
          </div>

          <div className="panel">
            <h3>Past Conversations</h3>
            {sessions.map((s) => (
              <div key={s.id} className="row" style={{ marginTop: 0, marginBottom: 8 }}>
                <Button block onClick={() => openSession(s.id)}>
                  {s.title}
                </Button>
                <Button danger onClick={() => removeSession(s.id)}>Delete</Button>
              </div>
            ))}
          </div>
        </div>
        <div className="sidebar-footer">
          <Button block className="logout-btn" onClick={logout}>Logout</Button>
        </div>
      </Layout.Sider>

      <Layout.Content className="main-pane">
        <div className="chat-head">
          <Typography.Title level={2}>{role === "admin" ? "Validation Chat" : "Chat Workspace"}</Typography.Title>
          <p className="muted">
            {role === "admin"
              ? "Validate response accuracy against knowledge base files."
              : "Ask grounded questions from your indexed documents."}
          </p>
        </div>

        <div className="chat-stream">
          {messages.map((m, i) => (
            <article className={`msg ${m.role}`} key={i}>
              <strong>{m.role}</strong>
              <div style={{ whiteSpace: "pre-wrap" }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
              </div>
              {m.citations_json && m.citations_json !== "[]" ? (
                <details>
                  <summary>Sources</summary>
                  {parseCitations(m.citations_json).map((c, idx) => (
                    <a key={idx} className="citation-link" href={`#${c.anchor}`}>
                      <strong>{c.source}</strong>
                      <div>{c.snippet}</div>
                    </a>
                  ))}
                </details>
              ) : null}
              {m.role === "assistant" && m.id ? (
                <div className="row">
                  <Button onClick={() => sendFeedback(token, m.id!, 1, "Helpful")}>Thumbs Up</Button>
                  <Button onClick={() => sendFeedback(token, m.id!, -1, "Not helpful")}>Thumbs Down</Button>
                </div>
              ) : null}
            </article>
          ))}
        </div>

        <div className="composer">
          {typing ? <p className="small">typing...</p> : null}
          {liveConfidence !== null ? <p className="small">confidence: {liveConfidence.toFixed(3)}</p> : null}
          <textarea
            rows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask with context, e.g. summarize uploaded policy doc"
          />
          <div className="row">
            <Button type="primary" onClick={ask} disabled={!canChat}>Send</Button>
            <span className="small">{status}</span>
          </div>
        </div>
      </Layout.Content>
    </Layout>
  );
}
