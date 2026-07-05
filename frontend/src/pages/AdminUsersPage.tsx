import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Layout, Popconfirm, Select, Table, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AdminUser, adminListUsers, adminOffboardUser, adminUpdateUserRole, me } from "../../lib/api";
import { useAppStore } from "../../lib/store";

type Row = AdminUser;

function normalizeRole(role: string): "admin" | "user" {
  return role === "admin" ? "admin" : "user";
}

export function AdminUsersPage() {
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

  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;
    me(token)
      .then((p) => setProfile({ userId: p.id, email: p.email, role: p.role }))
      .catch(() => setStatus("Failed to load profile"));
  }, [token, setProfile]);

  const usersQuery = useQuery({
    queryKey: ["admin-users", token],
    queryFn: async (): Promise<Row[]> => {
      const rows = await adminListUsers(token);
      return rows.map((r) => ({ ...r, role: normalizeRole(r.role) }));
    },
    enabled: !!token && role === "admin",
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, nextRole }: { userId: number; nextRole: "admin" | "user" }) =>
      adminUpdateUserRole(token, userId, nextRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", token] });
      setStatus("Role updated successfully");
    },
    onError: () => setStatus("Role update failed"),
  });

  const offboardMutation = useMutation({
    mutationFn: (userId: number) => adminOffboardUser(token, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", token] });
      setStatus("User offboarded successfully");
    },
    onError: () => setStatus("Offboarding failed"),
  });

  const myUser = useMemo(() => usersQuery.data?.find((u: Row) => u.email === email), [usersQuery.data, email]);

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
            <p className="muted">Admin User Management</p>
            <p className="small">{email || ""}</p>
          </div>
          <Button block onClick={() => navigate("/app")}>Back To Workspace</Button>
          <Button block onClick={() => navigate("/admin/knowledge-base")} style={{ marginTop: 8 }}>
            Knowledge Dashboard
          </Button>
          <Button block onClick={toggleTheme} style={{ marginTop: 8 }}>
            Theme: {theme === "dark" ? "Dark" : "Light"}
          </Button>
        </div>
        <div className="sidebar-footer">
          <Button block className="logout-btn" onClick={logout}>Logout</Button>
        </div>
      </Layout.Sider>

      <Layout.Content className="main-pane">
        <div className="chat-head">
          <Typography.Title level={2}>User Management</Typography.Title>
          <p className="muted">Promote or demote users safely. Self-demotion is blocked.</p>
        </div>

        {status ? <Alert type="info" showIcon message={status} /> : null}

        <Table<Row>
          rowKey="id"
          loading={usersQuery.isLoading}
          dataSource={usersQuery.data || []}
          columns={[
            {
              title: "Email",
              dataIndex: "email",
              key: "email",
            },
            {
              title: "Current Role",
              key: "role",
              render: (_, row) => <Tag color={row.role === "admin" ? "gold" : "blue"}>{row.role}</Tag>,
            },
            {
              title: "Created",
              dataIndex: "created_at",
              key: "created_at",
              render: (value: string) => new Date(value).toLocaleString(),
            },
            {
              title: "Set Role",
              key: "action",
              render: (_, row) => (
                <Select
                  value={normalizeRole(row.role)}
                  style={{ width: 140 }}
                  options={[
                    { label: "User", value: "user" },
                    { label: "Admin", value: "admin" },
                  ]}
                  onChange={(value: "admin" | "user") => {
                    if (myUser && row.id === myUser.id && value !== "admin") {
                      setStatus("Self-demotion is not allowed.");
                      return;
                    }
                    roleMutation.mutate({ userId: row.id, nextRole: value });
                  }}
                />
              ),
            },
            {
              title: "Offboard",
              key: "offboard",
              render: (_, row) => {
                const isSelf = !!myUser && row.id === myUser.id;
                return (
                  <Popconfirm
                    title="Offboard this user?"
                    description="This will remove account access and cleanup owned data sources."
                    okText="Offboard"
                    okButtonProps={{ danger: true }}
                    cancelText="Cancel"
                    onConfirm={() => offboardMutation.mutate(row.id)}
                    disabled={isSelf}
                  >
                    <Button danger disabled={isSelf} loading={offboardMutation.isPending}>
                      Offboard
                    </Button>
                  </Popconfirm>
                );
              },
            },
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Layout.Content>
    </Layout>
  );
}
