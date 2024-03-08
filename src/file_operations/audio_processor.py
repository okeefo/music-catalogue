import re, os, sys, subprocess, tempfile, stat

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Tuple
from pydub import AudioSegment
from pydub.silence import split_on_silence
from log_config import get_logger
from file_operations.auto_tag import get_discogs_client, ReleaseFacade, auto_tag_files
from file_operations.audio_tags import AudioTagHelper
from PyQt5.QtWidgets import QApplication


from config_manager import ConfigurationManager

config = ConfigurationManager()
config.add_to_system_path("utils\\sox")
config.add_to_system_path("utils\\soundstretch")
logger = get_logger(__name__)
__DISCOGS_CLIENT = get_discogs_client()
audio_tag_helper = AudioTagHelper()


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


def auto_process_files(fq_file_path: List[str]) -> None:
    """Process a list of audio files.  The file will be slowed down, amplified, split and tagged."""
    __batch_process_files(fq_file_path, option="ALL")


def __batch_process_files(fq_files: List[str], option="ALL") -> None:
    """Process a list of audio files.
    The option parameter can be ALL, Slowdown,Amplify, Split or Speed_Up.
    If ALL, the file will be slowed down, amplified.split and tagged.
    If Slowdown, the file will only be slowed down.
    If Amplify, the file will only be amplified.
    If Split, the file will, be split and tagged.
    If Speed_Up, the file will only be speed up.
    """

    maintain_tags = option != "ALL"

    for fq_file_path in fq_files:

        fq_file_path, root_dir, file_name = __normalise_file_path(fq_file_path)

        # skip directories
        if os.path.isdir(fq_file_path):
            logger.info(f"Skipping directory: {fq_file_path}")
            continue

        # skip if not a wav file
        if not fq_file_path.endswith(".wav"):
            logger.info(f"Skipping, wavs only,  file: {fq_file_path}")
            continue
        
        if is_file_locked(fq_file_path):
            logger.error(f"Skipping, file is locked: {fq_file_path}")
            continue

        logger.info(f"Processing file: {file_name}")

        release_id = __get_release_id(fq_file_path)
        if release_id is None:
            continue

        release = __get_release(release_id)
        if release is None:
            continue

        # Reduce the speed of the file to 33rpm
        if option in ["ALL", "Slowdown"]:
            result = __reduce_recording_speed(fq_file_path, release, maintain_tags)
            if (not result) or option == "Slowdown":
                continue

        # Amplify the file
        if option in ["ALL", "Amplify"]:
            result = __amplify_file(fq_file_path, release_id, maintain_tags)
            if not result or option == "Amplify":
                continue

        # Speed up the file to 45rpm
        if option == "Speed_Up":
            __increase_speed_of_file_from_33_45rpm(fq_file_path, release, maintain_tags)
            continue

        # Split the file into individual tracks
        tracks = __split_audio_file(fq_file_path, release)

        # Tag the files and rename them
        auto_tag_files(tracks, root_dir)

        logger.info(f"{release.get_id()} - Processing complete for file: {file_name}")


def __reduce_recording_speed(source_file: str, release: ReleaseFacade, maintain_tags=False) -> Tuple[bool, str]:
    

    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)

    speed = __get_recorded_speed(source_file, release)

    if speed != "33":
        logger.info(f"{release.get_id()} - NO identifiers to change speed:  Skipping...")
        return True

    result  = __reduce_speed_of_file_from_45_33rpm(source_file, release.get_id())
    
    if result and maintain_tags:
        audio_tag_helper.write_tags(source_file, tags)
        audio_tag_helper.write_cover_art(source_file, cover_art)
        
    return result


def __split_audio_file(fq_audio_file: str, release: ReleaseFacade) -> List[str]:
    """Split the audio file into individual tracks based on the number of tracks in the release.
    If the number of tracks in the release does not match the number of tracks in the audio file, adjust the silence threshold and try again.
    If the number of tracks in the release does not match the number of tracks in the audio file after X attempts, exit the loop.
    Implemented a binary search approach here to find the correct silence threshold."""

    logger.info(f"{release.get_id()} - Comparing number of tracks in release and audio file:")

    number_of_tracks = release.get_number_of_tracks()
    # TODO:  set these number if the configuration manager
    low_thresh = -55  # Initial low threshold
    high_thresh = -35  # Initial high threshold
    max_attempts = 8  # max number of attempts

    for _ in range(max_attempts):
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

        logger.error(
            f"{release.get_id()} - Number of tracks in release {number_of_tracks} does not match number found in audio file {number_of_chunks}.  Adjusting silence threshold to {silence_thresh}..."
        )

    logger.error(f"{release.get_id()} - Could not split audio file into tracks after maximum attempts.  Exiting...")
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
    chunks = split_on_silence(audio, min_silence_len=2000, silence_thresh=silence_thresh, keep_silence=True, seek_step=10)
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


def __increase_speed_of_file_from_33_45rpm(source_file: str, release_id: str, maintain_tags = False) -> bool:
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


def __amplify_file(source_file: str, release_id: str, maintain_tags) -> bool:
    """Amplify the audio file to the correct volume level. To do this, it calculates the gain value and then applies it to the audio file."""

    logger.info(f"{release_id} - Amplifying the audio: calculating gain value")
    
    if maintain_tags:
        tags, cover_art = audio_tag_helper.get_tags_and_cover_art(source_file)


    gain_value = __get_volume(source_file)
    if gain_value == 0:
        logger.info(f"{release_id} - Audio is already at the correct volume:  Skipping...")
        return True, "No Action Taken"

    command = ["sox.exe", "-v", f"{gain_value}", "{source}", "{target}"]
    result =  __execute_and_rename("Amplifying", source_file, command, release_id)
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
    
    # Get the current permissions
    file_stat = os.stat(source_file)

    # Make the file writable
    #os.chmod(source_file, file_stat.st_mode | stat.S_IWRITE)
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

    elif audio_tag_helper.get_tags(file_path) is not None:
        release_id = audio_tag_helper.get_tags(file_path)[audio_tag_helper.DISCOGS_RELEASE_ID][0]
        if release_id is not None:
            return release_id

    logger.error(f"Could not find release id in file name: {file_path}")
    return None


def __execute_system_command(command: List, action: str, release_id: str) -> Tuple[bool, str]:
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

def is_file_locked(file_path):
    """Check if a file is locked by trying to open it in append mode."""
    locked = None
    if os.path.exists(file_path):
        try:
            if file_object := open(file_path, 'a'):
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
