
import asyncio
import os
import random
import subprocess
import tempfile
import textwrap
import zipfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="SCARY RADIO AI Studio", page_icon="👻")
st.title("👻 SCARY RADIO AI Studio")
st.caption("Hindi horror video maker • Free-first prototype")

title = st.text_input("Horror story title", "आधी रात की गुड़िया")
duration = st.selectbox("Video duration", [30, 40, 60, 90, 120], index=2)
make_video = st.button("Create horror video", type="primary")

def make_story(name, seconds):
    scenes = max(4, seconds // 10)
    hooks = [
        "रात के ठीक बारह बजे, उस कमरे से किसी के रोने की आवाज़ आई।",
        "गाँव के लोग उस पुरानी गुड़िया से डरते थे, लेकिन असली राज़ किसी को नहीं पता था।",
        "जब उसने गुड़िया की आँखों में देखा, तो उसकी साँसें थम गईं।",
        "दरवाज़ा अपने आप बंद हो गया… और पीछे से किसी ने उसका नाम पुकारा।",
        "सुबह कमरा खाली था। लेकिन गुड़िया के चेहरे पर अब एक नई मुस्कान थी।",
    ]
    story = [
        f"कहानी है {name} की।",
        *[hooks[i % len(hooks)] for i in range(scenes - 2)],
        "लेकिन सबसे डरावनी बात यह थी… यह कहानी अभी खत्म नहीं हुई थी।",
    ]
    return story

def load_font(size):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def scene_card(text, index, folder):
    w, h = 720, 1280
    img = Image.new("RGB", (w, h), (13, 15, 24))
    draw = ImageDraw.Draw(img)
    random.seed(index)
    # Atmospheric amber glow
    for radius in range(220, 0, -8):
        x, y = 360, 420
        color = (max(13, 45 - radius // 10),
                 max(15, 30 - radius // 12),
                 max(24, 20 - radius // 15))
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
    # Simple eerie silhouette
    draw.ellipse((280, 260, 440, 430), fill=(8, 8, 12))
    draw.rectangle((300, 390, 420, 650), fill=(8, 8, 12))
    draw.ellipse((320, 325, 345, 350), fill=(180, 35, 35))
    draw.ellipse((375, 325, 400, 350), fill=(180, 35, 35))
    font = load_font(38)
    lines = textwrap.wrap(text, width=24)
    y = 790
    for line in lines[:5]:
        draw.text((55, y), line, font=font, fill=(245, 235, 220),
                  stroke_width=1, stroke_fill=(30, 10, 10))
        y += 58
    draw.text((55, 1180), "SCARY RADIO", font=load_font(28),
              fill=(220, 145, 70))
    path = Path(folder) / f"scene_{index:02d}.png"
    img.save(path)
    return path

async def make_voice(script, output):
    text = " ".join(script)
    voice = edge_tts.Communicate(
        text, voice="hi-IN-MadhurNeural", rate="-8%"
    )
    await voice.save(str(output))

if make_video:
    if not title.strip():
        st.error("Please enter a story title.")
        st.stop()

    with st.spinner("Creating your horror video…"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                script = make_story(title.strip(), duration)
                audio = folder / "narration.mp3"
                asyncio.run(make_voice(script, audio))

                images = [
                    scene_card(line, i, folder)
                    for i, line in enumerate(script)
                ]

                # Build a video from scene cards and narration.
                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                concat_file = folder / "scenes.txt"
                seconds_per_scene = duration / len(images)

                with open(concat_file, "w", encoding="utf-8") as f:
                    for image_path in images:
                        safe_path = str(image_path).replace("'", "'\\''")
                        f.write(f"file '{safe_path}'\n")
                        f.write(f"duration {seconds_per_scene}\n")
                    safe_path = str(images[-1]).replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

                output = folder / "scary_radio_video.mp4"
                cmd = [
                    ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat_file), "-i", str(audio),
                    "-vf", "scale=720:1280,fps=24,format=yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                    str(output),
                ]
                subprocess.run(cmd, check=True, capture_output=True)

                st.success("Your video is ready!")
                st.video(str(output))
                st.download_button(
                    "Download MP4",
                    data=output.read_bytes(),
                    file_name="scary_radio_horror.mp4",
                    mime="video/mp4",
                )
                st.subheader("Story narration")
                st.write(" ".join(script))
                st.download_button(
                    "Download narration",
                    data=audio.read_bytes(),
                    file_name="scary_radio_narration.mp3",
                    mime="audio/mpeg",
                )
        except Exception as e:
            st.error("Video creation failed. Check the setup and try again.")
            st.code(str(e))
            st.info("Voice generation requires an internet connection.")
              
