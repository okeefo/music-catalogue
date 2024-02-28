import re, os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Tuple
from pydub import AudioSegment
from pydub.silence import split_on_silence
from log_config import get_logger
from auto_tag import get_discogs_client, ReleaseFacade, auto_tag_files
import librosa
import soundfile as sf
from PyQt5.QtWidgets import QApplication

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

    speed = get_recorded_speed(file_name, release)

    proc_file_name = __reduce_speed_of_file(fq_file_path, speed, release_id)

    files_to_tag: list = split_audio_file(proc_file_name, root_dir, release)
    auto_tag_files(files_to_tag, root_dir)

    logger.info(f"{release.get_id()} - Processing complete for file: {fq_file_path}")


def split_audio_file(fq_audio_file: str, root_dir: str, release: ReleaseFacade) -> List[str]:

    logger.info(f"{release.get_id()} - Comparing number of tracks in release and audio file:")
    audio = AudioSegment.from_wav(fq_audio_file)
    chunks = split_on_silence(audio, min_silence_len=2000, silence_thresh=-50, keep_silence=1000, seek_step=10)

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
        file_list.append(track_name)

    return file_list


def __reduce_speed_of_file(file_path: str, speed: str, release_id: str) -> str:
    """Reduce the speed of the audio file"""

    if speed == "45":
        return file_path

    new_file_name = file_path.replace(".wav", "_slow.wav")
    # check to see if file has already been processed:
    logger.info(f"{release_id} - Checking if file has already been processed: {new_file_name}")
    if os.path.exists(new_file_name):
        logger.info(f"{release_id} - File has already been processed: {new_file_name}.  Skipping...")
        return new_file_name

    # Load the audio file
    logger.info(f"{release_id} - Reducing speed of audio file: {file_path} - Loading file...")
    y, sr = librosa.load(file_path, sr=None)

    logger.info(f"{release_id} - Reducing speed of audio file: {file_path} by a factor of {33.3/45}")
    # Slow down the audio by a factor of 33.3/45
    slow_rate = 33.3 / 45
    y_slow = librosa.effects.time_stretch(y, rate=slow_rate)

    # Save the slowed down audio to a new file

    logger.info(f"{release_id} - Saving slowed down audio to new file: {new_file_name}")
    sf.write(new_file_name, y_slow, sr)

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

    import librosa
    app = QApplication([])  # Create QApplication instance first
 #   app.exec_() 


    print(f" librosa version {librosa.__version__}")
    process_file("e:\\Audacity Projects\\a19_LightsOver_[r23187587].wav")
    print("Done")
