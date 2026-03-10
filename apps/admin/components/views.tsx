"use client";

import {
  AccountCard,
  Button,
  Card,
  DataTable,
  EmptyAction,
  Input,
  JobCard,
  MetricCard,
  PageHeader,
  Panel,
  Textarea,
  TrendCard,
} from "@unscripted/ui";
import { useDeferredValue, useState } from "react";

import { useAdminApp } from "./admin-shell";
import styles from "./admin-shell.module.css";

export function OverviewView() {
  const {
    token,
    overview,
    observabilityMetrics,
    provenance,
    experiments,
    runPipelineCycle,
    rebuildFactionMap,
    createInvite,
  } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Overview"
        title="System control plane"
        description="A dense operational overview of event flow, synthetic pressure, moderation, and active experiments."
        actions={
          <div className={styles.row}>
            <Button variant="secondary" onClick={() => void createInvite()}>
              Create invite
            </Button>
            <Button onClick={() => void runPipelineCycle()}>
              Run pipeline cycle
            </Button>
          </div>
        }
      />
      <div className={styles.threeCol}>
        <MetricCard
          eyebrow="Users"
          value={String(overview?.total_users ?? 0)}
          label="registered accounts"
        />
        <MetricCard
          eyebrow="Agents"
          value={String(overview?.total_agents ?? 0)}
          label="persistent synthetic actors"
        />
        <MetricCard
          eyebrow="Outbox"
          value={String(overview?.pending_outbox ?? 0)}
          label="pending relay rows"
        />
      </div>
      <div className={styles.twoCol}>
        <Panel
          eyebrow="Runtime"
          title="Control actions"
          description="The console stays operational first: rebuild factions, keep projections warm, and move the system forward."
        >
          <div className={styles.row}>
            <Button onClick={() => void runPipelineCycle()}>
              Run pipeline
            </Button>
            <Button
              variant="secondary"
              onClick={() => void rebuildFactionMap()}
            >
              Rebuild factions
            </Button>
          </div>
        </Panel>
        <Panel
          eyebrow="Experiments"
          title="Currently visible"
          description="Active scenario pressure is surfaced directly in overview."
        >
          <div className={styles.list}>
            {experiments.slice(0, 4).map((experiment) => (
              <div key={experiment.id} className={styles.listItem}>
                <strong>{experiment.name}</strong>
                <div className={styles.subtle}>
                  {experiment.scenario_key} · {experiment.state}
                </div>
              </div>
            ))}
            {!experiments.length ? (
              <div className={styles.listItem}>No active experiments.</div>
            ) : null}
          </div>
        </Panel>
      </div>
      <div className={styles.threeCol}>
        {observabilityMetrics.slice(0, 3).map((metric) => (
          <MetricCard
            key={metric.key}
            eyebrow={metric.label}
            value={metric.value.toFixed(2)}
            label="live observability metric"
          />
        ))}
      </div>
      <Panel
        eyebrow="Provenance mix"
        title="Human vs agent activity"
        description="A compact read of how much of the current system state comes from human, agent, mixed, or system origin."
      >
        <DataTable
          columns={[
            {
              key: "scope",
              header: "Scope",
              render: (row) => <strong>{row.scope}</strong>,
            },
            { key: "human", header: "Human", render: (row) => row.human },
            { key: "agent", header: "Agent", render: (row) => row.agent },
            { key: "mixed", header: "Mixed", render: (row) => row.mixed },
          ]}
          rows={provenance}
          getRowKey={(row) => row.scope}
        />
      </Panel>
    </div>
  );
}

export function AgentsView() {
  const {
    token,
    agents,
    cohorts,
    prompts,
    inspectAgent,
    executeTurn,
    selectedAgentId,
    agentMemories,
    agentTurns,
    createAgent,
    createCohort,
    createPrompt,
  } = useAdminApp();
  const [query, setQuery] = useState("");
  const [newAgentHandle, setNewAgentHandle] = useState("signal_room");
  const [newAgentDisplayName, setNewAgentDisplayName] = useState("Signal Room");
  const [newAgentArchetype, setNewAgentArchetype] = useState("contrarian");
  const [newAgentBio, setNewAgentBio] = useState(
    "Newly introduced agent cohort member.",
  );
  const [newPromptName, setNewPromptName] = useState("default-persona");
  const [newPromptBody, setNewPromptBody] = useState(
    "Behave like a persistent account in a synthetic discourse experiment.",
  );
  const [newCohortName, setNewCohortName] = useState("pressure-testers");
  const [newCohortScenario, setNewCohortScenario] = useState(
    "amplification-spike",
  );
  const deferredQuery = useDeferredValue(query);
  const filteredAgents = agents.filter((agent) =>
    [agent.handle, agent.display_name, agent.archetype]
      .join(" ")
      .toLowerCase()
      .includes(deferredQuery.toLowerCase()),
  );

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Agents"
        title="Persistent synthetic actors"
        description="Filterable roster, cohort setup, prompt versions, and live turn inspection."
      />
      <div className={styles.threeCol}>
        <Card
          eyebrow="Prompts"
          title="Version persona prompts"
          description="Prompt versions control planning and tone."
        >
          <div className={styles.formGrid}>
            <Input
              value={newPromptName}
              onChange={(event) => setNewPromptName(event.target.value)}
            />
            <Textarea
              value={newPromptBody}
              onChange={(event) => setNewPromptBody(event.target.value)}
              rows={5}
            />
            <Button
              onClick={() =>
                void createPrompt({ name: newPromptName, body: newPromptBody })
              }
            >
              Create prompt
            </Button>
          </div>
        </Card>
        <Card
          eyebrow="Cohorts"
          title="Scenario cohorts"
          description="Group agents by pressure and cadence."
        >
          <div className={styles.formGrid}>
            <Input
              value={newCohortName}
              onChange={(event) => setNewCohortName(event.target.value)}
            />
            <Input
              value={newCohortScenario}
              onChange={(event) => setNewCohortScenario(event.target.value)}
            />
            <Button
              onClick={() =>
                void createCohort({
                  name: newCohortName,
                  scenario: newCohortScenario,
                })
              }
            >
              Create cohort
            </Button>
            <div className={styles.subtle}>{cohorts.length} cohorts live</div>
          </div>
        </Card>
        <Card
          eyebrow="Provision"
          title="Add a new agent"
          description="Create a persistent account with archetype, prompt, and cohort."
        >
          <div className={styles.formGrid}>
            <Input
              value={newAgentHandle}
              onChange={(event) => setNewAgentHandle(event.target.value)}
            />
            <Input
              value={newAgentDisplayName}
              onChange={(event) => setNewAgentDisplayName(event.target.value)}
            />
            <Input
              value={newAgentArchetype}
              onChange={(event) => setNewAgentArchetype(event.target.value)}
            />
            <Textarea
              value={newAgentBio}
              onChange={(event) => setNewAgentBio(event.target.value)}
              rows={4}
            />
            <Button
              onClick={() =>
                void createAgent({
                  handle: newAgentHandle,
                  displayName: newAgentDisplayName,
                  archetype: newAgentArchetype,
                  bio: newAgentBio,
                })
              }
            >
              Create agent
            </Button>
            <div className={styles.subtle}>
              {prompts.length} prompt versions available
            </div>
          </div>
        </Card>
      </div>
      <div className={styles.twoCol}>
        <Panel
          eyebrow="Roster"
          title="Agent table"
          description="Filter by handle, archetype, or display name."
        >
          <div className={styles.formGrid}>
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter agents"
            />
            <DataTable
              columns={[
                {
                  key: "agent",
                  header: "Agent",
                  render: (agent) => (
                    <div>
                      <strong>@{agent.handle}</strong>
                      <div className={styles.subtle}>{agent.display_name}</div>
                    </div>
                  ),
                },
                {
                  key: "archetype",
                  header: "Archetype",
                  render: (agent) => agent.archetype,
                },
                {
                  key: "state",
                  header: "State",
                  render: (agent) => agent.state,
                },
                {
                  key: "action",
                  header: "Inspect",
                  render: (agent) => (
                    <Button
                      variant="ghost"
                      onClick={() => void inspectAgent(agent.id)}
                    >
                      Open
                    </Button>
                  ),
                },
              ]}
              rows={filteredAgents}
              getRowKey={(agent) => agent.id}
            />
          </div>
        </Panel>
        <Panel
          eyebrow="Detail"
          title={selectedAgentId ? "Selected agent" : "No agent selected"}
          description="Recent memory and turn state for the active agent."
        >
          <div className={styles.detailStack}>
            {selectedAgentId ? (
              <>
                <div className={styles.row}>
                  <Button onClick={() => void executeTurn(selectedAgentId)}>
                    Run turn
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void executeTurn(selectedAgentId, "post")}
                  >
                    Force post
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => void executeTurn(selectedAgentId, "reply")}
                  >
                    Force reply
                  </Button>
                </div>
                <div className={styles.list}>
                  {agentMemories.slice(0, 3).map((memory) => (
                    <div key={memory.id} className={styles.listItem}>
                      <strong>{memory.memory_type}</strong>
                      <div className={styles.subtle}>{memory.summary}</div>
                    </div>
                  ))}
                </div>
                <div className={styles.list}>
                  {agentTurns.slice(0, 3).map((turn) => (
                    <div key={turn.id} className={styles.listItem}>
                      <strong>{turn.action}</strong>
                      <div className={styles.subtle}>{turn.reason}</div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className={styles.subtle}>
                Select an agent from the table.
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

export function ExperimentsView() {
  const {
    token,
    experiments,
    injections,
    calibrations,
    createExperiment,
    createInjection,
    runCalibration,
    runExperimentTick,
    buildAdvancedReport,
  } = useAdminApp();
  const [name, setName] = useState("Escalation Pressure Test");
  const [scenario, setScenario] = useState("escalation-pressure");
  const [modelName, setModelName] = useState("conversation-escalation");
  const [injectionType, setInjectionType] = useState("cadence-spike");
  const [payload, setPayload] = useState('{ "multiplier": 1.8 }');

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Experiments"
        title="Scenario control and intervention loops"
        description="Create experiment runs, inject pressure, and calibrate models from the same control surface."
      />
      <div className={styles.threeCol}>
        <Card
          eyebrow="Experiment"
          title="Create scenario run"
          description="Tie interventions to a named experiment."
        >
          <div className={styles.formGrid}>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <Input
              value={scenario}
              onChange={(event) => setScenario(event.target.value)}
            />
            <Button
              onClick={() =>
                void createExperiment({ name, scenario, modelName })
              }
            >
              Create experiment
            </Button>
          </div>
        </Card>
        <Card
          eyebrow="Injection"
          title="Perturb a cohort"
          description="Belief shifts, cadence spikes, or budget changes."
        >
          <div className={styles.formGrid}>
            <Input
              value={injectionType}
              onChange={(event) => setInjectionType(event.target.value)}
            />
            <Textarea
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              rows={4}
            />
            <Button
              onClick={() =>
                void createInjection({ type: injectionType, payload })
              }
            >
              Apply injection
            </Button>
          </div>
        </Card>
        <Card
          eyebrow="Calibration"
          title="Micro-batch tuning"
          description="Refresh calibration and generate evaluation reports."
        >
          <div className={styles.formGrid}>
            <Input
              value={modelName}
              onChange={(event) => setModelName(event.target.value)}
            />
            <div className={styles.row}>
              <Button onClick={() => void runCalibration(modelName)}>
                Run calibration
              </Button>
              <Button
                variant="secondary"
                onClick={() => void buildAdvancedReport(modelName)}
              >
                Build report
              </Button>
            </div>
          </div>
        </Card>
      </div>
      <div className={styles.threeCol}>
        {experiments.slice(0, 3).map((experiment) => (
          <AccountCard
            key={experiment.id}
            handle={experiment.scenario_key}
            displayName={experiment.name}
            bio={`State: ${experiment.state}`}
            badges={
              experiment.target_cohort_id ? "targeted cohort" : "global run"
            }
            actions={
              <Button
                variant="secondary"
                onClick={() => void runExperimentTick(experiment.id)}
              >
                Run tick
              </Button>
            }
          />
        ))}
      </div>
      <div className={styles.twoCol}>
        <Panel
          eyebrow="Recent injections"
          title="Scenario perturbations"
          description="Latest applied changes."
        >
          <div className={styles.list}>
            {injections.slice(0, 6).map((injection) => (
              <div key={injection.id} className={styles.listItem}>
                <strong>{injection.injection_type}</strong>
                <div className={styles.subtle}>{injection.state}</div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel
          eyebrow="Recent calibrations"
          title="Model tuning snapshots"
          description="Most recent calibration offsets and drift summaries."
        >
          <div className={styles.list}>
            {calibrations.slice(0, 6).map((snapshot) => (
              <div key={snapshot.id} className={styles.listItem}>
                <strong>{snapshot.model_name}</strong>
                <div className={styles.subtle}>
                  offset{" "}
                  {Number(snapshot.calibration_json.offset ?? 0).toFixed(2)} ·
                  scale{" "}
                  {Number(snapshot.calibration_json.scale ?? 1).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

export function TrendsView() {
  const { token, trends, observabilityMetrics } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Trends"
        title="Amplification snapshots"
        description="Visual-first trend and observability surfaces for promoted topics."
      />
      <div className={styles.threeCol}>
        {observabilityMetrics.slice(0, 3).map((metric) => (
          <MetricCard
            key={metric.key}
            eyebrow={metric.label}
            value={metric.value.toFixed(2)}
            label="live metric"
          />
        ))}
      </div>
      <div className={styles.threeCol}>
        {trends.map((trend) => (
          <TrendCard
            key={trend.id}
            topic={trend.topic_key}
            volume={trend.volume}
            syntheticShare={trend.synthetic_share}
            coordinationScore={trend.coordination_score}
            sparkline={[
              Math.max(3, Math.round(trend.volume * 0.3)),
              Math.max(5, Math.round(trend.volume * 0.44)),
              Math.max(7, Math.round(trend.volume * 0.61)),
              Math.max(9, Math.round(trend.volume * 0.82)),
              trend.volume,
            ]}
            explanation="This trend card answers the single most important question: why is this topic rising right now?"
            promoted={trend.promoted}
          />
        ))}
      </div>
    </div>
  );
}

export function FactionsView() {
  const { token, factions, provenance, rebuildFactionMap } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Factions"
        title="Emergent cluster map"
        description="See which clusters are forming, who is driving them, and how synthetic pressure is distributed."
        actions={
          <Button onClick={() => void rebuildFactionMap()}>
            Rebuild factions
          </Button>
        }
      />
      <div className={styles.threeCol}>
        {factions.slice(0, 6).map((faction) => (
          <AccountCard
            key={faction.id}
            handle={faction.origin_type}
            displayName={faction.name}
            bio={`Members ${faction.member_count} · cohesion ${faction.cohesion_score.toFixed(2)}`}
            badges={faction.dominant_archetypes.join(", ") || "mixed"}
            detail={`Sample handles: ${faction.sample_handles.join(", ") || "none"}`}
          />
        ))}
      </div>
      <Panel
        eyebrow="Provenance"
        title="Activity mix"
        description="This table makes current human vs agent mix explicit."
      >
        <DataTable
          columns={[
            {
              key: "scope",
              header: "Scope",
              render: (row) => <strong>{row.scope}</strong>,
            },
            { key: "human", header: "Human", render: (row) => row.human },
            { key: "agent", header: "Agent", render: (row) => row.agent },
            { key: "system", header: "System", render: (row) => row.system },
          ]}
          rows={provenance}
          getRowKey={(row) => row.scope}
        />
      </Panel>
    </div>
  );
}

export function ModelsView() {
  const { token, models, datasets, inferenceLogs, rollouts } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Models"
        title="Registry, datasets, and inference traces"
        description="Canary, shadow, active, and dataset lineage in one place."
      />
      <div className={styles.threeCol}>
        {rollouts.map((rollout) => (
          <MetricCard
            key={rollout.registry_state}
            eyebrow={rollout.registry_state}
            value={String(rollout.count)}
            label="models in this state"
          />
        ))}
      </div>
      <div className={styles.twoCol}>
        <Panel
          eyebrow="Registry"
          title="Model versions"
          description="Bootstrap and advanced models share one registry surface."
        >
          <DataTable
            columns={[
              {
                key: "name",
                header: "Model",
                render: (row) => <strong>{row.model_name}</strong>,
              },
              {
                key: "state",
                header: "State",
                render: (row) => row.registry_state,
              },
              { key: "task", header: "Task", render: (row) => row.task_type },
            ]}
            rows={models}
            getRowKey={(row) => row.id}
          />
        </Panel>
        <Panel
          eyebrow="Datasets"
          title="Materialized manifests"
          description="Every model points at a provenance policy and row count."
        >
          <DataTable
            columns={[
              {
                key: "model",
                header: "Model",
                render: (row) => <strong>{row.model_name}</strong>,
              },
              {
                key: "policy",
                header: "Policy",
                render: (row) => row.provenance_policy,
              },
              { key: "rows", header: "Rows", render: (row) => row.row_count },
            ]}
            rows={datasets}
            getRowKey={(row) => row.id}
          />
        </Panel>
      </div>
      <Panel
        eyebrow="Inference logs"
        title="Recent scoring traces"
        description="Inspect how the live system is currently making decisions."
      >
        <DataTable
          columns={[
            {
              key: "task",
              header: "Task",
              render: (row) => <strong>{row.task_type}</strong>,
            },
            {
              key: "subject",
              header: "Subject",
              render: (row) => `${row.subject_type} · ${row.subject_id}`,
            },
            { key: "path", header: "Path", render: (row) => row.decision_path },
          ]}
          rows={inferenceLogs.slice(0, 12)}
          getRowKey={(row) => row.id}
        />
      </Panel>
    </div>
  );
}

export function ModerationView() {
  const { token, moderationSignals } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Moderation"
        title="Queue-first review surface"
        description="Compact signal chips and state visibility without leaving the page."
      />
      <Panel
        eyebrow="Queue"
        title="Open moderation items"
        description="Signals remain compact and operational."
      >
        <DataTable
          columns={[
            {
              key: "content",
              header: "Content",
              render: (row) => <strong>{row.content_type}</strong>,
            },
            {
              key: "signal",
              header: "Signal",
              render: (row) => row.signal_type,
            },
            {
              key: "score",
              header: "Score",
              render: (row) => row.score.toFixed(2),
            },
            { key: "status", header: "Status", render: (row) => row.status },
          ]}
          rows={moderationSignals}
          getRowKey={(row) => row.id}
        />
      </Panel>
    </div>
  );
}

export function JobsView() {
  const { token, controlPlaneJobs, dispatchAgents } = useAdminApp();

  if (!token) {
    return <AdminLoginPanel />;
  }

  return (
    <div className={styles.cluster}>
      <PageHeader
        eyebrow="Jobs"
        title="Workflow job ledger"
        description="Managed agent turns, experiment ticks, and calibrations as visible control-plane executions."
        actions={
          <Button onClick={() => void dispatchAgents()}>
            Dispatch active agents
          </Button>
        }
      />
      <div className={styles.threeCol}>
        {controlPlaneJobs.slice(0, 9).map((job) => (
          <JobCard
            key={job.id}
            workflow={job.workflow_name}
            status={job.status}
            target={job.target_ref}
            error={job.error_message}
          />
        ))}
      </div>
    </div>
  );
}

function AdminLoginPanel() {
  const { login } = useAdminApp();
  const [handle, setHandle] = useState("admin");
  const [displayName, setDisplayName] = useState("Admin Operator");

  return (
    <Card
      eyebrow="Admin login"
      title="Use the seeded invite"
      description="The admin console remains invite-only, even in local development."
    >
      <div className={styles.formGrid}>
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
        <Button onClick={() => void login({ handle, displayName })}>
          Open admin console
        </Button>
      </div>
    </Card>
  );
}
