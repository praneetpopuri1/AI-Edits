import os

os.environ["FORCE_QWENVL_VIDEO_READER"] = "decord"

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
import time
from whisper_and_wave import diarized_audio, wave_form_text, get_video_metadata
import json

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


def inference(video, prompt, max_new_tokens=2048*4, total_pixels=20480 * 32 * 32, min_pixels=64 * 32 * 32, max_frames= 2048, sample_fps = 1):
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
    source_meta = get_video_metadata(video)
    diarized_text = diarized_audio("/workspace/videos/youtube_downloads/first_half_lud.opus", hf_token)
    wave_form = wave_form_text("/workspace/videos/youtube_downloads/first_half_lud.opus")
    PROMPT_TIMELINE = f"""
        You are analyzing a video for an editing pipeline.

        Source metadata:
        {json.dumps(source_meta, indent=2)}
        speaker text:
        {diarized_text}

        # wave form outputs:
        {wave_form}

        You are making a rough cut, determining which segements of the video to discard,
          priotize parts where the main speaker is talking and where the video is engaging, just discard boring parts of the video espcially when no one is talking do lots of discards do not be shy, 
          just go with your gut feeling.
          format:[discard, timpstamp: 04-06]
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


answer = inference("/workspace/videos/youtube_downloads/ludwig_fixed_first.mp4", " ")
print(answer)

# rand prompt 
# first analyze this video, find what the purpose and reason of the video is. Next you are an expert video editor and your job is turn this video

#EXAMPLE OUTPUT:
# Got it, let's break down the video step by step. 

# First, the beginning of the video. The first frame shows the person, and then in the next frames, they wave. So the action at the beginning is waving. Let me check: the second frame (0.2s to 1.2s) shows the person raising their hand to wave. Yep, that's the first action.

# Second, the items held up in order. Let's list the sequence. First, after waving, they hold up a book. Then, after the book, they hold up a box (the blue one for slide bags). Then, they hold up a container with a ball (the black one). So the order is book, blue box, container. Let's confirm: frame 4-9 is book, then frame 17-22 is blue box, then 23-36 is the container. Correct.

# Third, the book's title. The book is shown in frames 4-9, and the cover has "Patterns for Building AI Agents". Let's check the text: in frame 5-8, the book cover says "Patterns for Building AI Agents". So that's the title.
# </think>

# 1) At the beginning of the video, the person waves their hand.  
# 2) The items the person holds up, in order, are: a book, a blue box labeled "Slide Bags," and a cylindrical container with a spherical top.  
# 3) The title of the book is "Patterns for Building AI Agents."