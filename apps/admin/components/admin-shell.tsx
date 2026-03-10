"use client";

import {
  AppShell,
  Badge,
  Button,
  Chip,
  Input,
  NavLink,
  Panel,
  Sidebar,
  Topbar,
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

import styles from "./admin-shell.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SESSION_STORAGE_KEY = "unscripted.admin.session";

export type Agent = {
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

export type AgentCohort = {
  id: string;
  name: string;
  description: string;
  scenario: string;
  state: string;
};

export type AgentPrompt = {
  id: string;
  name: string;
  version: number;
  system_prompt: string;
  is_active: boolean;
};

export type AgentMemory = {
  id: string;
  memory_type: string;
  summary: string;
  importance_score: number;
};

export type AgentTurnLog = {
  id: string;
  action: string;
  confidence: number;
  reason: string;
  generated_text: string | null;
  created_at: string;
};

export type DatasetManifest = {
  id: string;
  model_name: string;
  dataset_ref: string;
  row_count: number;
  provenance_policy: string;
};

export type ModelVersion = {
  id: string;
  model_name: string;
  task_type: string;
  registry_state: string;
  feature_set_version: string;
  metrics_json: Record<string, number | string>;
};

export type TrendSnapshot = {
  id: string;
  topic_key: string;
  volume: number;
  synthetic_share: number;
  coordination_score: number;
  promoted: boolean;
};

export type InferenceLog = {
  id: string;
  task_type: string;
  subject_type: string;
  subject_id: string;
  decision_path: string;
  created_at: string;
};

export type ModerationSignal = {
  id: string;
  content_type: string;
  content_id: string;
  signal_type: string;
  score: number;
  source: string;
  status: string;
  created_at: string;
};

export type ObservabilityMetric = {
  key: string;
  value: number;
  label: string;
};

export type ProvenanceSlice = {
  scope: string;
  human: number;
  agent: number;
  mixed: number;
  system: number;
};

export type RolloutState = {
  registry_state: string;
  count: number;
};

export type FactionDetail = {
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

export type ExperimentRun = {
  id: string;
  name: string;
  scenario_key: string;
  state: string;
  target_cohort_id: string | null;
};

export type ScenarioInjection = {
  id: string;
  experiment_id: string | null;
  target_cohort_id: string | null;
  injection_type: string;
  state: string;
  payload_json: Record<string, unknown>;
};

export type CalibrationSnapshot = {
  id: string;
  model_name: string;
  calibration_json: Record<string, number | string>;
  drift_summary_json: Record<string, number | string>;
};

export type ControlPlaneJob = {
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

type Flash = {
  title: string;
  description: string;
  tone: "info" | "success" | "warning" | "danger";
} | null;

type AdminState = {
  token: string;
  hasHydrated: boolean;
  flash: Flash;
  overview: {
    total_users: number;
    total_agents: number;
    total_posts: number;
    total_events: number;
    pending_outbox: number;
  } | null;
  invites: Array<{ id: string; code: string; role: string; use_count: number }>;
  moderationSignals: ModerationSignal[];
  agents: Agent[];
  cohorts: AgentCohort[];
  prompts: AgentPrompt[];
  datasets: DatasetManifest[];
  models: ModelVersion[];
  trends: TrendSnapshot[];
  inferenceLogs: InferenceLog[];
  observabilityMetrics: ObservabilityMetric[];
  provenance: ProvenanceSlice[];
  rollouts: RolloutState[];
  factions: FactionDetail[];
  experiments: ExperimentRun[];
  injections: ScenarioInjection[];
  calibrations: CalibrationSnapshot[];
  controlPlaneJobs: ControlPlaneJob[];
  selectedAgentId: string;
  agentMemories: AgentMemory[];
  agentTurns: AgentTurnLog[];
  login: (values: { handle: string; displayName: string }) => Promise<void>;
  refresh: () => Promise<void>;
  createInvite: () => Promise<void>;
  createPrompt: (values: { name: string; body: string }) => Promise<void>;
  createCohort: (values: { name: string; scenario: string }) => Promise<void>;
  createAgent: (values: {
    handle: string;
    displayName: string;
    archetype: string;
    bio: string;
  }) => Promise<void>;
  executeTurn: (agentId: string, forceAction?: string) => Promise<void>;
  dispatchAgents: () => Promise<void>;
  runPipelineCycle: () => Promise<void>;
  rebuildFactionMap: () => Promise<void>;
  createExperiment: (values: {
    name: string;
    scenario: string;
    modelName: string;
  }) => Promise<void>;
  createInjection: (values: { type: string; payload: string }) => Promise<void>;
  runCalibration: (modelName: string) => Promise<void>;
  runExperimentTick: (experimentId: string) => Promise<void>;
  buildAdvancedReport: (modelName: string) => Promise<void>;
  inspectAgent: (agentId: string) => Promise<void>;
  clearFlash: () => void;
};

const AdminContext = createContext<AdminState | null>(null);

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
    throw new Error(await response.text());
  }

  return (await response.json()) as T;
}

export function AdminProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState("");
  const [hasHydrated, setHasHydrated] = useState(false);
  const [flash, setFlash] = useState<Flash>(null);
  const [overview, setOverview] = useState<AdminState["overview"]>(null);
  const [invites, setInvites] = useState<
    Array<{ id: string; code: string; role: string; use_count: number }>
  >([]);
  const [moderationSignals, setModerationSignals] = useState<
    ModerationSignal[]
  >([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [cohorts, setCohorts] = useState<AgentCohort[]>([]);
  const [prompts, setPrompts] = useState<AgentPrompt[]>([]);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [trends, setTrends] = useState<TrendSnapshot[]>([]);
  const [inferenceLogs, setInferenceLogs] = useState<InferenceLog[]>([]);
  const [observabilityMetrics, setObservabilityMetrics] = useState<
    ObservabilityMetric[]
  >([]);
  const [provenance, setProvenance] = useState<ProvenanceSlice[]>([]);
  const [rollouts, setRollouts] = useState<RolloutState[]>([]);
  const [factions, setFactions] = useState<FactionDetail[]>([]);
  const [experiments, setExperiments] = useState<ExperimentRun[]>([]);
  const [injections, setInjections] = useState<ScenarioInjection[]>([]);
  const [calibrations, setCalibrations] = useState<CalibrationSnapshot[]>([]);
  const [controlPlaneJobs, setControlPlaneJobs] = useState<ControlPlaneJob[]>(
    [],
  );
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agentMemories, setAgentMemories] = useState<AgentMemory[]>([]);
  const [agentTurns, setAgentTurns] = useState<AgentTurnLog[]>([]);

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
        nextJobs,
      ] = await Promise.all([
        apiFetch<NonNullable<AdminState["overview"]>>(
          "/v1/admin/overview",
          activeToken,
        ),
        apiFetch<
          Array<{ id: string; code: string; role: string; use_count: number }>
        >("/v1/admin/invite-codes", activeToken),
        apiFetch<{ items: ModerationSignal[] }>(
          "/v1/admin/moderation-signals",
          activeToken,
        ),
        apiFetch<{ items: Agent[] }>("/v1/admin/agents", activeToken),
        apiFetch<AgentCohort[]>("/v1/admin/agent-cohorts", activeToken),
        apiFetch<AgentPrompt[]>("/v1/admin/agent-prompts", activeToken),
        apiFetch<{ datasets: DatasetManifest[]; models: ModelVersion[] }>(
          "/v1/admin/models",
          activeToken,
        ),
        apiFetch<TrendSnapshot[]>("/v1/admin/trends", activeToken),
        apiFetch<InferenceLog[]>("/v1/admin/inference-logs", activeToken),
        apiFetch<{
          metrics: ObservabilityMetric[];
          provenance: ProvenanceSlice[];
          rollouts: RolloutState[];
          factions: FactionDetail[];
        }>("/v1/admin/observability/overview", activeToken),
        apiFetch<ExperimentRun[]>("/v1/admin/experiments", activeToken),
        apiFetch<ScenarioInjection[]>(
          "/v1/admin/scenario-injections",
          activeToken,
        ),
        apiFetch<CalibrationSnapshot[]>("/v1/admin/calibrations", activeToken),
        apiFetch<ControlPlaneJob[]>(
          "/v1/admin/control-plane/jobs",
          activeToken,
        ),
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
        const nextAgentId = nextAgents.items[0].id;
        setSelectedAgentId(nextAgentId);
        await refreshAgentDetail(activeToken, nextAgentId);
      }
      setFlash(null);
    } catch (error) {
      setFlash({
        title: "Admin refresh failed",
        description:
          error instanceof Error
            ? error.message
            : "unable to refresh admin state",
        tone: "danger",
      });
    }
  }

  async function refreshAgentDetail(activeToken: string, agentId: string) {
    const [memories, turns] = await Promise.all([
      apiFetch<{ items: AgentMemory[] }>(
        `/v1/admin/agents/${agentId}/memories`,
        activeToken,
      ),
      apiFetch<{ items: AgentTurnLog[] }>(
        `/v1/admin/agents/${agentId}/turns`,
        activeToken,
      ),
    ]);
    setAgentMemories(memories.items);
    setAgentTurns(turns.items);
  }

  async function login(values: { handle: string; displayName: string }) {
    try {
      const response = await fetch(`${API_BASE_URL}/v1/auth/invite-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: "ADMIN-ROOT",
          handle: values.handle,
          display_name: values.displayName,
          bio: "Controls the synthetic discourse environment.",
          consent_version: "v1",
        }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as { session: { token: string } };
      window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session.token);
      setToken(payload.session.token);
      await refreshAll(payload.session.token);
    } catch (error) {
      setFlash({
        title: "Admin login failed",
        description:
          error instanceof Error
            ? error.message
            : "unable to open admin console",
        tone: "danger",
      });
    }
  }

  async function refresh() {
    if (!token) {
      return;
    }
    await refreshAll(token);
  }

  async function createInvite() {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/invite-codes", token, {
      method: "POST",
      body: JSON.stringify({
        role: "member",
        max_uses: 25,
        expires_in_hours: 168,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function createPrompt(values: { name: string; body: string }) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/agent-prompts", token, {
      method: "POST",
      body: JSON.stringify({
        name: values.name,
        system_prompt: values.body,
        planning_notes: "Prefer low-cost actions before high-cost actions.",
        style_guide: "Short, persuasive, platform-native.",
        activate: true,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function createCohort(values: { name: string; scenario: string }) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/agent-cohorts", token, {
      method: "POST",
      body: JSON.stringify({
        name: values.name,
        description: "Scenario-driven synthetic cohort",
        scenario: values.scenario,
        cadence_multiplier: 1.2,
        budget_multiplier: 1.1,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function createAgent(values: {
    handle: string;
    displayName: string;
    archetype: string;
    bio: string;
  }) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/agents", token, {
      method: "POST",
      body: JSON.stringify({
        handle: values.handle,
        display_name: values.displayName,
        archetype: values.archetype,
        bio: values.bio,
        prompt_version_id:
          prompts.find((prompt) => prompt.is_active)?.id ?? null,
        cohort_id: cohorts[0]?.id ?? null,
        belief_vector: [0.2, -0.1, 0.5],
        posts_per_day: 4,
        daily_tokens: 5000,
        dm_enabled: false,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function executeTurn(agentId: string, forceAction?: string) {
    if (!token) {
      return;
    }
    await apiFetch(`/v1/admin/agents/${agentId}/execute-turn`, token, {
      method: "POST",
      body: JSON.stringify({
        force_action: forceAction ?? null,
        target_topic:
          cohorts.find(
            (cohort) =>
              cohort.id ===
              agents.find((agent) => agent.id === agentId)?.primary_cohort_id,
          )?.scenario ?? null,
      }),
    });
    await refreshAll(token);
    await refreshAgentDetail(token, agentId);
  }

  async function dispatchAgents() {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/agents/dispatch", token, {
      method: "POST",
      body: JSON.stringify({ limit: 5 }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function runPipelineCycle() {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/pipeline/run-cycle", token, { method: "POST" });
    startTransition(() => void refreshAll(token));
  }

  async function rebuildFactionMap() {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/factions/rebuild", token, { method: "POST" });
    startTransition(() => void refreshAll(token));
  }

  async function createExperiment(values: {
    name: string;
    scenario: string;
    modelName: string;
  }) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/experiments", token, {
      method: "POST",
      body: JSON.stringify({
        name: values.name,
        scenario_key: values.scenario,
        target_cohort_id: cohorts[0]?.id ?? null,
        configuration_json: { target_model: values.modelName },
        start_immediately: true,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function createInjection(values: { type: string; payload: string }) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/scenario-injections", token, {
      method: "POST",
      body: JSON.stringify({
        experiment_id: experiments[0]?.id ?? null,
        target_cohort_id: cohorts[0]?.id ?? null,
        injection_type: values.type,
        payload_json: JSON.parse(values.payload),
        apply_now: true,
      }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function runCalibration(modelName: string) {
    if (!token) {
      return;
    }
    await apiFetch("/v1/admin/calibrations/managed-run", token, {
      method: "POST",
      body: JSON.stringify({ model_name: modelName, include_report: true }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function runExperimentTick(experimentId: string) {
    if (!token) {
      return;
    }
    await apiFetch(`/v1/admin/experiments/${experimentId}/tick`, token, {
      method: "POST",
      body: JSON.stringify({ include_followup_report: false }),
    });
    startTransition(() => void refreshAll(token));
  }

  async function buildAdvancedReport(modelName: string) {
    if (!token) {
      return;
    }
    await apiFetch(
      `/v1/admin/evaluations/${modelName}/advanced-report`,
      token,
      { method: "POST" },
    );
    startTransition(() => void refreshAll(token));
  }

  async function inspectAgent(agentId: string) {
    if (!token) {
      return;
    }
    setSelectedAgentId(agentId);
    await refreshAgentDetail(token, agentId);
  }

  return (
    <AdminContext.Provider
      value={{
        token,
        hasHydrated,
        flash,
        overview,
        invites,
        moderationSignals,
        agents,
        cohorts,
        prompts,
        datasets,
        models,
        trends,
        inferenceLogs,
        observabilityMetrics,
        provenance,
        rollouts,
        factions,
        experiments,
        injections,
        calibrations,
        controlPlaneJobs,
        selectedAgentId,
        agentMemories,
        agentTurns,
        login,
        refresh,
        createInvite,
        createPrompt,
        createCohort,
        createAgent,
        executeTurn,
        dispatchAgents,
        runPipelineCycle,
        rebuildFactionMap,
        createExperiment,
        createInjection,
        runCalibration,
        runExperimentTick,
        buildAdvancedReport,
        inspectAgent,
        clearFlash: () => setFlash(null),
      }}
    >
      {children}
    </AdminContext.Provider>
  );
}

export function useAdminApp() {
  const context = useContext(AdminContext);
  if (!context) {
    throw new Error("useAdminApp must be used within AdminProvider");
  }
  return context;
}

export function AdminConsoleShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { token, hasHydrated, flash, clearFlash, overview } = useAdminApp();
  const navItems: Array<{ href: Route; label: string }> = [
    { href: "/" as Route, label: "Overview" },
    { href: "/agents" as Route, label: "Agents" },
    { href: "/experiments" as Route, label: "Experiments" },
    { href: "/trends" as Route, label: "Trends" },
    { href: "/factions" as Route, label: "Factions" },
    { href: "/models" as Route, label: "Models" },
    { href: "/moderation" as Route, label: "Moderation" },
    { href: "/jobs" as Route, label: "Jobs" },
  ];

  return (
    <AppShell
      sidebar={
        <Sidebar
          brand={
            <div>
              <div>UnScripted Control</div>
              <div className={styles.subtle}>research + operations console</div>
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
          footer="Dense operational surface built from the same product design system."
        />
      }
      topbar={
        <Topbar
          left={
            <div className={styles.row}>
              <Badge>admin</Badge>
              <Badge>{hasHydrated && token ? "authenticated" : "guest"}</Badge>
            </div>
          }
          right={
            <div className={styles.row}>
              <Input
                aria-label="Admin search placeholder"
                placeholder="Search coming later"
                value=""
                readOnly
              />
              {overview ? (
                <Chip tone="primary">
                  {overview.pending_outbox} outbox pending
                </Chip>
              ) : null}
            </div>
          }
        />
      }
      insight={
        <div className={styles.cluster}>
          <Panel
            eyebrow="Control plane"
            title="Live system status"
            description="The right rail stays compact and operational while the main column handles dense workflows."
          >
            <div className={styles.list}>
              <div className={styles.listItem}>event flow visible</div>
              <div className={styles.listItem}>model state inspectable</div>
              <div className={styles.listItem}>agent cohorts controllable</div>
            </div>
          </Panel>
        </div>
      }
      mobileNav={
        <>
          {navItems.slice(0, 5).map((item) => (
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
