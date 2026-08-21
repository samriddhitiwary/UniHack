# Unilog Manufacturer and Brand Evidence

The evidence artifact is derived only from the supplied challenge input and two labelled output rows.
It is not official Unilog production master data.

`Part_Manuf` identifies an organizer-supplied organization and reference code. It is not automatically
a manufacturer. Dataset-observed supplier terms increase supplier likelihood and reduce manufacturer
likelihood. The exact parsed supplier remains available internally while delivery manufacturer stays
blank.

Placeholder brand fields remain missing. A consistent non-placeholder organizer brand is strong
evidence; conflicts remain ambiguous. Repeated description-leading phrases require at least three
distinct rows and a match to supplied observed brand vocabulary. MPN prefixes also require at least
three rows plus one corroborated candidate. Single-row prefixes cannot resolve.

Repeated manufacturer-brand and supplier-brand relations preserve support counts. These relations
describe feed observations, not corporate ownership. One organization may relate to multiple brands.

Manufacturer and brand confidence are separate from coverage and review status. Unknown or ambiguous
identity receives low field confidence and remains blank. Model suggestions require exact evidence,
observed vocabulary, and repeated dataset support, remain review-required, and never bypass
deterministic resolution.
