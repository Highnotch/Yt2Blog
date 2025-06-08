# import os
# import subprocess
# from fastapi import FastAPI, Request, Form
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from openai import OpenAI
# from pytube import YouTube
# from dotenv import load_dotenv
# import assemblyai as aai

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# client = OpenAI(api_key=OPENAI_API_KEY)
# aai.settings.api_key = ASSEMBLYAI_API_KEY

# app = FastAPI()
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

# def download_audio_from_youtube(url: str) -> str:
#     filename = "temp_audio.mp3"
#     command = [
#         "yt-dlp",
#         "-x", "--audio-format", "mp3",
#         "-o", filename,
#         url
#     ]
#     subprocess.run(command, check=True)
#     return filename

# def transcribe_audio(filepath: str) -> str:
#     aai.settings.api_key = "73a29d5d70d04815a28386c713acb6cd"
#     config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
#     transcript = aai.Transcriber(config=config).transcribe(filepath)

#     if transcript.status == "error":
#         raise RuntimeError(f"Transcription failed: {transcript.error}")

#     return transcript.text

# def generate_blog_from_transcript(transcript: str) -> str:
#     prompt = f"""
#     Convert the following transcript into a detailed, SEO-optimized blog post.
#     Include title, meta description, H2/H3s, and also give relevant keywords at last for SEO and hastags.

#     Transcript:
#     {transcript[:5000]}
#     """
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant that creates SEO-optimized blog posts like a pro and be professional and concise. Strictly do not hallucinate or add extra details."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.6
#     )
#     return response.choices[0].message.content

# @app.get("/", response_class=HTMLResponse)
# def read_form(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.post("/generate", response_class=HTMLResponse)
# def generate_blog_post(request: Request, youtube_url: str = Form(...)):
#     try:
#         audio_path = download_audio_from_youtube(youtube_url)
#         transcript = transcribe_audio(audio_path)
#         print(transcript)
#         os.remove(audio_path)
#         blog = generate_blog_from_transcript(transcript)
#         return templates.TemplateResponse("index.html", {"request": request, "blog": blog})
#     except Exception as e:
#         return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})




import os
import subprocess
import uuid
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from dotenv import load_dotenv
import assemblyai as aai

# Setup
load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Track video processing
video_tasks = {}

def download_audio_from_youtube(url: str) -> str:
    unique_id = str(uuid.uuid4())
    filename = f"temp_{unique_id}.mp3"
    command = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", filename, url]
    subprocess.run(command, check=True)
    return filename

def transcribe_with_assembly(filepath: str) -> str:
    transcript = aai.Transcriber(config=aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)).transcribe(filepath)
    if transcript.status == "error":
        raise RuntimeError(f"Transcription failed: {transcript.error}")
    return transcript.text

def generate_blog_from_transcript(transcript: str) -> str:
    prompt = f"""
    Convert the following transcript into a detailed, SEO-optimized blog post.
    Include title, meta description, H2/H3s, and relevant keywords.

    Transcript:
    {transcript[:5000]}
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates SEO-optimized blog posts. Strictly do not hallucinate or add extra details."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800
    )
    return response.choices[0].message.content

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "tasks": video_tasks})

@app.post("/generate", response_class=HTMLResponse)
def generate_blog(request: Request, youtube_url: str = Form(...)):
    try:
        video_id = str(uuid.uuid4())
        video_tasks[video_id] = {"url": youtube_url, "status": "Downloading Audio"}

        audio_path = download_audio_from_youtube(youtube_url)
        video_tasks[video_id]["status"] = "Transcribing"

        transcript = transcribe_with_assembly(audio_path)
        os.remove(audio_path)

        video_tasks[video_id]["status"] = "Generating Blog"
        blog = generate_blog_from_transcript(transcript)
        video_tasks[video_id].update({"status": "Complete", "blog": blog})

        return templates.TemplateResponse("index.html", {"request": request, "blog": blog, "tasks": video_tasks})
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e), "tasks": video_tasks})
