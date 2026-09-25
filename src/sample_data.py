"""
DATA-02: Multi-domain lecture repository.
Three benchmark LectureContext objects covering Algorithms, Machine Learning,
and Physics of Computing.
"""
from typing import Dict

try:
    from src.models import (
        LectureContext, TranscriptSegment, ExtractedText,
        VisualElement, TechnicalElement,
    )
except ModuleNotFoundError:
    from models import (  # type: ignore[no-redef]
        LectureContext, TranscriptSegment, ExtractedText,
        VisualElement, TechnicalElement,
    )

# ---------------------------------------------------------------------------
# Lecture 1: Algorithms — Quicksort & Complexity
# ---------------------------------------------------------------------------
_LECTURE_ALGORITHMS = LectureContext(
    transcript=[
        TranscriptSegment(
            id="a_s1", start_time=0.0, end_time=7.0,
            text="Quicksort was invented by Tony Hoare in 1959 and is one of the most widely used sorting algorithms in practice.",
        ),
        TranscriptSegment(
            id="a_s2", start_time=7.0, end_time=14.0,
            text="The algorithm selects a pivot element and partitions the array so that elements smaller than the pivot appear on the left and larger elements on the right.",
        ),
        TranscriptSegment(
            id="a_s3", start_time=14.0, end_time=21.0,
            text="This divide-and-conquer strategy gives an average-case time complexity of O(n log n), described by the recurrence T(n) = 2T(n/2) + O(n).",
        ),
        TranscriptSegment(
            id="a_s4", start_time=21.0, end_time=28.0,
            text="The worst case occurs when the pivot is always the minimum or maximum element, degrading to O(n^2), which is why randomised pivot selection is recommended.",
        ),
    ],
    extracted_text=[
        ExtractedText(
            id="a_e1", text="Average case: O(n log n) — balanced partitions",
            source_image="whiteboard_algo.png", confidence=0.96,
        ),
        ExtractedText(
            id="a_e2", text="Worst case: O(n^2) — pivot always min or max",
            source_image="whiteboard_algo.png", confidence=0.94,
        ),
        ExtractedText(
            id="a_e3", text="Recurrence: T(n) = 2T(n/2) + O(n)  =>  O(n log n) by Master Theorem",
            source_image="whiteboard_algo.png", confidence=0.91,
        ),
    ],
    visual_elements=[
        VisualElement(
            id="a_v1", visual_type="diagram",
            description="Recursion tree diagram showing Quicksort divide-and-conquer: each level performs O(n) total work across all partitions, giving O(log n) levels.",
            source_image="tree.png",
            key_entities=["recursion tree", "partition", "pivot", "subarray", "divide-and-conquer"],
        ),
    ],
    technical_elements=[
        TechnicalElement(id="a_t1", element_type="formula", raw_content="O(n log n)", description="Average/best-case Quicksort complexity"),
        TechnicalElement(id="a_t2", element_type="formula", raw_content="O(n^2)",    description="Worst-case Quicksort complexity"),
        TechnicalElement(id="a_t3", element_type="formula", raw_content="T(n) = 2T(n/2) + O(n)", description="Divide-and-conquer recurrence"),
        TechnicalElement(id="a_t4", element_type="technical_term", raw_content="divide-and-conquer", description="Algorithmic paradigm"),
        TechnicalElement(id="a_t5", element_type="technical_term", raw_content="pivot",              description="Partition reference element"),
    ],
    source_references=["whiteboard_algo.png", "tree.png"],
)

# ---------------------------------------------------------------------------
# Lecture 2: Machine Learning — Gradient Descent
# ---------------------------------------------------------------------------
_LECTURE_ML = LectureContext(
    transcript=[
        TranscriptSegment(
            id="ml_s1", start_time=0.0, end_time=7.0,
            text="Gradient descent is an iterative optimisation algorithm that minimises a cost function by moving in the direction of steepest descent.",
        ),
        TranscriptSegment(
            id="ml_s2", start_time=7.0, end_time=14.0,
            text="The update rule is theta_{t+1} = theta_t - alpha * gradient of L(theta), where alpha is the learning rate controlling step size.",
        ),
        TranscriptSegment(
            id="ml_s3", start_time=14.0, end_time=21.0,
            text="The cost function for linear regression is L = (1/2m) * sum of squared residuals between predictions y-hat and true values y.",
        ),
        TranscriptSegment(
            id="ml_s4", start_time=21.0, end_time=28.0,
            text="A learning rate alpha that is too large causes divergence; too small causes slow convergence. Adaptive methods like Adam adjust alpha dynamically.",
        ),
        TranscriptSegment(
            id="ml_s5", start_time=28.0, end_time=35.0,
            text="Stochastic gradient descent uses a single sample per update, mini-batch uses a subset, and batch gradient descent uses the full training set.",
        ),
    ],
    extracted_text=[
        ExtractedText(
            id="ml_e1",
            text="Update rule: theta_{t+1} = theta_t - alpha * nabla L(theta)",
            source_image="whiteboard_ml.png", confidence=0.95,
        ),
        ExtractedText(
            id="ml_e2",
            text="MSE cost: L = (1/2m) * sum(y - y_hat)^2",
            source_image="whiteboard_ml.png", confidence=0.93,
        ),
        ExtractedText(
            id="ml_e3",
            text="Learning rate alpha: too large -> diverge, too small -> slow",
            source_image="whiteboard_ml.png", confidence=0.90,
        ),
    ],
    visual_elements=[
        VisualElement(
            id="ml_v1", visual_type="graph",
            description="Loss contour plot showing gradient descent trajectory from initial parameters to minimum. Each step follows the negative gradient direction.",
            source_image="contour.png",
            key_entities=["loss contour", "gradient", "learning rate", "minimum", "parameter space"],
        ),
        VisualElement(
            id="ml_v2", visual_type="chart",
            description="Training loss vs epoch curve comparing SGD, mini-batch, and batch gradient descent convergence behaviour.",
            source_image="loss_curve.png",
            key_entities=["SGD", "mini-batch", "batch", "convergence", "epoch"],
        ),
    ],
    technical_elements=[
        TechnicalElement(id="ml_t1", element_type="formula",
            raw_content=r"\theta_{t+1} = \theta_t - \alpha \nabla L(\theta)",
            description="Gradient descent parameter update rule"),
        TechnicalElement(id="ml_t2", element_type="formula",
            raw_content=r"L = \frac{1}{2m}\sum(y - \hat{y})^2",
            description="Mean squared error cost function"),
        TechnicalElement(id="ml_t3", element_type="technical_term",
            raw_content="learning rate",    description="Step size hyperparameter alpha"),
        TechnicalElement(id="ml_t4", element_type="technical_term",
            raw_content="gradient descent", description="Iterative optimisation algorithm"),
        TechnicalElement(id="ml_t5", element_type="technical_term",
            raw_content="backpropagation",  description="Algorithm for computing gradients in neural networks"),
    ],
    source_references=["whiteboard_ml.png", "contour.png", "loss_curve.png"],
)

# ---------------------------------------------------------------------------
# Lecture 3: Physics of Computing — Thermodynamics & Energy
# ---------------------------------------------------------------------------
_LECTURE_PHYSICS = LectureContext(
    transcript=[
        TranscriptSegment(
            id="ph_s1", start_time=0.0, end_time=7.0,
            text="Landauer's principle states that erasing one bit of information requires a minimum energy of k_B * T * ln(2) joules, linking computation to thermodynamics.",
        ),
        TranscriptSegment(
            id="ph_s2", start_time=7.0, end_time=14.0,
            text="In CMOS circuits, dynamic power dissipation is P = alpha * C * V^2 * f, where alpha is activity factor, C is capacitance, V is supply voltage, and f is clock frequency.",
        ),
        TranscriptSegment(
            id="ph_s3", start_time=14.0, end_time=21.0,
            text="Dennard scaling predicted that as transistors shrink, power density remains constant, but this broke down around 2005 due to leakage currents.",
        ),
        TranscriptSegment(
            id="ph_s4", start_time=21.0, end_time=28.0,
            text="Einstein's mass-energy equivalence E = mc^2 appears in nuclear computing contexts and sets an absolute upper bound on information density per unit mass.",
        ),
        TranscriptSegment(
            id="ph_s5", start_time=28.0, end_time=35.0,
            text="Voltage scaling is the most effective technique for reducing dynamic power since power scales quadratically with voltage.",
        ),
    ],
    extracted_text=[
        ExtractedText(
            id="ph_e1",
            text="Landauer limit: E = k_B * T * ln(2) per bit erasure at temperature T",
            source_image="whiteboard_physics.png", confidence=0.94,
        ),
        ExtractedText(
            id="ph_e2",
            text="CMOS dynamic power: P = alpha * C * V^2 * f",
            source_image="whiteboard_physics.png", confidence=0.96,
        ),
        ExtractedText(
            id="ph_e3",
            text="Mass-energy: E = mc^2  (Boltzmann: k_B = 1.38e-23 J/K)",
            source_image="whiteboard_physics.png", confidence=0.92,
        ),
    ],
    visual_elements=[
        VisualElement(
            id="ph_v1", visual_type="graph",
            description="CMOS power dissipation graph showing dynamic and static power trends across technology nodes from 250nm to 5nm, with Dennard scaling breakdown visible after 90nm.",
            source_image="cmos.png",
            key_entities=["CMOS", "dynamic power", "static power", "Dennard scaling", "technology node"],
        ),
        VisualElement(
            id="ph_v2", visual_type="diagram",
            description="Energy hierarchy diagram: nuclear energy > chemical energy > Landauer limit per bit, illustrating fundamental bounds on computation.",
            source_image="energy_hierarchy.png",
            key_entities=["Landauer limit", "energy hierarchy", "bit erasure"],
        ),
    ],
    technical_elements=[
        TechnicalElement(id="ph_t1", element_type="formula",
            raw_content="$E = mc^2$",
            description="Einstein mass-energy equivalence"),
        TechnicalElement(id="ph_t2", element_type="formula",
            raw_content=r"E = k_B T \ln 2",
            description="Landauer's principle — minimum energy per bit erasure"),
        TechnicalElement(id="ph_t3", element_type="formula",
            raw_content=r"P = \alpha C V^2 f",
            description="CMOS dynamic power dissipation"),
        TechnicalElement(id="ph_t4", element_type="technical_term",
            raw_content="Landauer's principle", description="Thermodynamic limit on computation"),
        TechnicalElement(id="ph_t5", element_type="technical_term",
            raw_content="Dennard scaling",    description="Historical transistor power scaling law"),
    ],
    source_references=["whiteboard_physics.png", "cmos.png", "energy_hierarchy.png"],
)

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------
_LECTURES: Dict[str, LectureContext] = {
    "algorithms":  _LECTURE_ALGORITHMS,
    "ml_gradient": _LECTURE_ML,
    "physics":     _LECTURE_PHYSICS,
}

_METADATA = {
    "algorithms":  {"title": "Algorithms — Quicksort & Complexity",             "topic": "Data Structures & Algorithms"},
    "ml_gradient": {"title": "Machine Learning — Gradient Descent",              "topic": "Machine Learning & Optimisation"},
    "physics":     {"title": "Physics of Computing — Thermodynamics & Energy",   "topic": "Computer Architecture & Physics"},
}


def get_sample_lectures() -> Dict[str, LectureContext]:
    """Returns mapping of lecture_id -> LectureContext for all 3 benchmark lectures."""
    return dict(_LECTURES)


def get_lecture_metadata():
    """Returns list of {id, title, topic} dicts for UI display."""
    return [{"id": lid, **meta} for lid, meta in _METADATA.items()]


if __name__ == "__main__":
    lectures = get_sample_lectures()
    assert len(lectures) == 3, f"Expected 3 lectures, got {len(lectures)}"
    for lid, ctx in lectures.items():
        assert len(ctx.transcript) >= 4,        f"{lid}: too few transcript segments"
        assert len(ctx.technical_elements) >= 4, f"{lid}: too few technical elements"
        assert len(ctx.visual_elements) >= 1,    f"{lid}: missing visual elements"
    print("SAMPLE DATA OK")
