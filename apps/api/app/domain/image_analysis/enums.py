"""Image-analysis evidence enumerations."""

from enum import StrEnum


class ImageOrientation(StrEnum):
    NORMAL = "NORMAL"
    ROTATED_90 = "ROTATED_90"
    ROTATED_180 = "ROTATED_180"
    ROTATED_270 = "ROTATED_270"
    MIRRORED = "MIRRORED"
    UNKNOWN = "UNKNOWN"


class ImageRegionType(StrEnum):
    FULL_IMAGE = "FULL_IMAGE"
    CENTER = "CENTER"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class NameplateCandidateStatus(StrEnum):
    POSSIBLE = "POSSIBLE"
    UNLIKELY = "UNLIKELY"
    UNKNOWN = "UNKNOWN"
