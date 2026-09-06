# Matching review — 6 September 2026

**Agent-assisted official-source corroboration, not a human-independent precision release gate.**

26 purposeful cases from September 3 automated 294-pair audit: all five conflicts, every twentieth normal audit row, and doubleheader/team-alias strata; earliest stored match for each. Nonrandom and not blind.

Result: 26/26 sampled event identities corroborated; 0 unresolved. No EXACT decisions were sampled, so zero demonstrated mismatches here is not a 99% EXACT precision claim. Recall was not measured.

Every case was checked against a unique official MLB fixture by participant names and start, source event IDs, exact token-to-team identities, contract IDs, and the hash of its immutable historical source report. The five conflicts additionally matched MLB rescheduledFromDate to the older Polymarket slug date. Parent separately refetched all five MLB schedules.

| Kalshi fixture | MLB gamePk | Label |
|---|---:|---|
| KXMLBGAME-26AUG171340STLCING1 | 824514 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG201410ATLCWS | 824589 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG291305BOSNYYG1 | 823539 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG311805SFATL | 824911 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26SEP041410DETCLEG1 | 824424 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG121340BALMIN | 823672 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG131605CHCWSH | 822696 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG151507NYYTOR | 822775 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG161340WSHNYM | 823590 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG181840MIAPHI | 823423 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG191840SFCLE | 824394 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG211910WSHMIA | 823830 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG242145CINSF | 823183 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG261610PHISEA | 823096 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG281845MIAWSH | 822691 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG291610HOUNYM | 823582 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG301607PHILAA | 823987 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26SEP011940MIAKC | 824070 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26SEP022010CWSHOU | 824147 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26SEP042005TBTEX | 822852 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG171840STLCING2 | 824478 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG121505TBATH | 824967 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG121540COLAZ | 825047 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG121845CHCWSH | 822698 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG121915NYMATL | 824883 | CORROBORATED_EVENT_IDENTITY |
| KXMLBGAME-26AUG122210KCLAD | 823916 | CORROBORATED_EVENT_IDENTITY |

## Code defects fixed and limits

Reverse ambiguity now rejects two Kalshi fixtures competing for one Polymarket fixture. Malformed binary arrays and duplicate token IDs are rejected. Fractional time differences are compared before integer conversion. Existing small-page traversal preserves the bounded catalog and fails on cursor loops. Regression tests exercise each case; no eligibility logic was relaxed.

The production source-identifier audit remains conservative: all five slug-date discrepancies stay quarantined in resolution counts, despite evidence-level makeup corroboration. A review override requires a separately versioned provenance policy, not an ad hoc bypass.

Sources, per-check results and preserved raw captures: [review JSON](../data/reports/matching-independent-review.json). Reviewers timed out; their partial source collection was re-read and evaluated by the parent, not accepted as a completed independent sign-off.
