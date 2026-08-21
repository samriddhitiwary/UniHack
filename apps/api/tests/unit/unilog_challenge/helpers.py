"""Shared deterministic challenge test factories."""

from app.domain.unilog_challenge import ManufacturerParseStatus, UnilogChallengeInputRow
from app.services.unilog_challenge.cleansing import clean_challenge_value
from app.services.unilog_challenge.manufacturer import parse_part_manufacturer


def challenge_row(
    *,
    row_id: str = "a" * 64,
    part: str = "DCB518ASTS06G",
    description: str = 'DCB518ASTS06G Diablo 1/2"x18" Sanding Belt 6pc P150',
    e1: str = "Diablo",
    unilog: str = "-- No Unilog Brand --",
    dib: str = "-- No DIB Brand --",
    manufacturer: str = "Diablo Tools (DIA01)",
) -> UnilogChallengeInputRow:
    parsed = parse_part_manufacturer(manufacturer)
    return UnilogChallengeInputRow(
        row_id=row_id,
        source_row_number=2,
        mfg_part_num=part,
        part_desc=description,
        e1_brand_raw=e1,
        unilog_brand_raw=unilog,
        dib_brand_raw=dib,
        part_manuf_raw=manufacturer,
        e1_brand_clean=clean_challenge_value(e1),
        unilog_brand_clean=clean_challenge_value(unilog),
        dib_brand_clean=clean_challenge_value(dib),
        parsed_manufacturer=parsed.manufacturer_text,
        source_reference_code=parsed.source_reference_code,
        manufacturer_parse_status=parsed.status,
    )


def assert_parsed() -> ManufacturerParseStatus:
    return ManufacturerParseStatus.PARSED
