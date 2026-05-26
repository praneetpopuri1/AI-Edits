import json
import math

with open("/Users/praneetpopuri/Desktop/AI-Edits/pipeline/master_model/lud_full_segments.json") as f:
    segments = json.load(f)

num_seg = len(segments["segments"])
vram_for_data = 32
vram_per_seg = 8

batch_size = int(vram_for_data/vram_per_seg)

num_batches = math.ceil(num_seg/batch_size)
print(f"num_batches {num_batches}, batch_size {batch_size}, num_segs {num_seg}")

batches = []
video = "/workspace/videos/youtube_downloads/hasan_china_trump_raw.webm"
for i in range(num_batches):
    batches.append([])
print(f"batches length {len(batches)}")
for i in range(num_seg):
    
    # message = [
    #     {"role": "user", "content": [
    #             {"video": video,
    #             "total_pixels": total_pixels, 
    #             "min_pixels": min_pixels, 
    #             "max_frames": max_frames,
    #             'sample_fps':sample_fps},
    #             {"type": "text", "text": PROMPT_TIMELINE},
    #         ]
    #     },
    # ]
    batches[int(i/batch_size)].append(message)

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






