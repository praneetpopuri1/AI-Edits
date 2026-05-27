import os


import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
import time
from whisper_and_wave import diarized_audio, wave_form_text, get_video_duration
import json
from json_helpers import validate_video_json, extract_video_json, extract_thinking_trace


videos = ["/workspace/videos/youtube_downloads/hasan_china_trump_raw.webm","/workspace/videos/youtube_downloads/smallant_minecraft_raw.webm", "/workspace/videos/youtube_downloads/squeex_bad_steam_games_raw.webm"]
durations = [get_video_duration(videos[0]),get_video_duration(videos[1]),get_video_duration(videos[2])]
names = ["hasan_segments", "smallant_segments","squeex_segments"]
# video = "/workspace/videos/youtube_downloads/ludwig_mrbeast_raw.webm"
# duration = get_video_duration(video)
# name = "lud_full_segments"


def inference(video, duration, prompt, max_new_tokens=2048*2, total_pixels=20480 * 32 * 32, min_pixels=64 * 32 * 32, max_frames= 2048, sample_fps = 2):
    """
    Perform multimodal inference on input video and text prompt to generate model response.

    Args:
        video (str or list/tuple): Video input, supports two formats:
            - str: Path or URL to a video file. The function will automatically read and sample frames.
            - list/tuple: Pre-sampled list of video frames (PIL.Image or url). 
              In this case, `sample_fps` indicates the frame rate at which these frames were sampled from the original video.
        prompt (str): User text prompt to guide the model's generation.
        max_new_tokens (int, optional): Maximum number of tokens to generate. Default is 2048.
        total_pixels (int, optional): Maximum total pixels for video frame resizing (upper bound). Default is 20480*32*32.
        min_pixels (int, optional): Minimum total pixels for video frame resizing (lower bound). Default is 16*32*32.
        sample_fps (int, optional): ONLY effective when `video` is a list/tuple of frames!
            Specifies the original sampling frame rate (FPS) from which the frame list was extracted.
            Used for temporal alignment or normalization in the model. Default is 2.

    Returns:
        str: Generated text response from the model.

    Notes:
        - When `video` is a string (path/URL), `sample_fps` is ignored and will be overridden by the video reader backend.
        - When `video` is a frame list, `sample_fps` informs the model of the original sampling rate to help understand temporal density.
    """
    t0 = time.time()
    hf_token = "some_token"
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
        quantization_config=bnb_config,

        torch_dtype=torch.float16,
        token=hf_token
    )
    #diarized_text = diarized_audio("/workspace/videos/youtube_downloads/first_half_lud.opus", hf_token)
    #wave_form = wave_form_text("/workspace/videos/youtube_downloads/first_half_lud.opus")


    schema = """{
  "detailed_video_explanation": "string",
  "segments": [
    {
      "label": "intro",
      "start_sec": 0.0,
      "end_sec": 135.0
    }
  ]
}"""


    PROMPT_TIMELINE = f"""
        You are a video-editing planner.

Task:
Analyze the video and return a structured edit plan.

Rules:
- Return only valid JSON.
- Do not include markdown.
- Use seconds as numbers, not timestamp strings.
- Each segment must satisfy: start_sec < end_sec.
- Segments must be sorted by start_sec.
- Every second of the video must be in a segment
- Do not invent timestamps.
- Labels should describe the theme and content of each segment.
- Each segment should be between 0 seconds to 240 seconds
- The video duration is {duration} seconds.
- All timestamps must be between 0 and {duration}.
- Do not output overlapping segments 

Output schema:
{schema}

Editing intent:
You are an orchestrator, where you are sending video segments into another VLM to cut or keep parts of the segments. So break the video into thematic segments. 
                        """.strip()
    
        
    messages = [
        {"role": "user", "content": [
                {"video": video,
                "total_pixels": total_pixels, 
                "min_pixels": min_pixels, 
                "max_frames": max_frames,
                'sample_fps':sample_fps},
                {"type": "text", "text": PROMPT_TIMELINE},
            ]
        },
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    print("chat template:", time.time() - t0)
    t1 = time.time()
    image_inputs, video_inputs, video_kwargs = process_vision_info([messages], return_video_kwargs=True, 
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
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, video_metadata=video_metadatas, **video_kwargs, do_resize=False, return_tensors="pt")
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
    return output_text[0]


for i in range(len(videos)):
    answer = inference(videos[i],durations[i], " ")
    name = names[i]
    print(answer)
    json_answer = extract_video_json(answer)
    thinking_answer = extract_thinking_trace(answer)
    errors = validate_video_json(json_answer)

    if errors:
        print("Invalid JSON output:")
        for err in errors:
            print("-", err)
            print(json.dump(json_answer, indent=2))
    else:
        with open(name + '.json', "w", encoding="utf-8") as f:
            json.dump(json_answer, f, indent=2)

        with open(name + 'thinking.txt', "w", encoding="utf-8") as f:
            json.dump(thinking_answer, f, indent=2)

        print("sucessfully ouputed json at " + name + '.json')
