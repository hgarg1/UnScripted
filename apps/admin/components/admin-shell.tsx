"use client";

import type { AuthResponse, ModerationSignal } from "@unscripted/contracts";
import { StatusCard } from "@unscripted/ui";
import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SESSION_STORAGE_KEY = "unscripted.admin.session";

async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return (await response.json()) as T;
}

export function AdminShell() {
  const [token, setToken] = useState("");
  const [handle, setHandle] = useState("admin");
  const [displayName, setDisplayName] = useState("Admin Operator");
  const [message, setMessage] = useState("");
  const [overview, setOverview] = useState<{
    total_users: number;
    total_agents: number;
    total_posts: number;
    total_events: number;
    pending_outbox: number;
  } | null>(null);
  const [invites, setInvites] = useState<Array<{ id: string; code: string; role: string; use_count: number }>>([]);
  const [moderationSignals, setModerationSignals] = useState<ModerationSignal[]>([]);

  useEffect(() => {
    const storedToken = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedToken) {
      return;
    }
    setToken(storedToken);
    void refresh(storedToken);
  }, []);

  async function refresh(activeToken: string) {
    try {
      const [nextOverview, nextInvites, nextSignals] = await Promise.all([
        apiFetch<{
          total_users: number;
          total_agents: number;
          total_posts: number;
          total_events: number;
          pending_outbox: number;
        }>("/v1/admin/overview", activeToken),
        apiFetch<Array<{ id: string; code: string; role: string; use_count: number }>>("/v1/admin/invite-codes", activeToken),
        apiFetch<{ items: ModerationSignal[] }>("/v1/admin/moderation-signals", activeToken)
      ]);
      setOverview(nextOverview);
      setInvites(nextInvites);
      setModerationSignals(nextSignals.items);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "admin refresh failed");
    }
  }

  async function handleLogin() {
    try {
      const response = await fetch(`${API_BASE_URL}/v1/auth/invite-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: "ADMIN-ROOT",
          handle,
          display_name: displayName,
          bio: "Controls the synthetic discourse environment.",
          consent_version: "v1"
        })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as AuthResponse;
      window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session.token);
      setToken(payload.session.token);
      await refresh(payload.session.token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "admin login failed");
    }
  }

  async function createInvite() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/invite-codes", token, {
        method: "POST",
        body: JSON.stringify({ role: "member", max_uses: 25, expires_in_hours: 168 })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "invite creation failed");
    }
  }

  return (
    <section style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gap: 16 }}>
      <StatusCard
        eyebrow="Phase 1 admin"
        title="Invite-only control plane"
        description="The admin surface now authenticates via seeded invite and calls the API over the same session model as the user app."
      />

      {!token ? (
        <StatusCard
          eyebrow="Admin login"
          title="Use the seeded admin invite"
          description="The seed script provisions `ADMIN-ROOT` for invite-only control-plane access."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={handle} onChange={(event) => setHandle(event.target.value)} placeholder="Handle" />
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" />
            <button onClick={handleLogin}>Open admin console</button>
          </div>
        </StatusCard>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        {[
          { label: "Users", value: String(overview?.total_users ?? 0), note: "registered accounts" },
          { label: "Agents", value: String(overview?.total_agents ?? 0), note: "persistent actors" },
          { label: "Posts", value: String(overview?.total_posts ?? 0), note: "public discourse objects" },
          { label: "Outbox", value: String(overview?.pending_outbox ?? 0), note: "pending relay rows" }
        ].map((metric) => (
          <StatusCard key={metric.label} eyebrow={metric.note} title={metric.value} description={metric.label} />
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Invites"
          title="Invite issuance"
          description="Phase 1 keeps onboarding invite-only and observable."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <button onClick={createInvite} disabled={!token}>Create member invite</button>
            {invites.map((invite) => (
              <div key={invite.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{invite.code}</strong>
                <div style={{ color: "#5f5348" }}>
                  role {invite.role} · used {invite.use_count}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Moderation"
          title="Open moderation queue"
          description="Simple Phase 1 rule signals make flagged content visible before model-assisted moderation exists."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {moderationSignals.length ? (
              moderationSignals.map((signal) => (
                <div key={signal.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                  <strong>{signal.content_type}</strong>
                  <div style={{ color: "#5f5348" }}>
                    {signal.signal_type} · score {signal.score.toFixed(2)} · {signal.status}
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: "#5f5348" }}>No moderation signals yet.</p>
            )}
          </div>
        </StatusCard>
      </div>

      {message ? <StatusCard eyebrow="Status" title="Latest response" description={message} /> : null}
    </section>
  );
}
