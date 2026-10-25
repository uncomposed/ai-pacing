# Requirement traceability

All 13 current candidate requirements have inspectable upstream and downstream
paths. They are recorded derivation arguments, not validated deductions. In
particular, the actor model was expanded after the first requirements draft;
these links must be scrutinized for post-hoc justification.

## Inspect an actual trace

```sh
python3 tools/systems_tool.py trace --requirement REQ-COMPETE
python3 tools/systems_tool.py trace --requirement REQ-CUSTODY
python3 tools/systems_tool.py trace --requirement REQ-COORD
```

Each output identifies the complete model snapshot with a SHA-256 digest and shows:

1. The requirement, status, and source basis.
2. Challenges, scoped scenarios, intended outcomes, and adverse paths.
3. Directly linked interactions and their actor goals, constraints, and dependencies.
4. Use cases, actor-relative success, conflicting choices, and information differences.
5. Hazardous states, losses, and affected stakeholder classes.
6. Candidate mechanisms, their uncertain dependencies, and stopping rules.
7. Evaluation plans, baseline, pass criteria, evidence availability, and unresolved parameters.
8. Cross-requirement conflicts and the upstream source register.

The rendering distinguishes actors named in an interaction from additional
participants in its use cases. It does not infer that every actor in a broad
scenario directly motivates every requirement in that scenario.

## Worked example: REQ-COMPETE

| Link | Recorded content |
|---|---|
| Actor | ACT-BEHIND-LAB wants to catch up or differentiate, obtain funding, and attract customers. |
| Use case | UC-CATCHUP: train, license, collaborate, or specialize to achieve a capability or market position. |
| Other interests | ACT-FRONTIER-LAB wants to retain its lead; ACT-EXPERT seeks a defensible assessment and professional credibility. |
| Interaction | INT-ENTRY: an incumbent may possess needed expertise and benefit from obstructing the entrant. |
| Hazard and loss | HAZ-CAPTURE can lead to LOSS-BENEFIT: governance unnecessarily blocks beneficial development and competition. |
| Challenge | CH-ASSESS: make development assessable while enabling safe competition. |
| Candidate obligation | REQ-COMPETE currently specifies a published route to correct deficiencies and demonstrate equivalent safety under equivalent conditions. |
| Mechanisms to compare | PROP-RIVAL and PROP-PUBLIC, each evaluated separately against the baseline. |
| Evaluation | Matched applicant trials look for unexplained discrimination and test whether remediation is usable. |
| Open questions | Equivalent conditions, acceptable burden, appeal, actual authority, and the assumed actor incentives remain unresolved. |

This trace supports investigating fair, usable access to assessment. It does
**not** independently prove that a *published route* is the necessary solution.
That detail remains a design commitment to review. Nor does preventing exclusion
establish that a lab will be profitable: economic viability requires its own
analysis. The trace helps expose both gaps instead of concealing them behind a
coverage link.

## Other paths

| Requirement | Actor/use-case path | Interaction or failure being addressed |
|---|---|---|
| REQ-REPORT | Employee investigation and disclosure; lab financing and release incentives | INT-REPORT and INT-REVENUE: useful concerns may be suppressed or delayed. |
| REQ-CUSTODY | Employee reporting and expert assessment of an entrant | INT-REPORT and INT-ENTRY: the information needed for scrutiny may confer dangerous capability if disclosed. |
| REQ-PROTECT | Employee deciding whether to report | INT-REPORT: management controls career consequences and access. |
| REQ-EXPERT | Entrant seeking assessment; expert evaluating claims | INT-ENTRY: review needs competence, even when competent reviewers have conflicting interests. |
| REQ-ASSESS | Entrant and expert attempting to establish what a model can do safely | INT-ENTRY: access and intelligible, reproducible evidence must be sufficient for substantive scrutiny. |
| REQ-COMPETE | Entrant trying to catch up; incumbent participating in evaluation | INT-ENTRY: assessment can become an instrument of exclusion. |
| REQ-CONTROL | AI pursuing sovereignty; operators, investors, customers, and lab executives making operational choices | INT-SOVEREIGN and INT-REVENUE: power changes and commercial dependence can defeat effective control. |
| REQ-FEEDBACK | Same control situations, with incomplete or deceptive observations | INT-SOVEREIGN and INT-REVENUE: commands and apparent compliance may not establish actual protective effect. |
| REQ-COORD | Foreign lab release decision; foreign government response; domestic contingent policy | INT-STATE-FIRM: state and firm incentives may diverge. |
| REQ-ENTRY | Federal executive initiates action while other institutions deliberate | INT-FEDERAL: desired policy does not itself supply authority or resources. |
| REQ-OPTIONS | Later legislative, administrative, or judicial decisions | INT-FEDERAL: an initial step can create lock-in or prevent later participation and correction. |
| REQ-COOPERATE | AI pursuing a specified sovereignty objective; human parties choosing commitments and controls | INT-SOVEREIGN: the parties may lack credible commitments as bargaining power changes. |
| REQ-CONTEST | Affected party or entrant seeks review of a governance decision | INT-FEDERAL: institutional action may require timely, effective correction. |

## What remains incomplete

- Actor goals are fields on role templates, not independently identified,
  stakeholder-validated goal records with evidence for each assertion.
- Source records locate user intent and analytical inputs; they are not empirical
  support for all inferred motives or causal mechanisms.
- Each interaction has a shared rationale; necessity and sufficiency must still
  be argued for each linked requirement individually.
- Functional responsibility is not a validated allocation to a concrete institution.
- Requirement conflicts are recorded but their acceptable tradeoffs are unresolved.
- No evaluation has been executed; no proposal is established to satisfy a requirement.
- Coverage of the current inventory does not establish that the inventory is complete.

Use the traces to challenge requirements as well as justify them. If removing a
favored proposal makes its purported requirement meaningless, or if the upstream
need supports materially different outcomes, reopen that requirement rather than
using additional links to make it appear settled.
