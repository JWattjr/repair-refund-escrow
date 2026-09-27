# Security notes

## Terms and permissions

- The constructor sender is the buyer. The constructor names one different supplier and freezes the brief, criterion allocations, delivery and resolution deadlines, claim window, and repair limit. The remedy policy is fixed: release accepted or remedied criterion allocations; refund full allocations for defects still open at the repair limit or final deadline.
- The supplier must accept the exact terms digest before submitting work. Supplier rejection returns the full demo escrow. Before initial delivery, cancellation requires buyer request plus supplier confirmation. If acceptance or delivery is overdue, any participant can finalize the full refund.
- Only the buyer may submit the one initial claim batch. Each criterion can appear at most once. The buyer cannot file new claims after that assessment; repair reviews may only assess existing claims.
- The supplier can submit no more than the constructor-fixed number of repair versions. Anyone can submit a repair review, avoiding exclusive buyer control of the review call. Final deadline expiry settles the remaining allocations deterministically.

## Consensus and evidence

- Defect assessment binds the brief, exact criterion descriptions and allocations, current version, allegation, delivery URL, evidence URL, fetched bodies, and terms digest into one snapshot. Repair assessment binds the same frozen criteria and only open established defects to the new version.
- Validators independently fetch each required page and rerun the substantive judgment. Results must use exact criterion order, known citation URLs, valid findings, and the snapshot digest. Missing evidence requires `UNCERTAIN`; unknown fields, invented references, malformed schemas, or disagreement fail closed.
- Submitted summaries, allegations, criteria descriptions, and fetched page text are untrusted prompt data. HTTPS syntax checks do not verify publisher identity, signatures, DNS resolution, redirects, timestamps, or freshness.

## Accounting and limits

- Criterion allocations are positive integers and must sum exactly to the constructor budget. Settlement changes the one escrow balance once; aggregate escrow, supplier release, and buyer refund must equal the original total.
- Up to 8 criteria, one initial claim per criterion, 3 repair versions, 30-day review windows, bounded text/evidence, and bounded URLs keep work finite.
- A resolved defect releases that whole criterion allocation; a still-open or uncertain defect returns that whole allocation. There is no model-selected percentage or arbitrary deduction.
- The ledger uses synthetic demo units. It has no real token custody, arbitration, or independent proof that work was performed. Direct tests use mocked model/web responses; live validator behavior and target-chain runner availability remain unverified.
