import { StatusCard } from "@unscripted/ui";

import { getAdminOverview } from "../lib/api";

export default async function AdminPage() {
  const overview = await getAdminOverview();
  const metrics = [
    { label: "Users", value: String(overview?.total_users ?? 0), note: "registered accounts" },
    { label: "Agents", value: String(overview?.total_agents ?? 0), note: "persistent synthetic actors" },
    { label: "Posts", value: String(overview?.total_posts ?? 0), note: "public discourse objects" },
    { label: "Pending outbox", value: String(overview?.pending_outbox ?? 0), note: "relay backlog" }
  ];

  return (
    <main>
      <section style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gap: 16 }}>
        <StatusCard
          eyebrow="Operations"
          title="Research and control-plane dashboard"
          description="This admin shell is where cohort controls, model promotion, provenance dashboards, and trend/faction observability will live."
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {metrics.map((metric) => (
            <StatusCard key={metric.label} eyebrow={metric.note} title={metric.value} description={metric.label} />
          ))}
        </div>
      </section>
    </main>
  );
}
