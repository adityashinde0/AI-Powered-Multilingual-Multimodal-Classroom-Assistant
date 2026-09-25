import re
import hashlib
from typing import List, Tuple, Dict, Optional

try:
    from src.models import TechnicalElement
except ModuleNotFoundError:
    from models import TechnicalElement  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Detection patterns — ordered from most specific to least specific
# ---------------------------------------------------------------------------

# LaTeX display math: $$...$$ (must come before single-$ to avoid substr match)
_DISPLAY_MATH = re.compile(r'\$\$[^$]+?\$\$', re.DOTALL)

# LaTeX inline math: $...$
_INLINE_MATH = re.compile(r'\$[^$\n]+?\$')

# LaTeX \(...\) inline
_PAREN_MATH = re.compile(r'\\\(.*?\\\)', re.DOTALL)

# LaTeX \[...\] display
_BRACKET_MATH = re.compile(r'\\\[.*?\\\]', re.DOTALL)

# Big-O / Theta / Omega complexity: O(n log n), O(n^2), Θ(n), Ω(1), etc.
_BIGO = re.compile(
    r'(?:[OΘΩo]|Theta|Omega)\s*\([^)]+\)'
)

# Standalone equations: contain =, <=, >=, ≤, ≥, \approx, ^, _
# Must have at least one operator and look like math (no pure prose)
_EQUATION = re.compile(
    r'(?<!\w)'                          # not preceded by a word char
    r'(?:[A-Za-z0-9_^\\{}\[\]]+\s*'   # lhs token(s)
    r'(?:[+\-*/^_]?\s*)*'
    r'(?:=|<=|>=|≤|≥|\\approx|\\neq|\\equiv)\s*'
    r'[A-Za-z0-9_^\\{}\[\]()+\-*/\s]+)'
    r'(?!\w)',
    re.UNICODE,
)

# Power expressions without an explicit operator: a^2 + b^2 = c^2 style
# (caught partially by _EQUATION above, but also standalone x^n)
_POWER_EXPR = re.compile(
    r'[A-Za-z]\^[0-9]+(?:\s*[+\-]\s*[A-Za-z]\^[0-9]+)*'
    r'(?:\s*=\s*[A-Za-z]\^[0-9]+)?'
)

_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (_DISPLAY_MATH,  "formula"),
    (_BRACKET_MATH,  "formula"),
    (_PAREN_MATH,    "formula"),
    (_INLINE_MATH,   "formula"),
    (_BIGO,          "formula"),
    (_EQUATION,      "formula"),
    (_POWER_EXPR,    "formula"),
]


def _make_id(raw: str, index: int) -> str:
    digest = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"tech_{digest}_{index}"


def extract_technical_elements(
    text: str,
    source_reference: Optional[str] = None,
) -> List[TechnicalElement]:
    """Detects formulas (LaTeX, equations, math notation, Big-O) and technical
    terms from text. Returns list of TechnicalElement instances."""
    if not text:
        return []

    # Collect all (start, end, raw_content, element_type) matches
    spans: List[Tuple[int, int, str, str]] = []
    seen_ranges: List[Tuple[int, int]] = []

    for pattern, etype in _PATTERNS:
        for m in pattern.finditer(text):
            s, e = m.start(), m.end()
            raw = m.group(0).strip()
            if not raw:
                continue
            # Skip if this span overlaps with an already-recorded span
            if any(s < er and e > sr for sr, er in seen_ranges):
                continue
            seen_ranges.append((s, e))
            spans.append((s, e, raw, etype))

    # Sort by position for stable IDs
    spans.sort(key=lambda x: x[0])

    elements: List[TechnicalElement] = []
    seen_raw: set = set()
    for idx, (_, _, raw, etype) in enumerate(spans):
        if raw in seen_raw:
            continue
        seen_raw.add(raw)
        elements.append(
            TechnicalElement(
                id=_make_id(raw, idx),
                element_type=etype,
                raw_content=raw,
                normalized_latex=raw if raw.startswith("$") else None,
                source_reference=source_reference,
            )
        )

    return elements


def mask_technical_elements(
    text: str,
    elements: List[TechnicalElement],
) -> Tuple[str, Dict[str, str]]:
    """Replaces detected formulas/terms with opaque placeholders (e.g. __TECH_0__)
    so machine translation does not mangle them.
    Returns (masked_text, placeholder_map)."""
    if not text or not elements:
        return text, {}

    # Sort longest-first to avoid substring replacement corrupting longer matches
    sorted_elems = sorted(elements, key=lambda e: len(e.raw_content), reverse=True)

    masked = text
    placeholder_map: Dict[str, str] = {}

    for idx, elem in enumerate(sorted_elems):
        placeholder = f"__TECH_{idx}__"
        if elem.raw_content in masked:
            masked = masked.replace(elem.raw_content, placeholder, 1)
            placeholder_map[placeholder] = elem.raw_content

    return masked, placeholder_map


def unmask_technical_elements(
    masked_text: str,
    placeholder_map: Dict[str, str],
) -> str:
    """Restores masked placeholders in text back to their exact original raw content."""
    if not masked_text or not placeholder_map:
        return masked_text

    result = masked_text
    for placeholder, original in placeholder_map.items():
        result = result.replace(placeholder, original)
    return result


if __name__ == "__main__":
    sample = "The time complexity is O(n log n) and energy is $E=mc^2$ where a^2 + b^2 = c^2 holds."
    elems = extract_technical_elements(sample, source_reference="lecture_1")
    assert len(elems) >= 2, f"Expected at least 2 elements, got {len(elems)}: {[e.raw_content for e in elems]}"

    masked, pmap = mask_technical_elements(sample, elems)
    assert "$E=mc^2$" not in masked, f"Inline math still present: {masked}"
    assert "O(n log n)" not in masked, f"Big-O still present: {masked}"

    restored = unmask_technical_elements(masked, pmap)
    assert restored == sample, (
        f"Restoration mismatch:\nExpected: {sample}\nGot:      {restored}"
    )

    # Edge cases
    assert extract_technical_elements("") == []
    empty_masked, empty_map = mask_technical_elements("", [])
    assert empty_masked == "" and empty_map == {}
    assert unmask_technical_elements("", {}) == ""

    print("ALL FORMULA/TECHNICAL ACCEPTANCE TESTS PASSED")
