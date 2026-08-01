# Project Notebook

This notebook is a chronological record of project progress, design decisions,
experiments, results, and open questions. Every work session should add a local
date and time, changes made, validation performed, successes, failures, and
remaining work. Times use the `America/Denver` project timezone.

## 2026-07-31 — Documentation started

### Progress

- Created the project notebook and initial report draft.
- Added a current project description and documentation links to the README.
- Defined the project at a high level: use reinforcement learning to select
  among predefined QoS configurations on a MikroTik router based on observed
  network performance.

### Initial objective

Minimize packet loss and latency for high-priority DSCP traffic while
maximizing the throughput available to lower-priority traffic.

### Current design assumptions

- The agent will choose among predefined QoS configurations rather than
  directly generating arbitrary router settings.
- Candidate observations include packet loss, latency, and throughput.
- Traffic priority will be represented using DSCP markings.

These assumptions are provisional and should be updated as the environment and
RL formulation are designed.

### Next steps

- Define the project scope and research question precisely.
- Document the test network and MikroTik configuration.
- Specify the RL state/observation space, action space, and reward function.
- Choose a learning algorithm and baseline policies for comparison.
- Define evaluation scenarios, metrics, and success criteria.

## 2026-07-31 — Project requirements and environment draft

### Progress

- Reviewed `ProjectGuidelines.txt` and identified the required deliverables and
  report sections.
- Added the initial Environment section to the report.
- Documented the planned three-node topology, RouterOS version, traffic-class
  roles, and the RL environment's interaction loop.

### Requirements to track

- Maintain a Git repository containing working, commented, and explained code
  or notebooks.
- Produce a demo clip and link or embed it in the report or notebook.
- Cover the overview, approach, environment rules, model selection, experiment
  methods, troubleshooting and iterative improvements, results and
  visualizations, discussion, future work, and references in the final report.
- Preserve evidence of changes made when a correctly implemented learning
  approach performs poorly; implementation debugging alone does not satisfy
  the rubric's problem-solving criterion.

### Details still to confirm

- PC1 and PC2 hardware specifications
- MikroTik router model
- Link speeds and configured bottleneck rate
- Traffic rates and the generator for medium-priority traffic
- Remaining traffic-generation and measurement tools
- QoS profile definitions and queue parameters
- Reward formula, weights, measurement units, and normalization

## 2026-07-31 — RL environment rules drafted

### Progress

- Added the RL Environment section to the report.
- Defined the initial state as packet loss, latency, throughput, and the current
  queue profile.
- Defined each action as selecting one predefined QoS profile.
- Established a 300-second episode with a 5-second decision interval, producing
  60 decision steps per completed episode.
- Defined normal termination at the episode time limit and early termination
  for environment or measurement failures.

### Reward design

The reward will favor high throughput and low latency while penalizing packet
loss and queue-profile changes. Exact terms, weights, units, and normalization
remain open design decisions and must be documented before training. Any later
changes should be recorded as experiments to preserve evidence of the
problem-solving and iterative-improvement process required by the rubric.

## 2026-07-31 — Initial design decisions documented

### Fixed decisions and rationale

- **Use DSCP markings for traffic classification.** DSCP is a standardized,
  network-layer mechanism that makes traffic priorities explicit without
  application identification or packet-content inspection. It also keeps the
  router configuration understandable and experiments reproducible.
- **Limit actions to predefined QoS profiles.** A small, discrete action space
  simplifies learning, prevents arbitrary or invalid RouterOS configurations,
  and makes agent behavior easier to interpret.

These decisions are considered foundational and will remain fixed. Learning
algorithms, reward weights, and the contents of the QoS profiles may be tested
or refined without changing the DSCP-based classification method or the use of
predefined profiles as the action structure.

## 2026-07-31 18:35 MDT — Project plan reviewed

### Changes made

- Reviewed `ProjectPlan.md` and compared it with the report and existing open
  design questions.
- Updated the report with Xubuntu 26.04 for both PCs.
- Documented the planned traffic classes: voice-like UDP marked DSCP 46,
  interactive traffic marked DSCP 26, and bulk TCP marked DSCP 0 using
  `iperf3`.
- Refined the state definition to use high- and medium-priority loss and
  latency, low-priority throughput, and the current queue profile.
- Adopted timestamped notebook entries that explicitly track changes,
  validation, successes, failures, and remaining work.

### Plan and structure decisions

- Follow the nine project phases in `ProjectPlan.md`, beginning with a working
  static QoS configuration and progressing through traffic generation,
  measurement, router abstraction, logging, baselines, and tabular Q-learning.
- Treat DQN as optional and attempt it only if the required implementation and
  experiments are complete.
- Use the proposed directory structure as a guide, creating each directory
  when its implementation phase begins instead of adding empty directories.
- Keep RouterOS commands behind a router interface and keep networking code
  separate from RL code.

### Validation and outcome

- **Success:** The plan is consistent with the report's overview, environment,
  and fixed design decisions.
- **Success:** Previously unknown operating systems, traffic markings, traffic
  roles, and state layout were resolved and synchronized into the report.
- **Validation:** `git diff --check` passed after the documentation edit; no
  whitespace errors were found.
- **Failures:** None during the plan review or documentation update.

### Remaining work

- Begin Phase 1 by documenting and validating the static MikroTik Queue Tree,
  DSCP classification, queue counters, and bottleneck shaping.
- Resolve the remaining environment and reward details listed above.

## 2026-07-31 18:37 MDT — Local project plan ignored by Git

### Changes made

- Created the repository's root `.gitignore` file.
- Added `ProjectPlan.md` so the local planning document remains available in
  the workspace but is not included in Git commits.

### Validation and outcome

- **Success:** `git check-ignore` confirmed that `ProjectPlan.md` is ignored by
  the root `.gitignore` rule.
- **Success:** `git diff --check` passed with no whitespace errors.
- **Failures:** None.

### Remaining work

- No additional work is required for this configuration change.

## 2026-07-31 18:50 MDT — On-demand router backup tool added

### Changes made

- Added `scripts/backup_router.sh` to retrieve a RouterOS configuration export
  using SSH key authentication.
- Configured timestamped `.rsc` output in the local `routerbackups/` directory.
- Added `routerbackups/` to `.gitignore` because exports can reveal private
  network configuration.
- Added setup and invocation guidance to the README.

### Decisions and rationale

- Use SSH on TCP 22 for configuration exports. SSH directly supports remote
  `/export` execution and encrypts the session.
- Do not use the unencrypted RouterOS API service on TCP 8728 for backups. The
  API remains appropriate for later structured controller operations; if it is
  used, prefer API-SSL on TCP 8729 or a separately protected management path.
- Use `/export terse` without `show-sensitive`. This creates a readable,
  version-controllable configuration while excluding sensitive values.
- Require key-based, noninteractive login and preserve SSH host-key checking.
  This prevents passwords from being embedded in the script and detects a
  changed or impersonated router host.

### Validation and outcome

- **Success:** Bash syntax validation, help-output execution, ignore-rule
  validation, and whitespace validation passed.
- **Failure/limitation:** A live backup was not attempted because the router
  address, backup username, SSH key, and verified host key are not available in
  the repository.
- **Expected behavior:** Failed or empty exports are removed rather than being
  retained as valid backups.

### Remaining work

- Create a least-privilege RouterOS account capable of exporting configuration.
- Generate or select a dedicated client SSH key, import its public key for that
  RouterOS user, and verify the router's SSH host-key fingerprint out of band.
- Run the first live backup and confirm that the resulting `.rsc` file contains
  the required Queue Tree and DSCP configuration without sensitive values.

## 2026-07-31 19:00 MDT — Router backup defaults configured

### Changes made

- Set the backup script's default router address to `192.168.88.34`.
- Set the default RouterOS username to `backup`.
- Set the default identity to `~/.ssh/mikrotik_backup`, expanded internally to
  the invoking user's home directory.
- Updated the script help and README so an on-demand backup can be started with
  `scripts/backup_router.sh` and all defaults remain overridable.

### Validation and outcome

- **Success:** Bash syntax validation and help-output execution passed.
- **Success:** The documented defaults appear correctly in the help output.
- **Success:** `git diff --check` passed with no whitespace errors.
- **Failures:** None. A router connection was intentionally not attempted as
  part of this edit.

### Remaining work

- Run the script on demand after the SSH key and router account are ready.

## Entry template

Copy this section for future entries.

```markdown
## YYYY-MM-DD HH:MM TZ — Short description

### Changes made

- What changed or was completed

### Decisions and rationale

- Decision: ...
- Reason: ...

### Validation and outcome

- Checks or experiments performed: ...
- Successes: ...
- Failures: ...
- Interpretation: ...

### Open questions / next steps

- ...
```
