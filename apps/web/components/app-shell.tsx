"use client";

import type {
  AuthResponse,
  DiscoveryResponse,
  FeedResponse,
  Profile,
} from "@unscripted/contracts";
import {
  AccountCard,
  AppShell,
  Badge,
  Button,
  Chip,
  Drawer,
  EmptyAction,
  Input,
  NavLink,
  Panel,
  Sidebar,
  SignalCard,
  Textarea,
  Topbar,
  TrendCard,
} from "@unscripted/ui";
import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
} from "react";

import styles from "./app-shell.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SESSION_STORAGE_KEY = "unscripted.session";

type CommentRecord = {
  id: string;
  author_account_id: string;
  post_id: string;
  parent_comment_id: string | null;
  body: string;
  moderation_state: string;
  provenance_type: string;
  created_at: string;
  like_count: number;
};

export type FeedItemView = {
  id: string;
  href: Route;
  author: {
    id: string;
    handle: string;
    displayName: string;
  };
  body: string;
  moderationState: string;
  score: number;
  likes: number;
  replies: number;
  reposts: number;
  reason: string;
  signalLabel: string;
};

export type TrendView = {
  id: string;
  topicKey: string;
  volume: number;
  syntheticShare: number;
  coordinationScore: number;
  explanation: string;
  sparkline: number[];
  promoted: boolean;
};

export type GuessableAccountView = {
  accountId: string;
  handle: string;
  displayName: string;
  bio: string;
  excerpt: string | null;
  recentActivityCount: number;
  alreadyGuessed: boolean;
};

type Flash = {
  title: string;
  description: string;
  tone: "info" | "success" | "warning" | "danger";
} | null;

type WebAppContextValue = {
  token: string;
  hasHydrated: boolean;
  isBusy: boolean;
  profile: Profile | null;
  feed: FeedItemView[];
  discovery: DiscoveryResponse["items"];
  trends: TrendView[];
  guessables: GuessableAccountView[];
  guessScore: { attempts: number; correct: number; accuracy: number } | null;
  flash: Flash;
  commentMap: Record<string, CommentRecord[]>;
  login: (values: {
    inviteCode: string;
    handle: string;
    displayName: string;
    bio: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  createPost: (body: string) => Promise<void>;
  likePost: (postId: string) => Promise<void>;
  followAccount: (accountId: string) => Promise<void>;
  saveProfile: (values: { displayName: string; bio: string }) => Promise<void>;
  submitGuess: (accountId: string, guessedIsAgent: boolean) => Promise<void>;
  loadComments: (postId: string) => Promise<void>;
  createComment: (postId: string, body: string) => Promise<void>;
  resolveProfileByHandle: (handle: string) => Promise<Profile | null>;
  getFeedItem: (postId: string) => FeedItemView | undefined;
  clearFlash: () => void;
};

const WebAppContext = createContext<WebAppContextValue | null>(null);

async function apiFetch<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

function buildTrendExplanation(
  topicKey: string,
  syntheticShare: number,
  coordinationScore: number,
): string {
  if (coordinationScore >= 0.7) {
    return `${topicKey} is accelerating because a dense cluster of coordinated accounts is reinforcing it across the feed.`;
  }
  if (syntheticShare >= 0.5) {
    return `${topicKey} is being carried mostly by synthetic participation, with enough uptake to feel organic.`;
  }
  return `${topicKey} is trending through mixed attention, with genuine engagement still outweighing overt amplification.`;
}

function buildSparkline(
  volume: number,
  syntheticShare: number,
  coordinationScore: number,
): number[] {
  const floor = Math.max(4, Math.round(volume * 0.3));
  return [
    floor,
    Math.round(floor * (1 + syntheticShare)),
    Math.round(volume * (0.62 + syntheticShare * 0.12)),
    Math.round(volume * (0.74 + coordinationScore * 0.14)),
    Math.round(volume * (0.86 + syntheticShare * 0.08)),
    volume,
  ];
}

function toFeedItems(feed: FeedResponse): FeedItemView[] {
  return feed.items.map((item) => ({
    id: item.post.id,
    href: `/post/${item.post.id}` as Route,
    author: {
      id: item.author.id,
      handle: item.author.handle,
      displayName: item.author.displayName,
    },
    body: item.post.body,
    moderationState: item.post.moderation_state,
    score: item.rank.score,
    likes: item.post.like_count,
    replies: item.post.reply_count,
    reposts: item.post.repost_count,
    reason: item.rank.reason,
    signalLabel:
      item.post.provenance_type === "agent"
        ? "high synthetic pressure"
        : "mixed discourse",
  }));
}

function toTrends(
  rows: Array<{
    id: string;
    topic_key: string;
    volume: number;
    synthetic_share: number;
    coordination_score: number;
    promoted?: boolean;
  }>,
): TrendView[] {
  return rows.map((row) => ({
    id: row.id,
    topicKey: row.topic_key,
    volume: row.volume,
    syntheticShare: row.synthetic_share,
    coordinationScore: row.coordination_score,
    explanation: buildTrendExplanation(
      row.topic_key,
      row.synthetic_share,
      row.coordination_score,
    ),
    sparkline: buildSparkline(
      row.volume,
      row.synthetic_share,
      row.coordination_score,
    ),
    promoted: row.promoted ?? true,
  }));
}

export function WebAppProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState("");
  const [hasHydrated, setHasHydrated] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [feed, setFeed] = useState<FeedItemView[]>([]);
  const [discovery, setDiscovery] = useState<DiscoveryResponse["items"]>([]);
  const [trends, setTrends] = useState<TrendView[]>([]);
  const [guessables, setGuessables] = useState<GuessableAccountView[]>([]);
  const [guessScore, setGuessScore] = useState<{
    attempts: number;
    correct: number;
    accuracy: number;
  } | null>(null);
  const [flash, setFlash] = useState<Flash>(null);
  const [commentMap, setCommentMap] = useState<Record<string, CommentRecord[]>>(
    {},
  );

  useEffect(() => {
    const storedToken = window.localStorage.getItem(SESSION_STORAGE_KEY);
    setHasHydrated(true);
    if (!storedToken) {
      return;
    }

    setToken(storedToken);
    void refreshAll(storedToken);
  }, []);

  async function refreshAll(activeToken: string) {
    try {
      setIsBusy(true);
      const [
        sessionProfile,
        nextFeed,
        nextDiscovery,
        nextTrends,
        nextGuessables,
        nextGuessScore,
      ] = await Promise.all([
        apiFetch<Profile>("/v1/me", activeToken),
        apiFetch<FeedResponse>("/v1/feed", activeToken),
        apiFetch<DiscoveryResponse>("/v1/discovery/accounts", activeToken),
        apiFetch<
          Array<{
            id: string;
            topic_key: string;
            volume: number;
            synthetic_share: number;
            coordination_score: number;
            promoted?: boolean;
          }>
        >("/v1/trends", activeToken),
        apiFetch<{
          items: Array<{
            account_id: string;
            handle: string;
            display_name: string;
            bio: string;
            latest_post_excerpt: string | null;
            recent_activity_count: number;
            already_guessed: boolean;
          }>;
        }>("/v1/game/guessable-accounts", activeToken),
        apiFetch<{ attempts: number; correct: number; accuracy: number }>(
          "/v1/game/score",
          activeToken,
        ),
      ]);

      setProfile(sessionProfile);
      setFeed(toFeedItems(nextFeed));
      setDiscovery(nextDiscovery.items);
      setTrends(toTrends(nextTrends));
      setGuessables(
        nextGuessables.items.map((item) => ({
          accountId: item.account_id,
          handle: item.handle,
          displayName: item.display_name,
          bio: item.bio,
          excerpt: item.latest_post_excerpt,
          recentActivityCount: item.recent_activity_count,
          alreadyGuessed: item.already_guessed,
        })),
      );
      setGuessScore(nextGuessScore);
      setFlash(null);
    } catch (error) {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
      setToken("");
      setProfile(null);
      setFeed([]);
      setDiscovery([]);
      setTrends([]);
      setGuessables([]);
      setGuessScore(null);
      setFlash({
        title: "Session reset",
        description: error instanceof Error ? error.message : "refresh failed",
        tone: "danger",
      });
    } finally {
      setIsBusy(false);
    }
  }

  async function login(values: {
    inviteCode: string;
    handle: string;
    displayName: string;
    bio: string;
  }) {
    try {
      setIsBusy(true);
      const response = await fetch(`${API_BASE_URL}/v1/auth/invite-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: values.inviteCode,
          handle: values.handle,
          display_name: values.displayName,
          bio: values.bio,
          consent_version: "v1",
        }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as AuthResponse;
      window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session.token);
      setToken(payload.session.token);
      await refreshAll(payload.session.token);
    } catch (error) {
      setFlash({
        title: "Login failed",
        description:
          error instanceof Error ? error.message : "invite login failed",
        tone: "danger",
      });
    } finally {
      setIsBusy(false);
    }
  }

  async function logout() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/auth/logout", token, { method: "POST" });
    } catch {
      // best effort
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    setToken("");
    setProfile(null);
    setFeed([]);
    setDiscovery([]);
    setTrends([]);
    setGuessables([]);
    setGuessScore(null);
    setCommentMap({});
  }

  async function refresh() {
    if (!token) {
      return;
    }
    await refreshAll(token);
  }

  async function createPost(body: string) {
    if (!token || !body.trim() || !profile) {
      return;
    }

    const optimisticItem: FeedItemView = {
      id: `optimistic-${Date.now()}`,
      href: "#",
      author: {
        id: profile.id,
        handle: profile.handle,
        displayName: profile.display_name,
      },
      body,
      moderationState: "pending",
      score: 1.0,
      likes: 0,
      replies: 0,
      reposts: 0,
      reason: "Freshly published",
      signalLabel: "new signal",
    };
    setFeed((current) => [optimisticItem, ...current]);

    try {
      await apiFetch("/v1/posts", token, {
        method: "POST",
        headers: { "Idempotency-Key": `post:${body}` },
        body: JSON.stringify({ body }),
      });
      setFlash({
        title: "Post published",
        description: "Your post entered the discourse graph.",
        tone: "success",
      });
      startTransition(() => void refreshAll(token));
    } catch (error) {
      setFeed((current) =>
        current.filter((item) => item.id !== optimisticItem.id),
      );
      setFlash({
        title: "Post failed",
        description:
          error instanceof Error ? error.message : "unable to publish",
        tone: "danger",
      });
    }
  }

  async function likePost(postId: string) {
    if (!token) {
      return;
    }
    setFeed((current) =>
      current.map((item) =>
        item.id === postId ? { ...item, likes: item.likes + 1 } : item,
      ),
    );
    try {
      await apiFetch(`/v1/posts/${postId}/likes`, token, { method: "POST" });
    } catch (error) {
      setFeed((current) =>
        current.map((item) =>
          item.id === postId
            ? { ...item, likes: Math.max(item.likes - 1, 0) }
            : item,
        ),
      );
      setFlash({
        title: "Like failed",
        description:
          error instanceof Error ? error.message : "unable to like post",
        tone: "danger",
      });
    }
  }

  async function followAccount(accountId: string) {
    if (!token) {
      return;
    }
    setDiscovery((current) =>
      current.map((account) =>
        account.id === accountId ? { ...account, is_following: true } : account,
      ),
    );
    try {
      await apiFetch("/v1/follows", token, {
        method: "POST",
        body: JSON.stringify({ target_account_id: accountId }),
      });
      setFlash({
        title: "Account followed",
        description: "Your feed will tilt toward this account's discourse.",
        tone: "success",
      });
    } catch (error) {
      setDiscovery((current) =>
        current.map((account) =>
          account.id === accountId
            ? { ...account, is_following: false }
            : account,
        ),
      );
      setFlash({
        title: "Follow failed",
        description:
          error instanceof Error ? error.message : "unable to follow account",
        tone: "danger",
      });
    }
  }

  async function saveProfile(values: { displayName: string; bio: string }) {
    if (!token) {
      return;
    }
    try {
      const nextProfile = await apiFetch<Profile>("/v1/me/profile", token, {
        method: "PATCH",
        body: JSON.stringify({
          display_name: values.displayName,
          bio: values.bio,
          declared_interests: ["simulation", "platforms", "agents"],
        }),
      });
      setProfile(nextProfile);
      setFlash({
        title: "Profile updated",
        description: "Your signal profile has been refreshed.",
        tone: "success",
      });
    } catch (error) {
      setFlash({
        title: "Profile update failed",
        description:
          error instanceof Error ? error.message : "unable to save profile",
        tone: "danger",
      });
    }
  }

  async function submitGuess(accountId: string, guessedIsAgent: boolean) {
    if (!token) {
      return;
    }
    try {
      const result = await apiFetch<{
        was_correct: boolean;
        actual_account_type: string;
      }>("/v1/game/guesses", token, {
        method: "POST",
        body: JSON.stringify({
          target_account_id: accountId,
          guessed_is_agent: guessedIsAgent,
        }),
      });
      setGuessables((current) =>
        current.map((account) =>
          account.accountId === accountId
            ? { ...account, alreadyGuessed: true }
            : account,
        ),
      );
      startTransition(() => void refreshAll(token));
      setFlash({
        title: result.was_correct ? "Correct read" : "Wrong read",
        description: result.was_correct
          ? "Your guess matched the account type."
          : `Actual type: ${result.actual_account_type}.`,
        tone: result.was_correct ? "success" : "warning",
      });
    } catch (error) {
      setFlash({
        title: "Guess failed",
        description:
          error instanceof Error ? error.message : "unable to submit guess",
        tone: "danger",
      });
    }
  }

  async function loadComments(postId: string) {
    if (!token) {
      return;
    }
    try {
      const response = await apiFetch<{ items: CommentRecord[] }>(
        `/v1/posts/${postId}/comments`,
        token,
      );
      setCommentMap((current) => ({ ...current, [postId]: response.items }));
    } catch (error) {
      setFlash({
        title: "Unable to load thread",
        description:
          error instanceof Error ? error.message : "comment fetch failed",
        tone: "danger",
      });
    }
  }

  async function createComment(postId: string, body: string) {
    if (!token || !body.trim()) {
      return;
    }
    try {
      await apiFetch(`/v1/posts/${postId}/comments`, token, {
        method: "POST",
        body: JSON.stringify({ body }),
      });
      await loadComments(postId);
      startTransition(() => void refreshAll(token));
    } catch (error) {
      setFlash({
        title: "Reply failed",
        description:
          error instanceof Error ? error.message : "unable to create reply",
        tone: "danger",
      });
    }
  }

  async function resolveProfileByHandle(
    handle: string,
  ): Promise<Profile | null> {
    if (!token) {
      return null;
    }

    if (profile?.handle === handle) {
      return profile;
    }

    const knownAccount =
      discovery.find((account) => account.handle === handle) ??
      feed.find((item) => item.author.handle === handle)?.author;
    if (!knownAccount) {
      return null;
    }
    try {
      return await apiFetch<Profile>(`/v1/accounts/${knownAccount.id}`, token);
    } catch {
      return null;
    }
  }

  function getFeedItem(postId: string) {
    return feed.find((item) => item.id === postId);
  }

  return (
    <WebAppContext.Provider
      value={{
        token,
        hasHydrated,
        isBusy,
        profile,
        feed,
        discovery,
        trends,
        guessables,
        guessScore,
        flash,
        commentMap,
        login,
        logout,
        refresh,
        createPost,
        likePost,
        followAccount,
        saveProfile,
        submitGuess,
        loadComments,
        createComment,
        resolveProfileByHandle,
        getFeedItem,
        clearFlash: () => setFlash(null),
      }}
    >
      {children}
    </WebAppContext.Provider>
  );
}

export function useWebApp() {
  const context = useContext(WebAppContext);
  if (!context) {
    throw new Error("useWebApp must be used within WebAppProvider");
  }
  return context;
}

export function WebProductShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { profile, trends, discovery, flash, clearFlash, token, hasHydrated } =
    useWebApp();
  const navItems: Array<{ href: Route; label: string }> = [
    { href: "/" as Route, label: "Home" },
    { href: "/explore" as Route, label: "Explore" },
    { href: "/signals" as Route, label: "Signals" },
    { href: "/guess" as Route, label: "Guess" },
    {
      href: (profile ? `/profile/${profile.handle}` : "/profile") as Route,
      label: "Profile",
    },
  ];

  const rail = token ? (
    <div className={styles.railStack}>
      <SignalCard
        title="Synthetic pressure"
        description="A quick read on how aggressively the current discourse is being amplified."
        metrics={[
          {
            label: "Promoted trends",
            value: String(trends.length),
          },
          {
            label: "High coordination",
            value: String(
              trends.filter((trend) => trend.coordinationScore >= 0.7).length,
            ),
          },
          {
            label: "Following",
            value: String(
              discovery.filter((account) => account.is_following).length,
            ),
          },
        ]}
      />
      <div className={styles.railStack}>
        {trends.slice(0, 2).map((trend) => (
          <TrendCard
            key={trend.id}
            topic={trend.topicKey}
            volume={trend.volume}
            syntheticShare={trend.syntheticShare}
            coordinationScore={trend.coordinationScore}
            sparkline={trend.sparkline}
            explanation={trend.explanation}
            promoted={trend.promoted}
          />
        ))}
      </div>
      <div className={styles.railStack}>
        {discovery.slice(0, 2).map((account) => (
          <AccountCard
            key={account.id}
            handle={account.handle}
            displayName={account.display_name}
            bio={account.bio}
            badges={
              <Chip tone={account.is_agent_account ? "warning" : "neutral"}>
                {account.is_agent_account
                  ? "high signal volatility"
                  : "low volatility"}
              </Chip>
            }
            detail="Suggested because this account sits close to your current discourse neighborhood."
          />
        ))}
      </div>
    </div>
  ) : (
    <div className={styles.railStack}>
      <SignalCard
        title="What this is"
        description="UnScripted is a social simulation where human and synthetic behavior coexist in one visible network."
        metrics={[
          { label: "Humans", value: "invite-only" },
          { label: "Agents", value: "persistent" },
          { label: "Goal", value: "observe consensus" },
        ]}
      />
      <Panel
        eyebrow="Alpha"
        title="Built to be legible"
        description="The product should feel like a polished network first, then reveal how amplification and faction dynamics shape the discourse."
      />
    </div>
  );

  return (
    <AppShell
      sidebar={
        <Sidebar
          brand={
            <div>
              <div>UnScripted</div>
              <div className={styles.subtle}>dead internet simulation</div>
            </div>
          }
          nav={
            <>
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <NavLink active={pathname === item.href}>
                    {item.label}
                  </NavLink>
                </Link>
              ))}
            </>
          }
          footer="Invite-only alpha. Humans and agents share one discourse graph."
        />
      }
      topbar={
        <Topbar
          left={
            <div className={styles.row}>
              <Badge>alpha</Badge>
              <Badge>{hasHydrated && token ? "session active" : "guest"}</Badge>
            </div>
          }
          right={
            <div className={styles.row}>
              <div className={styles.desktopOnly}>
                <Input
                  aria-label="Search placeholder"
                  placeholder="Search is coming later"
                  readOnly
                  value=""
                />
              </div>
              {profile ? <Chip tone="primary">@{profile.handle}</Chip> : null}
            </div>
          }
        />
      }
      insight={rail}
      mobileNav={
        <>
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <NavLink active={pathname === item.href}>{item.label}</NavLink>
            </Link>
          ))}
        </>
      }
    >
      {flash ? (
        <Panel
          eyebrow={flash.tone}
          title={flash.title}
          description={flash.description}
        >
          <div className={styles.row}>
            <Button variant="ghost" onClick={clearFlash}>
              Dismiss
            </Button>
          </div>
        </Panel>
      ) : null}
      {children}
    </AppShell>
  );
}

export function SignalContextDrawer({
  item,
  open,
  onClose,
}: {
  item: FeedItemView | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={open}
      title={
        item ? `Why @${item.author.handle} is surfacing` : "Signal context"
      }
      onClose={onClose}
    >
      {item ? (
        <div className={styles.sectionStack}>
          <SignalCard
            title="Ranking context"
            description={item.reason}
            metrics={[
              { label: "Score", value: item.score.toFixed(2) },
              { label: "Likes", value: String(item.likes) },
              { label: "Replies", value: String(item.replies) },
            ]}
          />
          <Panel
            eyebrow="Signal read"
            title={item.signalLabel}
            description="This drawer keeps synthetic evidence optional in the main feed while still making the system legible when a user wants to inspect it."
          />
        </div>
      ) : null}
    </Drawer>
  );
}
