# automated-incident-triage-pipeline: Requirements and Module Breakdown

Oct 25, 2026 · @Bilawal

## Overview

Incident Copilot is an event-driven agent that investigates AWS alarms the way an on-call engineer would, then reports to Slack and Jira and pauses for human approval before any risky step.

An alarm says what crossed a threshold, not why. The first stretch of every incident goes to pulling logs, checking metrics and hunting for recent changes by hand. The agent does that legwork and hands the engineer a ranked root-cause hypothesis with evidence attached.

**Portfolio goals**

- Show event-driven AWS design where reliability matters: alarms arrive in bursts and must never be lost.
- Show an agent workflow with real branching, a retry loop and a human approval gate.
- Show that LLM behavior is tested like code: traces for debugging, a golden incident set, and an eval gate in CI.
- Show routine DevOps practice: containers, CI/CD and infrastructure defined as code.

**Done looks like:** one command makes the chaos Lambda fail, and with no manual steps a Slack report and a Jira ticket appear, both linking to the LangSmith trace. A prompt change that lowers root-cause accuracy fails the CI build.

## Scope

The agent investigates and proposes but never changes infrastructure, which keeps its AWS permissions read-only and the project small enough to explain in full.

**In scope**

- One AWS account and region, with a chaos Lambda that can fail in several ways: exception, timeout, throttling, slow downstream call.
- Alarm-driven trigger only: a CloudWatch alarm entering the ALARM state.
- Read-only evidence tools: CloudWatch Logs, CloudWatch metrics and recent Lambda version changes.
- A small set of runbooks, written as markdown files, that the agent can look up.
- Slack and Jira as outputs, with Slack buttons for human approval.
- A golden incident set and an eval run that CI can fail on.

**Out of scope**

- Auto-remediation. Humans carry out the proposed steps.
- Multi-agent swarms. One graph with several nodes is enough to explain.
- Kubernetes. One container on a managed service is easier to defend.
- A vector database cluster. With a handful of runbooks, a small local index is enough.
- Multi-account or multi-region setups, a custom web UI, and model fine-tuning.

**Stretch goals, only after the core works:** feedback buttons on the Slack report, and a small page showing past incidents and eval scores.

## Functional requirements

Fourteen requirements are Must or Should; the last one is a stretch. Must items make the demo work, Should items make it production-minded.

| ID | Requirement | Priority |
| --- | --- | --- |
| FR1 | Receive CloudWatch alarm state changes through EventBridge and place each one on an SQS queue. | Must |
| FR2 | Retry failed processing, and move a message to a dead-letter queue after a set number of attempts. | Must |
| FR3 | Treat repeated events for the same alarm within a time window as one incident. | Should |
| FR4 | Classify severity (P1 to P3) from alarm metadata and the first evidence. | Must |
| FR5 | Gather evidence with read-only tools: recent logs, metric history, recent Lambda version changes. | Must |
| FR6 | If evidence is too thin, gather more, up to a fixed iteration cap. | Must |
| FR7 | Produce ranked root-cause hypotheses, each with a confidence level and the evidence that supports it. | Must |
| FR8 | Look up matching runbook sections and use them to ground the remediation steps. | Should |
| FR9 | Propose ordered remediation steps, each tagged low risk or high risk. | Must |
| FR10 | Pause on high-risk steps until a human approves in Slack; the paused run survives a service restart. | Must |
| FR11 | Post a Slack report with severity, root cause, evidence and steps. | Must |
| FR12 | Create a Jira ticket with the same content and a link to the trace; a retry must not create a duplicate. | Must |
| FR13 | Trace every run in LangSmith, tagged with the alarm name and a run ID. | Must |
| FR14 | Provide one command that replays the golden incident set and prints a scored report. | Must |
| FR15 | Record thumbs up or down on the Slack report for later eval data. | Could |

## Architecture

An alarm is queued before the agent ever sees it, and inside the agent a graph decides what to look at next, when to stop, and when to wait for a person.

**System flow**

&#91;embedded content: system flow · 5 pipeline steps, 1 agent service\]

The agent reads AWS data but never changes it, and a message that keeps failing ends in the dead-letter queue instead of looping.

**Investigation graph**

&#91;embedded content: investigation graph · 8 steps, 2 decisions, 1 pause\]

A run loops back to gather more evidence until it has enough or reaches the cap, and at the cap the report says the evidence was limited. Only a run with a high-risk step waits for approval, and a rejected step is marked as rejected in the report.

## Modules

Eleven modules, each with one job, so you can build and test them one at a time and explain each in a sentence.

| # | Module | Responsibility | Key tech |
| --- | --- | --- | --- |
| M1 | Chaos service | A Lambda that fails on demand in chosen ways; the source of real alarms. | Lambda, CloudWatch |
| M2 | Alarm pipeline | Carries alarm state changes to a durable queue, with retries and a dead-letter queue. | EventBridge, SQS |
| M3 | Agent service | Long-lived container that polls the queue, runs the graph, and serves the approval callback and a health check. | Python, FastAPI, Docker |
| M4 | Investigation graph | The workflow itself: classify, gather evidence, assess, analyze, propose, approve, publish. | LangGraph |
| M5 | Evidence tools | Read-only functions for logs, metrics, recent deploys and runbook search, with output size limits. | boto3 |
| M6 | Model gateway | One interface over Bedrock Claude for the deployed version and Ollama for free local runs; returns schema-checked output. | Bedrock, Ollama, Pydantic |
| M7 | State store | Saves graph checkpoints so a paused run resumes after a restart, plus an incident record per run. | Postgres or DynamoDB |
| M8 | Integrations | Posts to Slack, verifies approval clicks, creates Jira tickets without duplicates. | Slack API, Jira API, Secrets Manager |
| M9 | Observability | Traces each run and logs structured events so any wrong answer can be traced to a step. | LangSmith, CloudWatch |
| M10 | Eval harness | Replays the golden incident set, scores the results, and exits non-zero when quality drops. | LangSmith evals, pytest |
| M11 | Delivery | Builds the image, runs tests and evals, deploys, and defines the infrastructure as code. | Docker, GitHub Actions, SAM or Terraform |

**Two design rules that hold across modules**

- Evidence tools return trimmed, labeled excerpts, not raw log dumps, so prompts stay small and each claim can cite its source.
- Every model call returns a typed object (severity, hypotheses, steps), so a malformed answer fails loudly instead of flowing into Jira.

## Technology justification

Each tool is here because a specific failure happens without it. If you cannot name the failure, cut the tool.

| Technology | Problem it solves | What breaks without it |
| --- | --- | --- |
| EventBridge | Routes only the alarm events you care about, with a rule instead of polling. | You write and run polling code to find alarms. |
| SQS with a dead-letter queue | Absorbs bursts and retries failures; sets aside messages that keep failing. | A traffic spike or a crash silently drops alarms. |
| LangGraph | The investigation branches by severity, loops when evidence is thin, and pauses for approval. | One long prompt cannot loop, branch or wait for a human. |
| Checkpoint store | Saves the run state so an approval that arrives hours later still resumes correctly. | A restart or deploy during a pause loses the run. |
| Typed model output | Forces severity, hypotheses and steps into a fixed shape that code can check. | Malformed text reaches Slack and Jira. |
| LangSmith | Shows every step of a run, so a wrong root cause can be traced to the step that caused it. | You debug by rereading logs and guessing. |
| Golden set with CI eval gate | Catches a prompt or model change that quietly makes answers worse. | Quality drifts and nobody notices until an incident. |
| Secrets Manager | Keeps Slack and Jira credentials out of code and images. | Tokens end up in the repo or the container. |
| Docker | Packages the agent with its dependencies for identical local, CI and cloud runs. | It works on one laptop and fails elsewhere. |
| GitHub Actions | Runs tests and evals on every change, then builds and deploys. | Releases depend on someone remembering the steps. |
| Infrastructure as code | Rebuilds the whole stack from the repo. | The setup lives in console clicks nobody can reproduce. |
| Bedrock with Claude | The model for the deployed version, inside your AWS account and IAM. | You send incident data to a third-party API outside your account. |
| Ollama | Free local model for development and CI smoke tests. | Every debug run costs money and needs network access. |

One honest limit: Ollama models are weaker than Claude, so use them to test plumbing and use Bedrock to judge answer quality.

## Non-functional requirements

The system must lose no alarm, change nothing in AWS, and explain every answer it gives. Each requirement below has a test you can run and show.

| Area | Requirement | How you verify it |
| --- | --- | --- |
| Reliability | Delivery is at-least-once, and publishing is idempotent, so a retry never creates a second ticket. | Send the same alarm twice and confirm one Jira ticket and one Slack report. |
| Reliability | A run waiting for approval survives a restart. | Stop the container while a run is paused, restart it, click approve, and confirm the run finishes. |
| Reliability | A message that keeps failing lands in the dead-letter queue instead of looping forever. | Force a failure and confirm the message appears in the dead-letter queue after the retry limit. |
| Security | The agent's AWS role is read-only; it can read logs and metrics and nothing else. | Review the IAM policy and attempt a write call; it must be denied. |
| Security | Log text is untrusted input. The agent never follows instructions found inside logs, and obvious secrets are redacted before text reaches the model. | Plant an instruction and a fake secret in a log line and check the trace. |
| Security | Tokens live in Secrets Manager, and Slack callbacks are signature-checked. | Search the repo and image for tokens; send a callback with a bad signature and confirm it is rejected. |
| Observability | Every run is traceable from alarm name to LangSmith trace to Jira ticket. | Pick any ticket and reach its trace in one click. |
| Observability | The service reports its own health: runs started, failed, waiting for approval, and run duration. | Check the CloudWatch metrics after a demo run. |
| Cost control | Each run has a cap on loop iterations, tokens and log excerpt size. | Feed a noisy log stream and confirm the run stops at the cap and says so in the report. |
| Latency | The report arrives fast enough to be useful during an incident. | Measure the first ten runs, then set a target; do not guess one now. |
| Maintainability | Modules have typed interfaces and their own tests; dependencies are pinned. | CI runs unit tests per module and builds from a clean checkout. |

## Evaluation strategy

A golden incident set turns "the answer looks right" into a number that CI can check on every change. This is the part of the project that shows you treat model behavior like code.

**Golden set.** Build 15 to 25 incidents with the chaos Lambda, covering each failure mode plus a few ambiguous and misleading cases. For each one, freeze a snapshot of the logs and metrics the agent would have seen, and record the expected severity, the expected root-cause category and the actions a good answer must include.

**Replay from snapshots.** In eval mode the evidence tools read the frozen snapshot instead of calling AWS. Runs become repeatable and cheap, and they work in CI without cloud access.

| Metric | How it is scored | Scored by |
| --- | --- | --- |
| Severity accuracy | Predicted severity equals the expected one. | Rule |
| Root-cause accuracy | Predicted category equals the expected one. | Rule, with a judge for free-text explanations |
| Evidence grounding | Every cited excerpt exists in the snapshot. | Rule |
| Remediation quality | Expected actions are present; forbidden actions are absent. | Rule, with a judge for wording |
| Risk tagging | Every destructive or restarting step is tagged high risk. | Rule |
| Efficiency | Loop iterations and tokens used per run. | Rule |

**CI gate.** A pull request that touches prompts, graph logic or the model setting runs the golden set. The build fails if root-cause accuracy or risk tagging falls below the stored baseline by more than a tolerance. Model output varies between runs, so measure that variation first and set the tolerance from it. Update the baseline only on purpose, in its own commit.

**Check the judge.** If an LLM judge scores free text, compare its verdicts with your own on a sample of cases before trusting it.

The LLM Evaluation playlist and the evaluation chapters of *AI Engineering* map directly onto this section.

## DevOps and deployment

One container, one pipeline and one infrastructure definition, so the whole project can be rebuilt from the repository alone.

**Suggested repository layout**

```text
automated-incident-triage-pipeline/
  infra/            # SAM or Terraform: EventBridge, SQS, DLQ, IAM, secrets, service
  src/
    agent/          # graph, state, prompts
    tools/          # logs, metrics, deploys, runbook search
    models/         # Bedrock and Ollama gateway
    integrations/   # slack, jira
    service/        # FastAPI app and queue worker
  chaos/            # the failing Lambda
  evals/            # golden set, scorers, run_evals.py
  runbooks/         # markdown runbooks the agent can look up
  tests/
  Dockerfile
  .github/workflows/
```

**CI/CD pipeline, in order**

1. Lint and run unit tests for each module.
2. Build the container image.
3. Run the golden set in eval mode; fail the build if quality drops (the eval gate).
4. Push the image to a registry.
5. On merge to the main branch, deploy the infrastructure and the service.

**Environments.** Run locally with Ollama and frozen snapshots, and in one AWS stack named by a stage parameter. A separate production stack adds cost without adding anything an interviewer can learn from.

**Config and secrets.** Slack and Jira tokens come from Secrets Manager at startup. The image holds no credentials, and the stage name arrives as an environment variable.

**Monitor the monitor.** Alarm on dead-letter queue depth above zero and on the agent service's own errors. A triage system that fails silently is worse than none.

**Hosting choice (open).** A container on ECS Fargate fits a long-lived worker that polls the queue and serves the approval callback. A Lambda container image costs less at low volume. See open decisions.

## Build phases

Seven phases, each ending in something you can demo, so you can stop after any phase with a presentable project. No dates yet: set them after phase 1, because AWS setup is your biggest unknown.

| Phase | Build | Done when | New skill |
| --- | --- | --- | --- |
| 1. Plumbing | M1 chaos service, M2 alarm pipeline | Failing the chaos Lambda puts one message on the queue, and a poison message ends in the dead-letter queue. | CloudWatch alarms, EventBridge rules, SQS visibility timeout |
| 2. First agent | M5 tools, M6 model gateway, a straight-line graph (classify, gather, analyze, propose), M9 tracing | An alarm produces a typed report visible as a LangSmith trace. | LangGraph state, structured output, tracing |
| 3. Branch and loop | Evidence assessment loop with a cap, runbook lookup | A thin-evidence case triggers a second gathering round and stops at the cap. | Conditional edges, loop control |
| 4. Output and approval | M7 state store, M8 Slack and Jira | One Slack report and one Jira ticket per alarm; a high-risk step pauses, survives a restart, and resumes on approval. | Checkpointing, interrupts, idempotency |
| 5. Package and ship | M3 service, Dockerfile, CI for lint and tests, first deploy | A merge to main runs the demo in AWS. Infrastructure may still be set up by hand. | Docker, GitHub Actions, ECS or Lambda deploys |
| 6. Eval gate | M10 golden set and scorers, CI gate | A deliberately worsened prompt fails the build. | LLM evaluation, regression testing |
| 7. Codify and polish | Infrastructure as code for the whole stack, README with diagrams, short demo recording | A fresh stack rebuilds from the repo with one command. | SAM or Terraform |

## Risks and open decisions

Five decisions are still open, and hosting is the one that changes the most. Settle it before phase 5; the others can wait until their phase.

**Open decisions**

| Decision | Options | Current lean |
| --- | --- | --- |
| Hosting | Lambda container image with an SQS trigger and API Gateway, or a container on ECS Fargate | Lambda: near-zero idle cost, and SQS retries and dead-letter handling come built in. Fargate shows more operations skill but costs more and adds networking. If you choose Lambda, change M3 from "long-lived container" to "container image run by Lambda". |
| Infrastructure as code | SAM or Terraform | Terraform, because it is the more commonly requested skill and phase 7 isolates the learning. SAM is the faster path. |
| Checkpoint store | Postgres or DynamoDB | Check which store the LangGraph checkpointer packages support well when you reach phase 4. Postgres is the well-trodden path. |
| Jira target | A free Jira Cloud site or a mock server | A free site if one is available when you start; otherwise a mock that records requests. |
| Slack callbacks | API Gateway endpoint, or a tunnel for local work | API Gateway when deployed, a tunnel while developing. Buttons need a public HTTPS address. |

**Risks**

| Risk | Mitigation |
| --- | --- |
| Scope creep | Stop at phase boundaries and keep stretch goals out until phase 7 is done. |
| Bedrock model access is not enabled in your account or region | Request access and confirm the model is available in your region before phase 2. |
| Runaway loops or token use inflate the bill | Iteration, token and log-size caps; an AWS budget alert set before phase 1. |
| Eval results vary from run to run | Measure variance first, repeat each case, and set the gate tolerance from the data. |
| Prompt injection through log text | Treat logs as data, keep tools read-only, redact secrets, and test with a planted instruction. |
| Local models are too weak for tool calling | Use Ollama to test plumbing only, and judge answer quality with Bedrock. |
| Learning LangGraph and AWS at the same time | Phase order separates them: plumbing first, then the agent. |

## Interview narrative

Tell each technology choice as problem, constraint, decision, then show proof. That order keeps any tool from sounding like résumé decoration.

| Story | Problem and constraint | Decision | Proof to show |
| --- | --- | --- | --- |
| Reliability | Alarms arrive in bursts and none may be lost; retries must not duplicate tickets. | SQS with a dead-letter queue, idempotent publishing. | Send one alarm twice; one ticket results. |
| Why a graph | The investigation branches by severity, loops on thin evidence and waits for a human. | LangGraph with a persisted checkpoint store. | A trace showing the loop, and a run resuming after a restart. |
| Safety | The agent must not change production, and logs can contain hostile text. | Read-only role, logs treated as untrusted, approval for risky steps. | A denied write call and a planted-instruction test. |
| Quality | Prompt edits can quietly make answers worse. | Golden incident set with a CI gate. | A build that fails after a deliberately bad prompt change. |
| Operability | The monitoring system can itself fail. | Alarms on dead-letter depth and service errors. | The alarm firing when you break the service on purpose. |

**Questions to prepare for**

- Why not a single prompt? Answer from the Why a graph row.
- How do you know the answers are right? Walk through the golden set, the metrics table and the judge check.
- What happens if the service restarts during an approval? Describe the checkpoint store and resume.
- What would change at much higher volume? Group related alarms, cap concurrent runs and rate-limit model calls. Be clear that the demo targets one account.
- What does one incident cost? Read tokens from the traces and multiply by the model's price; quote the measured figure, never a guess.
- What did you leave out, and why? Auto-remediation, multi-agent designs and Kubernetes, each for the reasons in the Scope section.
