import whisperx
import gc
from whisperx.diarize import DiarizationPipeline
import librosa
import numpy as np
import json
import torch

def cleanup_cuda(*objs):
    for obj in objs:
        try:
            if obj is not None and hasattr(obj, "to"):
                obj.to("cpu")
        except Exception:
            pass

    for obj in objs:
        try:
            del obj
        except Exception:
            pass

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

def diarized_audio(path, HF_TOKEN):
    device = "cuda"
    audio_file = path
    batch_size = 16
    compute_type = "float16"

    model = None
    model_a = None
    diarize_model = None

    try:
        # 1. Transcribe
        model = whisperx.load_model("large-v2", device, compute_type=compute_type)
        audio = whisperx.load_audio(audio_file)
        result = model.transcribe(audio, batch_size=batch_size)

        cleanup_cuda(model)
        model = None

        # 2. Align
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=device
        )

        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False
        )

        cleanup_cuda(model_a)
        model_a = None

        # 3. Diarize
        diarize_model = DiarizationPipeline(token=HF_TOKEN, device=device)
        diarize_segments = diarize_model(audio)

        result = whisperx.assign_word_speakers(diarize_segments, result)

        cleaned = clean_diarized_segments(result["segments"])
        output = json.dumps(cleaned, indent=2)

        return output

    finally:
        cleanup_cuda(model, model_a, diarize_model)

def clean_diarized_segments(segments):
    cleaned = []

    for segment in segments:
        cleaned.append({
            "text": segment["text"],
            "time_range": {
                "start": float(segment["start"]),
                "end": float(segment["end"])
            },
            "speaker": segment.get("speaker")
        })

    return cleaned

def wave_form_text(path_wav):
    audio_path = path_wav
    # path = Path(audio_path)
    # if path.suffix.lower() != ".wav":
    #     audio_path = extract_audio(audio_path)
  
    # Load audio as mono, 16 kHz
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    # Analyze in 0.5 second windows
    window_sec = 2
    frame_length = int(window_sec * sr)
    hop_length = frame_length

    # RMS = loudness/energy per window
    rms = librosa.feature.rms(
        y=y,
        frame_length=frame_length,
        hop_length=hop_length
    )[0]

    # Convert amplitude to relative dB
    db = librosa.amplitude_to_db(rms, ref=np.max)

    times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr,
        hop_length=hop_length
    )

    audio_timeline = []

    for t, level in zip(times, db):
        start = round(float(t), 2)
        end = round(float(t + window_sec), 2)

        if level < -40:
            label = "silence"
        elif level < -25:
            label = "low_volume"
        elif level < -10:
            label = "medium_volume"
        else:
            label = "high_volume_or_peak"

        audio_timeline.append({
            "start": start,
            "end": end,
            "volume_db_relative": round(float(level), 2),
            "type": label
        })

    return json.dumps(audio_timeline, indent=2)

import subprocess
from pathlib import Path

def extract_audio(input_video: str, output_audio: str = None):
    input_path = Path(input_video)

    if output_audio is None:
        output_audio = input_path.with_suffix(".opus")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",          # no video
        "-c:a", "copy", # copy audio stream, no re-encode
        str(output_audio),
    ]

    subprocess.run(cmd, check=True)
    return str(output_audio)

def get_video_metadata(path: str):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration",
        "-of",
        "json",
        path,
    ]
    out = subprocess.check_output(cmd).decode("utf-8")
    data = json.loads(out)
    stream = data["streams"][0]

    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) != 0 else 0.0
    duration_s = float(stream.get("duration", 0) or 0)

    return {
        "duration_s": round(duration_s, 3),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": round(fps, 3),
    }
