import type { ReactNode } from "react";

import { Badge, Button, Chip } from "./primitives";
import { Panel } from "./panels";
import { Sparkline } from "./data-display";
import styles from "./social.module.css";

export function PostCard({
  author,
  body,
  moderationState,
  score,
  likes,
  replies,
  reposts,
  reason,
  actions,
  subtleContext,
}: {
  author: ReactNode;
  body: ReactNode;
  moderationState: string;
  score: number;
  likes: number;
  replies: number;
  reposts?: number;
  reason?: string;
  actions?: ReactNode;
  subtleContext?: ReactNode;
}) {
  return (
    <Panel
      eyebrow={
        <div className={styles.row}>
          <span>{author}</span>
          <Badge>{moderationState}</Badge>
        </div>
      }
      title={subtleContext ?? "Ranked discourse"}
      description={
        reason ??
        "Scored by relevance, relationship strength, and current discourse pressure."
      }
    >
      <div className={styles.stack}>
        <p className={styles.postBody}>{body}</p>
        <div className={styles.meta}>
          <span>score {score.toFixed(2)}</span>
          <span>{likes} likes</span>
          <span>{replies} replies</span>
          {typeof reposts === "number" ? <span>{reposts} reposts</span> : null}
        </div>
        {actions ? <div className={styles.actionRow}>{actions}</div> : null}
      </div>
    </Panel>
  );
}

export function TrendCard({
  topic,
  volume,
  syntheticShare,
  coordinationScore,
  sparkline,
  explanation,
  promoted = true,
}: {
  topic: string;
  volume: number;
  syntheticShare: number;
  coordinationScore: number;
  sparkline: number[];
  explanation: string;
  promoted?: boolean;
}) {
  return (
    <Panel
      className={styles.trendAccent}
      eyebrow={
        <div className={styles.row}>
          <span>{promoted ? "Promoted trend" : "Observed signal"}</span>
          <Chip tone={coordinationScore >= 0.7 ? "warning" : "primary"}>
            {coordinationScore >= 0.7 ? "high coordination" : "rising"}
          </Chip>
        </div>
      }
      title={topic}
      description={explanation}
    >
      <div className={styles.stack}>
        <Sparkline values={sparkline} />
        <div className={styles.signalGrid}>
          <div className={styles.signalStat}>
            <span className={styles.miniLabel}>Volume</span>
            <strong className={styles.largeNumber}>{volume}</strong>
          </div>
          <div className={styles.signalStat}>
            <span className={styles.miniLabel}>Synthetic</span>
            <strong className={styles.largeNumber}>
              {(syntheticShare * 100).toFixed(0)}%
            </strong>
          </div>
          <div className={styles.signalStat}>
            <span className={styles.miniLabel}>Coordination</span>
            <strong className={styles.largeNumber}>
              {coordinationScore.toFixed(2)}
            </strong>
          </div>
        </div>
      </div>
    </Panel>
  );
}

export function AccountCard({
  handle,
  displayName,
  bio,
  badges,
  actions,
  detail,
}: {
  handle: string;
  displayName: string;
  bio: string;
  badges?: ReactNode;
  actions?: ReactNode;
  detail?: ReactNode;
}) {
  return (
    <Panel
      eyebrow={
        <div className={styles.accountHeader}>
          <div className={styles.avatar}>
            {displayName.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <strong>{displayName}</strong>
            <div className={styles.subtle}>@{handle}</div>
          </div>
        </div>
      }
      title={badges ?? "Suggested account"}
      description={bio}
    >
      <div className={styles.stack}>
        {detail ? <div className={styles.muted}>{detail}</div> : null}
        {actions ? <div className={styles.actionRow}>{actions}</div> : null}
      </div>
    </Panel>
  );
}

export function SignalCard({
  title,
  description,
  metrics,
}: {
  title: string;
  description: string;
  metrics: Array<{ label: string; value: string }>;
}) {
  return (
    <Panel eyebrow="Signal" title={title} description={description}>
      <div className={styles.signalGrid}>
        {metrics.map((metric) => (
          <div key={metric.label} className={styles.signalStat}>
            <span className={styles.miniLabel}>{metric.label}</span>
            <strong className={styles.largeNumber}>{metric.value}</strong>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function GuessCard({
  handle,
  displayName,
  bio,
  excerpt,
  score,
  onGuessHuman,
  onGuessAgent,
  disabled,
}: {
  handle: string;
  displayName: string;
  bio: string;
  excerpt?: string | null;
  score: string;
  onGuessHuman?: () => void;
  onGuessAgent?: () => void;
  disabled?: boolean;
}) {
  return (
    <Panel
      className={styles.guessCard}
      eyebrow="Guessing game"
      title={displayName}
      description={bio}
    >
      <div className={styles.stack}>
        <div className={styles.meta}>
          <span>@{handle}</span>
          <span>{score}</span>
        </div>
        {excerpt ? <p className={styles.postBody}>{excerpt}</p> : null}
        <div className={styles.actionRow}>
          <Button
            variant="secondary"
            disabled={disabled}
            onClick={onGuessHuman}
          >
            Guess human
          </Button>
          <Button disabled={disabled} onClick={onGuessAgent}>
            Guess agent
          </Button>
        </div>
      </div>
    </Panel>
  );
}

export function JobCard({
  workflow,
  status,
  target,
  error,
  action,
}: {
  workflow: string;
  status: string;
  target: string;
  error?: string | null;
  action?: ReactNode;
}) {
  return (
    <Panel eyebrow="Control plane" title={workflow} description={target}>
      <div className={styles.jobRow}>
        <div className={styles.stack}>
          <Chip
            tone={
              status === "completed"
                ? "success"
                : status === "failed"
                  ? "danger"
                  : "warning"
            }
          >
            {status}
          </Chip>
          {error ? <div className={styles.subtle}>{error}</div> : null}
        </div>
        {action}
      </div>
    </Panel>
  );
}

export function EmptyAction({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Panel eyebrow="Next move" title={title} description={description}>
      {action ? <div className={styles.actionRow}>{action}</div> : null}
    </Panel>
  );
}
