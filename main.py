import json, requests, datetime, asyncio, os
import edge_tts
from PIL import Image, ImageDraw
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, ImageClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

PIXABAY_API_KEY = os.environ["PIXABAY_API_KEY"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

scripts = [
    ("Space is Silent", "space galaxy", "Did you know space is completely silent? There is no atmosphere so sound cannot travel. An explosion next to you would be totally silent. Every atom in your body was forged inside an ancient star. You are literally made of stardust. Like and Subscribe for more amazing facts!"),
    ("Glass Rain Planet", "planet storms", "There is a planet called HD 189733b where it rains glass sideways at 5000 miles per hour. It looks beautiful blue from space but is the deadliest place in the universe. Like and Subscribe for more amazing facts!"),
    ("Sun Size", "sun solar flare", "The Sun is so massive that one million Earths could fit inside it. Yet compared to other stars in the universe our Sun is considered medium sized. Some stars are a thousand times bigger. Like and Subscribe for more amazing facts!"),
    ("Black Holes", "black hole space", "Black holes are regions where gravity is so strong that nothing not even light can escape. If you fell into one time would slow down for you while the universe aged billions of years outside. Like and Subscribe for more amazing facts!"),
    ("Milky Way", "milky way galaxy", "Our Milky Way galaxy contains over 200 billion stars. It takes light 100000 years to cross from one end to the other. And our galaxy is just one of two trillion galaxies in the observable universe. Like and Subscribe for more amazing facts!"),
]

day_of_year = datetime.datetime.now().timetuple().tm_yday
index = day_of_year % len(scripts)
title, search_query, script = scripts[index]

print(f"Today: {title}")

async def make_audio():
    communicate = edge_tts.Communicate(script, voice="en-US-GuyNeural")
    await communicate.save("/tmp/audio.mp3")

asyncio.run(make_audio())
print("Audio done")

queries = [search_query, "space galaxy", "planet stars", "astronaut NASA", "solar system",
           "milky way", "nebula space", "earth from space", "mars planet", "saturn rings",
           "deep space", "moon surface", "black hole space", "jupiter planet", "space shuttle launch"]

video_files = []
for i, query in enumerate(queries):
    url = "https://pixabay.com/api/videos/"
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": 5}
    data = requests.get(url, params=params).json()
    if data.get("hits"):
        video = data["hits"][0]
        for quality in ["large", "medium", "small"]:
            if quality in video["videos"] and video["videos"][quality]["url"]:
                video_url = video["videos"][quality]["url"]
                break
        output = f"/tmp/clip{i+1}.mp4"
        with open(output, "wb") as f:
            f.write(requests.get(video_url).content)
        video_files.append(output)
        print(f"Clip {i+1}: {query}")

audio = AudioFileClip("/tmp/audio.mp3")
clips = [VideoFileClip(vf).resize((1280, 720)) for vf in video_files]
combined = concatenate_videoclips(clips)

if combined.duration < audio.duration:
    repeats = int(audio.duration / combined.duration) + 1
    combined = concatenate_videoclips([combined] * repeats)

combined = combined.subclip(0, audio.duration).set_audio(audio)

img = Image.new("RGBA", (400, 60), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.text((10, 10), "Like & Subscribe", fill=(255, 255, 255, 220))
img.save("/tmp/watermark.png")

watermark = ImageClip("/tmp/watermark.png")\
    .set_duration(audio.duration)\
    .set_position(("right", "bottom"))\
    .margin(right=20, bottom=20, opacity=0)

final = CompositeVideoClip([combined, watermark])
final.write_videofile("/tmp/final_video.mp4", codec="libx264", audio_codec="aac", fps=24, logger=None)
print("Video done")

creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": f"{title} 🌌 #spacefacts",
            "description": "Amazing space facts!\n\nLike and Subscribe for more!",
            "tags": ["space", "facts", "universe", "amazing"],
            "categoryId": "27"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=MediaFileUpload("/tmp/final_video.mp4")
)

response = request.execute()
print(f"Uploaded: https://youtube.com/watch?v={response['id']}")
