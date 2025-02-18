import os
import random
import time
import logging  # Import the logging module
from pydub import AudioSegment
from moviepy.editor import *
import argparse

# Global Variables
MINUTES = 5

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_audio_track(sounds_dir, output_format="mp3"):
    """
    Creates a concatenated audio track from audio files (wav, mp3, m4a) in a directory,
    with crossfades and a duration of at least 1 hour.

    Args:
        sounds_dir (str): Path to the directory containing audio files.
        output_format (str): Output audio format ('mp3' or 'm4a').

    Returns:
        tuple: (AudioSegment, list) - Concatenated audio segment and list of song titles.
    """
    logging.info(f"Starting audio track generation from directory: '{sounds_dir}'")
    audio_files = []
    for f in os.listdir(sounds_dir):
        if f.lower().endswith((".wav", ".mp3", ".m4a")): # Look for wav, mp3, m4a files
            audio_files.append(f)

    if not audio_files:
        error_msg = f"No WAV, MP3, or M4A files found in '{sounds_dir}'."
        logging.error(error_msg)
        raise ValueError(error_msg)

    random.shuffle(audio_files)  # Randomize order
    used_files = set()
    combined_audio = AudioSegment.empty()
    total_duration_ms = 0
    song_titles = []

    crossfade_duration_ms = 3000  # 3 seconds crossfade

    while total_duration_ms < 5 * 60 * 1000:  # Target: 5 minutes in milliseconds (for testing)
        if not audio_files:
            logging.warning("Ran out of unique audio files, but still under 5 minutes. Looping from the start (without duplicates again).")
            audio_files = [f for f in os.listdir(sounds_dir) if f.lower().endswith((".wav", ".mp3", ".m4a")) and f not in used_files]
            if not audio_files:
                logging.warning("No more unique audio files left. Exiting audio generation early.")
                break # No more unique files to add
            random.shuffle(audio_files)

        audio_file = audio_files.pop(0) # Get the first file and remove it to avoid duplicates in this run
        if audio_file in used_files:
            logging.debug(f"Skipping already used audio file: '{audio_file}'") # Should not happen in this logic, but just in case
            continue # Should not happen in this logic, but just in case

        logging.debug(f"Processing audio file: '{audio_file}'")
        try:
            file_path = os.path.join(sounds_dir, audio_file)
            if audio_file.lower().endswith(".wav"):
                audio_segment = AudioSegment.from_wav(file_path)
            elif audio_file.lower().endswith(".mp3"):
                audio_segment = AudioSegment.from_mp3(file_path)
            elif audio_file.lower().endswith(".m4a"):
                audio_segment = AudioSegment.from_file(file_path, format="m4a") # Use generic from_file for m4a
            else:
                logging.warning(f"Skipping unsupported audio file format: '{audio_file}'")
                continue # Skip to the next file

            if combined_audio:
                combined_audio = combined_audio.append(audio_segment, crossfade=crossfade_duration_ms)
                logging.debug(f"Appended '{audio_file}' with crossfade.")
            else:
                combined_audio = audio_segment
                logging.debug(f"Started audio with '{audio_file}'.")

            total_duration_ms += len(audio_segment)
            song_title = os.path.splitext(audio_file)[0].replace("_", " ").replace("-", " ").title() # Basic title from filename
            song_titles.append(song_title)
            used_files.add(audio_file)
            logging.debug(f"Added song title: '{song_title}'. Total audio duration: {total_duration_ms / 1000:.2f} seconds.")

        except Exception as e:
            error_msg = f"Error loading or processing '{audio_file}': {e}"
            logging.error(error_msg)

    logging.info(f"Generated audio track of {total_duration_ms / (60 * 1000):.2f} minutes.")

    # *** ADDED LINES - Export temporary WAV for debugging ***
    temp_wav_path = "temp_combined_audio.wav" # Temporary WAV file in working directory
    combined_audio.export(temp_wav_path, format="wav") # Export to WAV first
    logging.info(f"Exported temporary WAV audio to: '{temp_wav_path}'") # Log message
    # *** END OF ADDED LINES ***


    output_audio_path = f"combined_audio.{output_format}"
    if output_format == "mp3":
        combined_audio.export(output_audio_path, format="mp3", bitrate="320k") # High quality mp3
        logging.info(f"Exported audio to MP3: '{output_audio_path}'")
    elif output_format == "m4a":
        combined_audio.export(output_audio_path, format="m4a", bitrate="320k", parameters=["-ac", "2"]) # Stereo m4a
        logging.info(f"Exported audio to M4A: '{output_audio_path}'")
    else:
        error_msg = f"Unsupported output format: '{output_format}'. Choose 'mp3' or 'm4a'."
        logging.error(error_msg)
        raise ValueError(error_msg)

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
    logging.info(f"Starting video track generation from directory: '{clips_dir}'")
    clip_files = [f for f in os.listdir(clips_dir) if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))] # Add more formats if needed
    if not clip_files:
        error_msg = f"No video files found in '{clips_dir}'."
        logging.error(error_msg)
        raise ValueError(error_msg)

    video_clips = []
    transition_duration = 1.5 # seconds for soft aperture transition

    for i, song_title in enumerate(song_titles):
        clip_file = random.choice(clip_files) # Allow duplicates
        logging.debug(f"Choosing video clip '{clip_file}' for song: '{song_title}'")
        try:
            video_clip = VideoFileClip(os.path.join(clips_dir, clip_file))
            logging.debug(f"Loaded video clip: '{clip_file}', duration: {video_clip.duration:.2f} seconds.")

            # Soft Aperture (Crossfade) Transition
            if video_clips: # If not the first clip, add transition
                logging.debug("Adding soft aperture transition.")
                video_clips[-1] = CompositeVideoClip([video_clips[-1].fx(vfx.fadeout, transition_duration),
                                                       video_clip.fx(vfx.fadein, transition_duration)])

            # Song Title TextClip
            text_clip = TextClip(song_title, fontsize=fontsize, font=fontname, color='white', align='center')
            text_clip = text_clip.set_duration(video_clip.duration).set_position(('center', 'bottom')).margin(bottom=20, opacity=0) # Margin for better visibility
            logging.debug(f"Created text clip for song title: '{song_title}'.")

            video_clip = CompositeVideoClip([video_clip, text_clip])
            video_clips.append(video_clip)
            logging.debug("Added video clip to the sequence.")

        except Exception as e:
            error_msg = f"Error loading or processing video clip '{clip_file}': {e}"
            logging.error(error_msg)

    if not video_clips:
        error_msg = "No video clips were successfully loaded."
        logging.error(error_msg)
        raise ValueError(error_msg)

    final_video = concatenate_videoclips(video_clips) # intercut=False removed for transitions to work as expected
    logging.info("Video track generation complete.")
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
    logging.info("Starting music video generation.")
    logging.info(f"Sounds directory: '{sounds_dir}', Clips directory: '{clips_dir}', Output filename: '{output_filename}', Audio format: '{audio_format}', Font: '{font}', Font size: {fontsize}")

    try:
        combined_audio, song_titles, audio_path = create_audio_track(sounds_dir, audio_format)
    except ValueError as e:
        logging.error(f"Error during audio track generation: {e}")
        return

    logging.info("Audio track generated successfully.")

    try:
        final_video = create_video_track(clips_dir, song_titles, font, fontsize)
    except ValueError as e:
        logging.error(f"Error during video track generation: {e}")
        os.remove(audio_path) # Clean up audio file if video fails
        return
    logging.info("Video track generated successfully.")

    logging.info("Combining audio and video...")
    final_video = final_video.set_audio(AudioFileClip(audio_path)) # Load audio from file to avoid potential memory issues

    logging.info("Rendering final video...")
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k") # HD 1080p, good bitrate
    logging.info(f"Video rendering complete. Output file: '{output_filename}'")

    final_video.close() # Clean up video memory
    os.remove(audio_path) # Clean up temporary audio file
    logging.info(f"Cleaned up temporary audio file: '{audio_path}'")
    logging.info(f"Music video generated successfully: {output_filename}")
    total_time_minutes = (time.time() - start_time)/60
    logging.info(f"Total time taken: {total_time_minutes:.2f} minutes.")
    logging.info("Music video generation finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a 1-hour music video from audio and video clips.")
    parser.add_argument("sounds_dir", help="Path to the directory containing WAV sound files.")
    parser.add_argument("clips_dir", help="Path to the directory containing video clips.")
    parser.add_argument("-o", "--output", dest="output_filename", default="music_video.mp4", help="Output filename for the MP4 video (default: music_video.mp4).")
    parser.add_argument("-af", "--audio_format", dest="audio_format", default="mp3", choices=['mp3', 'm4a'], help="Output audio format (mp3 or m4a, default: mp3).")
    parser.add_argument("-f", "--font", dest="font", default="OCR A Std", help="Font for song titles (default: OCR A Std).")
    parser.add_argument("-fs", "--fontsize", dest="fontsize", type=int, default=36, help="Font size for song titles (default: 36).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level).") # Added verbose flag

    args = parser.parse_args()

    if args.verbose: # Set logging level to DEBUG if verbose flag is used
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled.")

    if not os.path.isdir(args.sounds_dir):
        logging.error(f"Error: Sounds directory '{args.sounds_dir}' does not exist.")
    elif not os.path.isdir(args.clips_dir):
        logging.error(f"Error: Clips directory '{args.clips_dir}' does not exist.")
    else:
        generate_music_video(args.sounds_dir, args.clips_dir, args.output_filename, args.audio_format, args.font, args.fontsize)