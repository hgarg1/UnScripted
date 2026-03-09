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

CREATE TABLE IF NOT EXISTS feature_snapshots (
  id varchar(36) PRIMARY KEY,
  entity_type varchar(32) NOT NULL,
  entity_id varchar(36) NOT NULL,
  feature_set varchar(64) NOT NULL,
  feature_version varchar(32) NOT NULL,
  observed_at timestamptz NOT NULL,
  features_json jsonb NOT NULL,
  source_window varchar(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS consumer_checkpoints (
  consumer_name varchar(64) PRIMARY KEY,
  last_event_id varchar(36),
  last_outbox_id varchar(36),
  last_event_at timestamptz,
  processed_count integer NOT NULL,
  metadata_json jsonb NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_manifests (
  id varchar(36) PRIMARY KEY,
  model_name varchar(120) NOT NULL,
  dataset_ref varchar(255) NOT NULL UNIQUE,
  provenance_policy varchar(64) NOT NULL,
  feature_set_version varchar(32) NOT NULL,
  row_count integer NOT NULL,
  status varchar(32) NOT NULL,
  manifest_json jsonb NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
  id varchar(36) PRIMARY KEY,
  model_name varchar(120) NOT NULL,
  task_type varchar(64) NOT NULL,
  registry_state varchar(32) NOT NULL,
  artifact_uri varchar(512) NOT NULL,
  feature_set_version varchar(32) NOT NULL,
  training_dataset_ref varchar(255) NOT NULL,
  metrics_json jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  promoted_at timestamptz
);

CREATE TABLE IF NOT EXISTS model_evaluations (
  id varchar(36) PRIMARY KEY,
  model_version_id varchar(36) NOT NULL REFERENCES model_versions(id) ON DELETE CASCADE,
  dataset_ref varchar(255) NOT NULL,
  eval_type varchar(64) NOT NULL,
  metrics_json jsonb NOT NULL,
  decision varchar(32) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS inference_logs (
  id varchar(36) PRIMARY KEY,
  model_version_id varchar(36) REFERENCES model_versions(id) ON DELETE SET NULL,
  task_type varchar(64) NOT NULL,
  subject_type varchar(32) NOT NULL,
  subject_id varchar(36) NOT NULL,
  request_features_ref varchar(255) NOT NULL,
  prediction_json jsonb NOT NULL,
  latency_ms integer NOT NULL,
  decision_path varchar(255) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS trend_snapshots (
  id varchar(36) PRIMARY KEY,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  topic_key varchar(120) NOT NULL,
  volume integer NOT NULL,
  velocity double precision NOT NULL,
  synthetic_share double precision NOT NULL,
  coordination_score double precision NOT NULL,
  promoted boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS moderation_signals (
  id varchar(36) PRIMARY KEY,
  content_type varchar(32) NOT NULL,
  content_id varchar(36) NOT NULL,
  signal_type varchar(64) NOT NULL,
  score double precision NOT NULL,
  source varchar(64) NOT NULL,
  status varchar(32) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_feature_snapshots_entity_feature_observed_at
  ON feature_snapshots(entity_type, entity_id, feature_set, observed_at);

CREATE INDEX IF NOT EXISTS ix_dataset_manifests_model_created_at
  ON dataset_manifests(model_name, created_at);

CREATE INDEX IF NOT EXISTS ix_model_versions_name_registry_state
  ON model_versions(model_name, registry_state);

CREATE INDEX IF NOT EXISTS ix_model_evaluations_model_version_created_at
  ON model_evaluations(model_version_id, created_at);

CREATE INDEX IF NOT EXISTS ix_inference_logs_model_version_created_at
  ON inference_logs(model_version_id, created_at);

CREATE INDEX IF NOT EXISTS ix_inference_logs_subject_created_at
  ON inference_logs(subject_type, subject_id, created_at);

CREATE INDEX IF NOT EXISTS ix_trend_snapshots_window_promoted
  ON trend_snapshots(window_end, promoted);

CREATE INDEX IF NOT EXISTS ix_trend_snapshots_topic_window
  ON trend_snapshots(topic_key, window_end);

CREATE INDEX IF NOT EXISTS ix_moderation_signals_content
  ON moderation_signals(content_type, content_id);

CREATE INDEX IF NOT EXISTS ix_moderation_signals_status_created_at
  ON moderation_signals(status, created_at);

CREATE TABLE IF NOT EXISTS guess_game_guesses (
  id varchar(36) PRIMARY KEY,
  user_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_account_id varchar(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  guessed_is_agent boolean NOT NULL,
  was_correct boolean NOT NULL,
  created_at timestamptz NOT NULL,
  UNIQUE (user_id, target_account_id)
);

CREATE INDEX IF NOT EXISTS ix_guess_game_guesses_user_created_at
  ON guess_game_guesses(user_id, created_at);

CREATE INDEX IF NOT EXISTS ix_guess_game_guesses_target_created_at
  ON guess_game_guesses(target_account_id, created_at);
