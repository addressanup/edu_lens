"""
Child Speech Adaptation for EduLens

Provides acoustic model adaptations and preprocessing optimizations
specifically for children's speech patterns (ages 6-12).

Children's speech differs from adults in:
- Higher fundamental frequencies (pitch)
- Higher formant frequencies
- More variable pronunciation
- More disfluencies (um, uh, repetitions)
- Varied speaking rates
- Different articulation patterns
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


class AgeGroup(Enum):
    """Age group categories for speech adaptation."""

    EARLY_ELEMENTARY = "6-8"  # Ages 6-8
    LATE_ELEMENTARY = "9-10"  # Ages 9-10
    PRE_TEEN = "11-12"  # Ages 11-12
    GENERAL = "6-12"  # General children


@dataclass
class ChildAcousticProfile:
    """Acoustic profile characteristics for different age groups."""

    age_group: AgeGroup

    # Fundamental frequency (pitch) characteristics
    f0_mean: float  # Mean F0 in Hz
    f0_std: float  # Standard deviation of F0
    f0_range: Tuple[float, float]  # Min/max F0 range

    # Formant characteristics (relative to adult)
    formant_shift_factor: float  # Multiplier for formant frequencies

    # Speaking rate
    speaking_rate_wpm: float  # Words per minute
    speaking_rate_tolerance: float  # Tolerance factor

    # Pronunciation variability
    pronunciation_variance: float  # Higher = more variable

    # Energy characteristics
    energy_mean: float  # Mean energy level
    energy_dynamic_range: float  # Dynamic range in dB


# Acoustic profiles for different age groups
ACOUSTIC_PROFILES = {
    AgeGroup.EARLY_ELEMENTARY: ChildAcousticProfile(
        age_group=AgeGroup.EARLY_ELEMENTARY,
        f0_mean=280.0,  # Higher pitch
        f0_std=50.0,
        f0_range=(220.0, 400.0),
        formant_shift_factor=1.25,  # 25% higher formants
        speaking_rate_wpm=95.0,  # Slower speech
        speaking_rate_tolerance=0.25,
        pronunciation_variance=0.30,  # More variable
        energy_mean=0.15,
        energy_dynamic_range=20.0,
    ),
    AgeGroup.LATE_ELEMENTARY: ChildAcousticProfile(
        age_group=AgeGroup.LATE_ELEMENTARY,
        f0_mean=250.0,
        f0_std=45.0,
        f0_range=(200.0, 350.0),
        formant_shift_factor=1.20,  # 20% higher formants
        speaking_rate_wpm=110.0,
        speaking_rate_tolerance=0.20,
        pronunciation_variance=0.20,
        energy_mean=0.18,
        energy_dynamic_range=22.0,
    ),
    AgeGroup.PRE_TEEN: ChildAcousticProfile(
        age_group=AgeGroup.PRE_TEEN,
        f0_mean=230.0,
        f0_std=40.0,
        f0_range=(180.0, 320.0),
        formant_shift_factor=1.15,  # 15% higher formants
        speaking_rate_wpm=125.0,
        speaking_rate_tolerance=0.15,
        pronunciation_variance=0.15,
        energy_mean=0.20,
        energy_dynamic_range=24.0,
    ),
    AgeGroup.GENERAL: ChildAcousticProfile(
        age_group=AgeGroup.GENERAL,
        f0_mean=250.0,  # Average across all ages
        f0_std=50.0,
        f0_range=(180.0, 400.0),
        formant_shift_factor=1.20,
        speaking_rate_wpm=110.0,
        speaking_rate_tolerance=0.25,
        pronunciation_variance=0.25,
        energy_mean=0.18,
        energy_dynamic_range=22.0,
    ),
}


class ChildSpeechAdapter:
    """
    Adapts speech recognition for children's acoustic characteristics.

    Provides preprocessing and adaptation techniques to improve recognition
    accuracy for child speech.
    """

    def __init__(
        self,
        age_group: AgeGroup = AgeGroup.GENERAL,
        sample_rate: int = 16000,
        enable_formant_adaptation: bool = True,
        enable_rate_normalization: bool = True,
        enable_disfluency_handling: bool = True,
    ):
        """
        Initialize child speech adapter.

        Args:
            age_group: Target age group for adaptations
            sample_rate: Audio sample rate in Hz
            enable_formant_adaptation: Enable formant frequency adaptation
            enable_rate_normalization: Enable speaking rate normalization
            enable_disfluency_handling: Enable disfluency detection/handling
        """
        self.age_group = age_group
        self.sample_rate = sample_rate
        self.profile = ACOUSTIC_PROFILES[age_group]

        self.enable_formant_adaptation = enable_formant_adaptation
        self.enable_rate_normalization = enable_rate_normalization
        self.enable_disfluency_handling = enable_disfluency_handling

        logger.info(f"Initialized ChildSpeechAdapter for age group: {age_group.value}")

    def adapt_acoustic_model(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply acoustic adaptations to audio for child speech.

        This performs formant and pitch adaptations to make child speech
        sound more like adult speech, which most ASR models are trained on.

        Args:
            audio: Input audio signal

        Returns:
            Adapted audio signal
        """
        adapted_audio = audio.copy()

        if self.enable_formant_adaptation:
            # Apply vocal tract length normalization (VTLN)
            adapted_audio = self._apply_vtln(adapted_audio)

        return adapted_audio

    def _apply_vtln(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply Vocal Tract Length Normalization (VTLN).

        VTLN compensates for different vocal tract lengths by warping
        the frequency axis. Children have shorter vocal tracts, resulting
        in higher formant frequencies.

        Args:
            audio: Input audio signal

        Returns:
            Frequency-warped audio signal
        """
        # Use inverse of formant shift to normalize to adult-like frequencies
        warp_factor = 1.0 / self.profile.formant_shift_factor

        # Perform frequency warping using phase vocoder technique
        try:
            # Compute STFT
            hop_length = 256
            n_fft = 1024

            D = signal.stft(audio, fs=self.sample_rate, nperseg=n_fft, noverlap=n_fft - hop_length)[
                2
            ]

            # Warp frequency bins
            n_bins = D.shape[0]
            warped_D = np.zeros_like(D)

            for i in range(n_bins):
                # Calculate warped frequency bin
                warped_idx = i * warp_factor

                if 0 <= warped_idx < n_bins - 1:
                    # Linear interpolation between bins
                    idx_low = int(np.floor(warped_idx))
                    idx_high = int(np.ceil(warped_idx))
                    frac = warped_idx - idx_low

                    warped_D[i] = (1 - frac) * D[idx_low] + frac * D[idx_high]

            # Inverse STFT
            _, warped_audio = signal.istft(
                warped_D, fs=self.sample_rate, nperseg=n_fft, noverlap=n_fft - hop_length
            )

            # Ensure same length as input
            if len(warped_audio) > len(audio):
                warped_audio = warped_audio[: len(audio)]
            elif len(warped_audio) < len(audio):
                warped_audio = np.pad(warped_audio, (0, len(audio) - len(warped_audio)))

            return warped_audio

        except Exception as e:
            logger.warning(f"VTLN failed, returning original audio: {e}")
            return audio

    def normalize_speaking_rate(self, audio: np.ndarray, target_wpm: float = 120.0) -> np.ndarray:
        """
        Normalize speaking rate by time-stretching audio.

        Children often speak at different rates than adults. This normalizes
        the speaking rate to a target rate for better recognition.

        Args:
            audio: Input audio signal
            target_wpm: Target speaking rate in words per minute

        Returns:
            Time-stretched audio signal
        """
        if not self.enable_rate_normalization:
            return audio

        # Calculate stretch factor
        current_wpm = self.profile.speaking_rate_wpm
        stretch_factor = current_wpm / target_wpm

        # Only apply if difference is significant
        if abs(stretch_factor - 1.0) < 0.05:
            return audio

        # Apply time stretching using phase vocoder
        try:
            return self._time_stretch(audio, stretch_factor)
        except Exception as e:
            logger.warning(f"Speaking rate normalization failed: {e}")
            return audio

    def _time_stretch(self, audio: np.ndarray, stretch_factor: float) -> np.ndarray:
        """
        Time-stretch audio using phase vocoder.

        Args:
            audio: Input audio signal
            stretch_factor: Stretch factor (>1 = slower, <1 = faster)

        Returns:
            Time-stretched audio signal
        """
        hop_length = 256
        n_fft = 1024

        # Compute STFT
        _, _, D = signal.stft(
            audio, fs=self.sample_rate, nperseg=n_fft, noverlap=n_fft - hop_length
        )

        # Time-stretch by interpolating phase
        n_frames = D.shape[1]
        stretched_frames = int(n_frames * stretch_factor)

        # Create new time axis
        old_time = np.arange(n_frames)
        new_time = np.linspace(0, n_frames - 1, stretched_frames)

        # Interpolate magnitude and phase separately
        magnitude = np.abs(D)
        phase = np.angle(D)

        # Interpolate magnitude
        stretched_mag = np.zeros((D.shape[0], stretched_frames), dtype=complex)
        for i in range(D.shape[0]):
            interp_func = interp1d(old_time, magnitude[i], kind="linear", fill_value="extrapolate")
            stretched_mag[i] = interp_func(new_time)

        # Phase vocoder for phase interpolation
        stretched_phase = np.zeros((D.shape[0], stretched_frames))
        stretched_phase[:, 0] = phase[:, 0]

        for i in range(1, stretched_frames):
            old_idx = new_time[i]
            old_idx_low = int(np.floor(old_idx))
            old_idx_high = min(old_idx_low + 1, n_frames - 1)

            # Phase advance
            phase_advance = phase[:, old_idx_high] - phase[:, old_idx_low]
            stretched_phase[:, i] = stretched_phase[:, i - 1] + phase_advance

        # Reconstruct complex spectrogram
        stretched_D = stretched_mag * np.exp(1j * stretched_phase)

        # Inverse STFT
        _, stretched_audio = signal.istft(
            stretched_D, fs=self.sample_rate, nperseg=n_fft, noverlap=n_fft - hop_length
        )

        return stretched_audio

    def handle_disfluencies(self, text: str) -> str:
        """
        Handle common disfluencies in children's speech.

        Removes or normalizes fillers like "um", "uh", repetitions, etc.

        Args:
            text: Transcribed text

        Returns:
            Cleaned text with disfluencies handled
        """
        if not self.enable_disfluency_handling:
            return text

        # Common fillers in children's speech
        fillers = [
            "um",
            "uh",
            "uhm",
            "er",
            "ah",
            "like",
            "you know",
            "i mean",
            "well",
            "so",
            "okay",
            "right",
        ]

        words = text.lower().split()
        cleaned_words = []
        previous_word = None

        for word in words:
            # Remove punctuation for comparison
            word_clean = word.strip(".,!?;:")

            # Skip fillers
            if word_clean in fillers:
                continue

            # Handle repetitions (same word repeated)
            if word_clean == previous_word:
                continue

            cleaned_words.append(word)
            previous_word = word_clean

        return " ".join(cleaned_words)

    def boost_child_vocabulary(self, base_vocabulary: List[str]) -> List[str]:
        """
        Enhance vocabulary list with child-specific pronunciations.

        Children may pronounce words differently, so we add common variants.

        Args:
            base_vocabulary: Base vocabulary list

        Returns:
            Enhanced vocabulary with pronunciation variants
        """
        enhanced_vocab = base_vocabulary.copy()

        # Common pronunciation variations in children's speech
        variations = {
            "three": ["free", "twee"],
            "throw": ["frow"],
            "library": ["liberry", "libary"],
            "spaghetti": ["pasketti", "basketti"],
            "animal": ["aminal"],
            "comfortable": ["comftable", "comfterble"],
            "probably": ["probly", "prolly"],
            "suppose": ["spose"],
            "because": ["cuz", "becuz", "cause"],
            "want to": ["wanna"],
            "going to": ["gonna"],
            "got to": ["gotta"],
            "have to": ["hafta"],
        }

        for base_word, variants in variations.items():
            if base_word in base_vocabulary:
                enhanced_vocab.extend(variants)

        return list(set(enhanced_vocab))  # Remove duplicates

    def estimate_confidence_adjustment(
        self,
        base_confidence: float,
        audio_features: Optional[Dict] = None,
    ) -> float:
        """
        Adjust confidence score based on child speech characteristics.

        Child speech may have lower confidence scores due to differences
        from adult training data. This applies an adjustment factor.

        Args:
            base_confidence: Base confidence score from ASR
            audio_features: Optional audio features for adaptive adjustment

        Returns:
            Adjusted confidence score
        """
        # Base adjustment for child speech
        adjustment = 0.05  # Slight boost

        # Additional adjustments based on age group
        if self.age_group == AgeGroup.EARLY_ELEMENTARY:
            adjustment += 0.02  # More tolerance for younger children
        elif self.age_group == AgeGroup.PRE_TEEN:
            adjustment += 0.01  # Less adjustment for older children

        # Apply adjustment
        adjusted_confidence = min(base_confidence + adjustment, 1.0)

        return adjusted_confidence

    def detect_age_group(self, audio: np.ndarray) -> Tuple[AgeGroup, float]:
        """
        Estimate age group from audio characteristics.

        Analyzes fundamental frequency and formant patterns to estimate
        the speaker's age group.

        Args:
            audio: Audio signal

        Returns:
            Tuple of (estimated_age_group, confidence)
        """
        # Estimate fundamental frequency (F0)
        f0 = self._estimate_f0(audio)

        # Compare with age group profiles
        age_scores = {}

        for age_group, profile in ACOUSTIC_PROFILES.items():
            if age_group == AgeGroup.GENERAL:
                continue

            # Calculate distance from profile F0 mean
            f0_distance = abs(f0 - profile.f0_mean) / profile.f0_std

            # Convert distance to similarity score
            similarity = np.exp(-(f0_distance**2) / 2)
            age_scores[age_group] = similarity

        # Get best match
        if age_scores:
            best_age_group = max(age_scores, key=age_scores.get)
            confidence = age_scores[best_age_group]
            return best_age_group, confidence

        return AgeGroup.GENERAL, 0.5

    def _estimate_f0(self, audio: np.ndarray) -> float:
        """
        Estimate fundamental frequency using autocorrelation.

        Args:
            audio: Audio signal

        Returns:
            Estimated F0 in Hz
        """
        # Autocorrelation method for pitch detection
        try:
            # Normalize audio
            audio = audio / (np.max(np.abs(audio)) + 1e-8)

            # Apply window
            windowed = audio * np.hanning(len(audio))

            # Autocorrelation
            autocorr = np.correlate(windowed, windowed, mode="full")
            autocorr = autocorr[len(autocorr) // 2 :]

            # Find peak in expected F0 range
            min_lag = int(self.sample_rate / 400)  # Max F0 = 400 Hz
            max_lag = int(self.sample_rate / 150)  # Min F0 = 150 Hz

            if max_lag < len(autocorr):
                peak_lag = np.argmax(autocorr[min_lag:max_lag]) + min_lag
                f0 = self.sample_rate / peak_lag
                return float(f0)

        except Exception as e:
            logger.warning(f"F0 estimation failed: {e}")

        return 250.0  # Default to average child F0

    def preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply all preprocessing adaptations to audio.

        This is a convenience method that applies all enabled adaptations.

        Args:
            audio: Input audio signal

        Returns:
            Preprocessed audio signal
        """
        processed = audio.copy()

        # Apply acoustic adaptations
        processed = self.adapt_acoustic_model(processed)

        # Normalize speaking rate
        if self.enable_rate_normalization:
            processed = self.normalize_speaking_rate(processed)

        return processed

    def postprocess_transcription(self, text: str, confidence: float) -> Tuple[str, float]:
        """
        Post-process transcription results.

        Applies disfluency handling and confidence adjustment.

        Args:
            text: Transcribed text
            confidence: Original confidence score

        Returns:
            Tuple of (processed_text, adjusted_confidence)
        """
        # Handle disfluencies
        processed_text = self.handle_disfluencies(text)

        # Adjust confidence
        adjusted_confidence = self.estimate_confidence_adjustment(confidence)

        return processed_text, adjusted_confidence


class MultiAgeAdapter:
    """
    Adapter that handles multiple age groups automatically.

    Detects age group from audio and applies appropriate adaptations.
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize multi-age adapter.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Create adapters for each age group
        self.adapters = {
            age_group: ChildSpeechAdapter(age_group, sample_rate)
            for age_group in AgeGroup
            if age_group != AgeGroup.GENERAL
        }

        # Default to general adapter
        self.default_adapter = ChildSpeechAdapter(AgeGroup.GENERAL, sample_rate)

        logger.info("Initialized MultiAgeAdapter")

    def adapt_audio(self, audio: np.ndarray, age_group: Optional[AgeGroup] = None) -> np.ndarray:
        """
        Adapt audio with age group detection or specified age group.

        Args:
            audio: Input audio signal
            age_group: Optional specific age group (auto-detected if None)

        Returns:
            Adapted audio signal
        """
        if age_group is None:
            # Detect age group
            age_group, confidence = self.default_adapter.detect_age_group(audio)
            logger.debug(f"Detected age group: {age_group.value} (confidence: {confidence:.2f})")

        # Get appropriate adapter
        adapter = self.adapters.get(age_group, self.default_adapter)

        # Apply adaptations
        return adapter.preprocess_audio(audio)
