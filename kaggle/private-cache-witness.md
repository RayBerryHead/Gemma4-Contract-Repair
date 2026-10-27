# PrivateCacheWitness: A Clean Header Can Hide a Foreign Body

*Native cache traces, alternative repairs, and eight historical bug lineages.*

## Abstract

A cache repair can remove a sensitive response header while still returning another caller's personalized body. We study contract-preserving repair using eight historical lineages from Undici, Django, and django-graphex. Seven concern privacy obligations; one origin-integrity case is reported separately. Gemma 4 31B receives a source-backed contract, localized buggy code, and a visible reproducer. We evaluate two initial draws per root and paired repair controllers against independent behavior checks and legitimate-use controls. Initial proposals pass 12/16 frozen bundles; B finishes 14/16 and M 13/16. A two-request witness demonstrates why sanitizing Set-Cookie is insufficient when an existing private entry becomes visible to a shared client. The experiment does not establish a selector advantage: all sixteen paired blocks receive semantically equivalent initial feedback. A source audit also finds a false rejection caused by an excessive Authorization-header requirement; the correction reuses the same initial draws. We release pinned task recipes, executable traces, generated patches, and root-level outcomes. The contribution is an inspectable repair resource and empirical evidence about its tested failure modes; a finite trace suite does not establish universal cache safety.

## 1. The missing relationship

Alice legitimately populates a private cache. Bob subsequently reads the same URL through a shared-cache client using the same supported store. In one natural initial repair, Gemma prevents new shared responses carrying Set-Cookie from being stored. For existing entries, however, it constructs a copy of the cached headers with Set-Cookie removed and returns the original body.

Bob receives Alice's body without Alice's cookie. The header now looks clean, while the relationship between request identity and returned content remains wrong. Our minimized replay uses two public requests: the natural patch contacts the origin once, whereas the upstream reference and a successful revised patch contact it twice and return Bob's response. This is a measured example from C1/r01; its frequency in general agent use is unknown. Primary call accounting retains the frozen three-request trace rather than substituting the minimized two-request illustration.

The warm setup follows an [upstream regression fixture](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/test/interceptors/cache.js#L102). The [read guard](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/lib/interceptor/cache.js#L423) also addresses stores that outlive the Undici version that wrote their entries. We use private population as a public-API constructor of existing state; deployment frequency is unknown.

![Measured warm-state witness](https://raw.githubusercontent.com/RayBerryHead/Gemma4-Contract-Repair/0c3e78605a72128da60bc569e0763c5673a3579c/papers/assets/cache-warm-state.png)

The observation motivates three questions. Which initially plausible repairs fail a broader contract? Does patch-informed evidence ordering help under a fixed revision budget? Which parts of the resource transfer across repositories and cache mechanisms?

## 2. A small resource with explicit authority

PrivateCacheWitness contains eight pinned fix lineages. Undici contributes Set-Cookie storage/read behavior, redirect target integrity, and empty qualified-private parsing. Django contributes Authorization variation, cookie creation or refresh, session renewal, and qualified directive handling. django-graphex contributes per-user GraphQL cache isolation. It shares the Django ecosystem, so three repositories do not represent three independent framework families.

Each task records buggy and fixed revisions, the product contract, a visible reproducer Q0, functionality controls U, a visible trace bank V, and withheld checks E. Upstream fixed code is a positive control rather than the unique permitted implementation. The same bundle must reproduce the historical failure and pass the reference behavior before model evaluation.

The authority is version-specific. RFC 9111 does not categorically prohibit caching a response containing Set-Cookie. The [Undici advisory](https://github.com/nodejs/undici/security/advisories/GHSA-2jfj-6hjv-fm6j) also lists removing Set-Cookie before caching as a workaround. Our measured failure serves an existing actor-specific body after redacting its cached cookie. Undici can impose a stricter shared-cache policy. Likewise, Django's handling of qualified directives is a product policy, not a universal interpretation of every HTTP cache. We avoid inventing a requirement merely because it would make a stronger attack demonstration.

Traces use the original framework and supported public interfaces: MemoryCacheStore and local HTTP servers, or Django request/cache/session facilities. State is reset between traces and preserved within a trace. Synthetic actors make body and cookie relationships observable. We retain normal public-cache reuse, legitimate private-cache reuse, and access by the correct caller. A safe alternative is accepted when its observed behavior satisfies the declared contract.

C2 targets origin integrity. Its core result is not counted as a private-data disclosure. Additional same-origin capability-redirect checks, if reported, remain exploratory controls on that lineage rather than additional natural bugs.

## 3. Repair and evidence

The experiment is focused semantic repair: source localization and an explicit contract are supplied. Old-side context is curated using historical fix locations, but fixed text and E are excluded; Q0/U are supplied. This setting tests adherence to known requirements; it does not measure repository navigation or discovery of unspecified requirements.

Gemma 4 31B is accessed through Google's hosted API with high thinking, temperature 0.2, AUTO function calling, and a 32,768-token output ceiling. Independent campaigns later overlap HTTP under shared token reservations and request pacing; each repair trajectory remains sequential, with unchanged prompts and generation parameters. The model submits cumulative exact replacements against the buggy base. A common adapter requires unique old-text matches and materializes a product-code Git diff. Raw proposals, canonical diffs, and failures are retained.

For each root and draw, one initial response is shared between isolated B and M branches. B ranks visible traces by uncovered actor/state/phase/obligation tags per declared public-call cost. M adds a fixed preference for related, unmodified phases of the same obligation. Responsibilities are mapped from buggy-source symbols and old-side edit locations; unmapped edits fall back to B. Neither controller receives E.

Each branch has at most two revisions. Q0, U, and previously found witnesses are checked again. The final score requires an applicable retained patch and passing functionality, visible-bank audit, and withheld contract checks. Here, valid means passing this finite bundle. An invalid proposal consumes a revision; it is not silently retried until it succeeds.

On C1–C4/r01, F executes the complete visible bank and returns all failures. It is a practical complete-bank comparator; the information and cost can coincide with B/M when they already execute the whole bank. CPU diagnostics replay fixed patches through B/M/A/F; A prefers directly modified phases. CPU controls use upstream buggy/fixed versions and remain separate from natural model patches.

## 4. Results

| Root / task | Initial | B | M | F (r01) |
| --- | --- | --- | --- | --- |
| C1 Undici: existing Set-Cookie entry | 1/2 | 2/2 | 1/2 | 0/1 |
| C2 Undici: redirect origin * | 1/2 | 1/2 | 2/2 | 1/1 |
| C3 Django: Authorization | 2/2 | 2/2 | 2/2 | 1/1 |
| C4 Django: cookie creation | 2/2 | 2/2 | 2/2 | 1/1 |
| C5 django-graphex: user identity | 2/2 | 2/2 | 2/2 | — |
| C6 Django: session renewal | 2/2 | 2/2 | 2/2 | — |
| C7 Undici: empty private directive | 0/2 | 1/2 | 0/2 | — |
| C8 Django: qualified directives | 2/2 | 2/2 | 2/2 | — |

Each initial/B/M cell contains two draws; F contains one draw only on its preset subset. * C2 measures origin integrity. Privacy-only passes are B 13/14 and M 11/14; C2 contributes B 1/2 and M 2/2.

Thirteen initials pass Q0 and U. One of those, C1/r01, fails both broader visible and withheld checks. Three initial responses are unusable: one exhausts the generation budget and two fail exact replacement. We do not call those three observed privacy disclosures.

| Controller | Passes | New V subject calls | All public-feedback subject calls | Feedback execution seconds | Revision responses | Provider total revision tokens |
| --- | --- | --- | --- | --- | --- | --- |
| B | 4/4 | 32 | 64 | 4.40 | 2 | 30,482 |
| M | 3/4 | 32 | 64 | 4.47 | 2 | 22,141 |
| F | 3/4 | 32 | 64 | 4.30 | 2 | 27,833 |

Revision responses include unusable proposals. Token totals include provider-reported prompt, candidate, and thinking tokens.

On the matched four-root/r01 subset, B passes 4/4, M and F 3/4. All use 32 new visible subject calls and 64 total public-feedback calls, taking about 4.3–4.5 seconds. F does not improve repair success here. These are observed feedback costs, excluding initial diagnostics and final audits; hosted generation takes minutes per response.

We report eight natural roots and sixteen initial draws, not thirty-two independent bugs. Paired outcomes are both-valid, B-only, M-only, or neither. F is compared with the same four-root/r01 subset. Failures and incomplete executions remain visible.

The causal interpretation also depends on evidence actually differing. We compare the semantic content of the initial B/M feedback, excluding timing noise and normalizing equality relationships of synthetic opaque cookies. All 16 initial feedback pairs are equivalent, yet three final pairs disagree. Outcomes are both-valid in 12 blocks, B-only in two, M-only in one, and neither in one. Later stochastic proposals and their different subsequent observations prevent treating those discordances as isolated evidence-ordering effects. Different later proposals after equivalent evidence do not by themselves demonstrate a selector effect.

## 5. What the traces explain

The C1 example separates two obligations that a header-only check can conflate: preventing future storage, and refusing unsafe reuse of existing entries. The natural patch explicitly redacts a cached Set-Cookie header. The minimized trace shows that this does not make the personalized body suitable for Bob.

A second observation concerns the oracle itself. The C3 initial bypasses local caching for authenticated, non-public requests; Alice and Bob receive their own bodies, and explicit public responses still reuse the cache. Our original checker nevertheless rejected it for omitting Authorization in Vary. The task card specified behavioral isolation, and the [pinned Django documentation](https://github.com/django/django/blob/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9/docs/topics/cache.txt#L1406) states that Vary is not strictly necessary under the HTTP authenticated-response rules. We removed this excessive header requirement in a recorded C3-only amendment, retained the original raw trajectories, and reused the same initial draws for corrected B/M/F continuations. Absence of Vary is not reported as an observed privacy disclosure. Extra requests already spent on the superseded strict feedback remain in gross usage.

CPU replay covers seven applicable natural initials on the preset subset. B/M/A/F all find one visible witness; their new-call totals are 36/36/31/36. Under the implemented symbol map, A reaches the C1 witness after five calls versus ten for B/M. The mapped read path was modified but semantically wrong. This single-patch diagnostic supports neither broad ranking superiority nor closed-loop A repair gains. Eight upstream buggy/fixed controls are reported separately.

In the exploratory 26B A4B initial-only screen, C1 exhausts the 32K generation budget without a patch, while C3 passes. The original four roots across both papers were retained after narrowing the scope; the saved extra continuation remains in historical usage. This is a configuration-specific screen, not a general architecture comparison.

The complete bank is affordable as an assessment tool here, but it does not guarantee a better generated repair. A small decrease in test-call count is not automatically an end-to-end speedup when hosted generation dominates elapsed time.

## 6. Related work and limits

PatchEval already combines exploit checks and functionality, including cache/auth behavior. PatchEval-Verified explicitly reduced coupling to particular patch shapes and false rejection of equivalent repairs. P2Patch already uses post-patch counterexamples, persistent obligations, and independent holdouts. We do not claim to introduce those mechanisms or to outperform systems we did not execute. Our additional evidence is the pinned cache-contract resource and the natural trajectories measured here. C1 (CVE-2026-84933) and C7 (CVE-2026-13697) are absent by CVE ID from the [fixed 230-CVE Verified metadata](https://github.com/bytedance/PatchEval/blob/b43285cdde80cc04608d5f1178a330b740c91c2d/patcheval/datasets/patcheval_verified.json); this limited instance check does not establish disjointness from the original 1,000-CVE dataset or every historical release.

The authors inspected public historical fixes; model pretraining contamination cannot be excluded. C1 also served as a technical smoke case while fixing the transport and patch compiler. Those calibration responses are excluded; formal draws use the frozen common adapter. This is not an untouched holdout benchmark. Contracts, context selection, and adapters require human work. Withheld inputs within one lineage are not independent natural bugs, and related fixes share a repository ecosystem. Our focused controls cover declared behaviors rather than the complete upstream suites. Hosted inference does not demonstrate offline throughput or exact QAT behavior.

Only one natural patch in the CPU subset supplies a visible residual witness. Approximate symbol/phase mapping, small banks, edit-representation failures, and few draws limit claims about evidence ranking.

## Reproduction

The [companion artifact](https://github.com/RayBerryHead/Gemma4-Contract-Repair) contains the pinned inputs, complete outcomes, patches, and reproduction scripts. After the conda/Node setup in its README, replay the main example without an API key:

```bash
export PYTHONPATH=src
python tools/configure_public.py
python tools/prepare_sources.py --artifact-root "$PWD/artifacts" --ids C1
python tools/replay_published.py --ids C1
```

The same replay includes information-condition patches where applicable; removing `--ids` from both preparation and replay covers the complete published patch index.

The package records full upstream revisions and licenses, frozen probe specifications, model settings, raw patch provenance, selected evidence, and the script producing the tables. API credentials and internal thought text/signatures are excluded from publication artifacts. All measured tests and analysis ran on GB10; the inference endpoint was hosted. The primary dataset contains 32 saved responses and 416,547 provider-reported tokens, counting each shared initial once. Superseded C3 trajectories and the abandoned 26B continuation remain in the gross-usage ledger. The two 26B screen initials report 53,557 tokens. Additional API/cloud cash charges are US$0 under the verified [Gemma API pricing](https://ai.google.dev/gemini-api/docs/pricing#gemma-4); no model training was performed.

## References

1. PatchEval. [arXiv:2511.11019](https://arxiv.org/abs/2511.11019).
2. PatchEval-Verified. [Official artifact](https://github.com/bytedance/PatchEval).
3. P2Patch. [arXiv:2610.20245](https://arxiv.org/abs/2610.20245).
4. HTTP Caching. [RFC 9111](https://httpwg.org/specs/rfc9111.html).
