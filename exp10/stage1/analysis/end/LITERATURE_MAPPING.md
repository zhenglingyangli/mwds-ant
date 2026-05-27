# Stage 1 Literature Mapping

This note maps related work to the Stage-1 controller design. The purpose is to
borrow experimental discipline from mature frameworks without overstating the
novelty of the controller.

## Selection Hyper-Heuristic

Burke et al. and Drake et al. frame a selection hyper-heuristic as a high-level
method that selects among low-level heuristics. In Stage 1:

- state: cheap instance features plus online DBS/AQ probe signals;
- actions: `DBS-only`, `Light AQ`, `Standard AQ`, `Heavy AQ`, `Stop/Rollback`;
- low-level heuristics: DBS and Ant-Q budget variants;
- credit: LB gain per time, gap reduction, UB drift, and #OPT preservation;
- protocol: compare against hand-written `v006`, random arm, and simple
  non-contextual selectors before claiming a learned controller.

This means `v007/v009` should be described as hand-written arm selectors unless
they learn action values from logged rewards.

## MAB Hyper-Heuristic

Lagos and Pereira use MAB methods for low-level heuristic sequencing. The useful
parts for Stage 1 are the arm definition, online reward accounting, and operator
usage analysis. The mismatch is important:

- their setting repeatedly selects heuristics and receives frequent rewards;
- Stage 1 currently makes at most one run-level AQ budget decision, and reward is
  sparse because LB/gap/UB are only meaningful after a probe or run segment.

Therefore, a true MAB claim requires multiple decisions per run and logged
updates such as `continue AQ`, `increase K`, `reduce K`, `stop AQ`, and
`rollback`.

## LA-BHH

LA-BHH is relevant because it combines static landscape features with dynamic
search-state features and tests Random-HH, UCB-HH, contextual variants, and
context ablations. Stage 1 should borrow this evaluation pattern:

- static context: `|V|`, density, degree/weight spread, graph family proxies only
  if they are available online and not hard-coded by dataset name;
- dynamic context: `FIRST_GAP`, DBS LB slope, AQ probe slope, AQ gain, UB drift,
  stagnation;
- ablations: no context, static-only, dynamic-only, full context.

The limitation is that LA-BHH operators have immediate tour-length rewards,
while AQ reward is delayed and can hurt UB/#OPT even when LB improves.

## SATzilla-Style Algorithm Selection

SATzilla is the closest model if Stage 1 chooses one controller arm once per
instance. The mapping is:

- pre-solver: DBS probe;
- backup solver: `DBS-only`;
- candidate solvers: Light/Standard/Heavy AQ budget variants;
- censored runs: timeout or killed DIMACS10/NDR cases;
- split discipline: train/dev/test or leave-one-family-out;
- objective: avoid catastrophic timeouts and UB/#OPT regressions, not just raise
  LB.

If Stage 1 remains one-shot, the correct naming is per-run algorithm selection
or selection hyper-heuristic, not contextual bandit.

## Adaptive ACO Parameters

Reactive/self-adaptive ACO work already covers dynamic tuning of pheromone and
parameters such as `alpha`, `beta`, `rho`, `q0`, and ant count. Stage 1 should
avoid claiming novelty in generic ACO parameter adaptation.

The defensible contribution is narrower: MWDS-specific budget, stop, and
rollback control for DBS plus Ant-Q, with explicit negative-transfer detection
across graph families.

## Stage 1 Design Consequence

Use this naming rule:

- one decision at run start or after a fixed probe: `per-run selection`;
- repeated arm decisions with online reward updates: `contextual bandit`;
- deterministic thresholds without learned values: `hand-written gating`.

The main result must include strong baselines: `v006`, `DBS-only`, random arm,
non-contextual UCB/mean selector, and a simple linear/ridge selector if logged
data supports supervised policy learning.
