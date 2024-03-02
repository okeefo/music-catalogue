import re, os, sys, subprocess, tempfile, shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Tuple
from pydub import AudioSegment
from pydub.silence import split_on_silence
from log_config import get_logger
from auto_tag import get_discogs_client, ReleaseFacade, auto_tag_files

from PyQt5.QtWidgets import QApplication


from config_manager import ConfigurationManager

config = ConfigurationManager()
config.add_to_system_path("utils\\sox")
config.add_to_system_path("utils\\soundstretch")
logger = get_logger(__name__)
__DISCOGS_CLIENT = get_discogs_client()


def batch_process_file(fq_file_path: str) -> None:

    fq_file_path, root_dir, file_name = __normalise_file_path(fq_file_path)
    logger.info(f"Processing file: {file_name}")

    release_id = __get_release_id(fq_file_path)
    if release_id is None:
        return

    release = __get_release(release_id)
    if release is None:
        return
    
    # Reduce the speed of the file if it is 33rpm
    speed = __get_recorded_speed(fq_file_path, release)
    if speed == "33":
        fq_file_path = __reduce_speed_of_file_from_45_33rpm(fq_file_path, release_id)
    else:
        logger.info(f"{release_id} - NO identifiers to change speed:  Skipping...")

    # Amplify the file
    fq_file_path = __amplify_file(fq_file_path, release_id)

    # Split the file into tracks
    split_audio_file = __split_audio_file(fq_file_path, root_dir, release)
    
    # Tag the files and rename them
    auto_tag_files(split_audio_file, root_dir)

    logger.info(f"{release.get_id()} - Processing complete for file: {file_name}")


def __split_audio_file(fq_audio_file: str, root_dir: str, release: ReleaseFacade) -> List[str]:

    logger.info(f"{release.get_id()} - Comparing number of tracks in release and audio file:")
    audio = AudioSegment.from_wav(fq_audio_file)
    chunks = split_on_silence(audio, min_silence_len=2000, silence_thresh=-45, keep_silence=1000, seek_step=10)
    cleaned_chunks = []
    for chunk in chunks:
        estimated_size = chunk.frame_count() * 2 / 1024
        if estimated_size >= 550:
            cleaned_chunks.append(chunk)

    number_of_tracks = release.get_number_of_tracks()
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


def __reduce_speed_of_file_from_45_33rpm(source_file: str, target_file:str, release_id:str) -> Tuple[bool, str]:
    """Reduce the speed of the audio file
    
    The speed increase from 33.3 RPM to 45 RPM is approximately 35.1%. This is calculated as follows:
    (45 - 33.3) / 33.3 * 100 = 35.1%

    To revert the speed back to the original, you need to decrease the speed by the same factor. 
    However, you need to decrease the speed relative to the increased speed (45 RPM), not the original speed (33.3 RPM). 
    This is calculated as follows:
    100 - (100 / (1 + 35.1 / 100)) = 26.0%
    
    So, a decrease of 26.0% from the increased speed (45 RPM) will bring you back to the original speed (33.3 RPM). 
    This is why I use -rate=-25.926 
    The slight difference between 26.0% and 25.926% is due to rounding errors in the calculations.
    
    """
    logger.info(f"{release_id} - Reducing speed of file from 45 RPM to 33 RPM, source file is: {source_file}, target file is: {target_file}")

    command_mask = ['soundstretch.exe', '{source}', '{target}', '-rate=-25.926']
    return __execute_and_rename(source_file, target_file, command_mask, release_id)
     

def __amplify_file(source_file: str, target_file:str, release_id:str) -> Tuple[bool, str]:
    """ Amplify the audio file to the correct volume level. To do this, it calculates the gain value and then applies it to the audio file."""
    
    logger.info(f"{release_id} - Amplifying the audio: calculating gain value")

    gain_value = __get_volume(source_file)
    if gain_value == 0:
        logger.info(f"{release_id} - Audio is already at the correct volume:  Skipping...")
        return True, "No Action Taken"

    command=['sox.exe', '-v', f'{gain_value}', '{source}', '{target}']
    return __execute_and_rename(source_file, target_file, command, release_id)

def __execute_and_rename(source_file: str, target_file: str, command_mask: list, release_id: str) -> Tuple[bool, str]:
    temp_fd, temp_file = tempfile.mkstemp(suffix=".wav", dir=os.path.dirname(source_file))  # Add dir parameter

    # Replace placeholders in the command mask with the source file and temporary file
    command = [arg.replace('{source}', source_file).replace('{target}', temp_file) for arg in command_mask]

    logger.info(f"{release_id} - Executing command: {command}")
    success, message = __execute_system_command(command, "processing audio", release_id)

    if not success:
        return False, message

    os.close(temp_fd)  # Close the file descriptor before renaming the file

    if source_file == target_file:
        os.remove(source_file)

    os.rename(temp_file, target_file)
    logger.info(f"{release_id} - Processing completed: target file is: {target_file}")
    return True, f"{target_file}"

def __get_volume(file_path: str) -> float:
    result = subprocess.run(['sox', file_path, '-n', 'stat'], capture_output=True, text=True)
    lines = result.stderr.splitlines()
    return next(
        (
            float(line.split(':')[-1].strip())
            for line in lines
            if 'Volume adjustment:' in line
        ),
        None,
    )


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

    else:
        logger.error(f"Could not find release id in file name: {file_path}")
        return None
def __execute_system_command(command: List, action: str, release_id:str) -> Tuple[bool, str]:
    logger.info(f"{release_id} - {action} - {command}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"{release_id} - {action} - Command failed with exit code {result.returncode}")
            logger.error(f"{release_id} - {action} - Error was: {result.stderr}")
            return False, f"Command failed with exit code {result.returncode}. Error was: {result.stderr}"
        else:
            logger.info(f"{release_id} - {action} - succeeded with exit code {result.returncode}")
            logger.info(f"{release_id} - {action} - Output was: {result.stdout}")
            return True, f"Command succeeded with exit code {result.returncode}. Output was: {result.stdout}"
    except Exception as e:
        logger.error(f"{release_id} - An error occurred while running the command: {e}")
        return False, f"An error occurred while running the command: {e}"

def __normalise_file_path(fq_file_path: str) -> Tuple[str, str, str]:
    """Normalise the file path"""
    fq_file_path = os.path.normpath(fq_file_path)
    root_dir, file_name = os.path.split(fq_file_path)
    return fq_file_path, root_dir, file_name


if __name__ == "__main__":

    app = QApplication([])  # Create QApplication instance first
    
    #batch_process_file("e:\\Audacity Projects\\a20_HV_Regen_2_33rpm_[r22685345].wav")
    __reduce_speed_of_file_from_45_33rpm("e:\\Audacity Projects\\a20_HV_Regen_2_33rpm_[r22685345].wav", "e:\\Audacity Projects\\a20_test.wav", "r22685345")
    __reduce_speed_of_file_from_45_33rpm("e:\\Audacity Projects\\a20_test.wav", "e:\\Audacity Projects\\a20_test_amped.wav", "r22685345")
    print("Done")
