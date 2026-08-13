"""Mockable local OCR protocol and RapidOCR ONNX Runtime adapter."""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from importlib.metadata import PackageNotFoundError, version
from typing import Protocol

import numpy as np
from PIL import Image

from app.core.exceptions import (
    ImageOcrEngineError,
    ImageOcrEngineUnavailableError,
    ImageOcrRegionInvalidError,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OcrEngineBlock:
    text: str
    confidence_bp: int
    x: int
    y: int
    width: int
    height: int


class OcrEngine(Protocol):
    @property
    def engine_name(self) -> str: ...

    @property
    def engine_version(self) -> str: ...

    def recognize(self, image: Image.Image) -> tuple[OcrEngineBlock, ...]: ...


def confidence_to_basis_points(value: object) -> int:
    """Convert RapidOCR's 0..1 score into deterministic integer basis points."""
    if isinstance(value, bool):
        raise ImageOcrRegionInvalidError()
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ImageOcrRegionInvalidError() from exc
    if not Decimal(0) <= decimal <= Decimal(1):
        raise ImageOcrRegionInvalidError()
    return int((decimal * 10_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class RapidOcrEngine:
    """On-device OCR using bundled ONNX models and no hosted service."""

    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]

            self._engine = RapidOCR()
            self._version = version("rapidocr-onnxruntime")
        except (ImportError, OSError, PackageNotFoundError, RuntimeError) as exc:
            raise ImageOcrEngineUnavailableError() from exc

    @property
    def engine_name(self) -> str:
        return "RapidOCR-ONNXRuntime"

    @property
    def engine_version(self) -> str:
        return self._version

    def recognize(self, image: Image.Image) -> tuple[OcrEngineBlock, ...]:
        try:
            raw_result, _ = self._engine(np.asarray(image.convert("RGB")), text_score=0.0)
            if raw_result is None:
                return ()
            return tuple(self._block(value, image.width, image.height) for value in raw_result)
        except (ImageOcrRegionInvalidError, ImageOcrEngineError):
            raise
        except Exception as exc:
            raise ImageOcrEngineError() from exc

    @staticmethod
    def _block(value: object, image_width: int, image_height: int) -> OcrEngineBlock:
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ImageOcrRegionInvalidError()
        raw_box, raw_text, raw_confidence = value[0], value[1], value[2]
        if not isinstance(raw_text, str) or not isinstance(raw_box, (list, tuple)):
            raise ImageOcrRegionInvalidError()
        points: list[tuple[float, float]] = []
        for point in raw_box:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                raise ImageOcrRegionInvalidError()
            x, y = point[0], point[1]
            if (
                isinstance(x, bool)
                or isinstance(y, bool)
                or not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
                or not math.isfinite(float(x))
                or not math.isfinite(float(y))
            ):
                raise ImageOcrRegionInvalidError()
            points.append((float(x), float(y)))
        if not points:
            raise ImageOcrRegionInvalidError()
        left = math.floor(min(point[0] for point in points))
        top = math.floor(min(point[1] for point in points))
        right = math.ceil(max(point[0] for point in points))
        bottom = math.ceil(max(point[1] for point in points))
        if left < 0 or top < 0 or right > image_width or bottom > image_height:
            raise ImageOcrRegionInvalidError()
        if right <= left or bottom <= top:
            raise ImageOcrRegionInvalidError()
        return OcrEngineBlock(
            text=raw_text,
            confidence_bp=confidence_to_basis_points(raw_confidence),
            x=left,
            y=top,
            width=right - left,
            height=bottom - top,
        )
