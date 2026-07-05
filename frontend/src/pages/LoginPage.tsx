import { Alert, Button, Input } from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../../lib/api";
import { useAppStore } from "../../lib/store";
import { AuthShell } from "../components/AuthShell";

export function LoginPage() {
  const navigate = useNavigate();
  const token = useAppStore((s) => s.token);
  const setToken = useAppStore((s) => s.setToken);
  const setProfile = useAppStore((s) => s.setProfile);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (token) navigate("/app", { replace: true });
  }, [token, navigate]);

  async function onLogin() {
    setLoading(true);
    setError("");
    try {
      const data = await login(email, password);
      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("auth_role", data.role || "user");
      localStorage.setItem("auth_email", data.email || email);
      localStorage.setItem("auth_user_id", String(data.user_id || ""));
      setToken(data.access_token);
      setProfile({ userId: data.user_id, email: data.email, role: data.role });
      navigate("/app", { replace: true });
    } catch {
      setError("Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Welcome Back"
      subtitle="Sign in to open your knowledge workspace."
      ctaText="Need an account? Register"
      ctaTo="/register"
    >
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      <Input size="large" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input.Password
        size="large"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ marginTop: 10 }}
      />
      <Button type="primary" size="large" loading={loading} onClick={onLogin} style={{ marginTop: 12, width: "100%" }}>
        Login
      </Button>
    </AuthShell>
  );
}
