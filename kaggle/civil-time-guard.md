# CivilTimeGuard: When Fixing a Day Breaks 24 Hours

*Declared time policies and residual regressions in eight repository repair lineages.*

## Abstract

A repair can pass every frozen temporal check and still make half of a 24-hour duration zero. CivilTimeGuard studies Gemma 4 31B on eight historical roots from seven repositories, using source-backed policies, localized buggy code, two initial draws, and paired evidence controllers. Initial proposals pass 11/16 frozen bundles; B and M each finish at 14/16. One natural Pendulum repair exchanges calendar-day errors for elapsed-hour errors. A later retained patch passes the frozen suite and thirty additional unit contrasts but breaks multiplication and division outside that suite. These exploratory audits remain separate from primary scores. On four roots, policy plus Q0 passes 6/8, policy without Q0 5/8, and Q0 without the added policy card 2/8. We release pinned repository contracts, generated patches, root-level outcomes, and executable observations. The study measures repair given declared requirements, not discovery of an unstated intent or proof of correctness for every operation.

## 1. What should stay invariant?

Across a daylight-saving transition, adding one calendar day can preserve the local clock while advancing only twenty-three elapsed hours. Adding twenty-four elapsed hours can correctly change the local clock. Conversely, an in-process scheduler must not wait an extra hour merely because its wall-clock representation jumped.

Neither output is inherently defective. Correctness depends on the interface's contract. A repair that converts every operation to UTC can fix the scheduler and damage calendar arithmetic. A repair that always preserves local fields has the reverse problem.

![Measured reciprocal duration failure](https://raw.githubusercontent.com/RayBerryHead/Gemma4-Contract-Repair/0c3e78605a72128da60bc569e0763c5673a3579c/papers/assets/time-measured-contrast.png)

Month recurrence exposes another ambiguity. January 31 followed by February 28 does not determine whether March should contain the 28th or 31st. Arrow's tested contract preserves the original day anchor, temporarily clips an impossible date, and later restores that anchor. Starting on February 28 instead preserves 28; it is not an instruction to remain at every month end.

CivilTimeGuard asks whether source-backed behavioral checks expose these distinctions in natural repairs, whether choosing different evidence improves revision, and what extra information is provided by an authored policy card versus a concrete reproducer.

## 2. Repository contracts

The eight roots cover Arrow origin-day recurrence; croniter caller-zone phases; dateutil POSIX day rules; Pendulum global-calendar independence and duration units; APScheduler elapsed waits; Luxon keepLocalTime; and date-fns complete local days. Multiple symptoms in one fix are one root. Development cases from croniter and APScheduler are separate from the formal denominator; same-repository transfer is identified as such.

Each task supplies a version-specific policy, localized buggy code, one visible reproducer Q0, and functionality controls U. The controllers can execute a shared visible pool V. Independent inputs or modes E are reserved for final evaluation and never returned as revision feedback. Historical fixed code is a positive control, not the only acceptable patch.

Observations preserve only contract-relevant dimensions: local fields, elapsed instants, offsets/fold where needed, duration units, result type, and relevant global side effects. We do not collapse every result to UTC. We also do not use native datetime equality as a substitute for fold-aware instant comparison.

The oracle follows source authority rather than majority agreement between libraries. For example, dateutil's POSIX n is zero-based and includes leap day, whereas Jn is one-based and excludes it. A library sharing the same faulty algorithm would not be an independent correctness vote. Month-anchor expectations use explicit calendar calculations. Global-calendar checks require the API result and unchanged caller state.

All controls replay the same test-only bundle on the pinned buggy and fixed revisions. The resource accepts behaviorally correct alternatives and distinguishes internal helper-shape assertions from required semantics.

## 3. Controlled repair

Gemma 4 31B uses high thinking, temperature 0.2, AUTO tools, and a 32,768-token output ceiling through Google's hosted API. Independent campaigns later overlap HTTP under shared token reservations and request pacing; each repair trajectory remains sequential, with unchanged prompts and generation parameters. Source locations are supplied from historical old-side context; gold text and E are excluded. The task is focused contract repair rather than full repository navigation.

The model submits cumulative exact replacements; a shared adapter checks the product scope and materializes a Git diff. One initial draw is forked into B/M histories and workspaces. Each branch receives its visible results and may revise twice. Invalid proposals consume a revision, and every prior visible witness is checked again.

B orders the fixed pool by policy-aware boundary coverage and public-call cost. M favors inputs for which predefined alternative implementation semantics predict outcomes outside the allowed policy, then updates compatible hypotheses after observations. Duplicate predictions do not gain weight. Undefined predictions fall back to B. Most tasks have one allowed policy, so this is counterexample selection under known requirements, not intent inference.

A static CPU comparator tests the value of updating the hypothesis set. F runs all visible probes on T1/T4/T5/T6/r01 and returns the complete failure set. Actual testing time and model tokens are reported separately; F is not presented as an equal-test-cost comparison.

The primary outcome is a retained repair whose product edits apply, Q0/U pass, and final visible audit and E pass. Valid refers to this finite bundle. We keep invalid edits and runtime failures distinct from observed policy violations.

## 4. Results

| Root / task | Initial | B | M | F (r01) |
| --- | --- | --- | --- | --- |
| T1 Arrow: original month anchor | 2/2 | 2/2 | 2/2 | 1/1 |
| T2 croniter: caller zone | 2/2 | 2/2 | 2/2 | — |
| T3 dateutil: POSIX ordinal | 2/2 | 2/2 | 2/2 | — |
| T4 Pendulum: global calendar | 2/2 | 2/2 | 2/2 | 1/1 |
| T5 Pendulum: duration units | 0/2 | 2/2 | 2/2 | 1/1 |
| T6 APScheduler: elapsed wait | 2/2 | 2/2 | 2/2 | 1/1 |
| T7 Luxon: keepLocalTime | 0/2 | 0/2 | 0/2 | — |
| T8 date-fns: complete local days | 1/2 | 2/2 | 2/2 | — |

Initial/B/M cells contain two draws per root; F is the preset one-draw subset. All counts use the frozen checks, including the same functionality controls.

Thirteen initials pass Q0/U, but the two T5 draws fail hour-unit checks in the visible bank. Their day-based E check still passes: withheld tests alone do not cover every mode. Both T7 initials apply but raise product runtime errors; they are not labelled wrong-policy repairs. B/M each recover three initially failing draws.

| Controller | Passes | New V subject calls | All public-feedback subject calls | Feedback execution seconds | Revision responses | Provider total revision tokens |
| --- | --- | --- | --- | --- | --- | --- |
| B | 4/4 | 12 | 27 | 3.13 | 2 | 25,350 |
| M | 4/4 | 11 | 22 | 2.31 | 1 | 13,331 |
| F | 4/4 | 12 | 24 | 2.30 | 1 | 15,107 |

Revision responses include unusable proposals. Token totals include provider-reported prompt, candidate, and thinking tokens.

All three controllers pass the matched four-root/r01 subset. M uses one fewer new visible call and one fewer revision than B in these sampled trajectories; equivalent initial feedback and stochastic later proposals do not isolate the cause. Feedback lasts about 2.3–3.1 seconds. On eight applicable natural initials, CPU B/M/static-A each find two visible witnesses with 18 new calls; F uses 22. The witnesses are two draws of T5, not two independent bugs. Eight upstream controls remain separate.

Root-level counts and paired transitions are primary. There are eight natural lineages and two draws per lineage, not sixteen independent bug families. All sixteen initial feedback pairs are semantically equivalent, and final pairs are both-valid in fourteen blocks and neither-valid in two. This study establishes no selection advantage or statistical equivalence across future tasks. If B/M receive equivalent evidence, a later stochastic difference cannot establish a benefit from evidence selection.

A small 26B A4B screen on the preselected T1/T6 roots produces no usable initial patch under high thinking and the 32K cap: both reach MAX_TOKENS. The initial-only scope was adopted after the first secondary-model exhaustion across the four-root screen; all selected roots and historical extra responses remain visible. These are generation-budget outcomes, not observed temporal policy errors.

## 5. What information resolves a temporal repair?

The additional information experiment uses T1/T4/T5/T6, selected before observing their formal outcomes. It reuses each main initial as the policy-plus-Q0 condition and generates one initial per new condition: remove Q0 while retaining the authored policy, or remove the added policy card while retaining Q0. Original source/docstrings and common functionality controls remain available in every condition.

All conditions use the same localized source, model settings, tool interface, and final oracle. No condition receives test feedback or additional revisions. We alternate the order of the two new conditions by root and keep r01/r02 separate.

This is an information ablation, not an equal-information selector comparison. Removing the added card does not remove every policy clue already present in the source or API name. It can reveal whether the supplied declaration or reproducer is useful in these particular tasks, without treating underspecified requirements as a model error by definition.

| Root | Policy + Q0 | Policy, no Q0 | Q0, no added card |
| --- | --- | --- | --- |
| T1 | 2/2 | 2/2 | 2/2 |
| T4 | 2/2 | 2/2 | 0/2 |
| T5 | 0/2 | 1/2 | 0/2 |
| T6 | 2/2 | 0/2 | 0/2 |
| All four roots | 6/8 | 5/8 | 2/8 |

Both-information failures are two observed contract violations. Policy-only failures are two contract violations and one generation-budget exhaustion; no-added-card failures are three invalid proposals and three contract violations. Thus the 6/8 versus 2/8 comparison mixes applicability and behavior. It is descriptive evidence on four roots with two draws each, not automatic intent discovery or proof that adding examples always helps.

The natural T5/r01 initial changes normalized duration days into calendar days. It fixes the day reproducer but makes 24 hours advance only 23 elapsed hours in spring and 25 in autumn. An exploratory 30-input replay across New York, Paris, and Sydney exposes an exchange: upstream buggy code and the initial patch both pass 18/30, but fail opposite unit contrasts. This is one lineage, not thirty independent bugs.

A revised M-labelled patch then passes the frozen suite yet changes the meaning of the shared internal _days field. For a duration constructed with 24 hours, the calendar-day argument is zero even though its normalized length is one day. Other arithmetic still reads the repurposed field to compute microseconds. We followed those callers and tested two public operations outside the frozen suite: duration(hours=24) * 0.5 and division by 2. Both return zero seconds, where upstream buggy, upstream fixed, and the B-labelled repair return 43,200.

![A passed repair breaks fractional duration arithmetic](https://raw.githubusercontent.com/RayBerryHead/Gemma4-Contract-Repair/0c3e78605a72128da60bc569e0763c5673a3579c/papers/assets/time-residual-scaling.png)

The consumer methods were outside the supplied source excerpts as well as the frozen test bundle. This is evidence about focused repair with incomplete context; a full-repository agent's response remains unmeasured. The proposed change also changes which consumers matter: a context boundary fixed before the proposal does not automatically include the consequences of repurposing a shared field. These post-hoc observations remain separate from the primary scores. They show why preserving the distinction between input units must not destroy the normalized representation used by other operations; they do not show that the selector caused the regression.

## 6. Relation to existing work

The MSR2025 date/time-bug study already analyzes 151 bugs from 102 projects and explicitly shows why converting everything to UTC is not universal. The public dt-fuzz artifact covers month-end, endpoint, and duration convention differences through generation and differential testing. These semantic families are established prior work. DateSAT provides date/period constraints and SMT encodings; formal date-arithmetic work already models alternative rounding policies and non-properties. PEP 495 specifies fold and temporal arithmetic/comparison behavior. Policy ambiguity and daylight-saving edge cases are not new discoveries here.

Our resource instead fixes the source authority, repository revision, repair task, and executable observation together, then measures natural model-generated patches under controlled inputs. It does not introduce a new solver, date language, or general proof of correctness. The authors of Chronically Buggy report EMSE acceptance, but its full manuscript was not retrieved; we do not claim to have excluded every overlap with that work.

## 7. Limits and reproduction

The authors inspected the fixes, and historical public code may occur in model training. Most policies are author-supplied singletons. Context and task preparation require human effort. Some roots share repositories or ecosystems; small descriptive results do not establish universal transfer or statistical equivalence.

Withheld probes are finite and sometimes test a different mode of the same API. Complete visible testing is therefore not a proof of the full contract. Infrastructure interruption, a failed patch application, and a policy error receive different labels. The strongest representation audit concerns one Pendulum lineage. T7 remains unsolved under this localized context and edit protocol; no claim about a full-repository agent follows.

T1 also served as a technical smoke case while repairing the common transport and patch compiler; those responses are excluded from formal draws. The corpus was not untouched during engineering. Curation time was not measured, so automation savings cannot be inferred from the runtime alone.

The [companion artifact](https://github.com/RayBerryHead/Gemma4-Contract-Repair) contains the pinned inputs, complete outcomes, patches, and reproduction scripts. After the conda/Node setup in its README, replay the main example without an API key:

```bash
export PYTHONPATH=src
python tools/configure_public.py
python tools/prepare_sources.py --artifact-root "$PWD/artifacts" --ids T5
python tools/replay_published.py --ids T5
```

The same replay includes information-condition patches where applicable; removing `--ids` from both preparation and replay covers the complete published patch index.

The release contains source revisions, oracle projections, visible/withheld specifications, natural edits and patches, model settings, paired outcomes, and table/figure scripts. Test execution and analysis ran on GB10; model inference was hosted. Primary inference reports 34 responses and 341,463 tokens; the sixteen extra information responses report 253,969, and the two secondary-model initials 69,357. Three additional information requests have unknown network results and are not assigned zero token use. Reported totals include returned responses only. Additional API/cloud cash charges are US$0 at [Gemma pricing](https://ai.google.dev/gemini-api/docs/pricing#gemma-4); no training was performed.

## References

1. dt-fuzz. [Official framework](https://github.com/cmu-pasta/date-time-genai).
2. DateSAT. [arXiv:2605.25180](https://arxiv.org/abs/2605.25180).
3. Formalizing Date Arithmetic. [arXiv:2403.08935](https://arxiv.org/abs/2403.08935).
4. Local Time Disambiguation. [PEP 495](https://peps.python.org/pep-0495/).
5. It's About Time. [MSR2025 paper](https://rohan.padhye.org/files/datetimebugs-msr25.pdf).
6. Chronically Buggy. [Author publication listing](https://www.shreytiwari.com/).
