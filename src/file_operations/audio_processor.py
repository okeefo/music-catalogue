import os
import re
import subprocess
import sys
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Tuple

from pydub import AudioSegment
from pydub.silence import split_on_silence

from config_manager import ConfigurationManager
from file_operations.audio_tags import AudioTagHelper
from file_operations.auto_tag import ReleaseFacade, auto_tag_files, get_discogs_client
from log_config import get_logger
from ui.progress_bar_helper import ProgressBarHelper

config = ConfigurationManager()
config.add_to_system_path("utils\\sox")
config.add_to_system_path("utils\\soundstretch")
logger = get_logger(__name__)
__DISCOGS_CLIENT = get_discogs_client()
audio_tag_helper = AudioTagHelper()

# Audio splitting thresholds (dBFS) and binary-search limits.
_SPLIT_LOW_THRESH_DBFS: int = -55
_SPLIT_HIGH_THRESH_DBFS: int = -25
_SPLIT_MAX_ATTEMPTS: int = 8
_SPLIT_MIN_SILENCE_MS: int = 2000

# Options that only use the Discogs release for log messages, so files without
# a release id (e.g. not recorded via the usual vinyl workflow) can still be processed.
_RELEASE_OPTIONAL_OPTIONS = ("Amplify", "Trim")

# Silence-trim constants.
_TRIM_SILENCE_THRESHOLD_DBFS: int = -35
# Pad this many milliseconds of silence before trimming to avoid clipping the
# real audio start — SoX can introduce a tiny DC offset at the very beginning.
_TRIM_PRE_START_BUFFER_MS: int = 100


def amplify_files(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be amplified."""
    __batch_process_files(fq_file_path, option="Amplify")


def slowdown_files_45_33(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be slowed down."""
    __batch_process_files(fq_file_path, option="Slowdown")


def speed_up_files_33_45rpm(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be speed up."""
    __batch_process_files(fq_file_path, option="Speed_Up")


def split_files(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be split."""
    __batch_process_files(fq_file_path, option="Split")


def trim_audio_silence(fq_file_path: List[str]) -> None:
    """Trims the silience at the begining of the audio file"""
    __batch_process_files(fq_file_path, option="Trim")


def auto_process_files(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be slowed down, amplified, split and tagged."""
    __batch_process_files(fq_file_path, option="ALL")


def __batch_process_files(fq_files: List[str], option="ALL") -> None:
    """Process a list of audio files.
    option may be: ALL, Slowdown, Amplify, Split, Speed_Up, or Trim.
    """
    progress_parts = 5 if option == "ALL" else 1  # slowdown, trim, amplify, split, tag
    progress_bar = ProgressBarHelper((len(fq_files) * progress_parts) + 2, "Processing..", min_files=1)
    maintain_tags = option != "ALL"

    for fq_file_path in fq_files:
        status_msg = f"Processing file: {os.path.basename(fq_file_path)}\n"
        progress_bar.increment_with_message(status_msg)

        validated = __validate_file_for_processing(fq_file_path, option)
        if validated is None:
            continue
        fq_file_path, root_dir, release = validated

        __apply_processing_option(fq_file_path, root_dir, release, option, maintain_tags, progress_bar, status_msg)

    progress_bar.complete_progress_bar()


def __validate_file_for_processing(fq_file_path: str, option: str = "ALL"):
    """Return (fq_file_path, root_dir, release) if the file is processable, else None."""
    fq_file_path, root_dir, file_name = __normalise_file_path(fq_file_path)

    if os.path.isdir(fq_file_path):
        logger.info(f"Skipping directory: {fq_file_path}")
        return None
    if not fq_file_path.endswith(".wav"):
        logger.info(f"Skipping, wavs only, file: {fq_file_path}")
        return None
    if is_file_locked(fq_file_path):
        logger.error(f"Skipping, file is locked: {fq_file_path}")
        return None

    logger.info(f"Processing file: {file_name}")
    release_optional = option in _RELEASE_OPTIONAL_OPTIONS

    release_id = __get_release_id(fq_file_path)
    if release_id is None:
        if not release_optional:
            return None
        logger.info(f"No release id for '{file_name}': continuing, '{option}' does not need one")
        return fq_file_path, root_dir, _FilenameRelease(file_name)

    release = __get_release(release_id)
    if release is None:
        if not release_optional:
            return None
        logger.info(f"Could not fetch release {release_id} for '{file_name}': continuing, '{option}' does not need it")
        return fq_file_path, root_dir, _FilenameRelease(file_name)

    return fq_file_path, root_dir, release


def __apply_processing_option(
    fq_file_path: str,
    root_dir: str,
    release,
    option: str,
    maintain_tags: bool,
    progress_bar,
    status_msg: str,
) -> None:
    """Dispatch to the correct processing step(s) for the given option."""
    if option in ["ALL", "Slowdown"]:
        progress_bar.increment_with_message(f"{status_msg} Reduce speed to 33rpm")
        result = __reduce_recording_speed(fq_file_path, release, maintain_tags, option == "Slowdown")
        if (not result) or option == "Slowdown":
            return

    if option == "ALL":
        progress_bar.increment_with_message(f"{status_msg} Trimming leading silence")
        __trim_the_silence(fq_file_path, release.get_id(), maintain_tags=False)

    if option in ["ALL", "Amplify"]:
        progress_bar.increment_with_message(f"{status_msg} Amplify file")
        result = __amplify_file(fq_file_path, release.get_id(), maintain_tags)
        if not result or option == "Amplify":
            return

    if option == "Speed_Up":
        progress_bar.increment_with_message(f"{status_msg} increasing speed up to 45rpm")
        __increase_speed_of_file_from_33_45rpm(fq_file_path, release, maintain_tags)
        return

    if option == "Trim":
        progress_bar.increment_with_message(f"{status_msg} trimming")
        __trim_the_silence(fq_file_path, release.get_id(), maintain_tags)
        return

    if option in ["ALL", "Split"]:
        progress_bar.increment_with_message(f"{status_msg} splitting into files")
        tracks = __split_audio_file(fq_file_path, release, progress_bar)
        if option == "Split":
            return
        progress_bar.update_progress_bar_text(f"{status_msg} tagging files")
        auto_tag_files(tracks, root_dir)

    logger.info(f"{release.get_id()} - Processing complete for {os.path.basename(fq_file_path)}")


def __reduce_recording_speed(source_file: str, release: ReleaseFacade, maintain_tags=False, skip_speed_check=False) -> Tuple[bool, str]:
    """Reduce the speed of the file by a ration of 45rpm -> 33rpm."""

    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)

    if not skip_speed_check:
        speed = __get_recorded_speed(source_file, release)

        if speed != "33":
            logger.info(f"{release.get_id()} - NO identifiers to change speed:  Skipping...")
            return True

    result = __reduce_speed_of_file_from_45_33rpm(source_file, release.get_id())

    if result and maintain_tags:
        audio_tag_helper.write_tags(source_file, tags)
        audio_tag_helper.write_cover_art(source_file, cover_art)

    return result


def __split_audio_file(fq_audio_file: str, release: ReleaseFacade, progress_bar: ProgressBarHelper = None) -> List[str]:
    """Split the audio file into individual tracks based on the number of tracks in the release.
    If the number of tracks in the release does not match the number of tracks in the audio file, adjust the silence threshold and try again.
    If the number of tracks in the release does not match the number of tracks in the audio file after X attempts, exit the loop.
    Implemented a binary search approach here to find the correct silence threshold."""

    msg = f"{release.get_id()} - Comparing number of tracks in release and audio file:"
    logger.info(msg)
    if progress_bar is not None:
        progress_bar.update_progress_bar_text(msg)

    number_of_tracks = release.get_number_of_tracks()
    low_thresh = _SPLIT_LOW_THRESH_DBFS
    high_thresh = _SPLIT_HIGH_THRESH_DBFS

    for _ in range(_SPLIT_MAX_ATTEMPTS):
        silence_thresh = (low_thresh + high_thresh) / 2  # Midpoint of current range
        chunks = __execute_split(fq_audio_file, silence_thresh)

        number_of_chunks = len(chunks)
        if number_of_tracks is not None and number_of_chunks == number_of_tracks:
            return __split(release.get_id(), fq_audio_file, chunks, silence_thresh)  # Exit the loop if the number of chunks matches the number of tracks

        # Adjust the silence threshold based on the number of chunks
        if number_of_chunks < number_of_tracks:
            low_thresh = silence_thresh  # Adjust the low threshold if there are too few chunks
        else:
            high_thresh = silence_thresh  # Adjust the high threshold if there are too many chunks

        msg = f"{release.get_id()} - Number of tracks in release {number_of_tracks} does not match number found in audio file {number_of_chunks}.  Adjusting silence threshold to {silence_thresh}..."
        logger.error(msg)
        if progress_bar is not None:
            progress_bar.update_progress_bar_text(msg)

    msg = f"{release.get_id()} - Could not split audio file into tracks after maximum attempts.  Exiting..."
    logger.error(msg)
    progress_bar.update_progress_bar_text(msg)

    return []


def __split(release_id: str, fq_audio_file: str, chunks: List[AudioSegment], silence_thresh: int) -> List[str]:
    number_of_chunks = len(chunks)
    filename = fq_audio_file.split("\\")[-1]
    logger.info(f"{release_id} - Number of tracks in release {number_of_chunks} matches number of tracks in audio file {filename},  silence threshold {silence_thresh}")
    logger.info(f"{release_id} - Splitting audio file into {number_of_chunks} tracks")

    try:
        file_list = []
        for track_no, chunk in enumerate(chunks, start=1):
            track_name = fq_audio_file.replace(".wav", f"_{track_no}.wav")
            logger.info(f"{release_id} - writing track {track_name} to disk.")
            chunk.export(track_name, format="wav")
            file_list.append(track_name)

        logger.info(f"{release_id} - Audio file split successfully. remove original file.")
        os.remove(fq_audio_file)
        return file_list
    except Exception as e:
        logger.error(f"{release_id} - An error occurred while splitting the audio file: {e}")
        return file_list


def __execute_split(fq_audio_file: str, silence_thresh: int) -> List[AudioSegment]:
    """Split the audio file into individual tracks"""

    audio = AudioSegment.from_wav(fq_audio_file)
    chunks = split_on_silence(audio, min_silence_len=_SPLIT_MIN_SILENCE_MS, silence_thresh=silence_thresh, keep_silence=True, seek_step=10)
    cleaned_chunks = []
    for chunk in chunks:
        estimated_size = chunk.frame_count() * 2 / 1024
        if estimated_size >= 10000:
            cleaned_chunks.append(chunk)

    return cleaned_chunks


def __reduce_speed_of_file_from_45_33rpm(source_file: str, release_id: str) -> bool:
    """Reduce the speed of the audio file from 45 RPM to 33 RPM. Percentage reduction calculation is as follows:

    (from speed - to speed) / from speed * 100
    45 - 33.333 / 45 * 100 = -25.926

    """
    logger.info(f"{release_id} - Reducing speed of file from 45 RPM to 33 RPM")
    command_mask = ["soundstretch.exe", "{source}", "{target}", "-rate=-25.926"]
    return __execute_and_rename("Slowing", source_file, command_mask, release_id)


def __increase_speed_of_file_from_33_45rpm(source_file: str, release_id: str, maintain_tags=False) -> bool:
    """Increase the speed of the audio file from 33 RPM to 45 RPM. Percentage increase calculation is as follows:

    (from speed - to speed) / from speed * 100

    (33.333 - 45 / 33.333) * 100 = 35.001

    """

    logger.info(f"{release_id} - Speeding up file from 33 RPM to 45 RPM")

    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)

    command_mask = ["soundstretch.exe", "{source}", "{target}", "-rate=35.001"]
    result = __execute_and_rename("Speeding up", source_file, command_mask, release_id)

    if result and maintain_tags:
        audio_tag_helper.write_tags(source_file, tags)
        audio_tag_helper.write_cover_art(source_file, cover_art)

    return result


def __trim_the_silence(source_file: str, release_id: str, maintain_tags: bool = False) -> bool:
    """Trim leading silence from source_file using SoX.

    Pads _TRIM_PRE_START_BUFFER_MS of silence before trimming to prevent SoX
    from clipping the first few samples of real audio (DC-offset workaround).
    """
    logger.info(f"{release_id} - Trimming the silence at the beginning of the audio file")
    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)

    pad_secs = _TRIM_PRE_START_BUFFER_MS / 1000.0
    command = [
        "sox.exe", "{source}", "{target}",
        "pad", f"{pad_secs:.3f}", "0",
        "silence", "-l", "1", "0.1", f"{_TRIM_SILENCE_THRESHOLD_DBFS}d",
    ]
    result = __execute_and_rename("Trim", source_file, command, release_id)
    if result and maintain_tags:
        audio_tag_helper.write_tags(source_file, tags)
        audio_tag_helper.write_cover_art(source_file, cover_art)

    return result


def __amplify_file(source_file: str, release_id: str, maintain_tags) -> bool:
    """Amplify the audio file to the correct volume level. To do this, it calculates the gain value and then applies it to the audio file."""

    logger.info(f"{release_id} - Amplifying the audio: calculating gain value")

    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)

    gain_value = __get_volume(source_file)
    if gain_value is None:
        logger.error(f"{release_id} - Could not determine volume (is sox available?):  Skipping...")
        return False
    # sox reports the multiplier needed to reach full scale; ~1.0 means already at max volume
    if abs(gain_value - 1.0) < 0.01:
        logger.info(f"{release_id} - Audio is already at the correct volume:  Skipping...")
        return True

    command = ["sox.exe", "-v", f"{gain_value}", "{source}", "{target}"]
    result = __execute_and_rename("Amplifying", source_file, command, release_id)
    if result and maintain_tags:
        audio_tag_helper.write_tags(source_file, tags)
        audio_tag_helper.write_cover_art(source_file, cover_art)

    return result


def __execute_and_rename(action: str, source_file: str, command_mask: list, release_id: str) -> bool:
    """Execute the command and rename the file.  Use a temporary file to avoid overwriting the source file."""

    temp_file = __get_temp_file(source_file)

    # Replace placeholders in the command mask with the source file and temporary file
    command = [arg.replace("{source}", source_file).replace("{target}", temp_file) for arg in command_mask]

    logger.info(f"{release_id} - {action}:  Executing command: {command}")
    success = __execute_system_command(command, action, release_id)

    if not success:
        return False

    os.replace(temp_file, source_file)
    logger.info(f"{release_id} - {action}: completed")
    return True


def __get_volume(file_path: str) -> float:
    result = subprocess.run(["sox", file_path, "-n", "stat"], capture_output=True, text=True)
    lines = result.stderr.splitlines()
    return next(
        (float(line.split(":")[-1].strip()) for line in lines if "Volume adjustment:" in line),
        None,
    )


def __get_temp_file(file_path: str) -> str:
    """Get a temporary file to use as the target file for processing.  This is to avoid overwriting the source file."""
    temp_fd, temp_file = tempfile.mkstemp(suffix=".wav", dir=os.path.dirname(file_path))
    os.close(temp_fd)
    return temp_file


def __get_recorded_speed(filename: str, release: ReleaseFacade) -> str:
    """Get the recorded speed of the audio file:  Assumes that the vinyl was recoded at 45rpm as per my workflow"""

    release_id = release.get_id()
    if match := re.search(r"(\d{2,3})rpm", filename):
        speed = match[1]
        logger.info(f"{release_id} - Found speed '{speed}' in file name: {filename}")
        return str(speed)

    if match := re.search(r"33.*rpm", release.get_media(), re.IGNORECASE):
        logger.info(f"{release_id} - Found speed '33' in release media: {release.get_media()}")
        return str(33)


class _FilenameRelease:
    """Stand-in for a Discogs release when an option doesn't need one; only supplies an id for log messages."""

    def __init__(self, name: str):
        self._name = name

    def get_id(self) -> str:
        return self._name


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

    elif tags := audio_tag_helper.get_tags(file_path):
        release_id = tags.get(audio_tag_helper.DISCOGS_RELEASE_ID, [None])[0]
        if release_id is not None:
            return release_id

    logger.error(f"Could not find release id in file name: {file_path}")
    return None


def __execute_system_command(command: List, action: str, release_id: str) -> bool:
    logger.info(f"{release_id} - {action} - {command}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"{release_id} - {action} - Command failed with exit code {result.returncode}")
            logger.error(f"{release_id} - {action} - Error was: {result.stderr}")
            return False
        else:
            logger.info(f"{release_id} - {action} - succeeded with exit code {result.returncode}")
            logger.info(f"{release_id} - {action} - Output was: {result.stdout}")
            return True
    except Exception as e:
        logger.error(f"{release_id} - {action} - An error occurred while running the command: {e}")
        return False


def is_file_locked(file_path: str) -> bool | None:
    """Check if a file is locked by trying to open it in append mode."""
    locked = None
    if os.path.exists(file_path):
        try:
            if file_object := open(file_path, "a"):
                locked = False
                file_object.close()
        except IOError:
            locked = True
    return locked


def __normalise_file_path(fq_file_path: str) -> Tuple[str, str, str]:
    """Normalise the file path"""
    fq_file_path = os.path.normpath(fq_file_path)
    root_dir, file_name = os.path.split(fq_file_path)
    return fq_file_path, root_dir, file_name


if __name__ == "__main__":
    print("Error: must run main_window.py")
