import librosa
import numpy as np
import matplotlib.pyplot as plt
import moviepy as mp
import moviepy.video.fx as vfx
from mutagen import File
from mutagen.id3 import ID3NoHeaderError
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox


def generate_ai_visuals(theme):
    width, height = 1920, 1080
    image = Image.new("RGB", (width, height), theme)
    draw = ImageDraw.Draw(image)
    for i in range(height):
        color = (
            int(theme[0] * (i / height)),
            int(theme[1] * (i / height)),
            int(theme[2] * (i / height))
        )
        draw.line([(0, i), (width, i)], fill=color)
    return image


def extract_metadata(audio_path):
    metadata = {"title": "Unknown Title", "artist": "Unknown Artist", "album": "Unknown Album"}
    try:
        audio = File(audio_path)
        if audio is None:
            return metadata
        tags = audio.tags
        if tags:
            metadata['title'] = tags.get('TIT2', metadata['title']).text[0] if 'TIT2' in tags else metadata['title']
            metadata['artist'] = tags.get('TPE1', metadata['artist']).text[0] if 'TPE1' in tags else metadata['artist']
            metadata['album'] = tags.get('TALB', metadata['album']).text[0] if 'TALB' in tags else metadata['album']
    except ID3NoHeaderError:
        pass
    except Exception:
        pass
    return metadata


def brighten(clip, factor):
    return clip.fl_image(lambda frame: np.clip(frame * factor, 0, 255).astype(np.uint8))


def apply_beat_effects(clip, beat_times):
    clips = []
    last_t = 0
    for bt in beat_times:
        if bt > last_t:
            clips.append(clip.subclip(last_t, bt))
        effect_clip = (
            clip.subclip(bt, min(bt + 0.1, clip.duration))
            .fx(brighten, 1.5)
            .fx(vfx.crop, x_center=clip.w / 2, y_center=clip.h / 2, width=clip.w * 0.9, height=clip.h * 0.9)
        )
        clips.append(effect_clip)
        last_t = bt + 0.1
    if last_t < clip.duration:
        clips.append(clip.subclip(last_t))
    return mp.concatenate_videoclips(clips)


def generate_waveform_video_with_effects(audio_path, output_path, theme=(0, 0, 255)):
    y, sr = librosa.load(audio_path)
    amplitude_envelope = np.abs(y)
    time = np.linspace(0, len(y) / sr, len(y))
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Save waveform image
    plt.figure(figsize=(10, 4))
    plt.plot(time, amplitude_envelope, color='cyan')
    plt.title('Waveform')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.tight_layout()
    waveform_image_path = 'waveform.png'
    plt.savefig(waveform_image_path)
    plt.close()

    # Generate AI visuals
    ai_visuals = generate_ai_visuals(theme)
    ai_visuals_path = 'ai_visuals.png'
    ai_visuals.save(ai_visuals_path)

    # Create video clips
    duration = librosa.get_duration(y=y, sr=sr)
    ai_clip = mp.ImageClip(ai_visuals_path).set_duration(duration)
    waveform_clip = mp.ImageClip(waveform_image_path).set_duration(duration)
    combined_clip = mp.CompositeVideoClip([ai_clip, waveform_clip.set_position(("center", "center"))])
    audio_clip = mp.AudioFileClip(audio_path)
    video = combined_clip.set_audio(audio_clip)

    # Apply beat-synced effects
    video_with_effects = apply_beat_effects(video, beat_times)

    # Add metadata overlay
    metadata = extract_metadata(audio_path)
    txt = f"Title: {metadata['title']}\nArtist: {metadata['artist']}\nAlbum: {metadata['album']}"
    txt_clip = mp.TextClip(txt, fontsize=24, color='white').set_position(('center', 'bottom')).set_duration(duration)
    final_video = mp.CompositeVideoClip([video_with_effects, txt_clip])

    # Export
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')


def select_audio_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
    if file_path:
        audio_file_entry.delete(0, tk.END)
        audio_file_entry.insert(0, file_path)


def select_output_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Files", "*.mp4")])
    if file_path:
        output_file_entry.delete(0, tk.END)
        output_file_entry.insert(0, file_path)


def generate_video():
    audio_path = audio_file_entry.get()
    output_path = output_file_entry.get()
    if not audio_path or not output_path:
        messagebox.showerror("Error", "Please select both audio file and output file.")
        return
    generate_waveform_video_with_effects(audio_path, output_path)
    messagebox.showinfo("Success", f"Video saved to {output_path}")


# Create the GUI
root = tk.Tk()
root.title("AI Music Video Generator")

tk.Label(root, text="Select Audio File:").grid(row=0, column=0, padx=10, pady=10)
audio_file_entry = tk.Entry(root, width=50)
audio_file_entry.grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="Browse", command=select_audio_file).grid(row=0, column=2, padx=10, pady=10)

tk.Label(root, text="Select Output File:").grid(row=1, column=0, padx=10, pady=10)
output_file_entry = tk.Entry(root, width=50)
output_file_entry.grid(row=1, column=1, padx=10, pady=10)
tk.Button(root, text="Browse", command=select_output_file).grid(row=1, column=2, padx=10, pady=10)

tk.Button(root, text="Generate Video", command=generate_video).grid(row=2, column=0, columnspan=3, padx=10, pady=20)

root.mainloop()
