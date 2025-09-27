# audio_waveform_analyzer.py
import os
from dataclasses import dataclass
from typing import List, Optional

from pydub import AudioSegment
import numpy as np
# create logger
from log_config import get_logger

logger = get_logger(__name__)

@dataclass
class AudioAnalysisResult:
    waveform: List[float]  # Normalized values between 0 and 1
    duration: float  # Duration in seconds


SUPPORTED_EXTENSIONS = (".wav", ".mp3", ".flac")

# Number of decimal places for waveform values
WAVEFORM_DECIMAL_PLACES = 3  # Change this value to adjust precision

def analyze_audio_file_go_style(path: str, num_samples: int = 1000) -> np.ndarray:
    """
    Analyze an audio file and return waveform data using max-pooling and normalization,
    similar to the Go backend logic.
    Returns a numpy array of floats in the range 0.0–1.0.
    """
    audio = AudioSegment.from_file(path)
    samples = np.array(audio.get_array_of_samples())
    # Convert to mono (average channels, or use only left channel for exact Go match)
    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels))
        samples = samples.mean(axis=1)  # Or: samples = samples[:, 0] for left only

    length = len(samples)
    factor = max(1, length // num_samples)
    waveform = []
    for i in range(num_samples):
        start = i * factor
        end = min(start + factor, length)
        if start < end:
            max_amp = np.max(np.abs(samples[start:end]))
        else:
            max_amp = 0.0
        waveform.append(max_amp)
    waveform = np.array(waveform)
    
    # Normalize to 0.0–1.0
    if waveform.max() > 0:
        waveform = waveform / waveform.max()
    else:
        waveform = np.zeros(num_samples)
    
    # Round waveform values to the specified decimal places
    waveform = np.round(waveform, WAVEFORM_DECIMAL_PLACES)
    
    duration = len(audio) / 1000.0  # milliseconds to seconds
    return AudioAnalysisResult(waveform=waveform.tolist(), duration=duration)

def analyze_audio_file(path: str, num_samples: int = 1000) -> Optional[AudioAnalysisResult]:
    """
    Analyze an audio file and return waveform data and duration.
    Args:
        path: Path to the audio file.
        num_samples: Number of waveform samples to generate.
    Returns:
        AudioAnalysisResult or None if unsupported file type.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Unsupported audio format: {ext}")
        return None

    audio = AudioSegment.from_file(path)
    duration = len(audio) / 1000.0  # milliseconds to seconds

    # Get raw samples as numpy array
    samples = np.array(audio.get_array_of_samples())
    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels))
        samples = samples.mean(axis=1)  # Convert to mono

    # Downsample to num_samples for waveform display
    factor = max(1, len(samples) // num_samples)
    waveform = np.abs(samples[::factor])
    if waveform.max() > 0:
        waveform = waveform / waveform.max()
    else:
        waveform = np.zeros(num_samples)

    # Ensure the waveform is the requested length
    waveform = waveform[:num_samples]
    if len(waveform) < num_samples:
        waveform = np.pad(waveform, (0, num_samples - len(waveform)), "constant")

    # Round waveform values to the specified decimal places
    waveform = np.round(waveform, WAVEFORM_DECIMAL_PLACES)

    return AudioAnalysisResult(waveform=waveform.tolist(), duration=duration)


# --- Fast Downsampling for Display ---
def get_display_waveform(waveform: np.ndarray, widget_width: int) -> np.ndarray:
    """
    Downsample a high-resolution waveform to match the widget width for fast drawing.
    Uses max-pooling for each pixel column for best visual quality.
    Args:
        waveform: np.ndarray of normalized waveform values (0-1), shape (N,)
        widget_width: number of horizontal pixels to draw
    Returns:
        np.ndarray of length widget_width
    """
    if len(waveform) <= widget_width:
        return waveform
    factor = len(waveform) // widget_width
    # Use max in each bin for a visually accurate envelope
    return np.max(waveform[: factor * widget_width].reshape(-1, factor), axis=1)
