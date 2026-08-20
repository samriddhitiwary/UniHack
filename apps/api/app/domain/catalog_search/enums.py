"""Deliberate Product catalog query plans."""

from enum import StrEnum


class CatalogSearchAccessPattern(StrEnum):
    CREATED_AT = "CREATED_AT"
    STATUS = "STATUS"
    CATEGORY = "CATEGORY"
    CATEGORY_STATUS = "CATEGORY_STATUS"
    MANUFACTURER = "MANUFACTURER"
    MODEL_NUMBER = "MODEL_NUMBER"
    NAME_PREFIX = "NAME_PREFIX"
