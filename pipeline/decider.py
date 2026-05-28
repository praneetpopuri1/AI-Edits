import json
import math
import os
import subprocess
from pathlib import Path
import time
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from json_helpers import validate_video_json, extract_video_json, extract_thinking_trace
from whisper_and_wave import diarized_audio, wave_form_text, get_video_duration
import pickle

hf_token = ""
with open("../inputs/in_context_jsons/Valkyrae_fixed.json", 'r', encoding="utf-8") as f:
    in_context_json = json.load(f)
#"G:\youtube_downloads\hasan_china_trump_raw.webm"
def get_segments(json_file, video_path):
    with open(json_file, 'r', encoding="utf-8") as f:
        segments = json.load(f)

    num_seg = len(segments["segments"])
    #defaults 
    vram_for_data = 32
    vram_per_seg = 32
    total_pixels=20480 * 32 * 32
    min_pixels=64 * 32 * 32
    max_frames= 2048
    video = video_path 
    batch_size = int(vram_for_data/vram_per_seg)

    num_batches = math.ceil(num_seg/batch_size)
    print(f"num_batches {num_batches}, batch_size {batch_size}, num_segs {num_seg}")

    batches = []
    
    path = Path("temp_video_files")
    path.mkdir(parents=True, exist_ok=True)


    for i in range(num_batches):
        batches.append([])
    print(f"batches length {len(batches)}")
    for i in range(num_seg):
        #meta data for each video
        segment = segments["segments"][i]
        label = segment["label"]
        start_sec = segment["start_sec"]
        end_sec = segment["end_sec"]

        video_seg = "temp_video_files/segment_" + str(i)  + ".webm"

        cmd = [
            "ffmpeg",
            "-i",
            video,
            "-ss",
            str(start_sec),
            "-to",
            str(end_sec),
            "-c",
            "copy",
            video_seg
        ]
        subprocess.call(cmd)
        duration = get_video_duration(video_seg)
        diarized_text = diarized_audio(video_seg, hf_token)
        wave_form = wave_form_text(video_seg)
        prompt = f"""You are a video-editing planner.

Task:

Analyze the video and determine which parts of the video to keep or cut.

Rules:
- Return only valid JSON.
- Do not include markdown.
- Use seconds as numbers, not timestamp strings.
- Each part must satisfy: start_sec < end_sec.
- part must be sorted by start_sec.
- Every second of the video must be in a segment
- Do not invent timestamps.
- Labels should describe the theme and content of each segment.
- The video duration is {duration} seconds.
- All timestamps must be between 0 and {duration}.
- Do not output overlapping segments 

Output schema:
{schema}

the first video you are given is an example of the type cuts you should make
here is the output for that video example:
{in_context_json}

speaker text:
        {diarized_text}

wave form outputs:
        {wave_form}
Editing intent:
You are looking at a segment of a larger video and your job is to determine whether to keep ."""
        message = [
            {"role": "user", "content": [
                    {"video": context_video,
                    "total_pixels": total_pixels, 
                    "min_pixels": min_pixels, 
                    "max_frames": max_frames,
                    'sample_fps':sample_fps},{"video": video_seg,
                    "total_pixels": total_pixels, 
                    "min_pixels": min_pixels, 
                    "max_frames": max_frames,
                    'sample_fps':sample_fps},
                    {"type": "text", "text": prompt},
                ]
            },
        ]
        batches[int(i/batch_size)].append(message)
    return batches
    

schema = """{
    "parts": [
        {
        "decision": "keep | cut",
        "reasoning": "the main speaker is not saying much and is not engaging to the viewer",
        "start_sec": 0.0,
        "end_sec": 28.5
        }
    ]
    }"""

def batch_inference(name,batches):
    t0 = time.time()
    output_json = []
    hf_token = "some_token"
    #change to omni
    model_id = "Qwen/Qwen3-VL-8B-Thinking"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


    processor = AutoProcessor.from_pretrained(model_id, token=hf_token)

    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        device_map="auto",
        #quantization_config=bnb_config,

        torch_dtype=torch.float16,
        token=hf_token
    )
    for batch in batches:
        max_new_tokens=2048*2

        
        
        text = processor.apply_chat_template(batch, tokenize=False, add_generation_prompt=True)
        print("chat template:", time.time() - t0)
        t1 = time.time()
        image_inputs, video_inputs, video_kwargs = process_vision_info(batch, return_video_kwargs=True, 
                                                                    image_patch_size= 16,
                                                                    return_video_metadata=True)
        print("process_vision_info:", time.time() - t1)
        if video_inputs is not None:
            t2 = time.time()
            video_inputs, video_metadatas = zip(*video_inputs)
            video_inputs, video_metadatas = list(video_inputs), list(video_metadatas)
            print("video unpack:", time.time() - t2)
        else:
            video_metadatas = None
        t3 = time.time()
        inputs = processor(text=text, images=image_inputs, videos=video_inputs, video_metadata=video_metadatas, **video_kwargs, do_resize=False, return_tensors="pt")
        print("processor:", time.time() - t3)
        t4 = time.time()
        inputs = inputs.to('cuda')
        print("to cuda:", time.time() - t4)

        t5 = time.time()
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        print("generate:", time.time() - t5)

        t6 = time.time()
        generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)]
        output_text = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        print("decode:", time.time() - t6)
        
        for i in range(len(output_text)):
            answer = output_text[i]
            print(answer)
            json_answer = extract_video_json(answer)
            thinking_answer = extract_thinking_trace(answer)
            #errors = validate_video_json(json_answer)
            
            # if errors:
            #     print("Invalid JSON output:")
            #     for err in errors:
            #         print("-", err)
            #         print(json.dump(json_answer, indent=2))
            # else:
            output_json += json_answer["parts"]

            with open('../outputs/segment' +str(i) + 'thinking.txt', "w", encoding="utf-8") as f:
                json.dump(thinking_answer, f, indent=2)

            print("sucessfully compiled segment_" + str(i)+ " json")
    with open('../outputs/' + name + '_edl.json', "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2)
    return output_json


# some ideas, cut high level parts or chunks that irrelvant to the editors intent, then make meduim level edits,
# like getting meduim sized chunks the editor does care about, then make granular edits, like these seconds are bad
# so first part removes 10's of minutes, second pass removes minutes at a time, and last edit removes seconds at a time
json_file = "/workspace/AI-Edits/outputs/hasan_segments.json"
video_path = "/workspace/AI-Edits/inputs/videos/hasan_china_trump_raw.webm"
CACHE_PATH = Path("../outputs/hasan_batches.pkl")
if CACHE_PATH.exists():
    print("Loading batches from cache...")
    with open(CACHE_PATH, "rb") as f:
        batches = pickle.load(f)
else:
    print("Generating batches...")
    batches = get_segments(json_file, video_path)

    with open(CACHE_PATH, "wb") as f:
        pickle.dump(batches, f)

result = batch_inference("Hasan_china",batches)