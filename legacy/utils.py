import boto3
import yt_dlp

def upload_to_s3():
    s3 = boto3.client("s3")

    file_path = "videos/Private_Credit_is_Imploding.mkv"
    bucket_name = "aiedit-praneet-video-upload-bucket-890988597138-us-east-2-an"
    s3_key = "videos/my_video.mp4"

    response = s3.upload_file(file_path, bucket_name, s3_key)
    print(response)

def download_youtube_video():
    url = "https://www.youtube.com/watch?v=OhKM1l7Lfs4"

    ydl_opts = {
        "outtmpl": "videos/%(title)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def compress_video(input_path):
    import subprocess
    output_path = input_path.replace(".mkv", "_compressed.mp4")

    command = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "h264_videotoolbox",
        ""
        "-crf", "28",
        "-acodec", "aac",
        "-b:a", "128k",
        output_path
        
    ]

    subprocess.run(command, check=True)
