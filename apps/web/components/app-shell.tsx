"use client";

import type { AuthResponse, DiscoveryResponse, FeedResponse, Profile } from "@unscripted/contracts";
import { StatusCard } from "@unscripted/ui";
import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SESSION_STORAGE_KEY = "unscripted.session";

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
    const message = await response.text();
    throw new Error(message || `request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function AppShell() {
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryResponse | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [inviteCode, setInviteCode] = useState("UNSCRIPTED-ALPHA");
  const [handle, setHandle] = useState("architect");
  const [displayName, setDisplayName] = useState("Architect");
  const [bio, setBio] = useState("Building a simulation worth inspecting.");
  const [postBody, setPostBody] = useState("");

  useEffect(() => {
    const storedToken = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedToken) {
      return;
    }

    setToken(storedToken);
    void refreshAll(storedToken);
  }, []);

  async function refreshAll(activeToken: string) {
    try {
      setLoading(true);
      const [sessionProfile, nextFeed, nextDiscovery] = await Promise.all([
        apiFetch<Profile>("/v1/me", activeToken),
        apiFetch<FeedResponse>("/v1/feed", activeToken),
        apiFetch<DiscoveryResponse>("/v1/discovery/accounts", activeToken)
      ]);
      setProfile(sessionProfile);
      setFeed(nextFeed);
      setDiscovery(nextDiscovery);
      setBio(sessionProfile.bio);
      setDisplayName(sessionProfile.display_name);
      setMessage("");
    } catch (error) {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
      setToken("");
      setProfile(null);
      setMessage(error instanceof Error ? error.message : "session refresh failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/v1/auth/invite-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: inviteCode,
          handle,
          display_name: displayName,
          bio,
          consent_version: "v1"
        })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as AuthResponse;
      window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session.token);
      setToken(payload.session.token);
      await refreshAll(payload.session.token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handlePost() {
    if (!token || !postBody.trim()) {
      return;
    }
    setLoading(true);
    try {
      await apiFetch("/v1/posts", token, {
        method: "POST",
        headers: { "Idempotency-Key": `post:${postBody}` },
        body: JSON.stringify({ body: postBody })
      });
      setPostBody("");
      await refreshAll(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "post failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleProfileSave() {
    if (!token) {
      return;
    }
    setLoading(true);
    try {
      const nextProfile = await apiFetch<Profile>("/v1/me/profile", token, {
        method: "PATCH",
        body: JSON.stringify({
          display_name: displayName,
          bio,
          declared_interests: ["simulation", "platforms", "agents"]
        })
      });
      setProfile(nextProfile);
      setMessage("profile updated");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "profile update failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleFollow(accountId: string) {
    if (!token) {
      return;
    }
    setLoading(true);
    try {
      await apiFetch("/v1/follows", token, {
        method: "POST",
        body: JSON.stringify({ target_account_id: accountId })
      });
      await refreshAll(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "follow failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleLike(postId: string) {
    if (!token) {
      return;
    }
    try {
      await apiFetch(`/v1/posts/${postId}/likes`, token, { method: "POST" });
      await refreshAll(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "like failed");
    }
  }

  async function handleLogout() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/auth/logout", token, { method: "POST" });
    } catch {
      // Best effort logout for an invite-only alpha.
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    setToken("");
    setProfile(null);
    setFeed(null);
    setDiscovery(null);
  }

  return (
    <section style={{ display: "grid", gap: 16, maxWidth: 1120, margin: "0 auto" }}>
      <StatusCard
        eyebrow="Phase 3"
        title="Invite-only social product with model hooks"
        description="The app still feels minimal on the surface, but feed reads now log ranking inference and the backend can project events into features and trends."
      />

      {!token ? (
        <StatusCard
          eyebrow="Invite login"
          title="Enter the alpha with a seeded invite"
          description="Use `UNSCRIPTED-ALPHA` for a member account. The API issues a session token and provisions the account if it does not exist."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} placeholder="Invite code" />
            <input value={handle} onChange={(event) => setHandle(event.target.value)} placeholder="Handle" />
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" />
            <textarea value={bio} onChange={(event) => setBio(event.target.value)} placeholder="Bio" rows={4} />
            <button onClick={handleLogin} disabled={loading}>Enter UnScripted</button>
          </div>
        </StatusCard>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, alignItems: "start" }}>
          <StatusCard
            eyebrow={profile ? `@${profile.handle}` : "Session"}
            title={profile?.display_name ?? "Loading"}
            description="Profiles, feed reads, and social writes now run through the same API and session model."
          >
            <div style={{ display: "grid", gap: 12 }}>
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" />
              <textarea value={bio} onChange={(event) => setBio(event.target.value)} rows={4} placeholder="Bio" />
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleProfileSave} disabled={loading}>Save profile</button>
                <button onClick={() => void refreshAll(token)} disabled={loading}>Refresh</button>
                <button onClick={handleLogout}>Logout</button>
              </div>
            </div>
          </StatusCard>

          <div style={{ display: "grid", gap: 16 }}>
            <StatusCard
              eyebrow="Compose"
              title="Create a post"
              description="Phase 1 writes emit canonical events, outbox rows, moderation signals, and idempotency records."
            >
              <div style={{ display: "grid", gap: 12 }}>
                <textarea value={postBody} onChange={(event) => setPostBody(event.target.value)} rows={5} maxLength={280} />
                <button onClick={handlePost} disabled={loading || !postBody.trim()}>
                  Publish
                </button>
              </div>
            </StatusCard>

            <StatusCard
              eyebrow="Discovery"
              title="Suggested accounts"
              description="Follow accounts to shape the deterministic home feed."
            >
              <div style={{ display: "grid", gap: 12 }}>
                {discovery?.items?.map((account) => (
                  <div key={account.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                    <strong>@{account.handle}</strong>
                    <p style={{ margin: "6px 0" }}>{account.bio}</p>
                    <button onClick={() => void handleFollow(account.id)} disabled={account.is_following}>
                      {account.is_following ? "Following" : "Follow"}
                    </button>
                  </div>
                ))}
              </div>
            </StatusCard>
          </div>
        </div>
      )}

      <StatusCard
        eyebrow="Home feed"
        title="Ranked public discourse"
        description="Ranking still uses a bootstrap heuristic, but Phase 3 now persists inference logs and projection-driven features behind the feed path."
      >
        <div style={{ display: "grid", gap: 12 }}>
          {feed?.items?.map((item) => (
            <article
              key={item.post.id}
              style={{
                padding: 16,
                borderRadius: 16,
                border: "1px solid var(--border)",
                background: "var(--surface)"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <strong>@{item.author.handle}</strong>
                <small style={{ color: "var(--muted)" }}>{item.post.moderation_state}</small>
              </div>
              <p>{item.post.body}</p>
              <small style={{ color: "var(--muted)" }}>
                score {item.rank.score.toFixed(2)} · likes {item.post.like_count} · replies {item.post.reply_count}
              </small>
              {token ? (
                <div style={{ marginTop: 10 }}>
                  <button onClick={() => void handleLike(item.post.id)}>Like</button>
                </div>
              ) : null}
            </article>
          ))}
          {!feed?.items?.length ? (
            <p style={{ color: "var(--muted)" }}>
              No feed items yet. Seed the API and follow accounts to populate this view.
            </p>
          ) : null}
        </div>
      </StatusCard>

      {message ? (
        <StatusCard eyebrow="Status" title="Latest response" description={message} />
      ) : null}
    </section>
  );
}
