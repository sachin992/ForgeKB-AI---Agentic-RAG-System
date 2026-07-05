import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Layout, Progress, Table, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  DataSource,
  deleteDataSource,
  listDataSources,
  me,
  retryDataSource,
  uploadBulkAndIngest,
  uploadAndIngest,
} from "../../lib/api";
import { useAppStore } from "../../lib/store";

export function AdminKnowledgeBasePage() {
  const navigate = useNavigate();
  const token = useAppStore((s) => s.token);
  const role = useAppStore((s) => s.role);
  const email = useAppStore((s) => s.email);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setProfile = useAppStore((s) => s.setProfile);
  const clearProfile = useAppStore((s) => s.clearProfile);
  const setToken = useAppStore((s) => s.setToken);
  const [status, setStatus] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;
    me(token)
      .then((p) => setProfile({ userId: p.id, email: p.email, role: p.role }))
      .catch(() => setStatus("Failed to load profile"));
  }, [token, setProfile]);

  const dsQuery = useQuery({
    queryKey: ["admin-datasources", token],
    queryFn: () => listDataSources(token),
    enabled: !!token && role === "admin",
    refetchInterval: 2500,
  });

  const retryMutation = useMutation({
    mutationFn: (id: number) => retryDataSource(token, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-datasources", token] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      await Promise.all(ids.map((id) => deleteDataSource(token, id)));
      return ids.length;
    },
    onSuccess: (count) => {
      setStatus(`Queued deletion for ${count} file(s)`);
      setSelectedIds([]);
      queryClient.invalidateQueries({ queryKey: ["admin-datasources", token] });
    },
    onError: () => setStatus("Delete failed"),
  });

  const files = useMemo(() => dsQuery.data || [], [dsQuery.data]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!token || !e.target.files?.[0]) return;
    const out = await uploadAndIngest(token, e.target.files[0]);
    setStatus(`Queued indexing for data source ${out.id}`);
    queryClient.invalidateQueries({ queryKey: ["admin-datasources", token] });
  }

  async function onBulkUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!token || !e.target.files?.length) return;
    const out = await uploadBulkAndIngest(token, Array.from(e.target.files));
    setStatus(`Queued ${out.count} files for indexing`);
    queryClient.invalidateQueries({ queryKey: ["admin-datasources", token] });
  }

  function logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_role");
    localStorage.removeItem("auth_email");
    localStorage.removeItem("auth_user_id");
    setToken("");
    clearProfile();
    navigate("/login", { replace: true });
  }

  if (!token) return <Navigate to="/login" replace />;
  if (role !== "admin") return <Navigate to="/app" replace />;

  return (
    <Layout className="app-shell">
      <Layout.Sider width={330} theme="light" className="left-rail">
        <div className="sidebar-main">
          <div className="brand-box">
            <Typography.Title level={3}>ForgeKB AI</Typography.Title>
            <p className="muted">Admin Knowledge Dashboard</p>
            <p className="small">{email || ""}</p>
          </div>
          <Button block onClick={() => navigate("/app")}>Back To Chat</Button>
          <Button block onClick={() => navigate("/admin/users")} style={{ marginTop: 8 }}>
            User Management
          </Button>
          <Button block onClick={toggleTheme} style={{ marginTop: 8 }}>
            Theme: {theme === "dark" ? "Dark" : "Light"}
          </Button>

          <div className="panel">
            <h3>Add File</h3>
            <input type="file" onChange={onUpload} />
          </div>

          <div className="panel">
            <h3>Bulk Upload</h3>
            <input type="file" multiple onChange={onBulkUpload} />
          </div>

          <div className="panel">
            <h3>Bulk Actions</h3>
            <Button
              danger
              block
              disabled={selectedIds.length === 0 || deleteMutation.isPending}
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(selectedIds)}
            >
              Delete Selected ({selectedIds.length})
            </Button>
          </div>
        </div>

        <div className="sidebar-footer">
          <Button block className="logout-btn" onClick={logout}>Logout</Button>
        </div>
      </Layout.Sider>

      <Layout.Content className="main-pane">
        <div className="chat-head">
          <Typography.Title level={2}>Knowledge Base Manager</Typography.Title>
          <p className="muted">Add, retry, delete single files, or select multiple files for deletion.</p>
        </div>

        {status ? <Alert type="info" showIcon message={status} /> : null}

        <Table<DataSource>
          rowKey="id"
          loading={dsQuery.isLoading}
          dataSource={files}
          rowSelection={{
            selectedRowKeys: selectedIds,
            onChange: (keys) => setSelectedIds(keys as number[]),
          }}
          columns={[
            {
              title: "File",
              key: "display_name",
              render: (_, row) => row.display_name || row.file_path.split("/").pop(),
            },
            {
              title: "Status",
              key: "status",
              render: (_, row) => <Tag>{row.status}</Tag>,
            },
            {
              title: "Stage",
              dataIndex: "stage",
              key: "stage",
            },
            {
              title: "Progress",
              key: "progress",
              render: (_, row) => (
                <Progress
                  percent={row.progress_percent}
                  size="small"
                  status={row.status === "Failed" ? "exception" : "active"}
                />
              ),
            },
            {
              title: "Actions",
              key: "actions",
              render: (_, row) => (
                <div className="row" style={{ marginTop: 0 }}>
                  <Button size="small" onClick={() => retryMutation.mutate(row.id)}>Retry</Button>
                  <Button size="small" danger onClick={() => deleteMutation.mutate([row.id])}>Delete</Button>
                </div>
              ),
            },
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Layout.Content>
    </Layout>
  );
}
