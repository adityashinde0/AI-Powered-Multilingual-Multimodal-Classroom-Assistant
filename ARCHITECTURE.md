# ARCHITECTURE --- The Smart Classroom

## 1. Architecture Overview

The Smart Classroom is a modular multimodal AI pipeline that converts
classroom lecture inputs into a personalized multilingual learning
resource.

**Core flow:**

`Lecture Input → Speech/OCR/Vision Processing → Unified Lecture Representation → Notes/Translation/Q&A → Student UI → Validation/Fallback`

The architecture follows the problem statement directly. It does not
require microservices, Kubernetes, PostgreSQL, a vector database, or an
agent framework unless later evidence shows a concrete need.

### High-Level Flow

``` mermaid
flowchart TD
    A[Lecture Audio + Classroom Images] --> B[Input Orchestrator]
    B --> C[Speech Recognition]
    B --> D[OCR]
    B --> E[Computer Vision]
    B --> F[Formula & Technical Content]
    C --> G[Unified Lecture Representation]
    D --> G
    E --> G
    F --> G
    G --> H[Lecture Content Normalization]
    H --> I[Structured Notes]
    H --> J[Machine Translation]
    H --> K[Lecture Grounding]
    K --> L[Student Q&A]
    I --> M[Student Learning Resource]
    J --> M
    E --> M
    L --> M
    M --> N[Student Interface]
    N --> O{Validation}
    O -->|Valid| P[Present Result]
    O -->|Failure| Q[Fallback / Source Reference]
```

## 2. System Flow

### 2.1 Lecture Input

The MVP accepts lecture audio and classroom/whiteboard images. The exact
capture mechanism is an implementation decision because the problem
statement does not mandate a particular device or streaming
architecture.

### 2.2 Speech Recognition

**Input:** lecture audio\
**Output:** ordered/timestamped transcript.

### 2.3 OCR

**Input:** classroom or whiteboard images\
**Output:** extracted text with a reference to the source image where
practical.

### 2.4 Computer Vision

Processes diagrams, graphs, charts, and other instructional visuals.

**Input:** visual material\
**Output:** structured visual interpretation.

### 2.5 Formula and Technical Content

Important formulas and technical terms receive explicit preservation
treatment. The system should avoid blindly translating or rewriting them
as ordinary prose.

### 2.6 Unified Lecture Representation

All modality outputs are normalized into a shared lecture context:

``` text
LectureContext
├── transcript segments
├── extracted classroom text
├── visual elements
│   ├── diagrams
│   ├── graphs
│   └── charts
├── formulas
├── technical terms
└── source references
```

### 2.7 Structured Notes

The lecture context is transformed into organized notes containing
relevant concepts, explanations, important terms, formulas, and visual
explanations.

### 2.8 Machine Translation

The system produces learning material in the student's selected
language. Initial MVP languages are English, Hindi, Bangla, and Arabic.

### 2.9 Lecture-Grounded Q&A

``` text
Student Question
      ↓
Question Processing
      ↓
Retrieve Relevant Lecture Context
      ↓
Generate Answer
      ↓
Grounding Check
      ↓
Answer / Controlled Fallback
```

Answers presented as lecture-derived must be supported by the processed
lecture context.

### 2.10 Student Interface

The UI should expose language selection, structured notes, translated
material, classroom text, visual explanations, formulas, technical
terms, and lecture Q&A.

## 3. Component Architecture

  ---------------------------------------------------------------------------------------
  Component           Responsibility           Inputs                   Outputs
  ------------------- ------------------------ ------------------------ -----------------
  Input Orchestrator  Route lecture inputs     Audio, images            Modality inputs

  Speech Recognition  Convert speech to text   Audio                    Transcript

  OCR                 Extract classroom text   Images                   Text + source
                                                                        reference

  Vision Module       Understand               Images/regions           Visual
                      diagrams/graphs/charts                            interpretation

  Formula/Technical   Preserve formulas and    Transcript/OCR/visuals   Technical
  Handler             terminology                                       elements

  Lecture             Combine and normalize    All processed outputs    LectureContext
  Representation      modalities                                        

  Notes Generator     Create organized notes   LectureContext           Structured notes

  Translation         Convert content to       LectureContext/notes     Translated
                      selected language                                 material

  Grounding/Q&A       Answer lecture questions Question +               Answer + support
                                               LectureContext           

  Student UI          Present learning         All outputs              User interaction
                      resource                                          

  Evaluation Layer    Measure quality          Outputs + references     Metrics/results
  ---------------------------------------------------------------------------------------

## 4. Data / Storage Design

For the first MVP, persistent storage is not required by the problem
statement.

> **PostgreSQL: Not required for this problem.**

A lecture session can use in-memory state and/or local files. A database
should be introduced only if persistent accounts, history, analytics, or
another demonstrated requirement appears.

A vector database is also not automatically required. For a controlled
single-lecture MVP, simpler retrieval is preferred.

Conceptual session structure:

``` text
LectureSession
├── source audio
├── source images
├── transcript
├── extracted text
├── visual interpretations
├── formulas
├── technical terms
├── structured notes
├── translations
└── Q&A context
```

## 5. Core Interfaces

``` text
LectureInput
├── audio: optional
└── images: optional[]
```

``` text
LectureContext
├── transcript
├── extracted_text
├── visual_elements
├── technical_elements
└── source_references
```

``` text
QuestionRequest
├── lecture_session_id
├── question
└── language
```

``` text
QuestionResponse
├── answer
├── supporting_context
└── grounding_status
```

Exact programming-language types should be finalized after repository
inspection and technology selection.

## 6. Technology Decisions

  --------------------------------------------------------------------------------------
  Decision       Selected approach      Alternative     Rationale         Confidence
  -------------- ---------------------- --------------- ----------------- --------------
  Architecture   Modular                Microservices   Lower coupling    Medium
                 pipeline/application                   and less          
                                                        infrastructure    
                                                        for a 24-hour MVP 

  AI models      Suitable pretrained    Training large  More feasible     Medium
                 components             models from     within the        
                                        scratch         implementation    
                                                        window            

  Database       None initially         PostgreSQL      No explicit       High
                                                        persistence       
                                                        requirement in    
                                                        the problem       

  Vector DB      None initially         Vector database Single-lecture    Medium
                                                        retrieval does    
                                                        not establish a   
                                                        need              

  External APIs  Minimize dependency    Fully hosted    Reduces           Medium
                                        pipeline        network/service   
                                                        dependency and    
                                                        cost risk         
  --------------------------------------------------------------------------------------

Exact models and vendors must be selected only after verifying current
official documentation, capabilities, licensing, hardware requirements,
and availability.

## 7. Security / Reliability

-   Never expose API credentials in frontend code.
-   Validate uploaded file types and sizes.
-   Avoid unnecessary logging of lecture/student content.
-   Treat untrusted lecture text as data, not executable instructions.
-   Keep source images available when OCR/vision interpretation fails.
-   Preserve original-language content when translation fails.
-   Prevent unsupported Q&A responses from being presented as lecture
    facts.

## 8. Performance Strategy

No performance results are claimed before measurement.

Measure: - Speech recognition processing time. - OCR processing time. -
Vision processing time. - Translation time. - Note generation time. -
Q&A latency. - End-to-end processing time. - CPU/GPU usage and memory
where relevant.

Quality metrics should include appropriate measures such as WER for
speech recognition, OCR accuracy, translation evaluation, visual
interpretation correctness, note coverage, and Q&A correctness.

Use:

`Baseline → Proposed Solution → Measured Result`

Do not invent improvement percentages.

## 9. Failure & Fallback Strategy

  -----------------------------------------------------------------------
  Failure                 Detection               Fallback
  ----------------------- ----------------------- -----------------------
  Speech recognition      Invalid/empty           Continue other
  failure                 transcript              modalities

  OCR failure             No usable text          Retain source image

  Vision failure          Model error/unusable    Show source visual
                          output                  without fabricated
                                                  explanation

  Formula failure         Missing/invalid formula Preserve source
                                                  representation

  Translation failure     Error/timeout           Show original-language
                                                  content

  Note generation failure Empty/invalid notes     Show normalized lecture
                                                  content

  Q&A lacks evidence      No supporting lecture   State that lecture does
                          context                 not establish the
                                                  answer

  External service        Network/API error       Use fallback/local
  failure                                         component where
                                                  available

  Resource exhaustion     Memory/time threshold   Reduce scope or return
                                                  partial result
  -----------------------------------------------------------------------

## 10. Engineering Invariants

1.  Never silently fabricate lecture information.
2.  Do not silently alter important formulas.
3.  Preserve technical terminology.
4.  One failed modality must not unnecessarily erase successful
    modalities.
5.  Lecture-derived Q&A must be grounded in lecture context.
6.  Unsupported answers must not be presented as lecture facts.
7.  Secrets must never reach the client.
8.  Invalid inputs must fail safely.
9.  Performance and quality claims require measurement.
10. Critical module interfaces must remain explicit and testable.

## 11. Technical Trade-offs

### Multimodal integration vs simplicity

Multiple AI capabilities are explicitly required, so some pipeline
complexity is unavoidable. Unrelated infrastructure complexity is not.

### Live processing vs controlled MVP

Fully live processing adds streaming, synchronization, noise handling,
and real-time constraints. The first MVP should prioritize a controlled
end-to-end workflow unless live processing can be implemented without
jeopardizing correctness.

### Specialized models vs one multimodal model

The final choice must depend on verified capabilities, licensing,
hardware requirements, availability, and measured quality rather than
popularity.

### Local vs hosted processing

Local execution provides greater dependency control; hosted services may
simplify access but introduce network, pricing, availability, and
data-handling dependencies.

## 12. Accepted Technical Debt

-   Controlled lecture inputs rather than universal classroom capture.
-   Initial support for the explicitly mentioned languages.
-   Local/in-memory session state.
-   Limited evaluation dataset.
-   Limited visual categories focused on diagrams, graphs, and charts.
-   Sequential processing where true streaming is not necessary.
-   Limited persistent history.

These compromises must not remove the core multimodal-to-multilingual
workflow.
