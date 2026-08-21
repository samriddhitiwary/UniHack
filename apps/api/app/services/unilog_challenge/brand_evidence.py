"""Keep organizer brand fields distinct while deriving bounded candidates."""

from app.domain.unilog_challenge import BrandEvidence, UnilogChallengeInputRow


def extract_brand_evidence(row: UnilogChallengeInputRow) -> BrandEvidence:
    candidates = tuple(
        dict.fromkeys(
            value
            for value in (
                row.e1_brand_clean,
                row.unilog_brand_clean,
                row.dib_brand_clean,
            )
            if value is not None
        )
    )
    return BrandEvidence(
        e1_raw=row.e1_brand_raw,
        unilog_raw=row.unilog_brand_raw,
        dib_raw=row.dib_brand_raw,
        e1_clean=row.e1_brand_clean,
        unilog_clean=row.unilog_brand_clean,
        dib_clean=row.dib_brand_clean,
        candidate_brand_strings=candidates,
        description_text=row.part_desc,
    )
