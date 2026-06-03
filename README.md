# AI-Edits

AI-Edits is a prompt-based agentic video editing pipeline designed to reduce redundant and tedious workflows common in content creation.

It converts natural language editing requests into a structured edit plan, which is then rendered into a final video.

There are currently two versions of the project:

1. **Long-form rough cut pipeline**
   Creates rough cuts from ultra-long videos, including videos over 3 hours long.

2. **Short-form editing pipeline**
   Performs a wider range of edits on videos up to 3 minutes long.

---

## Overview

The purpose of AI-Edits is to support content creators and video editors by automating repetitive parts of the editing process.

Content creators producing high-value videos often spend anywhere from a quarter to half of their production time editing. This process is critical for creating engaging long-form videos, but many parts of it can be tedious and repetitive.

Examples of these workflows include:

* Creating rough cuts
* Removing irrelevant or boring segments
* Adding B-roll
* Creating transitions
* Applying basic edits

The goal of AI-Edits is not to replace content creators or video editors. Instead, it is designed to enhance their capabilities by automating repetitive editing tasks, allowing them to spend more time on the creative parts of their work.

---

## Technical Overview

AI-Edits uses an orchestrator-style agentic pipeline.

![Orchestrator pipeline](legacy/ochestrator_pipeline.webp)

A video and a natural language prompt are sent to a Vision-Language Model, or VLM.

For example, the input may be a 2-hour video of someone explaining how to make chole. While the full video could be published, it may not perform well because it contains many unengaging sections.

A user could provide a prompt such as:

> Create a rough cut of this video by removing irrelevant and boring segments.

In this project, the VLM used is **Qwen3-VL-8B-Thinking**.

The pipeline first chunks the video into thematic segments and outputs those segments in JSON format:

[Example segment JSON file](outputs/hasan_segments.json)

Each chunk is then sent back into the model for further analysis.

However, Qwen3-VL-8B-Thinking does not have native audio understanding, which is highly important for creating accurate edit plans. To address this, the model is also given additional audio-based context:

* A diarized audio transcript
* A waveform timeline of audio levels

The diarized transcript is generated using **WhisperX**. A diarized transcript is a text transcript of an audio recording that identifies who is speaking at each point in time.

The model then outputs an edit decision list, or EDL, for each segment, including a reason for each decision:

[Example segment EDL JSON file](outputs/Hasan_china_edl.json)

---

## In-Context Examples

In-context examples were found to be extremely important for producing good edits.

Without examples of how the model should edit, the model tends to be overly conservative and often refuses to cut out any parts of the video. Providing examples helps guide the model toward more useful editing decisions.

[In-Context example JSON file](inputs/in_context_jsons/Valkyrae_fixed.json)

---

## Rough Cut Demo

### Original Long VOD

[![Watch the original VOD](https://img.youtube.com/vi/LLEILkXzij4/maxresdefault.jpg)](https://www.youtube.com/watch?v=LLEILkXzij4)

### AI-Edited Rough Cut

A 50-minute segment from the original VOD was fed into the pipeline.

[![Watch the AI-edited rough cut](https://img.youtube.com/vi/eNvpxff8Ykw/maxresdefault.jpg)](https://www.youtube.com/watch?v=eNvpxff8Ykw)

### Human-Edited Video From the Same Segment

[![Watch the human-edited video](https://img.youtube.com/vi/ijj-qB6xl3U/maxresdefault.jpg)](https://www.youtube.com/watch?v=ijj-qB6xl3U)


## Takeaways and Future Plans

Almost all of the code for this project was handwritten, although AI tools were still used throughout the development process. If the goal had been to build an MVP as quickly as possible, this approach significantly slowed down progress.

However, the major advantage of building the system this way was that it allowed me to actively learn how the full video editing pipeline works. As a result, future iterations of the project can be much more focused, targeted, and applicable to the original use case.

Currently, AI-Edits is only able to produce complete rough cuts. In the future, adapting the system to support additional editing workflows will be crucial. These workflows could include adding B-roll, creating transitions, applying basic edits, and supporting more detailed user-directed editing requests.

This project was also built using an open-source model running on RunPod GPUs. Compared to using a hosted API, this significantly slowed down development time and reduced output quality. However, building the project this way made the system more practical under limited compute constraints and helped create a pipeline that can still function with weaker GPUs.

