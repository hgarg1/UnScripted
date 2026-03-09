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

CREATE TABLE IF NOT EXISTS agent_cohorts (
  id varchar(36) PRIMARY KEY,
  name varchar(120) NOT NULL UNIQUE,
  description text NOT NULL,
  scenario varchar(120) NOT NULL,
  state varchar(32) NOT NULL,
  cadence_multiplier double precision NOT NULL,
  budget_multiplier double precision NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS factions (
  id varchar(36) PRIMARY KEY,
  name varchar(120) NOT NULL UNIQUE,
  origin_type varchar(32) NOT NULL,
  belief_centroid jsonb NOT NULL,
  cohesion_score double precision NOT NULL,
  visibility varchar(16) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
  id varchar(36) PRIMARY KEY,
  account_user_id varchar(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  archetype varchar(64) NOT NULL,
  persona_prompt_ref varchar(255) NOT NULL,
  primary_cohort_id varchar(36) REFERENCES agent_cohorts(id) ON DELETE SET NULL,
  faction_id varchar(36) REFERENCES factions(id) ON DELETE SET NULL,
  belief_vector jsonb NOT NULL,
  influence_score double precision NOT NULL,
  cadence_policy jsonb NOT NULL,
  budget_policy jsonb NOT NULL,
  budget_state jsonb NOT NULL,
  safety_policy jsonb NOT NULL,
  state varchar(32) NOT NULL,
  last_active_at timestamptz,
  last_memory_compacted_at timestamptz
);

CREATE TABLE IF NOT EXISTS agent_prompt_versions (
  id varchar(36) PRIMARY KEY,
  name varchar(120) NOT NULL,
  version integer NOT NULL,
  system_prompt text NOT NULL,
  planning_notes text NOT NULL,
  style_guide text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL,
  UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS agent_memories (
  id varchar(36) PRIMARY KEY,
  agent_id varchar(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  memory_type varchar(32) NOT NULL,
  summary text NOT NULL,
  metadata_json jsonb NOT NULL,
  importance_score double precision NOT NULL,
  last_used_at timestamptz,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_cohort_memberships (
  id varchar(36) PRIMARY KEY,
  cohort_id varchar(36) NOT NULL REFERENCES agent_cohorts(id) ON DELETE CASCADE,
  agent_id varchar(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  role varchar(32) NOT NULL,
  joined_at timestamptz NOT NULL,
  UNIQUE (cohort_id, agent_id)
);

CREATE TABLE IF NOT EXISTS agent_turn_logs (
  id varchar(36) PRIMARY KEY,
  agent_id varchar(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  action varchar(32) NOT NULL,
  confidence double precision NOT NULL,
  reason text NOT NULL,
  generated_text text,
  status varchar(32) NOT NULL,
  token_cost integer NOT NULL,
  output_ref_type varchar(32),
  output_ref_id varchar(36),
  created_at timestamptz NOT NULL
);
