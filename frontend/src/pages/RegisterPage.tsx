import { Alert, Button, Input, Select } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { register } from "../../lib/api";
import { AuthShell } from "../components/AuthShell";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"user" | "admin">("user");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function onRegister() {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await register(email, password, role);
      setSuccess("Registration successful. Please log in.");
      setTimeout(() => navigate("/login"), 700);
    } catch {
      setError("Registration failed. Try another email.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Create Account"
      subtitle="Register first, then sign in to access role-based chat and knowledge tools."
      ctaText="Already have an account? Login"
      ctaTo="/login"
    >
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      {success ? <Alert type="success" showIcon message={success} style={{ marginBottom: 12 }} /> : null}
      <Input size="large" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input.Password
        size="large"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ marginTop: 10 }}
      />
      <Select
        size="large"
        value={role}
        onChange={(v) => setRole(v)}
        style={{ marginTop: 10, width: "100%" }}
        options={[
          { label: "User", value: "user" },
          { label: "Admin", value: "admin" },
        ]}
      />
      <Button type="primary" size="large" loading={loading} onClick={onRegister} style={{ marginTop: 12, width: "100%" }}>
        Register
      </Button>
    </AuthShell>
  );
}
