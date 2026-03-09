CREATE TABLE IF NOT EXISTS users (
  id varchar(36) PRIMARY KEY,
  auth_subject varchar(255) NOT NULL UNIQUE,
  handle varchar(40) NOT NULL UNIQUE,
  display_name varchar(120) NOT NULL,
  email_hash varchar(128) NOT NULL,
  status varchar(20) NOT NULL,
  role varchar(32) NOT NULL,
  consent_version varchar(32) NOT NULL,
  is_agent_account boolean NOT NULL DEFAULT false,
  invite_code_id varchar(36),
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
  account_id varchar(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  bio text NOT NULL,
  avatar_url varchar(512),
  declared_interests jsonb NOT NULL,
  location_hint varchar(120),
  visibility_flags jsonb NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  id varchar(36) PRIMARY KEY,
  author_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body text NOT NULL,
  language varchar(12) NOT NULL,
  topic_embedding jsonb NOT NULL,
  reply_count integer NOT NULL,
  like_count integer NOT NULL,
  repost_count integer NOT NULL,
  quote_post_id varchar(36) REFERENCES posts(id),
  visibility varchar(32) NOT NULL,
  moderation_state varchar(16) NOT NULL DEFAULT 'clear',
  provenance_type varchar(16) NOT NULL,
  actor_origin varchar(16) NOT NULL,
  content_origin varchar(16) NOT NULL,
  lineage_root_origin varchar(16) NOT NULL,
  generator_model_version varchar(120),
  scenario_id varchar(64),
  contains_synthetic_ancestry boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
  id varchar(36) PRIMARY KEY,
  post_id varchar(36) NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  parent_comment_id varchar(36) REFERENCES comments(id) ON DELETE CASCADE,
  author_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body text NOT NULL,
  depth integer NOT NULL,
  like_count integer NOT NULL,
  moderation_state varchar(16) NOT NULL DEFAULT 'clear',
  provenance_type varchar(16) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS follows (
  follower_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followed_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL,
  state varchar(16) NOT NULL,
  source varchar(32) NOT NULL,
  PRIMARY KEY (follower_account_id, followed_account_id)
);

CREATE TABLE IF NOT EXISTS dms (
  id varchar(36) PRIMARY KEY,
  thread_id varchar(72) NOT NULL,
  sender_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  recipient_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body text NOT NULL,
  delivery_state varchar(16) NOT NULL,
  moderation_state varchar(16) NOT NULL DEFAULT 'clear',
  provenance_type varchar(16) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS invite_codes (
  id varchar(36) PRIMARY KEY,
  code varchar(64) NOT NULL UNIQUE,
  created_by_user_id varchar(36) REFERENCES users(id) ON DELETE SET NULL,
  role varchar(32) NOT NULL,
  metadata_json jsonb NOT NULL,
  max_uses integer NOT NULL,
  use_count integer NOT NULL,
  expires_at timestamptz,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS session_tokens (
  id varchar(36) PRIMARY KEY,
  user_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash varchar(128) NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL,
  last_used_at timestamptz,
  revoked_at timestamptz
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id varchar(36) PRIMARY KEY,
  actor_id varchar(36) NOT NULL,
  key varchar(128) NOT NULL,
  request_hash varchar(128) NOT NULL,
  response_json jsonb NOT NULL,
  status_code integer NOT NULL,
  created_at timestamptz NOT NULL,
  UNIQUE (actor_id, key)
);

CREATE TABLE IF NOT EXISTS events (
  event_id varchar(36) PRIMARY KEY,
  aggregate_type varchar(64) NOT NULL,
  aggregate_id varchar(72) NOT NULL,
  actor_type varchar(32) NOT NULL,
  actor_id varchar(36) NOT NULL,
  event_type varchar(64) NOT NULL,
  event_version integer NOT NULL,
  causation_id varchar(36),
  correlation_id varchar(36),
  trace_id varchar(64),
  occurred_at timestamptz NOT NULL,
  payload_json jsonb NOT NULL,
  provenance_type varchar(16) NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_messages (
  id varchar(36) PRIMARY KEY,
  event_id varchar(36) NOT NULL UNIQUE REFERENCES events(event_id) ON DELETE CASCADE,
  stream_name varchar(128) NOT NULL,
  payload_json jsonb NOT NULL,
  status varchar(16) NOT NULL,
  attempts integer NOT NULL,
  last_error text,
  available_at timestamptz NOT NULL,
  published_at timestamptz
);
