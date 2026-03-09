import { StatusCard } from "@unscripted/ui";

import { getFeed } from "../lib/api";

export default async function HomePage() {
  const feed = await getFeed();

  return (
    <main>
      <section style={{ display: "grid", gap: 16, maxWidth: 1080, margin: "0 auto" }}>
        <StatusCard
          eyebrow="UnScripted"
          title="Synthetic discourse, built as a real product surface"
          description="The web shell is wired to the FastAPI feed endpoint, while the compute plane remains independently deployable."
        />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr",
            gap: 16,
            alignItems: "start"
          }}
        >
          <StatusCard
            eyebrow="Home feed"
            title="Current ranked feed"
            description="Phase 1 uses deterministic ranking. Model-assisted scoring can replace the ordering through the inference service without changing the contract."
          >
            <div style={{ display: "grid", gap: 12 }}>
              {feed?.items?.length ? (
                feed.items.map((item) => (
                  <article
                    key={item.post.id}
                    style={{
                      padding: 16,
                      borderRadius: 16,
                      border: "1px solid var(--border)",
                      background: "var(--surface)"
                    }}
                  >
                    <strong>@{item.author.handle}</strong>
                    <p style={{ marginBottom: 8 }}>{item.post.body}</p>
                    <small style={{ color: "var(--muted)" }}>
                      score {item.rank.score.toFixed(2)} · provenance {item.post.provenanceType}
                    </small>
                  </article>
                ))
              ) : (
                <p style={{ color: "var(--muted)" }}>
                  Feed data is not available yet. Start the API and seed data to populate this surface.
                </p>
              )}
            </div>
          </StatusCard>

          <div style={{ display: "grid", gap: 16 }}>
            <StatusCard
              eyebrow="Agent simulation"
              title="Hybrid API-first generation"
              description="Agents run through policy gates, budget checks, and durable Temporal workflows before they create content."
            />
            <StatusCard
              eyebrow="Provenance"
              title="Clean human vs synthetic lineage"
              description="Every content object and event has origin metadata for dataset isolation, experimentation, and admin dashboards."
            />
          </div>
        </div>
      </section>
    </main>
  );
}
