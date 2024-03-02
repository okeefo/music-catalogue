import re, os, sys
import time
import numpy as np
import librosa
import soundfile as sf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Tuple
from pydub import AudioSegment
from pydub.silence import split_on_silence
from log_config import get_logger
from auto_tag import get_discogs_client, ReleaseFacade, auto_tag_files

from PyQt5.QtWidgets import QApplication
from pyloudnorm import Meter


logger = get_logger(__name__)

__DISCOGS_CLIENT = get_discogs_client()


def process_file(fq_file_path: str) -> None:

    fq_file_path, root_dir, file_name = __normalise_file_path(fq_file_path)
    logger.info(f"Processing file: {fq_file_path}")

    release_id = __get_release_id(fq_file_path)
    if release_id is None:
        return

    release = __get_release(release_id)
    if release is None:
        return

    proc_file_name = __reduce_speed_of_file(fq_file_path, release)

    # files_to_tag = split_audio_file(proc_file_name, root_dir, release)
    # auto_tag_files(files_to_tag, root_dir)

    logger.info(f"{release.get_id()} - Processing complete for file: {fq_file_path}")


def __apply_loudness_normalisation(file_path: str, release_id: str) -> str:
    """Apply loudness normalisation to the audio file"""

    logger.info(f"{release_id} - Applying loudness normalisation to audio file: {file_path}")
    y, sr = librosa.load(file_path, sr=None)

    # Calculate the current maximum amplitude
    current_max_amplitude = np.max(np.abs(y))
    # Calculate the maximum possible amplitude for audio normalized between -1 and 1
    max_possible_amplitude = 1.0
    # Calculate the maximum possible gain in dB
    max_possible_gain = 15 * np.log10(max_possible_amplitude / current_max_amplitude)

    logger.info(f"{release_id} - Current Max Amplitude: {current_max_amplitude}, The maximum possible gain without clipping is {max_possible_gain}")

    if max_possible_gain < 0:
        logger.info(f"{release_id} - Audio file is already loud enough.  Skipping...")
        return file_path

    new_file = file_path.replace("slow", "amp")
    # AudioSegment.from_file(file_path).export(new_file, format="wav", parameters=["-filter:a", "loudnorm=I=-23:LRA=11:TP=-2.0"])  # Normalise to -23 LUFS

    audio = AudioSegment.from_file(file_path)

    # Increase volume by 10 dB
    louder_audio = audio.apply_gain(max_possible_gain)

    # Save the louder audio
    louder_audio.export(new_file, format="wav")

    logger.info(f"{release_id} - Loudness normalisation complete for audio file: {file_path}")
    return new_file


def __apply_loudness_normalisation_OLD(file_path: str, release_id: str) -> str:
    """Apply loudness normalisation to the audio file"""

    logger.info(f"{release_id} - Applying loudness normalisation to audio file: {file_path}")
    data, rate = sf.read(file=file_path)

    meter = Meter(rate)
    loudness = meter.integrated_loudness(data)
    logger.info(f"{release_id} - Integrated loudness of audio file: {loudness}")

    if loudness < -23:
        logger.info(f"{release_id} - Audio file is already loud enough.  Skipping...")
        return file_path
    target_loudness = 23
    gain = target_loudness - loudness
    logger.info(f"{release_id} - Audio file is too quiet.  Normalising loudness to -23 LUFS - gain will be {gain}")

    new_file = file_path.replace("slow", "amp")
    # AudioSegment.from_file(file_path).export(new_file, format="wav", parameters=["-filter:a", "loudnorm=I=-23:LRA=11:TP=-2.0"])  # Normalise to -23 LUFS

    audio = AudioSegment.from_file(file_path)

    # Increase volume by 10 dB
    louder_audio = audio.apply_gain(4)

    # Save the louder audio
    louder_audio.export(new_file, format="wav")

    logger.info(f"{release_id} - Loudness normalisation complete for audio file: {file_path}")
    return new_file


def split_audio_file(fq_audio_file: str, root_dir: str, release: ReleaseFacade) -> List[str]:

    logger.info(f"{release.get_id()} - Comparing number of tracks in release and audio file:")
    audio = AudioSegment.from_wav(fq_audio_file)
    chunks = split_on_silence(audio, min_silence_len=2000, silence_thresh=-45, keep_silence=1000, seek_step=10)

    number_of_tracks = release.get_number_of_tracks()
    number_of_chunks = len(chunks)

    cleaned_chunks = []
    for chunk in chunks:
        estimated_size = chunk.frame_count() * 2 / 1024
        if estimated_size >= 550:
            cleaned_chunks.append(chunk)

    number_of_chunks = len(cleaned_chunks)
    if number_of_tracks is not None and number_of_chunks != number_of_tracks:
        logger.error(f"{release.get_id()} - Number of tracks in release {release.get_number_of_tracks()} does not match number of tracks in audio file {number_of_chunks}.  Skipping...")
        return []

    logger.info(f"{release.get_id()} - Number of tracks in release {release.get_number_of_tracks()} matches number of tracks in audio file {fq_audio_file}")
    logger.info(f"{release.get_id()} - Splitting audio file into {number_of_chunks} tracks")

    file_list = []
    for track_no, chunk in enumerate(cleaned_chunks, start=1):

        track_name = fq_audio_file.replace(".wav", f"_{track_no}.wav")
        logger.info(f"{release.get_id()} - writing track {track_name} to disk.")
        chunk.export(track_name, format="wav")
        proc_file_name = __apply_loudness_normalisation(track_name, release.get_id())
        file_list.append(proc_file_name)

    return file_list


def __reduce_speed_of_file(file_path: str, release: ReleaseFacade) -> str:
    """Reduce the speed of the audio file"""

    speed = get_recorded_speed(file_path, release)
    if speed == "45":
        logger.info(f"{release_id} - NO identifiers to change speed:  Skipping...")
        return file_path

    release_id = release.get_id()
    new_file_name = file_path.replace(".wav", "_slow.wav")

    # check to see if file has already been processed:
    logger.info(f"{release_id} - Checking for an already processed file: {new_file_name}")
    if os.path.exists(new_file_name):
        logger.info(f"{release_id} - File has already been processed:  Skipping...")
        return new_file_name

    # Load the audio file with its original sample rate and in stereo
    logger.info(f"{release_id} - Loading file...")
    audio = AudioSegment.from_file(file_path)

    # The speed increase from 33.3 RPM to 45 RPM is approximately 35.1%. This is calculated as follows:
    # (45 - 33.3) / 33.3 * 100 = 35.1%

    # To revert the speed back to the original, you need to decrease the speed by the same factor. 
    # However, you need to decrease the speed relative to the increased speed (45 RPM), not the original speed (33.3 RPM). 
    # This is calculated as follows:
    # 100 - (100 / (1 + 35.1 / 100)) = 26.0%
    
    # So, a decrease of 26.0% from the increased speed (45 RPM) will bring you back to the original speed (33.3 RPM). 
    # This is why I use -rate=-25.926 
    # The slight difference between 26.0% and 25.926% is due to rounding errors in the calculations.

    # Slow down the tempo
    
    logger.info(f"{release_id} - slowing down the tempo file...")

    # Use soundstretch to slow down the tempo
    os.system(f'.\\soundstretch-v2.3.2\\soundstretch.exe "{file_path}" "{new_file_name}" -rate=-25.926')
    
    gain_value = 5
    amp_file_name = new_file_name.replace("_slow", "_amp")
    #time.sleep(5000)
    command=f'sox.exe "{new_file_name}" "{amp_file_name}" gain -l {gain_value}'
    logger.info(f"{release_id} - Amplifying the audio by {gain_value} dB - {command}")
    os.system(command)

    logger.info(f"{release_id} - done with soundstretch and sox new file: {amp_file_name}")

    return new_file_name


def __reduce_speed_of_file_3(file_path: str, release: ReleaseFacade) -> str:
    """Reduce the speed of the audio file"""

    speed = get_recorded_speed(file_path, release)
    if speed == "45":
        logger.info(f"{release_id} - NO identifiers to change speed:  Skipping...")
        return file_path

    release_id = release.get_id()
    new_file_name = file_path.replace(".wav", "_slow.wav")

    # check to see if file has already been processed:
    logger.info(f"{release_id} - Checking for an already processed file: {new_file_name}")
    if os.path.exists(new_file_name):
        logger.info(f"{release_id} - File has already been processed:  Skipping...")
        return new_file_name

    # Load the audio file with its original sample rate and in stereo
    logger.info(f"{release_id} - Loading file...")
    audio = AudioSegment.from_file(file_path)

    # Slow down the audio by a factor of 33.3/45 and reduce the pitch by the same factor for each channel separately
    original_speed = 45  # The original speed in rpm
    desired_speed = 33.3  # The desired speed in rpm
    slow_rate = 0.741  # desired_speed / original_speed

    # Slow down the tempo
    logger.info(f"{release_id} - slowing down the tempo file...")
    audio_slow = audio.speedup(playback_speed=slow_rate)
    logger.info(f"{release_id} - done")

    # Calculate the current maximum dBFS
    current_max_dBFS = audio_slow.max_dBFS

    # Calculate the maximum possible gain in dB without clipping
    max_possible_gain = 0 - current_max_dBFS

    # Print the maximum possible gain
    logger.info(f"{release_id} - The maximum possible gain without clipping is {max_possible_gain} dB.")
    audio_amplified = audio_slow.apply_gain(6)

    # Save the slowed audio
    logger.info(f"{release_id} - writing audio to new file: {new_file_name}")
    audio_amplified.export(new_file_name, format="wav")
    return new_file_name


def __reduce_speed_of_file_2(file_path: str, release: ReleaseFacade) -> str:
    """Reduce the speed of the audio file"""

    speed = get_recorded_speed(file_path, release)
    if speed == "45":
        logger.info(f"{release_id} - NO identifiers to change speed:  Skipping...")
        return file_path

    release_id = release.get_id()
    new_file_name = file_path.replace(".wav", "_slow.wav")

    # check to see if file has already been processed:
    logger.info(f"{release_id} - Checking for an already processed file: {new_file_name}")
    if os.path.exists(new_file_name):
        logger.info(f"{release_id} - File has already been processed:  Skipping...")
        return new_file_name

    # Get the sample rate of the original file
    original_info = sf.info(file_path)
    original_sr = original_info.samplerate
    original_subtype = original_info.subtype
    logger.info(f"{release_id} - Sample rate: {original_sr}, subtype: {original_subtype}, format: {original_info.format}, endian: {original_info.endian}")

    # Load the audio file with its original sample rate and in stereo
    logger.info(f"{release_id} - Loading file...")
    y, sr = librosa.load(file_path, sr=original_sr, mono=False)

    # Slow down the audio by a factor of 33.3/45 and reduce the pitch by the same factor for each channel separately
    original_speed = 45  # The original speed in rpm
    desired_speed = 33  # The desired speed in rpm
    slow_rate = 0.741  # desired_speed / original_speed
    pitch_shift = 12 * np.log2(slow_rate)
    logger.info(f"{release_id} - Slowing by a factor of {slow_rate}, with a pitch shift of {pitch_shift} semitones")

    y_slow_pitched = []
    for i in range(y.shape[0]):
        # Slow down the audio
        y_slow = librosa.effects.time_stretch(y[i], rate=slow_rate)
        # Decrease the pitch
        y_pitch_shifted = librosa.effects.pitch_shift(y_slow, sr=original_sr, n_steps=pitch_shift)
        y_slow_pitched.append(y_pitch_shifted)

    # Transpose y_slow_pitched so that it's a 2D array with shape (num_samples, num_channels)
    y_slow_pitched = np.array(y_slow_pitched).T

    # Convert to 16-bit PCM
    y_slow_pitched = (y_slow_pitched * 32767).astype(np.int16)

    logger.info(f"{release_id} - writing audio to new file: {new_file_name}")
    sf.write(new_file_name, y_slow_pitched, original_sr, subtype=original_subtype, format=original_info.format, endian=original_info.endian)

    return new_file_name


def get_recorded_speed(filename: str, release: ReleaseFacade) -> str:
    """Get the recorded speed of the audio file:  Assumes that the vinyl was recoded at 45rpm as per my workflow"""

    release_id = release.get_id()
    if match := re.search(r"(\d{2,3})rpm", filename):
        speed = match[1]
        logger.info(f"{release_id} - Found speed '{speed}' in file name: {filename}")
        return str(speed)

    if match := re.search(r"33.*rpm", release.get_media(), re.IGNORECASE):
        logger.info(f"{release_id} - Found speed '33' in release media: {release.get_media()}")
        return str(33)


def __get_release(release_id) -> ReleaseFacade:

    release_id = int(release_id[1:]) if release_id.startswith("r") else int(release_id)

    try:
        release_raw = __DISCOGS_CLIENT.release(release_id)
        if release_raw is None:
            logger.error(f"{release_id} - Could not get release from discogs.  Skipping...")
            return None
        return ReleaseFacade(release=release_raw)

    except Exception:
        logger.error(f"{release_id} - Could not get from release from discogs: exception caught", exc_info=True)
        return None


def __get_release_id(file_path) -> str:

    if match := re.search(r"r(\d{6,10})", file_path):
        release_id = match[1]
        logger.info(f"{release_id} - Found release id in file name: {file_path}")
        return release_id

    else:
        logger.error(f"Could not find release id in file name: {file_path}")
        return None


def __normalise_file_path(fq_file_path: str) -> Tuple[str, str, str]:
    """Normalise the file path"""
    fq_file_path = os.path.normpath(fq_file_path)
    root_dir, file_name = os.path.split(fq_file_path)
    return fq_file_path, root_dir, file_name


if __name__ == "__main__":

    import librosa, sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    app = QApplication([])  # Create QApplication instance first
    #   app.exec_()

    print(f" librosa version {librosa.__version__}")
    process_file("e:\\Audacity Projects\\a20_HV_Regen_2_33rpm_[r22685345].wav")
    print("Done")
