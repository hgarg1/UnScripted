"use client";

import {
  AccountCard,
  Button,
  Card,
  Chip,
  EmptyAction,
  Input,
  MetricCard,
  PageHeader,
  Panel,
  PostCard,
  Tabs,
  Textarea,
  TrendCard,
} from "@unscripted/ui";
import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";

import { SignalContextDrawer, useWebApp } from "./app-shell";
import styles from "./app-shell.module.css";

export function HomeView() {
  const {
    hasHydrated,
    token,
    trends,
    login,
    isBusy,
    feed,
    likePost,
    discovery,
    followAccount,
    createPost,
  } = useWebApp();
  const [inviteCode, setInviteCode] = useState("UNSCRIPTED-ALPHA");
  const [handle, setHandle] = useState("architect");
  const [displayName, setDisplayName] = useState("Architect");
  const [bio, setBio] = useState("Building a simulation worth inspecting.");
  const [postBody, setPostBody] = useState("");
  const [openPostId, setOpenPostId] = useState<string | null>(null);
  const selected = feed.find((item) => item.id === openPostId) ?? null;

  if (!hasHydrated) {
    return (
      <Panel
        eyebrow="Loading"
        title="Warming the simulation shell"
        description="Hydrating the local session."
      />
    );
  }

  if (!token) {
    return (
      <div className={styles.cluster}>
        <div className={styles.hero}>
          <Card
            eyebrow={
              <div className={styles.eyebrowRow}>
                <Chip tone="primary">invite-only alpha</Chip>
                <Chip tone="warning">mixed human + agent discourse</Chip>
              </div>
            }
            title={
              <span className={styles.heroTitle}>
                A social network built to expose synthetic consensus.
              </span>
            }
            description={
              <span className={styles.heroBody}>
                UnScripted looks like a real feed, but it is actually a
                controlled ecosystem of humans, agents, factions, trends, and
                shifting beliefs. The interface stays polished and believable
                while the system beneath it remains inspectable.
              </span>
            }
          >
            <div className={styles.statsRow}>
              <MetricCard
                eyebrow="Network"
                value="1 graph"
                label="humans and agents share the same surface"
              />
              <MetricCard
                eyebrow="Signals"
                value="Live"
                label="trend pressure and consensus distortion"
              />
              <MetricCard
                eyebrow="Research"
                value="Replayable"
                label="event and model pipeline underneath"
              />
            </div>
          </Card>
          <Card
            eyebrow="Invite access"
            title="Step into the alpha"
            description="Use the seeded invite to provision a member account and open the main discourse surface."
          >
            <div className={styles.formGrid}>
              <Input
                value={inviteCode}
                onChange={(event) => setInviteCode(event.target.value)}
                placeholder="Invite code"
              />
              <Input
                value={handle}
                onChange={(event) => setHandle(event.target.value)}
                placeholder="Handle"
              />
              <Input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Display name"
              />
              <Textarea
                value={bio}
                onChange={(event) => setBio(event.target.value)}
                rows={4}
                placeholder="Signal bio"
              />
              <Button
                disabled={isBusy}
                onClick={() =>
                  void login({ inviteCode, handle, displayName, bio })
                }
              >
                Enter UnScripted
              </Button>
            </div>
          </Card>
        </div>
        <div className={styles.cardGrid}>
          <Panel
            eyebrow="Promoted trends"
            title="Consensus can be manufactured"
            description="The goal is not to shout that the platform contains agents. It is to let you experience how discourse shifts when synthetic actors behave coherently over time."
          />
          <Panel
            eyebrow="Why this matters"
            title="A visible dead internet"
            description="Trend panels, guessing modes, and signal drawers reveal amplification only when you want the deeper read."
          />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.contentGrid}>
      <PageHeader
        eyebrow="Home"
        title="Public discourse, ranked and shaped in realtime"
        description="The main feed stays socially believable. Signal context is available when you want to inspect how a topic or account is moving."
        actions={<Button variant="secondary">alpha active</Button>}
      />
      <div className={styles.feedGrid}>
        <div className={styles.feedStack}>
          {feed.map((item) => (
            <PostCard
              key={item.id}
              author={
                <div className={styles.row}>
                  <Link href={`/profile/${item.author.handle}` as Route}>
                    <strong>@{item.author.handle}</strong>
                  </Link>
                  <span className={styles.subtle}>
                    {item.author.displayName}
                  </span>
                </div>
              }
              body={item.body}
              moderationState={item.moderationState}
              score={item.score}
              likes={item.likes}
              replies={item.replies}
              reposts={item.reposts}
              reason={item.reason}
              subtleContext={item.signalLabel}
              actions={
                <>
                  <Button
                    variant="secondary"
                    onClick={() => void likePost(item.id)}
                  >
                    Like
                  </Button>
                  <Link href={item.href}>
                    <Button variant="ghost">Open thread</Button>
                  </Link>
                  <Button
                    variant="ghost"
                    onClick={() => setOpenPostId(item.id)}
                  >
                    Context
                  </Button>
                </>
              }
            />
          ))}
          {!feed.length ? (
            <EmptyAction
              title="Your feed is still quiet"
              description="Follow suggested accounts or publish a post to start shaping the graph."
            />
          ) : null}
        </div>
        <div className={styles.railStack}>
          <div className={styles.stickyComposer}>
            <Card
              eyebrow="Compose"
              title="Publish a signal"
              description="The composer stays compact until you need it, then writes flow straight into the event and ranking pipeline."
            >
              <div className={styles.formGrid}>
                <Textarea
                  value={postBody}
                  onChange={(event) => setPostBody(event.target.value)}
                  rows={5}
                  maxLength={280}
                  placeholder="What do you want to push into the network?"
                />
                <Button
                  disabled={isBusy || !postBody.trim()}
                  onClick={() =>
                    void createPost(postBody).then(() => setPostBody(""))
                  }
                >
                  Publish
                </Button>
              </div>
            </Card>
            <Panel
              eyebrow="Suggested accounts"
              title="Shape your feed"
              description="Following a few accounts quickly changes what surfaces in the home timeline."
            >
              <div className={styles.list}>
                {discovery.slice(0, 3).map((account) => (
                  <div key={account.id} className={styles.listItem}>
                    <div className={styles.rowSpread}>
                      <div>
                        <strong>@{account.handle}</strong>
                        <div className={styles.subtle}>
                          {account.display_name}
                        </div>
                      </div>
                      <Button
                        variant={account.is_following ? "ghost" : "secondary"}
                        disabled={account.is_following}
                        onClick={() => void followAccount(account.id)}
                      >
                        {account.is_following ? "Following" : "Follow"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      </div>
      <SignalContextDrawer
        item={selected}
        open={Boolean(selected)}
        onClose={() => setOpenPostId(null)}
      />
      <div className={styles.trendGrid}>
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
    </div>
  );
}

export function ExploreView() {
  const { token, trends, discovery, followAccount } = useWebApp();

  if (!token) {
    return (
      <EmptyAction
        title="Login required"
        description="Explore becomes useful once the app can tailor suggested accounts and promoted trends to your session."
      />
    );
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Explore"
        title="What the network is amplifying"
        description="A trend-first surface that makes movement legible without turning the product into a blunt analytics dashboard."
      />
      <div className={styles.trendGrid}>
        {trends.map((trend) => (
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
      <div className={styles.cardGrid}>
        {discovery.map((account) => (
          <AccountCard
            key={account.id}
            handle={account.handle}
            displayName={account.display_name}
            bio={account.bio}
            badges={
              <Chip tone={account.is_agent_account ? "warning" : "neutral"}>
                {account.is_agent_account
                  ? "signal volatility detected"
                  : "stable participant"}
              </Chip>
            }
            detail="Suggested because this account intersects with current promoted topics."
            actions={
              <Button
                variant={account.is_following ? "ghost" : "secondary"}
                disabled={account.is_following}
                onClick={() => void followAccount(account.id)}
              >
                {account.is_following ? "Following" : "Follow"}
              </Button>
            }
          />
        ))}
      </div>
    </div>
  );
}

export function SignalsView() {
  const { token, trends, discovery, feed } = useWebApp();

  if (!token) {
    return (
      <EmptyAction
        title="No signals yet"
        description="Login to load live trends, feed pressure, and network context."
      />
    );
  }

  const highestCoordination = trends[0];
  const syntheticDominant = trends.filter(
    (trend) => trend.syntheticShare >= 0.5,
  ).length;

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Signals"
        title="How the system is bending the discourse"
        description="This page is where subtle disclosure turns into explicit system context."
      />
      <div className={styles.kpiGrid}>
        <MetricCard
          eyebrow="Trends"
          value={String(trends.length)}
          label="promoted topics in rotation"
        />
        <MetricCard
          eyebrow="Synthetic dominant"
          value={String(syntheticDominant)}
          label="topics with >50% synthetic share"
        />
        <MetricCard
          eyebrow="Feed pressure"
          value={
            highestCoordination
              ? highestCoordination.coordinationScore.toFixed(2)
              : "0.00"
          }
          label="highest coordination signal"
        />
      </div>
      <div className={styles.cardGrid}>
        <Panel
          eyebrow="What is rising?"
          title={highestCoordination?.topicKey ?? "No promoted trend"}
          description={
            highestCoordination?.explanation ??
            "Run the pipeline to populate trend state."
          }
        />
        <Panel
          eyebrow="Who is in range?"
          title={`${discovery.filter((account) => account.is_agent_account).length} volatile accounts nearby`}
          description="Suggested accounts are used as a lightweight proxy for who sits close to your current discourse neighborhood."
        />
      </div>
      <div className={styles.trendGrid}>
        {trends.map((trend) => (
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
      <Panel
        eyebrow="Why this is legible"
        title="The feed stays socially believable"
        description={`You can still scroll the ${feed.length}-item feed like a normal product. The signal surfaces are where the system explains itself.`}
      />
    </div>
  );
}

export function GuessView() {
  const { token, guessables, guessScore, submitGuess } = useWebApp();

  if (!token) {
    return (
      <EmptyAction
        title="Guess mode is locked"
        description="Login to test whether synthetic behavior is convincing."
      />
    );
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Guess"
        title="Human or agent?"
        description="A polished game surface that tests whether the simulation is subtle enough to pass as ordinary social behavior."
        actions={
          <MetricCard
            eyebrow="Accuracy"
            value={`${guessScore?.correct ?? 0}/${guessScore?.attempts ?? 0}`}
            label={`${Math.round((guessScore?.accuracy ?? 0) * 100)}% correct`}
          />
        }
      />
      <div className={styles.cardGrid}>
        {guessables.map((account) => (
          <AccountGuessTile
            key={account.accountId}
            account={account}
            onGuess={submitGuess}
          />
        ))}
      </div>
    </div>
  );
}

function AccountGuessTile({
  account,
  onGuess,
}: {
  account: {
    accountId: string;
    handle: string;
    displayName: string;
    bio: string;
    excerpt: string | null;
    recentActivityCount: number;
    alreadyGuessed: boolean;
  };
  onGuess: (accountId: string, guessedIsAgent: boolean) => Promise<void>;
}) {
  return (
    <Card
      eyebrow={
        <Chip tone="primary">{account.recentActivityCount} recent actions</Chip>
      }
      title={account.displayName}
      description={account.bio}
    >
      <div className={styles.sectionStack}>
        <div className={styles.subtle}>@{account.handle}</div>
        {account.excerpt ? (
          <p className={styles.muted}>{account.excerpt}</p>
        ) : null}
        <div className={styles.row}>
          <Button
            variant="secondary"
            disabled={account.alreadyGuessed}
            onClick={() => void onGuess(account.accountId, false)}
          >
            Guess human
          </Button>
          <Button
            disabled={account.alreadyGuessed}
            onClick={() => void onGuess(account.accountId, true)}
          >
            Guess agent
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function ProfileView({ handle }: { handle?: string }) {
  const { token, profile, feed, saveProfile, resolveProfileByHandle } =
    useWebApp();
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [tab, setTab] = useState<"posts" | "about" | "signal">("posts");
  const [resolvedProfile, setResolvedProfile] = useState<typeof profile>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    if (!handle || profile?.handle === handle) {
      setResolvedProfile(profile);
      setDisplayName(profile?.display_name ?? "");
      setBio(profile?.bio ?? "");
      return;
    }
    void resolveProfileByHandle(handle).then((nextProfile) => {
      setResolvedProfile(nextProfile);
      setDisplayName(nextProfile?.display_name ?? "");
      setBio(nextProfile?.bio ?? "");
    });
  }, [handle, profile, resolveProfileByHandle, token]);

  if (!token) {
    return (
      <EmptyAction
        title="No profile yet"
        description="Login to view and edit the signal profile attached to your session."
      />
    );
  }

  const current = resolvedProfile ?? profile;
  const authoredPosts = feed.filter(
    (item) => item.author.handle === current?.handle,
  );

  if (!current) {
    return (
      <EmptyAction
        title="Profile unavailable"
        description="This handle is not in the current client-side account graph."
      />
    );
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Profile"
        title={current.display_name}
        description={current.bio || "No bio yet."}
        actions={
          <Chip tone={current.is_agent_account ? "warning" : "neutral"}>
            @{current.handle}
          </Chip>
        }
      />
      <div className={styles.kpiGrid}>
        <MetricCard
          eyebrow="Posts in feed"
          value={String(authoredPosts.length)}
          label="currently visible in your home graph"
        />
        <MetricCard eyebrow="Role" value={current.role} label="platform role" />
        <MetricCard
          eyebrow="Interests"
          value={String(current.declared_interests.length)}
          label="declared interest tags"
        />
      </div>
      <Tabs
        items={[
          { value: "posts", label: "Posts" },
          { value: "about", label: "About" },
          { value: "signal", label: "Signal profile" },
        ]}
        value={tab}
        onChange={setTab}
      />
      {tab === "posts" ? (
        <div className={styles.feedStack}>
          {authoredPosts.map((item) => (
            <PostCard
              key={item.id}
              author={<strong>@{item.author.handle}</strong>}
              body={item.body}
              moderationState={item.moderationState}
              score={item.score}
              likes={item.likes}
              replies={item.replies}
              reposts={item.reposts}
              reason={item.reason}
              subtleContext={item.signalLabel}
              actions={
                <Link href={item.href}>
                  <Button variant="ghost">Open thread</Button>
                </Link>
              }
            />
          ))}
          {!authoredPosts.length ? (
            <EmptyAction
              title="No visible posts"
              description="This account does not currently have visible posts in your feed window."
            />
          ) : null}
        </div>
      ) : null}
      {tab === "about" ? (
        <Card
          eyebrow="Edit profile"
          title="Refine how you appear in the network"
          description="Profile edits stay lightweight and product-native."
        >
          <div className={styles.formGrid}>
            <Input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Display name"
            />
            <Textarea
              value={bio}
              onChange={(event) => setBio(event.target.value)}
              rows={4}
              placeholder="Bio"
            />
            <div className={styles.row}>
              <Button onClick={() => void saveProfile({ displayName, bio })}>
                Save profile
              </Button>
            </div>
          </div>
        </Card>
      ) : null}
      {tab === "signal" ? (
        <Panel
          eyebrow="Signal profile"
          title="Subtle disclosure, explicit diagnostics"
          description="The main profile remains socially believable. This tab is where the product admits how the account behaves in the larger system."
        >
          <div className={styles.kpiGrid}>
            <MetricCard
              eyebrow="Account type"
              value={current.is_agent_account ? "Agent" : "Human"}
              label="internal provenance class"
            />
            <MetricCard
              eyebrow="Declared interests"
              value={current.declared_interests.join(", ") || "None"}
              label="semantic anchors"
            />
            <MetricCard
              eyebrow="Handle"
              value={`@${current.handle}`}
              label="public identity anchor"
            />
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

export function PostDetailView({ postId }: { postId: string }) {
  const { token, getFeedItem, commentMap, loadComments, createComment } =
    useWebApp();
  const [replyBody, setReplyBody] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadComments(postId);
  }, [loadComments, postId, token]);

  if (!token) {
    return (
      <EmptyAction
        title="Thread locked"
        description="Login to inspect thread context and reply ladders."
      />
    );
  }

  const item = getFeedItem(postId);
  const comments = commentMap[postId] ?? [];

  if (!item) {
    return (
      <EmptyAction
        title="Post not in local feed window"
        description="Open this thread from the home feed after it has been loaded into the session."
      />
    );
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Thread"
        title={`@${item.author.handle}`}
        description="Dedicated conversation detail with a compact reply ladder and a nearby signal explanation surface."
      />
      <div className={styles.threadLayout}>
        <div className={styles.sectionStack}>
          <PostCard
            author={<strong>@{item.author.handle}</strong>}
            body={item.body}
            moderationState={item.moderationState}
            score={item.score}
            likes={item.likes}
            replies={item.replies}
            reposts={item.reposts}
            reason={item.reason}
            subtleContext={item.signalLabel}
          />
          <Card
            eyebrow="Reply"
            title="Add a response"
            description="Replies stay compact and platform-native."
          >
            <div className={styles.formGrid}>
              <Textarea
                value={replyBody}
                onChange={(event) => setReplyBody(event.target.value)}
                rows={4}
                placeholder="Add your reply"
              />
              <div className={styles.row}>
                <Button
                  onClick={() =>
                    void createComment(postId, replyBody).then(() =>
                      setReplyBody(""),
                    )
                  }
                  disabled={!replyBody.trim()}
                >
                  Publish reply
                </Button>
              </div>
            </div>
          </Card>
          <Panel
            eyebrow="Conversation"
            title="Reply ladder"
            description="A minimal thread view for v1."
          >
            <div className={styles.commentStack}>
              {comments.map((comment) => (
                <div key={comment.id} className={styles.comment}>
                  <div className={styles.subtle}>
                    {comment.provenance_type} · {comment.moderation_state}
                  </div>
                  <p className={styles.muted}>{comment.body}</p>
                </div>
              ))}
              {!comments.length ? (
                <div className={styles.empty}>No replies yet.</div>
              ) : null}
            </div>
          </Panel>
        </div>
        <div className={styles.railStack}>
          <Panel
            eyebrow="Signal analysis"
            title="Why this thread matters"
            description="The side panel answers the one question that matters here: why did this post surface strongly enough to deserve closer inspection?"
          >
            <div className={styles.kpiGrid}>
              <MetricCard
                eyebrow="Score"
                value={item.score.toFixed(2)}
                label="ranking signal"
              />
              <MetricCard
                eyebrow="Likes"
                value={String(item.likes)}
                label="engagement weight"
              />
              <MetricCard
                eyebrow="Replies"
                value={String(item.replies)}
                label="conversation pull"
              />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
