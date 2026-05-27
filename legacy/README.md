# AI-Edits

An AI-powered video editing platform that automates complex editing workflows using natural language prompts.

[Full Report](./report.pdf)

---

## Overview

Creating high-quality video content is extremely time-intensive — often requiring **100+ hours of editing** for a single polished video. This creates a major barrier for both:

* Smaller creators with limited resources
* Professionals looking to scale production efficiently

**AI-Edits** aims to solve this by building a *deeply integrated AI editing system* that allows users to edit videos through simple prompts like:

* "Add a digital arrow pointing to the main character"
* "Crop the video to only show the face cam"
* "Find clips at 9 PM on December 11, 2025"

The system interprets these prompts and generates corresponding edits automatically.

---

## Key Idea

The project treats video editing as a **mapping from prompts → structured edits**, where:

* Input space = natural language prompts
* Output space = video transformations

This creates a powerful and generalizable system applicable beyond just content creation.

---

## System Architecture

The system is designed as a **multi-stage pipeline**:

```
Raw Video → Processing → Planning → Rendering → Final Edit
```

### 1. Processing

Goal: Convert raw video into structured, useful representations.

Key components:

* Frame embeddings (e.g., CLIP / SigLIP)
* Audio transcription
* Shot boundary detection

Design priorities:

* Lightweight
* Information-dense representations for downstream models

---

### 2. Planning

Goal: Convert user prompts + processed data into a structured editing plan.

* Input:

  * User prompt
  * Processed video features

* Output:

  * Structured plan (likely JSON)

Example:

```json
{
  "action": "crop",
  "target": "face_cam",
  "timestamp_range": [120, 180]
}
```

#### Model Options

* Closed-source:

  * Gemini (multi-modal reasoning)

* Open-source:

  * Fine-tuned multi-modal models (LoRA, custom architectures)

#### Research Directions

* Tradeoff between API models vs fine-tuned models
* Efficient inference (low compute planning models)
* Temporal attention strategies (focus on nearby frames)

---

### 3. Rendering (Agentic Editing)

Goal: Execute the plan and produce the final video.

Approach:

* Build an **agent** that interacts with a video editor
* Translate structured plans into real edits

Open questions:

* How effective is editing *without* video context?
* How far can prompt-only editing go?

---

## Evaluation

The system will be evaluated across two key dimensions:

### 1. Practical Utility

* Does this improve real editing workflows?
* Does it reduce time/effort meaningfully?

### 2. Output Quality

Measured using:

* Task success rate
* Tool accuracy
* Output quality (via LLM judges or human feedback)

---

## Why This Matters

Video editing is a major bottleneck in content creation.

AI-Edits aims to:

* Lower the barrier to entry
* Accelerate professional workflows
* Enable new forms of interactive media editing

---

## Future Directions

* End-to-end multimodal models (no explicit pipeline)
* Better temporal reasoning in video
* Real-time editing assistants
* Generalization beyond video (e.g., media understanding systems)

---

## Authors

**Praneet Popuri (Lead), Steve (Yu-Hsin) Lin, Pranav Karthik, Gabe Brazil, Arista Ranka, Kevin Tseng, Kevin Park**

---

## Notes

This README is a high-level overview.
For full technical details, see the accompanying report.
