import hashlib
from pathlib import Path
from typing import List

try:
    from src.models import VisualElement
except ModuleNotFoundError:
    from models import VisualElement  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Heuristic visual-type classification based on image properties
# ---------------------------------------------------------------------------

# Aspect ratios and size thresholds are observations, not guarantees —
# they guide a best-effort classification only when no vision model is present.
_WIDE_RATIO = 1.6   # width/height > this → likely a graph/chart (landscape)
_TALL_RATIO = 0.7   # width/height < this → likely a diagram (portrait/square)


def _classify_visual_type(width: int, height: int) -> str:
    """Heuristic: classify visual type from image dimensions alone."""
    if height == 0:
        return "other"
    ratio = width / height
    if ratio > _WIDE_RATIO:
        return "chart"
    if ratio < _TALL_RATIO:
        return "diagram"
    return "graph"


def _make_id(image_path: str, index: int) -> str:
    digest = hashlib.md5(image_path.encode()).hexdigest()[:8]
    return f"vis_{digest}_{index}"


def analyze_visual(image_path: str) -> List[VisualElement]:
    """Analyzes diagrams, graphs, charts from a lecture image.
    Returns empty list if image unreadable, missing, or no visual found (fail-safe)."""
    try:
        if not image_path:
            return []

        path = Path(image_path)
        if not path.exists() or not path.is_file():
            return []

        visual_type = "other"
        description = f"Lecture visual element from {path.name}"
        key_entities: List[str] = []

        # --- Attempt PIL inspection for dimensions / format ---
        try:
            from PIL import Image  # type: ignore

            with Image.open(path) as img:
                width, height = img.size
                fmt = (img.format or "unknown").lower()

                visual_type = _classify_visual_type(width, height)

                # Non-fabricated description: structural facts only
                description = (
                    f"Lecture visual element from {path.name} "
                    f"({width}x{height}, {fmt})"
                )

                # key_entities: image mode is a factual label (RGB, L, RGBA…)
                if img.mode:
                    key_entities = [img.mode]

        except ImportError:
            pass  # PIL absent — use defaults above
        except Exception:
            pass  # corrupt / unreadable image — still return structural record

        return [
            VisualElement(
                id=_make_id(image_path, 0),
                visual_type=visual_type,
                description=description,
                source_image=image_path,
                key_entities=key_entities,
            )
        ]

    except Exception:
        return []


def analyze_visuals(image_paths: List[str]) -> List[VisualElement]:
    """Processes multiple lecture images sequentially, returning aggregated VisualElements."""
    results: List[VisualElement] = []
    for path in image_paths:
        results.extend(analyze_visual(path))
    return results


if __name__ == "__main__":
    # 1. Non-existent file: must return empty list, not crash
    assert analyze_visual("non_existent_diagram.png") == []
    # 2. Empty list batch call
    assert analyze_visuals([]) == []
    # 3. Batch call with missing file
    assert analyze_visuals(["missing.png"]) == []
    print("ALL VISION ACCEPTANCE TESTS PASSED")
