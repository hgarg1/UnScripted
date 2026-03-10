"use client";

import type { AuthResponse, ModerationSignal } from "@unscripted/contracts";
import { StatusCard } from "@unscripted/ui";
import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SESSION_STORAGE_KEY = "unscripted.admin.session";

type Agent = {
  id: string;
  user_id: string;
  handle: string;
  display_name: string;
  archetype: string;
  persona_prompt_ref: string;
  primary_cohort_id: string | null;
  faction_id: string | null;
  influence_score: number;
  state: string;
  last_active_at: string | null;
  budget_state: Record<string, unknown>;
  memory_count: number;
};

type AgentCohort = {
  id: string;
  name: string;
  description: string;
  scenario: string;
  state: string;
};

type AgentPrompt = {
  id: string;
  name: string;
  version: number;
  system_prompt: string;
  is_active: boolean;
};

type AgentMemory = {
  id: string;
  memory_type: string;
  summary: string;
  importance_score: number;
};

type AgentTurnLog = {
  id: string;
  action: string;
  confidence: number;
  reason: string;
  generated_text: string | null;
  created_at: string;
};

type DatasetManifest = {
  id: string;
  model_name: string;
  dataset_ref: string;
  row_count: number;
  provenance_policy: string;
};

type ModelVersion = {
  id: string;
  model_name: string;
  task_type: string;
  registry_state: string;
  feature_set_version: string;
  metrics_json: Record<string, number | string>;
};

type TrendSnapshot = {
  id: string;
  topic_key: string;
  volume: number;
  synthetic_share: number;
  coordination_score: number;
  promoted: boolean;
};

type InferenceLog = {
  id: string;
  task_type: string;
  subject_type: string;
  subject_id: string;
  decision_path: string;
  created_at: string;
};

type ObservabilityMetric = {
  key: string;
  value: number;
  label: string;
};

type ProvenanceSlice = {
  scope: string;
  human: number;
  agent: number;
  mixed: number;
  system: number;
};

type RolloutState = {
  registry_state: string;
  count: number;
};

type FactionDetail = {
  id: string;
  name: string;
  origin_type: string;
  cohesion_score: number;
  member_count: number;
  avg_influence: number;
  dominant_archetypes: string[];
  sample_handles: string[];
  scenario_mix: string[];
};

type ExperimentRun = {
  id: string;
  name: string;
  scenario_key: string;
  state: string;
  target_cohort_id: string | null;
};

type ScenarioInjection = {
  id: string;
  experiment_id: string | null;
  target_cohort_id: string | null;
  injection_type: string;
  state: string;
  payload_json: Record<string, unknown>;
};

type CalibrationSnapshot = {
  id: string;
  model_name: string;
  calibration_json: Record<string, number | string>;
  drift_summary_json: Record<string, number | string>;
};

type ControlPlaneJob = {
  id: string;
  workflow_name: string;
  job_type: string;
  status: string;
  target_ref: string;
  requested_by: string;
  result_json: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
};

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
  const [agents, setAgents] = useState<Agent[]>([]);
  const [cohorts, setCohorts] = useState<AgentCohort[]>([]);
  const [prompts, setPrompts] = useState<AgentPrompt[]>([]);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [trends, setTrends] = useState<TrendSnapshot[]>([]);
  const [inferenceLogs, setInferenceLogs] = useState<InferenceLog[]>([]);
  const [observabilityMetrics, setObservabilityMetrics] = useState<ObservabilityMetric[]>([]);
  const [provenance, setProvenance] = useState<ProvenanceSlice[]>([]);
  const [rollouts, setRollouts] = useState<RolloutState[]>([]);
  const [factions, setFactions] = useState<FactionDetail[]>([]);
  const [experiments, setExperiments] = useState<ExperimentRun[]>([]);
  const [injections, setInjections] = useState<ScenarioInjection[]>([]);
  const [calibrations, setCalibrations] = useState<CalibrationSnapshot[]>([]);
  const [controlPlaneJobs, setControlPlaneJobs] = useState<ControlPlaneJob[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agentMemories, setAgentMemories] = useState<AgentMemory[]>([]);
  const [agentTurns, setAgentTurns] = useState<AgentTurnLog[]>([]);
  const [newAgentHandle, setNewAgentHandle] = useState("signal_room");
  const [newAgentDisplayName, setNewAgentDisplayName] = useState("Signal Room");
  const [newAgentArchetype, setNewAgentArchetype] = useState("contrarian");
  const [newAgentBio, setNewAgentBio] = useState("Newly introduced agent cohort member.");
  const [newPromptName, setNewPromptName] = useState("default-persona");
  const [newPromptBody, setNewPromptBody] = useState("Behave like a persistent account in a synthetic discourse experiment.");
  const [newCohortName, setNewCohortName] = useState("pressure-testers");
  const [newCohortScenario, setNewCohortScenario] = useState("amplification-spike");
  const [newExperimentName, setNewExperimentName] = useState("Escalation Pressure Test");
  const [newExperimentScenario, setNewExperimentScenario] = useState("escalation-pressure");
  const [newInjectionType, setNewInjectionType] = useState("cadence-spike");
  const [newInjectionPayload, setNewInjectionPayload] = useState('{ "multiplier": 1.8 }');
  const [calibrationModelName, setCalibrationModelName] = useState("conversation-escalation");

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
      const [
        nextOverview,
        nextInvites,
        nextSignals,
        nextAgents,
        nextCohorts,
        nextPrompts,
        nextRegistry,
        nextTrends,
        nextLogs,
        nextObservability,
        nextExperiments,
        nextInjections,
        nextCalibrations,
        nextJobs
      ] = await Promise.all([
        apiFetch<{
          total_users: number;
          total_agents: number;
          total_posts: number;
          total_events: number;
          pending_outbox: number;
        }>("/v1/admin/overview", activeToken),
        apiFetch<Array<{ id: string; code: string; role: string; use_count: number }>>("/v1/admin/invite-codes", activeToken),
        apiFetch<{ items: ModerationSignal[] }>("/v1/admin/moderation-signals", activeToken),
        apiFetch<{ items: Agent[] }>("/v1/admin/agents", activeToken),
        apiFetch<AgentCohort[]>("/v1/admin/agent-cohorts", activeToken),
        apiFetch<AgentPrompt[]>("/v1/admin/agent-prompts", activeToken),
        apiFetch<{ datasets: DatasetManifest[]; models: ModelVersion[] }>("/v1/admin/models", activeToken),
        apiFetch<TrendSnapshot[]>("/v1/admin/trends", activeToken),
        apiFetch<InferenceLog[]>("/v1/admin/inference-logs", activeToken),
        apiFetch<{
          metrics: ObservabilityMetric[];
          provenance: ProvenanceSlice[];
          rollouts: RolloutState[];
          factions: FactionDetail[];
        }>("/v1/admin/observability/overview", activeToken),
        apiFetch<ExperimentRun[]>("/v1/admin/experiments", activeToken),
        apiFetch<ScenarioInjection[]>("/v1/admin/scenario-injections", activeToken),
        apiFetch<CalibrationSnapshot[]>("/v1/admin/calibrations", activeToken),
        apiFetch<ControlPlaneJob[]>("/v1/admin/control-plane/jobs", activeToken)
      ]);
      setOverview(nextOverview);
      setInvites(nextInvites);
      setModerationSignals(nextSignals.items);
      setAgents(nextAgents.items);
      setCohorts(nextCohorts);
      setPrompts(nextPrompts);
      setDatasets(nextRegistry.datasets);
      setModels(nextRegistry.models);
      setTrends(nextTrends);
      setInferenceLogs(nextLogs);
      setObservabilityMetrics(nextObservability.metrics);
      setProvenance(nextObservability.provenance);
      setRollouts(nextObservability.rollouts);
      setFactions(nextObservability.factions);
      setExperiments(nextExperiments);
      setInjections(nextInjections);
      setCalibrations(nextCalibrations);
      setControlPlaneJobs(nextJobs);
      if (!selectedAgentId && nextAgents.items.length) {
        setSelectedAgentId(nextAgents.items[0].id);
        void refreshAgentDetail(activeToken, nextAgents.items[0].id);
      }
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "admin refresh failed");
    }
  }

  async function refreshAgentDetail(activeToken: string, agentId: string) {
    if (!agentId) {
      return;
    }
    try {
      const [memories, turns] = await Promise.all([
        apiFetch<{ items: AgentMemory[] }>(`/v1/admin/agents/${agentId}/memories`, activeToken),
        apiFetch<{ items: AgentTurnLog[] }>(`/v1/admin/agents/${agentId}/turns`, activeToken)
      ]);
      setAgentMemories(memories.items);
      setAgentTurns(turns.items);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "agent detail refresh failed");
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

  async function createPrompt() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/agent-prompts", token, {
        method: "POST",
        body: JSON.stringify({
          name: newPromptName,
          system_prompt: newPromptBody,
          planning_notes: "Prefer low-cost actions before high-cost actions.",
          style_guide: "Short, persuasive, platform-native.",
          activate: true
        })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "prompt creation failed");
    }
  }

  async function createCohort() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/agent-cohorts", token, {
        method: "POST",
        body: JSON.stringify({
          name: newCohortName,
          description: "Phase 2 test cohort",
          scenario: newCohortScenario,
          cadence_multiplier: 1.2,
          budget_multiplier: 1.1
        })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "cohort creation failed");
    }
  }

  async function createAgent() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/agents", token, {
        method: "POST",
        body: JSON.stringify({
          handle: newAgentHandle,
          display_name: newAgentDisplayName,
          archetype: newAgentArchetype,
          bio: newAgentBio,
          prompt_version_id: prompts.find((prompt) => prompt.is_active)?.id ?? null,
          cohort_id: cohorts[0]?.id ?? null,
          belief_vector: [0.2, -0.1, 0.5],
          posts_per_day: 4,
          daily_tokens: 5000,
          dm_enabled: false
        })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "agent creation failed");
    }
  }

  async function executeTurn(agentId: string, forceAction?: string) {
    if (!token) {
      return;
    }
    try {
      await apiFetch(`/v1/admin/agents/${agentId}/execute-turn`, token, {
        method: "POST",
        body: JSON.stringify({
          force_action: forceAction ?? null,
          target_topic:
            cohorts.find((cohort) => cohort.id === agents.find((agent) => agent.id === agentId)?.primary_cohort_id)?.scenario ?? null
        })
      });
      await refresh(token);
      await refreshAgentDetail(token, agentId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "agent turn failed");
    }
  }

  async function runPipelineCycle() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/pipeline/run-cycle", token, { method: "POST" });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "pipeline run failed");
    }
  }

  async function rebuildFactionMap() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/factions/rebuild", token, { method: "POST" });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "faction rebuild failed");
    }
  }

  async function createExperiment() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/experiments", token, {
        method: "POST",
        body: JSON.stringify({
          name: newExperimentName,
          scenario_key: newExperimentScenario,
          target_cohort_id: cohorts[0]?.id ?? null,
          configuration_json: { target_model: calibrationModelName },
          start_immediately: true
        })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "experiment creation failed");
    }
  }

  async function createInjection() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/scenario-injections", token, {
        method: "POST",
        body: JSON.stringify({
          experiment_id: experiments[0]?.id ?? null,
          target_cohort_id: cohorts[0]?.id ?? null,
          injection_type: newInjectionType,
          payload_json: JSON.parse(newInjectionPayload),
          apply_now: true
        })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "scenario injection failed");
    }
  }

  async function runCalibration() {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/v1/admin/calibrations/managed-run", token, {
        method: "POST",
        body: JSON.stringify({ model_name: calibrationModelName, include_report: true })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "calibration failed");
    }
  }

  async function runExperimentTick(experimentId: string) {
    if (!token) {
      return;
    }
    try {
      await apiFetch(`/v1/admin/experiments/${experimentId}/tick`, token, {
        method: "POST",
        body: JSON.stringify({ include_followup_report: false })
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "experiment tick failed");
    }
  }

  async function buildAdvancedReport() {
    if (!token) {
      return;
    }
    try {
      await apiFetch(`/v1/admin/evaluations/${calibrationModelName}/advanced-report`, token, {
        method: "POST"
      });
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "advanced evaluation failed");
    }
  }

  return (
    <section style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gap: 16 }}>
      <StatusCard
        eyebrow="Phase 3 admin"
        title="Control plane with pipeline visibility"
        description="The admin surface now manages agents and also exposes model registry, trends, and inference traces."
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

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Phase 4 pipeline"
          title="Run projections and feature updates"
          description="Relay the outbox, consume published events, rebuild trends, refresh faction assignments, and update observability state."
        >
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={runPipelineCycle} disabled={!token}>Run pipeline cycle</button>
            <button onClick={rebuildFactionMap} disabled={!token}>Rebuild factions</button>
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Observability"
          title="Control-plane health"
          description="These metrics expose event flow, inference volume, moderation load, and current synthetic pressure."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {observabilityMetrics.slice(0, 4).map((metric) => (
              <div key={metric.key} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{metric.label}</strong>
                <div style={{ color: "#5f5348" }}>{metric.value.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </StatusCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Invites"
          title="Invite issuance"
          description="Invite-only onboarding still anchors the alpha while the pipeline layer hardens underneath it."
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
          description="Rule-based signals remain visible while model-driven scoring is still isolated to Phase 3 analytics paths."
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Prompts"
          title="Prompt versions"
          description="Seed or revise the prompt set agents use for planning and style."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={newPromptName} onChange={(event) => setNewPromptName(event.target.value)} placeholder="Prompt name" />
            <textarea value={newPromptBody} onChange={(event) => setNewPromptBody(event.target.value)} rows={5} />
            <button onClick={createPrompt} disabled={!token}>Create prompt version</button>
            {prompts.map((prompt) => (
              <div key={prompt.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{prompt.name} v{prompt.version}</strong>
                <div style={{ color: "#5f5348" }}>{prompt.is_active ? "active" : "inactive"}</div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Cohorts"
          title="Agent cohorts"
          description="Cohorts still shape pressure and scenario, while Phase 3 lets you inspect their downstream event signatures."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={newCohortName} onChange={(event) => setNewCohortName(event.target.value)} placeholder="Cohort name" />
            <input value={newCohortScenario} onChange={(event) => setNewCohortScenario(event.target.value)} placeholder="Scenario" />
            <button onClick={createCohort} disabled={!token}>Create cohort</button>
            {cohorts.map((cohort) => (
              <div key={cohort.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{cohort.name}</strong>
                <div style={{ color: "#5f5348" }}>{cohort.scenario}</div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Agents"
          title="Provision new agent"
          description="Create a persistent synthetic account with archetype, budget, prompt, and cohort."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={newAgentHandle} onChange={(event) => setNewAgentHandle(event.target.value)} placeholder="Handle" />
            <input value={newAgentDisplayName} onChange={(event) => setNewAgentDisplayName(event.target.value)} placeholder="Display name" />
            <input value={newAgentArchetype} onChange={(event) => setNewAgentArchetype(event.target.value)} placeholder="Archetype" />
            <textarea value={newAgentBio} onChange={(event) => setNewAgentBio(event.target.value)} rows={4} />
            <button onClick={createAgent} disabled={!token}>Create agent</button>
          </div>
        </StatusCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Experiments"
          title="Run intervention cohorts"
          description="Phase 5 adds explicit experiment objects so injections, calibrations, and reports can be attributed to a scenario."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={newExperimentName} onChange={(event) => setNewExperimentName(event.target.value)} placeholder="Experiment name" />
            <input value={newExperimentScenario} onChange={(event) => setNewExperimentScenario(event.target.value)} placeholder="Scenario key" />
            <button onClick={createExperiment} disabled={!token}>Create experiment</button>
            {experiments.slice(0, 4).map((experiment) => (
              <div key={experiment.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{experiment.name}</strong>
                <div style={{ color: "#5f5348" }}>{experiment.scenario_key} · {experiment.state}</div>
                <button style={{ marginTop: 8 }} onClick={() => void runExperimentTick(experiment.id)} disabled={!token}>
                  Run tick
                </button>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Scenario injection"
          title="Perturb agent cohorts"
          description="Inject belief shifts, cadence spikes, budget boosts, or scenario overrides into a target cohort."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={newInjectionType} onChange={(event) => setNewInjectionType(event.target.value)} placeholder="Injection type" />
            <textarea value={newInjectionPayload} onChange={(event) => setNewInjectionPayload(event.target.value)} rows={4} />
            <button onClick={createInjection} disabled={!token}>Create and apply injection</button>
            {injections.slice(0, 4).map((injection) => (
              <div key={injection.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{injection.injection_type}</strong>
                <div style={{ color: "#5f5348" }}>{injection.state}</div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Calibration"
          title="Micro-batch model tuning"
          description="Run short-window calibration and advanced evaluation reports from live inference logs."
        >
          <div style={{ display: "grid", gap: 12 }}>
            <input value={calibrationModelName} onChange={(event) => setCalibrationModelName(event.target.value)} placeholder="Model name" />
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={runCalibration} disabled={!token}>Run calibration</button>
              <button onClick={buildAdvancedReport} disabled={!token}>Build report</button>
            </div>
            {calibrations.slice(0, 4).map((snapshot) => (
              <div key={snapshot.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{snapshot.model_name}</strong>
                <div style={{ color: "#5f5348" }}>
                  offset {Number(snapshot.calibration_json.offset ?? 0).toFixed(2)} · scale {Number(snapshot.calibration_json.scale ?? 1).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Factions"
          title="Emergent cluster map"
          description="Faction assignments are reconstructed from agent belief vectors and cohort scenario pressure."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {factions.slice(0, 6).map((faction) => (
              <div key={faction.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{faction.name}</strong>
                <div style={{ color: "#5f5348" }}>
                  members {faction.member_count} · cohesion {faction.cohesion_score.toFixed(2)} · influence {faction.avg_influence.toFixed(2)}
                </div>
                <div style={{ color: "#5f5348" }}>
                  archetypes {faction.dominant_archetypes.join(", ") || "none"} · handles {faction.sample_handles.join(", ") || "none"}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Provenance mix"
          title="Human vs agent activity"
          description="The dashboard now exposes how much of the current discourse is human, agent, mixed, or system-origin."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {provenance.map((slice) => (
              <div key={slice.scope} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{slice.scope}</strong>
                <div style={{ color: "#5f5348" }}>
                  human {slice.human} · agent {slice.agent} · mixed {slice.mixed} · system {slice.system}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Rollouts"
          title="Model registry state"
          description="Model rollout state is surfaced directly in admin so canary, active, and shadow footprints are visible."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {rollouts.map((rollout) => (
              <div key={rollout.registry_state} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{rollout.registry_state}</strong>
                <div style={{ color: "#5f5348" }}>{rollout.count} models</div>
              </div>
            ))}
          </div>
        </StatusCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Workflow ops"
          title="Control-plane job ledger"
          description="Managed agent turns, experiment ticks, and calibration runs now persist execution records for worker-facing visibility."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {controlPlaneJobs.slice(0, 6).map((job) => (
              <div key={job.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{job.workflow_name}</strong>
                <div style={{ color: "#5f5348" }}>
                  {job.job_type} · {job.status} · {job.target_ref}
                </div>
                {job.error_message ? <div style={{ color: "#8a3b2e" }}>{job.error_message}</div> : null}
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Runtime"
          title="Agent roster"
          description="Execute turns manually to validate memory updates, budget accounting, and event generation."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {agents.map((agent) => (
              <div key={agent.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <strong>@{agent.handle}</strong>
                    <div style={{ color: "#5f5348" }}>
                      {agent.archetype} · memories {agent.memory_count} · influence {agent.influence_score.toFixed(2)}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedAgentId(agent.id);
                      void refreshAgentDetail(token, agent.id);
                    }}
                  >
                    Inspect
                  </button>
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button onClick={() => void executeTurn(agent.id)}>Run turn</button>
                  <button onClick={() => void executeTurn(agent.id, "post")}>Force post</button>
                  <button onClick={() => void executeTurn(agent.id, "reply")}>Force reply</button>
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Inspection"
          title={selectedAgentId ? "Selected agent detail" : "Select an agent"}
          description="Latest memories and turn logs expose persistent identity and behavior evolution."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {agentMemories.slice(0, 3).map((memory) => (
              <div key={memory.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{memory.memory_type}</strong>
                <div style={{ color: "#5f5348" }}>{memory.summary}</div>
              </div>
            ))}
            {agentTurns.slice(0, 3).map((turn) => (
              <div key={turn.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{turn.action}</strong>
                <div style={{ color: "#5f5348" }}>{turn.reason}</div>
                {turn.generated_text ? <div style={{ color: "#5f5348" }}>{turn.generated_text}</div> : null}
              </div>
            ))}
          </div>
        </StatusCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <StatusCard
          eyebrow="Model registry"
          title="Bootstrap model versions"
          description="Phase 3 seeds feed ranking, ideology embedding, and coordination anomaly models with dataset manifests and evaluations."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {models.map((model) => (
              <div key={model.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{model.model_name}</strong>
                <div style={{ color: "#5f5348" }}>
                  {model.registry_state} · {model.feature_set_version} · quality {Number(model.metrics_json.quality ?? 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Datasets"
          title="Offline manifests"
          description="Every bootstrap model now points at a materialized manifest with provenance policy and row counts."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {datasets.map((dataset) => (
              <div key={dataset.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{dataset.model_name}</strong>
                <div style={{ color: "#5f5348" }}>
                  {dataset.provenance_policy} · rows {dataset.row_count}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>

        <StatusCard
          eyebrow="Inference"
          title="Recent scoring logs"
          description="Feed ranking and anomaly scoring now leave inspectable inference traces in the control plane."
        >
          <div style={{ display: "grid", gap: 12 }}>
            {inferenceLogs.slice(0, 5).map((log) => (
              <div key={log.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <strong>{log.task_type}</strong>
                <div style={{ color: "#5f5348" }}>
                  {log.subject_type} · {log.decision_path}
                </div>
              </div>
            ))}
          </div>
        </StatusCard>
      </div>

      <StatusCard
        eyebrow="Trends"
        title="Synthetic amplification snapshots"
        description="Trend snapshots now expose volume, synthetic share, and coordination score for the latest event windows."
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {trends.slice(0, 6).map((trend) => (
            <div key={trend.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <strong>{trend.topic_key}</strong>
              <div style={{ color: "#5f5348" }}>
                volume {trend.volume} · synthetic {trend.synthetic_share.toFixed(2)} · coordination {trend.coordination_score.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </StatusCard>

      {message ? <StatusCard eyebrow="Status" title="Latest response" description={message} /> : null}
    </section>
  );
}
