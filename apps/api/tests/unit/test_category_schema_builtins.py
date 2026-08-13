"""Approved motor/pump v1 schema contract tests."""

import pytest

from app.core.exceptions import CategoryAttributeSchemaNotAvailableError
from app.domain.category_schemas import CategoryAttributeSchemaStatus
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.domain.products import ProductCategory
from app.services.category_schemas import CategoryAttributeSchemaService


class BuiltinRepository:
    def __init__(self) -> None:
        self.schemas = {
            (schema.category, schema.version): schema
            for schema in (centrifugal_pump_schema_v1(), induction_motor_schema_v1())
        }

    def get_by_category_and_version(self, category, version):
        return self.schemas.get((category, version))

    def get_active_by_category(self, category):
        return next(
            (
                schema
                for (item_category, _), schema in self.schemas.items()
                if item_category is category
                and schema.status is CategoryAttributeSchemaStatus.ACTIVE
            ),
            None,
        )

    def create(self, schema):
        self.schemas[(schema.category, schema.version)] = schema
        return schema


def test_motor_v1_has_exact_approved_attributes_requiredness_aliases_and_units() -> None:
    schema = induction_motor_schema_v1()
    by_name = {attribute.canonical_name: attribute for attribute in schema.attributes}
    assert set(by_name) == {
        "ratedPower",
        "voltage",
        "current",
        "frequency",
        "speedRpm",
        "efficiency",
        "powerFactor",
        "phase",
        "insulationClass",
        "ipRating",
        "frameSize",
        "duty",
        "mountingType",
    }
    assert {name for name, attribute in by_name.items() if attribute.required} == {
        "ratedPower",
        "voltage",
        "frequency",
        "speedRpm",
        "phase",
    }
    assert tuple(unit.symbol for unit in by_name["ratedPower"].allowed_units) == ("kW", "W", "hp")
    service = CategoryAttributeSchemaService(BuiltinRepository())
    for alias, expected in {
        "rated output": "ratedPower",
        "motor power": "ratedPower",
        "rated voltage": "voltage",
        "rated speed": "speedRpm",
        "rpm": "speedRpm",
        "power factor": "powerFactor",
        "cos phi": "powerFactor",
        "ip rating": "ipRating",
    }.items():
        assert (
            service.resolve_alias(
                category=ProductCategory.INDUCTION_MOTOR, alias=alias
            ).canonical_name
            == expected
        )


def test_pump_v1_has_exact_approved_attributes_requiredness_aliases_and_units() -> None:
    schema = centrifugal_pump_schema_v1()
    by_name = {attribute.canonical_name: attribute for attribute in schema.attributes}
    assert set(by_name) == {
        "flowRate",
        "head",
        "maximumPressure",
        "speedRpm",
        "ratedPower",
        "efficiency",
        "suctionSize",
        "dischargeSize",
        "impellerDiameter",
        "sealType",
        "material",
        "npshRequired",
    }
    assert {name for name, attribute in by_name.items() if attribute.required} == {
        "flowRate",
        "head",
    }
    assert tuple(unit.symbol for unit in by_name["flowRate"].allowed_units) == (
        "m3/h",
        "L/min",
        "gpm",
    )
    service = CategoryAttributeSchemaService(BuiltinRepository())
    for alias, expected in {
        "capacity": "flowRate",
        "rated flow": "flowRate",
        "delivery head": "head",
        "tdh": "head",
        "max pressure": "maximumPressure",
        "outlet diameter": "dischargeSize",
        "inlet diameter": "suctionSize",
        "impeller size": "impellerDiameter",
        "npshr": "npshRequired",
    }.items():
        assert (
            service.resolve_alias(
                category=ProductCategory.CENTRIFUGAL_PUMP, alias=alias
            ).canonical_name
            == expected
        )


def test_alias_resolution_is_category_scoped_and_unclassified_is_unavailable() -> None:
    service = CategoryAttributeSchemaService(BuiltinRepository())
    assert service.resolve_alias(category=ProductCategory.INDUCTION_MOTOR, alias="capacity") is None
    with pytest.raises(CategoryAttributeSchemaNotAvailableError):
        service.get_active_schema(category=ProductCategory.UNCLASSIFIED)
