"""Fixed Decimal unit registry limited to existing motor and pump schemas."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.attribute_normalization.enums import UnitDimension


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitNormalizationRule:
    dimension: UnitDimension
    source_unit: str
    canonical_unit: str
    aliases: tuple[str, ...]
    factor: Decimal
    conversion_rule: str | None = None


def _rule(
    dimension: UnitDimension,
    source: str,
    canonical: str,
    aliases: tuple[str, ...],
    factor: str = "1",
    conversion: str | None = None,
) -> UnitNormalizationRule:
    return UnitNormalizationRule(
        dimension=dimension,
        source_unit=source,
        canonical_unit=canonical,
        aliases=aliases,
        factor=Decimal(factor),
        conversion_rule=conversion,
    )


UNIT_RULES = (
    _rule(UnitDimension.POWER, "kW", "kW", ("kw",)),
    _rule(UnitDimension.POWER, "W", "kW", ("w",), "0.001", "W_TO_KW"),
    _rule(UnitDimension.POWER, "hp", "kW", ("hp",), "0.745699872", "HP_TO_KW"),
    _rule(UnitDimension.VOLTAGE, "V", "V", ("v", "volt", "volts")),
    _rule(UnitDimension.CURRENT, "A", "A", ("a", "amp", "amps", "ampere", "amperes")),
    _rule(UnitDimension.FREQUENCY, "Hz", "Hz", ("hz", "hertz")),
    _rule(
        UnitDimension.ROTATIONAL_SPEED,
        "rpm",
        "rpm",
        ("rpm", "r/min", "rev/min", "revolutions per minute"),
    ),
    _rule(UnitDimension.PERCENT, "%", "%", ("%", "percent", "percentage")),
    _rule(UnitDimension.FLOW_RATE, "m3/h", "m3/h", ("m3/h", "m³/h", "m3/hr", "m³/hr")),
    _rule(UnitDimension.FLOW_RATE, "L/min", "m3/h", ("l/min", "lpm"), "0.06", "L_MIN_TO_M3_H"),
    _rule(UnitDimension.FLOW_RATE, "gpm", "m3/h", ("gpm",), "0.22712470704", "US_GPM_TO_M3_H"),
    _rule(UnitDimension.LENGTH, "m", "m", ("m", "meter", "metre", "meters", "metres")),
    _rule(UnitDimension.LENGTH, "ft", "m", ("ft", "feet", "foot"), "0.3048", "FT_TO_M"),
    _rule(
        UnitDimension.DIAMETER,
        "mm",
        "mm",
        ("mm", "millimeter", "millimetre", "millimeters", "millimetres"),
    ),
    _rule(UnitDimension.DIAMETER, "in", "mm", ("in", "inch", "inches", '"'), "25.4", "IN_TO_MM"),
    _rule(UnitDimension.PRESSURE, "bar", "bar", ("bar",)),
    _rule(UnitDimension.PRESSURE, "psi", "bar", ("psi",), "0.0689475729", "PSI_TO_BAR"),
)


ATTRIBUTE_DIMENSIONS = {
    "ratedPower": UnitDimension.POWER,
    "voltage": UnitDimension.VOLTAGE,
    "current": UnitDimension.CURRENT,
    "frequency": UnitDimension.FREQUENCY,
    "speedRpm": UnitDimension.ROTATIONAL_SPEED,
    "efficiency": UnitDimension.PERCENT,
    "flowRate": UnitDimension.FLOW_RATE,
    "head": UnitDimension.LENGTH,
    "npshRequired": UnitDimension.LENGTH,
    "suctionSize": UnitDimension.DIAMETER,
    "dischargeSize": UnitDimension.DIAMETER,
    "impellerDiameter": UnitDimension.DIAMETER,
    "maximumPressure": UnitDimension.PRESSURE,
}
