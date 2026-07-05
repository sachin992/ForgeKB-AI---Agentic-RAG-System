import { Navigate, Route, Routes } from "react-router-dom";
import { AppPage } from "./pages/AppPage";
import { AdminKnowledgeBasePage } from "./pages/AdminKnowledgeBasePage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { useAppStore } from "../lib/store";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAppStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const token = useAppStore((s) => s.token);
  const role = useAppStore((s) => s.role);
  if (!token) return <Navigate to="/login" replace />;
  return role === "admin" ? <>{children}</> : <Navigate to="/app" replace />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <AppPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/users"
        element={
          <RequireAdmin>
            <AdminUsersPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/knowledge-base"
        element={
          <RequireAdmin>
            <AdminKnowledgeBasePage />
          </RequireAdmin>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
