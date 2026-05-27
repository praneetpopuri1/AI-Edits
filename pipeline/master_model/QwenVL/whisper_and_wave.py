import whisperx
import gc
from whisperx.diarize import DiarizationPipeline
import librosa
import numpy as np
import json

def diarized_audio(path, HF_TOKEN):
    device = "cuda"
    audio_file = path
    batch_size = 16 # reduce if low on GPU mem
    compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

    # 1. Transcribe with original whisper (batched)
    model = whisperx.load_model("large-v2", device, compute_type=compute_type)

    # save model to local path (optional)
    # model_dir = "/path/"
    # model = whisperx.load_model("large-v2", device, compute_type=compute_type, download_root=model_dir)

    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=batch_size)

    # delete model if low on GPU resources
    # import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model

    # 2. Align whisper output
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    # delete model if low on GPU resources
    import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model_a

    # 3. Assign speaker labels
    diarize_model = DiarizationPipeline(token=HF_TOKEN, device=device)

    # add min/max number of speakers if known
    diarize_segments = diarize_model(audio)
    # diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

    result = whisperx.assign_word_speakers(diarize_segments, result)

    return result["segments"] # segments are now assigned speaker IDs


def wave_form_text(path_wav):
    audio_path = path_wav

    # Load audio as mono, 16 kHz
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    # Analyze in 0.5 second windows
    window_sec = 0.5
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

    return json.dumps(audio_timeline[:20], indent=2)