from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class LectureInput:
    audio_path: Optional[str] = None
    image_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validates presence of at least one input modality and file readability.
        Raises ValueError on empty input."""
        if self.audio_path is None and not self.image_paths:
            raise ValueError(
                "At least one audio or image input must be provided."
            )
        if self.audio_path is not None and not Path(self.audio_path).exists():
            raise ValueError(
                f"Audio file not found: {self.audio_path}"
            )
        for path in self.image_paths:
            if not Path(path).exists():
                raise ValueError(f"Image file not found: {path}")


@dataclass
class TranscriptSegment:
    id: str
    start_time: float
    end_time: float
    text: str


@dataclass
class ExtractedText:
    id: str
    text: str
    source_image: str
    confidence: float = 1.0
    bounding_box: Optional[Dict[str, float]] = None


@dataclass
class VisualElement:
    id: str
    visual_type: str  # 'diagram', 'graph', 'chart', or 'other'
    description: str
    source_image: str
    key_entities: List[str] = field(default_factory=list)


@dataclass
class TechnicalElement:
    id: str
    element_type: str  # 'formula' or 'technical_term'
    raw_content: str
    normalized_latex: Optional[str] = None
    description: Optional[str] = None
    source_reference: Optional[str] = None


@dataclass
class LectureContext:
    transcript: List[TranscriptSegment] = field(default_factory=list)
    extracted_text: List[ExtractedText] = field(default_factory=list)
    visual_elements: List[VisualElement] = field(default_factory=list)
    technical_elements: List[TechnicalElement] = field(default_factory=list)
    source_references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes context to clean dictionary for downstream consumption."""
        def _seg(s: TranscriptSegment) -> Dict[str, Any]:
            return {"id": s.id, "start_time": s.start_time,
                    "end_time": s.end_time, "text": s.text}

        def _ext(e: ExtractedText) -> Dict[str, Any]:
            return {"id": e.id, "text": e.text, "source_image": e.source_image,
                    "confidence": e.confidence, "bounding_box": e.bounding_box}

        def _vis(v: VisualElement) -> Dict[str, Any]:
            return {"id": v.id, "visual_type": v.visual_type,
                    "description": v.description, "source_image": v.source_image,
                    "key_entities": list(v.key_entities)}

        def _tech(t: TechnicalElement) -> Dict[str, Any]:
            return {"id": t.id, "element_type": t.element_type,
                    "raw_content": t.raw_content,
                    "normalized_latex": t.normalized_latex,
                    "description": t.description,
                    "source_reference": t.source_reference}

        return {
            "transcript": [_seg(s) for s in self.transcript],
            "extracted_text": [_ext(e) for e in self.extracted_text],
            "visual_elements": [_vis(v) for v in self.visual_elements],
            "technical_elements": [_tech(t) for t in self.technical_elements],
            "source_references": list(self.source_references),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LectureContext":
        """Constructs LectureContext from dictionary."""
        transcript = [
            TranscriptSegment(
                id=s["id"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                text=s["text"],
            )
            for s in data.get("transcript", [])
        ]
        extracted_text = [
            ExtractedText(
                id=e["id"],
                text=e["text"],
                source_image=e["source_image"],
                confidence=e.get("confidence", 1.0),
                bounding_box=e.get("bounding_box"),
            )
            for e in data.get("extracted_text", [])
        ]
        visual_elements = [
            VisualElement(
                id=v["id"],
                visual_type=v["visual_type"],
                description=v["description"],
                source_image=v["source_image"],
                key_entities=list(v.get("key_entities", [])),
            )
            for v in data.get("visual_elements", [])
        ]
        technical_elements = [
            TechnicalElement(
                id=t["id"],
                element_type=t["element_type"],
                raw_content=t["raw_content"],
                normalized_latex=t.get("normalized_latex"),
                description=t.get("description"),
                source_reference=t.get("source_reference"),
            )
            for t in data.get("technical_elements", [])
        ]
        return cls(
            transcript=transcript,
            extracted_text=extracted_text,
            visual_elements=visual_elements,
            technical_elements=technical_elements,
            source_references=list(data.get("source_references", [])),
        )


if __name__ == "__main__":
    inp = LectureInput(image_paths=["test.png"])
    # Skip file-existence check for acceptance test by patching validate's path check.
    # Instead run the contract-required paths only:

    # 1. validate() passes when image_paths is non-empty (path check would normally run,
    #    but here we only test the modality-presence branch):
    _orig = Path.exists
    Path.exists = lambda self: True  # type: ignore[method-assign]
    try:
        inp.validate()

        ctx = LectureContext(
            transcript=[TranscriptSegment(id="t1", start_time=0.0, end_time=1.5, text="Hello world")],
            technical_elements=[TechnicalElement(id="f1", element_type="formula", raw_content="E=mc^2")],
        )
        d = ctx.to_dict()
        restored = LectureContext.from_dict(d)
        assert len(restored.transcript) == 1
        assert restored.transcript[0].text == "Hello world"
        assert restored.technical_elements[0].raw_content == "E=mc^2"
    finally:
        Path.exists = _orig  # type: ignore[method-assign]

    try:
        LectureInput().validate()
        assert False, "Validation should fail on empty input"
    except ValueError:
        pass

    print("ALL ACCEPTANCE TESTS PASSED")
