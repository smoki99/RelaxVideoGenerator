import os
import random
import time
from pydub import AudioSegment
from pydub.effects import crossfade
from moviepy.editor import *
import argparse

def create_audio_track(sounds_dir, output_format="mp3"):
    """
    Creates a concatenated audio track from wav files in a directory,
    with crossfades and a duration of at least 1 hour.

    Args:
        sounds_dir (str): Path to the directory containing wav files.
        output_format (str): Output audio format ('mp3' or 'm4a').

    Returns:
        tuple: (AudioSegment, list) - Concatenated audio segment and list of song titles.
    """
    sound_files = [f for f in os.listdir(sounds_dir) if f.lower().endswith(".wav")]
    if not sound_files:
        raise ValueError(f"No WAV files found in '{sounds_dir}'.")

    random.shuffle(sound_files)  # Randomize order
    used_files = set()
    combined_audio = AudioSegment.empty()
    total_duration_ms = 0
    song_titles = []

    crossfade_duration_ms = 3000  # 3 seconds crossfade

    while total_duration_ms < 60 * 60 * 1000:  # Target: 1 hour in milliseconds
        if not sound_files:
            print("Ran out of unique sound files, but still under 1 hour. Looping from the start (without duplicates again).")
            sound_files = [f for f in os.listdir(sounds_dir) if f.lower().endswith(".wav") and f not in used_files]
            if not sound_files:
                print("No more unique sound files left. Exiting audio generation early.")
                break # No more unique files to add
            random.shuffle(sound_files)

        sound_file = sound_files.pop(0) # Get the first file and remove it to avoid duplicates in this run
        if sound_file in used_files:
            continue # Should not happen in this logic, but just in case

        try:
            audio_segment = AudioSegment.from_wav(os.path.join(sounds_dir, sound_file))
            if combined_audio:
                combined_audio = combined_audio.append(audio_segment, crossfade=crossfade_duration_ms)
            else:
                combined_audio = audio_segment

            total_duration_ms += len(audio_segment)
            song_title = os.path.splitext(sound_file)[0].replace("_", " ").replace("-", " ").title() # Basic title from filename
            song_titles.append(song_title)
            used_files.add(sound_file)

        except Exception as e:
            print(f"Error loading or processing '{sound_file}': {e}")

    print(f"Generated audio track of {total_duration_ms / (60 * 1000):.2f} minutes.")

    output_audio_path = f"combined_audio.{output_format}"
    if output_format == "mp3":
        combined_audio.export(output_audio_path, format="mp3", bitrate="320k") # High quality mp3
    elif output_format == "m4a":
        combined_audio.export(output_audio_path, format="m4a", bitrate="320k", parameters=["-ac", "2"]) # Stereo m4a
    else:
        raise ValueError(f"Unsupported output format: '{output_format}'. Choose 'mp3' or 'm4a'.")

    return combined_audio, song_titles, output_audio_path


def create_video_track(clips_dir, song_titles, fontname="OCR A Std", fontsize=36):
    """
    Creates a video track from video clips in a directory, with soft aperture transitions
    and song titles overlaid.

    Args:
        clips_dir (str): Path to the directory containing video clips.
        song_titles (list): List of song titles to display.
        fontname (str): Font name for song titles.
        fontsize (int): Font size for song titles.

    Returns:
        VideoFileClip: Concatenated video clip.
    """
    clip_files = [f for f in os.listdir(clips_dir) if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))] # Add more formats if needed
    if not clip_files:
        raise ValueError(f"No video files found in '{clips_dir}'.")

    video_clips = []
    transition_duration = 1.5 # seconds for soft aperture transition

    for i, song_title in enumerate(song_titles):
        clip_file = random.choice(clip_files) # Allow duplicates
        try:
            video_clip = VideoFileClip(os.path.join(clips_dir, clip_file))

            # Soft Aperture (Crossfade) Transition
            if video_clips: # If not the first clip, add transition
                video_clips[-1] = CompositeVideoClip([video_clips[-1].fx(vfx.fadeout, transition_duration),
                                                       video_clip.fx(vfx.fadein, transition_duration)])

            # Song Title TextClip
            text_clip = TextClip(song_title, fontsize=fontsize, font=fontname, color='white', align='center')
            text_clip = text_clip.set_duration(video_clip.duration).set_position(('center', 'bottom')).margin(bottom=20, opacity=0) # Margin for better visibility

            video_clip = CompositeVideoClip([video_clip, text_clip])
            video_clips.append(video_clip)

        except Exception as e:
            print(f"Error loading or processing video clip '{clip_file}': {e}")

    if not video_clips:
        raise ValueError("No video clips were successfully loaded.")

    final_video = concatenate_videoclips(video_clips, intercut=False) # intercut=False important for transitions to work as expected

    return final_video


def generate_music_video(sounds_dir, clips_dir, output_filename="music_video.mp4", audio_format="mp3", font="OCR A Std", fontsize=36):
    """
    Generates a 1-hour music video by combining audio and video tracks.

    Args:
        sounds_dir (str): Directory with WAV sound files.
        clips_dir (str): Directory with video clips.
        output_filename (str): Name for the output MP4 file.
        audio_format (str): Output audio format ('mp3' or 'm4a').
        font (str): Font for song titles.
        fontsize (int): Font size for song titles.
    """
    start_time = time.time()
    print("Starting audio track generation...")
    try:
        combined_audio, song_titles, audio_path = create_audio_track(sounds_dir, audio_format)
    except ValueError as e:
        print(f"Error during audio track generation: {e}")
        return

    print("Audio track generated successfully.")

    print("Starting video track generation...")
    try:
        final_video = create_video_track(clips_dir, song_titles, font, fontsize)
    except ValueError as e:
        print(f"Error during video track generation: {e}")
        os.remove(audio_path) # Clean up audio file if video fails
        return
    print("Video track generated successfully.")

    print("Combining audio and video...")
    final_video = final_video.set_audio(AudioFileClip(audio_path)) # Load audio from file to avoid potential memory issues

    print("Rendering final video...")
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac",
                                 resolution=(1920, 1080), bitrate="8000k") # HD 1080p, good bitrate

    final_video.close() # Clean up video memory
    os.remove(audio_path) # Clean up temporary audio file
    print(f"Music video generated successfully: {output_filename}")
    print(f"Total time taken: {(time.time() - start_time)/60:.2f} minutes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a 1-hour music video from audio and video clips.")
    parser.add_argument("sounds_dir", help="Path to the directory containing WAV sound files.")
    parser.add_argument("clips_dir", help="Path to the directory containing video clips.")
    parser.add_argument("-o", "--output", dest="output_filename", default="music_video.mp4", help="Output filename for the MP4 video (default: music_video.mp4).")
    parser.add_argument("-af", "--audio_format", dest="audio_format", default="mp3", choices=['mp3', 'm4a'], help="Output audio format (mp3 or m4a, default: mp3).")
    parser.add_argument("-f", "--font", dest="font", default="OCR A Std", help="Font for song titles (default: OCR A Std).")
    parser.add_argument("-fs", "--fontsize", dest="fontsize", type=int, default=36, help="Font size for song titles (default: 36).")

    args = parser.parse_args()

    if not os.path.isdir(args.sounds_dir):
        print(f"Error: Sounds directory '{args.sounds_dir}' does not exist.")
    elif not os.path.isdir(args.clips_dir):
        print(f"Error: Clips directory '{args.clips_dir}' does not exist.")
    else:
        generate_music_video(args.sounds_dir, args.clips_dir, args.output_filename, args.audio_format, args.font, args.fontsize)
    