"""
Audio Feature Extraction for EduLens Wake Word Detection

This module provides audio feature extraction optimized for wake word detection
with special considerations for children's voices (ages 6-12). Includes MFCC,
mel spectrogram, VAD, and noise estimation.
"""

import logging
from typing import Optional, Tuple

import numpy as np
from scipy import signal
from scipy.fftpack import dct

logger = logging.getLogger(__name__)


class MFCCExtractor:
    """
    Mel-Frequency Cepstral Coefficients (MFCC) extractor.

    Optimized for children's voices with adjusted frequency ranges.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        n_mfcc: int = 13,
        n_fft: int = 512,
        hop_length: int = 160,  # 10ms at 16kHz
        n_mels: int = 40,
        fmin: float = 100.0,  # Lower for children's voices
        fmax: float = 8000.0,  # Upper frequency limit
        window: str = 'hamming'
    ):
        """
        Initialize MFCC extractor.

        Args:
            sample_rate: Audio sample rate in Hz
            n_mfcc: Number of MFCCs to extract
            n_fft: FFT window size
            hop_length: Number of samples between frames
            n_mels: Number of mel bands
            fmin: Minimum frequency (Hz) - adjusted for children
            fmax: Maximum frequency (Hz)
            window: Window function type
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax
        self.window = window

        # Create mel filterbank
        self.mel_basis = self._create_mel_filterbank()

        # Create window function
        self.window_func = signal.get_window(window, n_fft)

        logger.info(
            f"Initialized MFCCExtractor: {n_mfcc} coefficients, "
            f"{n_mels} mel bands, {fmin}-{fmax}Hz"
        )

    def extract(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features from audio.

        Args:
            audio_data: Audio samples (1D array)

        Returns:
            MFCC features (n_mfcc, n_frames)
        """
        if len(audio_data) == 0:
            return np.zeros((self.n_mfcc, 0))

        # Compute mel spectrogram
        mel_spec = self.compute_mel_spectrogram(audio_data)

        # Convert to log scale (add small epsilon for stability)
        log_mel_spec = np.log(mel_spec + 1e-10)

        # Apply DCT to get MFCCs
        mfcc = dct(log_mel_spec, type=2, axis=0, norm='ortho')[:self.n_mfcc]

        return mfcc

    def compute_mel_spectrogram(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Compute mel spectrogram.

        Args:
            audio_data: Audio samples

        Returns:
            Mel spectrogram (n_mels, n_frames)
        """
        # Compute STFT
        stft = self._compute_stft(audio_data)

        # Compute power spectrogram
        power_spec = np.abs(stft) ** 2

        # Apply mel filterbank
        mel_spec = np.dot(self.mel_basis, power_spec)

        return mel_spec

    def _compute_stft(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Compute Short-Time Fourier Transform.

        Args:
            audio_data: Audio samples

        Returns:
            STFT matrix (freq_bins, time_frames)
        """
        # Calculate number of frames
        n_frames = 1 + (len(audio_data) - self.n_fft) // self.hop_length

        if n_frames <= 0:
            return np.zeros((self.n_fft // 2 + 1, 0), dtype=complex)

        # Initialize STFT matrix
        stft = np.zeros((self.n_fft // 2 + 1, n_frames), dtype=complex)

        # Compute STFT frame by frame
        for i in range(n_frames):
            start = i * self.hop_length
            end = start + self.n_fft

            if end > len(audio_data):
                # Pad last frame if necessary
                frame = np.zeros(self.n_fft)
                frame[:len(audio_data) - start] = audio_data[start:]
            else:
                frame = audio_data[start:end]

            # Apply window
            windowed = frame * self.window_func

            # Compute FFT
            fft = np.fft.rfft(windowed)
            stft[:, i] = fft

        return stft

    def _create_mel_filterbank(self) -> np.ndarray:
        """
        Create mel-scale filterbank.

        Returns:
            Filterbank matrix (n_mels, freq_bins)
        """
        freq_bins = self.n_fft // 2 + 1

        # Convert Hz to mel scale
        mel_min = self._hz_to_mel(self.fmin)
        mel_max = self._hz_to_mel(self.fmax)

        # Create mel-spaced frequencies
        mel_points = np.linspace(mel_min, mel_max, self.n_mels + 2)
        hz_points = self._mel_to_hz(mel_points)

        # Convert to FFT bin numbers
        bin_points = np.floor((self.n_fft + 1) * hz_points / self.sample_rate).astype(int)

        # Create filterbank
        filterbank = np.zeros((self.n_mels, freq_bins))

        for i in range(self.n_mels):
            left = bin_points[i]
            center = bin_points[i + 1]
            right = bin_points[i + 2]

            # Rising slope
            for j in range(left, center):
                filterbank[i, j] = (j - left) / (center - left)

            # Falling slope
            for j in range(center, right):
                filterbank[i, j] = (right - j) / (right - center)

        return filterbank

    @staticmethod
    def _hz_to_mel(hz: float) -> float:
        """Convert Hz to mel scale."""
        return 2595 * np.log10(1 + hz / 700)

    @staticmethod
    def _mel_to_hz(mel: float) -> float:
        """Convert mel scale to Hz."""
        return 700 * (10 ** (mel / 2595) - 1)


class VoiceActivityDetector:
    """
    Voice Activity Detection (VAD) for wake word detection.

    Uses energy and zero-crossing rate to detect speech presence.
    Optimized for children's voice characteristics.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: float = 30.0,
        energy_threshold: float = 0.05,  # Lower for children
        zcr_threshold: float = 0.3,
        speech_pad_ms: float = 300.0  # Padding around speech
    ):
        """
        Initialize VAD.

        Args:
            sample_rate: Audio sample rate
            frame_duration_ms: Frame duration in milliseconds
            energy_threshold: Energy threshold for speech detection
            zcr_threshold: Zero-crossing rate threshold
            speech_pad_ms: Padding to add around detected speech
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.zcr_threshold = zcr_threshold
        self.speech_pad_ms = speech_pad_ms

        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.pad_frames = int(speech_pad_ms / frame_duration_ms)

        logger.info(f"Initialized VAD: frame={frame_duration_ms}ms, pad={speech_pad_ms}ms")

    def detect(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if audio contains speech.

        Args:
            audio_data: Audio samples

        Returns:
            Tuple of (is_speech, confidence)
        """
        if len(audio_data) < self.frame_size:
            return False, 0.0

        # Compute features
        energy = self._compute_energy(audio_data)
        zcr = self._compute_zero_crossing_rate(audio_data)

        # Normalize features
        energy_score = min(energy / self.energy_threshold, 1.0)
        zcr_score = min(zcr / self.zcr_threshold, 1.0)

        # Combine scores
        confidence = 0.7 * energy_score + 0.3 * zcr_score

        # Determine if speech is present
        is_speech = (energy > self.energy_threshold) and (zcr > self.zcr_threshold * 0.5)

        return is_speech, confidence

    def get_speech_segments(self, audio_data: np.ndarray) -> list:
        """
        Get speech segments from audio.

        Args:
            audio_data: Audio samples

        Returns:
            List of (start_sample, end_sample) tuples
        """
        n_frames = len(audio_data) // self.frame_size
        speech_frames = []

        # Detect speech in each frame
        for i in range(n_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_data[start:end]

            is_speech, _ = self.detect(frame)
            speech_frames.append(is_speech)

        # Merge consecutive speech frames with padding
        segments = []
        in_speech = False
        start_frame = 0

        for i, is_speech in enumerate(speech_frames):
            if is_speech and not in_speech:
                # Start of speech segment
                start_frame = max(0, i - self.pad_frames)
                in_speech = True
            elif not is_speech and in_speech:
                # End of speech segment
                end_frame = min(n_frames - 1, i + self.pad_frames)
                segments.append((
                    start_frame * self.frame_size,
                    end_frame * self.frame_size
                ))
                in_speech = False

        # Handle case where speech continues to end
        if in_speech:
            segments.append((
                start_frame * self.frame_size,
                len(audio_data)
            ))

        return segments

    @staticmethod
    def _compute_energy(audio_data: np.ndarray) -> float:
        """Compute frame energy."""
        if len(audio_data) == 0:
            return 0.0
        return np.sqrt(np.mean(audio_data ** 2))

    @staticmethod
    def _compute_zero_crossing_rate(audio_data: np.ndarray) -> float:
        """Compute zero-crossing rate."""
        if len(audio_data) <= 1:
            return 0.0

        signs = np.sign(audio_data)
        signs[signs == 0] = 1  # Treat zero as positive
        crossings = np.sum(np.abs(np.diff(signs))) / 2

        return crossings / len(audio_data)


class NoiseEstimator:
    """
    Adaptive noise floor estimator for robust wake word detection.

    Tracks background noise statistics to improve detection in varying environments.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        adaptation_rate: float = 0.1,
        min_noise_floor: float = 0.001
    ):
        """
        Initialize noise estimator.

        Args:
            sample_rate: Audio sample rate
            adaptation_rate: Rate of noise floor adaptation (0-1)
            min_noise_floor: Minimum noise floor estimate
        """
        self.sample_rate = sample_rate
        self.adaptation_rate = adaptation_rate
        self.min_noise_floor = min_noise_floor

        self.noise_floor = min_noise_floor
        self.noise_variance = 0.0
        self.n_updates = 0

        logger.info(f"Initialized NoiseEstimator: adaptation_rate={adaptation_rate}")

    def update(self, audio_data: np.ndarray, is_speech: bool = False) -> None:
        """
        Update noise estimates.

        Args:
            audio_data: Audio samples
            is_speech: Whether audio contains speech (don't update if True)
        """
        if len(audio_data) == 0 or is_speech:
            return

        # Compute current noise level
        current_level = np.sqrt(np.mean(audio_data ** 2))

        # Adaptive update
        if self.n_updates == 0:
            self.noise_floor = max(current_level, self.min_noise_floor)
        else:
            alpha = self.adaptation_rate
            self.noise_floor = alpha * current_level + (1 - alpha) * self.noise_floor
            self.noise_floor = max(self.noise_floor, self.min_noise_floor)

        # Update variance
        variance = np.var(audio_data)
        if self.n_updates == 0:
            self.noise_variance = variance
        else:
            self.noise_variance = alpha * variance + (1 - alpha) * self.noise_variance

        self.n_updates += 1

    def get_snr(self, audio_data: np.ndarray) -> float:
        """
        Estimate signal-to-noise ratio.

        Args:
            audio_data: Audio samples

        Returns:
            SNR in dB
        """
        if len(audio_data) == 0 or self.noise_floor == 0:
            return 0.0

        signal_level = np.sqrt(np.mean(audio_data ** 2))
        snr = 20 * np.log10(signal_level / self.noise_floor)

        return snr

    def apply_noise_reduction(
        self,
        audio_data: np.ndarray,
        strength: float = 1.0
    ) -> np.ndarray:
        """
        Apply spectral subtraction-based noise reduction.

        Args:
            audio_data: Audio samples
            strength: Noise reduction strength (0-1)

        Returns:
            Noise-reduced audio
        """
        if len(audio_data) == 0 or strength == 0.0:
            return audio_data

        # Simple spectral subtraction approximation
        # Attenuate signal below noise floor
        threshold = self.noise_floor * (1 + strength)

        # Soft thresholding
        magnitude = np.abs(audio_data)
        mask = np.maximum(0, (magnitude - threshold) / (magnitude + 1e-10))

        reduced = audio_data * mask

        return reduced.astype(np.float32)

    @property
    def noise_level_db(self) -> float:
        """Get current noise floor in dB."""
        return 20 * np.log10(self.noise_floor) if self.noise_floor > 0 else -100.0


class FeatureNormalizer:
    """
    Online feature normalization for consistent wake word detection.

    Uses running statistics for mean and variance normalization.
    """

    def __init__(self, feature_dim: int, momentum: float = 0.99):
        """
        Initialize feature normalizer.

        Args:
            feature_dim: Dimensionality of features
            momentum: Momentum for running statistics
        """
        self.feature_dim = feature_dim
        self.momentum = momentum

        self.mean = np.zeros(feature_dim)
        self.variance = np.ones(feature_dim)
        self.n_updates = 0

    def update(self, features: np.ndarray) -> None:
        """
        Update running statistics.

        Args:
            features: Feature array (feature_dim, n_frames)
        """
        if features.shape[0] != self.feature_dim:
            logger.warning(f"Feature dimension mismatch: expected {self.feature_dim}, got {features.shape[0]}")
            return

        # Compute batch statistics
        batch_mean = np.mean(features, axis=1)
        batch_var = np.var(features, axis=1)

        # Update running statistics
        if self.n_updates == 0:
            self.mean = batch_mean
            self.variance = batch_var
        else:
            self.mean = self.momentum * self.mean + (1 - self.momentum) * batch_mean
            self.variance = self.momentum * self.variance + (1 - self.momentum) * batch_var

        self.n_updates += 1

    def normalize(self, features: np.ndarray) -> np.ndarray:
        """
        Normalize features.

        Args:
            features: Feature array (feature_dim, n_frames)

        Returns:
            Normalized features
        """
        if self.n_updates == 0:
            return features

        # Z-score normalization
        std = np.sqrt(self.variance + 1e-8)
        normalized = (features - self.mean[:, np.newaxis]) / std[:, np.newaxis]

        return normalized.astype(np.float32)


def extract_delta_features(features: np.ndarray, width: int = 2) -> np.ndarray:
    """
    Compute delta (velocity) features.

    Args:
        features: Feature array (feature_dim, n_frames)
        width: Width of delta computation window

    Returns:
        Delta features
    """
    n_features, n_frames = features.shape

    if n_frames <= 2 * width:
        return np.zeros_like(features)

    deltas = np.zeros_like(features)

    for t in range(n_frames):
        # Compute delta using neighboring frames
        start = max(0, t - width)
        end = min(n_frames - 1, t + width)

        if end > start:
            deltas[:, t] = (features[:, end] - features[:, start]) / (end - start)

    return deltas


def extract_delta_delta_features(features: np.ndarray, width: int = 2) -> np.ndarray:
    """
    Compute delta-delta (acceleration) features.

    Args:
        features: Feature array (feature_dim, n_frames)
        width: Width of computation window

    Returns:
        Delta-delta features
    """
    deltas = extract_delta_features(features, width)
    delta_deltas = extract_delta_features(deltas, width)

    return delta_deltas


def combine_features(
    mfcc: np.ndarray,
    include_delta: bool = True,
    include_delta_delta: bool = True
) -> np.ndarray:
    """
    Combine MFCC with delta and delta-delta features.

    Args:
        mfcc: MFCC features (n_mfcc, n_frames)
        include_delta: Include delta features
        include_delta_delta: Include delta-delta features

    Returns:
        Combined feature array
    """
    features = [mfcc]

    if include_delta:
        delta = extract_delta_features(mfcc)
        features.append(delta)

    if include_delta_delta:
        delta_delta = extract_delta_delta_features(mfcc)
        features.append(delta_delta)

    combined = np.vstack(features)
    return combined
