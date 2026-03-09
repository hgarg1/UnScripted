import type { PropsWithChildren } from "react";

type StatusCardProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  description: string;
}>;

export function StatusCard({ eyebrow, title, description, children }: StatusCardProps) {
  return (
    <section
      style={{
        borderRadius: 20,
        border: "1px solid rgba(124, 101, 74, 0.2)",
        background: "rgba(255, 255, 255, 0.82)",
        padding: 20,
        boxShadow: "0 18px 40px rgba(31, 23, 16, 0.06)"
      }}
    >
      <small style={{ color: "#8c5b3c", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {eyebrow}
      </small>
      <h2 style={{ margin: "8px 0", fontSize: "1.4rem" }}>{title}</h2>
      <p style={{ color: "#5f5348", margin: 0 }}>{description}</p>
      {children ? <div style={{ marginTop: 16 }}>{children}</div> : null}
    </section>
  );
}
