# Content scoring and experimentation specification

**Status:** Proposed scoring contract for OCIF. Scores are decision aids, not guarantees of reach or virality.  
**Default publishing policy:** Human approval required; OIS authorization required; sandbox/no-op execution only until a separate publishing release is approved.

## 1. Separate two questions

OCIF should calculate distinct scores:

1. **Historical performance score:** how a published item performed relative to comparable content.
2. **Draft potential score:** how well a proposed draft matches the strategy, evidence, platform format and creative quality.

Do not train the draft score directly on raw lifetime likes. Historical performance is affected by account size, distribution, format, paid spend, posting age, seasonality and audience mix.

## 2. Historical performance

For each platform and content format, define a comparable cohort by account, format, objective, publication period and measurement window. Calculate only metrics available for that cohort.

Example normalized components, each clipped to [0, 1]:

- `engagement_component`: cohort-relative percentile for an explicitly defined engagement rate.
- `retention_component`: cohort-relative percentile for average watch duration or completion rate where exposed.
- `click_component`: cohort-relative percentile for CTR where measurable.
- `conversion_component`: cohort-relative percentile for conversions per defined eligible denominator.
- `audience_quality_component`: evidence-backed downstream action or target-audience fit; omit when not measured.
- `sentiment_component`: optional audience-response signal with model version, calibration and human-review sampling.

Example for a goal focused on qualified traffic:

```text
historical_score = 100 * (
  0.25 * engagement_component +
  0.20 * retention_component +
  0.20 * click_component +
  0.25 * conversion_component +
  0.10 * audience_quality_component
)
```

These weights are an initial configurable example, not empirically validated constants. Renormalize over available components only if the missingness policy is explicit; also emit a coverage score so a draft with sparse evidence cannot appear equally certain.

For awareness, lead generation, community building and conversion, maintain separate formula IDs. Never compare scores from different formula versions without a migration or recalculation.

## 3. Draft quality and potential

Score each draft from 0 to 100 across independently defined dimensions:

| Dimension | Example weight | What is evaluated |
|---|---:|---|
| Objective fit | 20% | Match to the campaign goal and intended audience |
| Evidence strength | 20% | Claims trace to captured sources and approved research findings |
| Hook and clarity | 15% | Clear promise, relevance, specificity and opening strength |
| Platform fit | 15% | Format, length, accessibility and platform constraints |
| Distinctiveness | 10% | Novel angle relative to the current content library |
| Action path | 10% | CTA and next step fit the intended outcome |
| Brand and safety | 10% | Voice, policy, rights and factual checks |

`draft_potential_score` is the weighted sum of available, validated components. A hard-fail check (unsupported factual claim, policy violation, missing required source, prohibited format or unsafe CTA) blocks advancement regardless of the numeric score.

Keep these separate from any machine-predicted outcome. If a predictive model is later trained, store its model version, training window, target, cohort, calibration results and uncertainty. Do not label a heuristic score as a probability of going viral.

## 4. Evidence and claim requirements

Each factual research claim should include:

- Claim ID and text.
- Supporting evidence IDs and source captures.
- Source timestamps and retrieval query/version.
- Confidence and limitations.
- Whether it is observed fact, inference or hypothesis.
- Contradictory evidence or unresolved uncertainty.

Draft generation may cite only evidence supplied in its research brief. A claim without adequate evidence is marked as a hypothesis or removed. Keep the source material and model prompt/version in the audit lineage, subject to applicable privacy and retention rules.

## 5. Experiment design

- State the hypothesis and primary metric before the test starts.
- Change one main variable per experiment where practical: hook, format, CTA, posting window or topic framing.
- Randomize assignment where the platform and workflow permit it; otherwise record the observational design and confounders.
- Define minimum observation window and stop rules before reviewing results.
- Compare within the same platform/account/objective and similar publication age.
- Use confidence intervals or a suitable Bayesian estimate; avoid selecting winners from tiny samples.
- Preserve experiment assignment, content version, publication time, spend, distribution context and metric snapshots.
- Avoid claiming causal lift from organic posts with uncontrolled distribution.

## 6. Outcome feedback

Outcome events are append-only. Each event records content/draft ID, platform object ID if published, metric definition version, value, window, source method, capture lineage, experiment ID and ingestion timestamp. Re-polling a metric creates a new observation rather than overwriting history.

Scoring updates require a versioned change proposal, backtest against a fixed historical dataset, comparison against the prior formula and a documented acceptance decision. Do not silently change weights based on one high-performing post.

## 7. Evaluation and release gates

Required before a score is used to automate a consequential action:

1. A fixed golden dataset with documented cohort and missing-data rules.
2. Reproducible scores for a pinned formula version.
3. Tests for zero denominators, missing metrics, stale observations, metric-definition mismatch and outliers.
4. Score breakdown stored with each result.
5. Comparison against simple baselines (cohort percentile, recent median and human ranking).
6. Retrieval evaluation using recall@k, MRR and precision@k on a labeled query set.
7. Human review of a sample of classifications, sentiment labels and generated factual claims.
8. Approval bound to the exact draft digest/version; edits invalidate approval.
9. OIS authorization before any execution adapter is invoked.
10. No live publishing until a separately reviewed adapter, rollback plan, consent and metric verification are accepted.
