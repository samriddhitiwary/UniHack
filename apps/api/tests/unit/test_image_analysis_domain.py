"""Image metadata, regions, heuristic, and immutable result tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.image_analysis import (
    REGION_ORDER,
    ImageMetadata,
    ImageOrientation,
    NameplateCandidateStatus,
    assess_nameplate_candidate,
    generate_analysis_regions,
)
from tests.fixtures.image_analysis import make_image_analysis_result


def test_regions_are_complete_ordered_bounded_and_basis_point_safe() -> None:
    regions = generate_analysis_regions(401, 201, 100)
    assert tuple(region.region_type for region in regions) == REGION_ORDER
    full = regions[0]
    assert (full.x, full.y, full.width, full.height) == (0, 0, 401, 201)
    assert (
        full.relative_x_bp,
        full.relative_y_bp,
        full.relative_width_bp,
        full.relative_height_bp,
    ) == (0, 0, 10_000, 10_000)
    for region in regions:
        assert region.width > 0 and region.height > 0
        assert region.x + region.width <= 401 and region.y + region.height <= 201
        assert region.relative_x_bp + region.relative_width_bp <= 10_000


def test_tiny_images_still_generate_safe_six_regions() -> None:
    regions = generate_analysis_regions(1, 1, 0)
    assert len(regions) == 6
    assert all(
        (region.x, region.y, region.width, region.height) == (0, 0, 1, 1) for region in regions
    )


@pytest.mark.parametrize(
    ("width", "height", "status", "score"),
    [
        (400, 200, NameplateCandidateStatus.POSSIBLE, 100),
        (100, 50, NameplateCandidateStatus.UNLIKELY, 30),
        (250, 100, NameplateCandidateStatus.UNKNOWN, 30),
    ],
)
def test_candidate_heuristic_is_deterministic_and_bounded(
    width: int, height: int, status: NameplateCandidateStatus, score: int
) -> None:
    assert assess_nameplate_candidate(width, height) == (status, score)
    assert assess_nameplate_candidate(width, height) == (status, score)
    assert 0 <= score <= 100


def test_result_is_immutable_and_domain_invariants_are_enforced() -> None:
    result = make_image_analysis_result()
    assert result.nameplate_candidate_status is NameplateCandidateStatus.POSSIBLE
    with pytest.raises(FrozenInstanceError):
        result.heuristic_score = 0  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(result, heuristic_score=0)
    with pytest.raises(ValueError):
        replace(result, regions=tuple(reversed(result.regions)))


def test_metadata_rejects_invalid_pixel_or_aspect_evidence() -> None:
    metadata = make_image_analysis_result().metadata
    with pytest.raises(ValueError):
        replace(metadata, pixel_count=1)
    with pytest.raises(ValueError):
        replace(metadata, aspect_ratio_numerator=1)
    with pytest.raises(ValueError):
        ImageMetadata(
            format="GIF",
            mime_type="image/gif",
            width=1,
            height=1,
            pixel_count=1,
            aspect_ratio_numerator=1,
            aspect_ratio_denominator=1,
            color_mode="RGB",
            has_alpha=False,
            is_grayscale=False,
            orientation=ImageOrientation.NORMAL,
            file_size_bytes=1,
        )
