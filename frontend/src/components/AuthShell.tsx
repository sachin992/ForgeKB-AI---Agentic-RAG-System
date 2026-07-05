import { Link } from "react-router-dom";

export function AuthShell({
  title,
  subtitle,
  children,
  ctaText,
  ctaTo,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  ctaText: string;
  ctaTo: string;
}) {
  return (
    <div className="auth-wrap">
      <section className="auth-center">
        <div className="auth-brand">ForgeKB AI</div>
        <p className="auth-tagline">Precision knowledge base operations for Admin and User workflows.</p>
      </section>
      <section className="auth-card">
        <h2>{title}</h2>
        <p className="muted">{subtitle}</p>
        {children}
        <p className="muted auth-switch">
          <Link to={ctaTo}>{ctaText}</Link>
        </p>
      </section>
    </div>
  );
}
