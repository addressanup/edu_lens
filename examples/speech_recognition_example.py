"""
Example Usage: Child Speech Recognition with EduLens

Demonstrates how to use the speech recognition system with child speech
adaptations and educational vocabulary boosting.
"""

import asyncio
from pathlib import Path

import numpy as np

from src.audio import (
    AgeGroup,
    ChildSpeechAdapter,
    EducationalVocabulary,
    SpeechConfig,
    SpeechRecognizer,
    Subject,
    VocabularyContextManager,
)


async def basic_transcription_example():
    """Example 1: Basic transcription with child speech optimization."""
    print("=" * 60)
    print("Example 1: Basic Speech Recognition")
    print("=" * 60)

    # Configure recognizer for child speech
    config = SpeechConfig(
        model_size="base",
        device="cpu",
        language="en",
        child_mode=True,
        age_group="6-12",
    )

    # Initialize recognizer
    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    # Generate sample audio (in practice, load from file or microphone)
    sample_rate = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

    print("\nTranscribing audio...")
    result = await recognizer.transcribe(audio)

    print(f"Text: {result.text}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Language: {result.language}")
    print(f"Processing time: {result.processing_time:.2f}s")

    await recognizer.close()


async def child_speech_adaptation_example():
    """Example 2: Child speech adaptation for different age groups."""
    print("\n" + "=" * 60)
    print("Example 2: Child Speech Adaptation")
    print("=" * 60)

    # Create adapter for early elementary (ages 6-8)
    adapter = ChildSpeechAdapter(
        age_group=AgeGroup.EARLY_ELEMENTARY,
        enable_formant_adaptation=True,
        enable_rate_normalization=True,
        enable_disfluency_handling=True,
    )

    # Generate sample audio (simulating child's voice)
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Higher frequency to simulate child's voice
    audio = np.sin(2 * np.pi * 280 * t).astype(np.float32) * 0.3

    print("\nApplying child speech adaptations...")

    # Preprocess audio
    adapted_audio = adapter.preprocess_audio(audio)
    print(f"Original audio shape: {audio.shape}")
    print(f"Adapted audio shape: {adapted_audio.shape}")

    # Post-process transcription
    sample_text = "um I think the answer is is five plus um three equals eight"
    sample_confidence = 0.78

    processed_text, adjusted_confidence = adapter.postprocess_transcription(
        sample_text, sample_confidence
    )

    print(f"\nOriginal text: '{sample_text}'")
    print(f"Processed text: '{processed_text}'")
    print(f"Original confidence: {sample_confidence:.2f}")
    print(f"Adjusted confidence: {adjusted_confidence:.2f}")


async def educational_vocabulary_example():
    """Example 3: Educational vocabulary boosting."""
    print("\n" + "=" * 60)
    print("Example 3: Educational Vocabulary Boosting")
    print("=" * 60)

    # Initialize vocabulary manager
    vocab_manager = EducationalVocabulary()

    # Get math vocabulary
    math_vocab = vocab_manager.get_math_vocabulary("operations")
    print(f"\nMath operations vocabulary ({len(math_vocab)} terms):")
    print(math_vocab[:10])  # Show first 10

    # Get science vocabulary
    science_vocab = vocab_manager.get_science_vocabulary("life_science")
    print(f"\nLife science vocabulary ({len(science_vocab)} terms):")
    print(science_vocab[:10])

    # Create vocabulary boost prompt
    prompt = vocab_manager.create_boost_prompt(
        subjects=[Subject.MATHEMATICS, Subject.SCIENCE], max_terms=30
    )
    print(f"\nVocabulary boost prompt:")
    print(prompt[:200] + "...")

    # Configure recognizer with vocabulary boost
    config = SpeechConfig(
        model_size="base",
        device="cpu",
        child_mode=True,
    )

    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    # Set vocabulary boost
    recognizer.set_vocabulary_boost(math_vocab + science_vocab)
    print(f"\nSet vocabulary boost with {len(math_vocab) + len(science_vocab)} terms")

    await recognizer.close()


async def context_aware_vocabulary_example():
    """Example 4: Context-aware vocabulary management."""
    print("\n" + "=" * 60)
    print("Example 4: Context-Aware Vocabulary")
    print("=" * 60)

    # Initialize context manager
    context_manager = VocabularyContextManager()

    # Set context to mathematics
    context_manager.set_context(Subject.MATHEMATICS)
    print("\nContext set to: MATHEMATICS")

    # Get context-specific vocabulary
    vocab = context_manager.get_context_vocabulary(max_terms=30)
    print(f"Context vocabulary ({len(vocab)} terms): {vocab[:15]}")

    # Create context prompt
    prompt = context_manager.create_context_prompt()
    print(f"\nContext prompt: {prompt[:150]}...")

    # Change context to science
    context_manager.set_context(Subject.SCIENCE)
    print("\n\nContext set to: SCIENCE")

    vocab = context_manager.get_context_vocabulary(max_terms=30)
    print(f"Context vocabulary ({len(vocab)} terms): {vocab[:15]}")


async def streaming_transcription_example():
    """Example 5: Real-time streaming transcription."""
    print("\n" + "=" * 60)
    print("Example 5: Streaming Transcription")
    print("=" * 60)

    # Configure recognizer
    config = SpeechConfig(
        model_size="base",
        device="cpu",
        child_mode=True,
        chunk_duration=5.0,  # Process 5-second chunks
    )

    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    # Simulate streaming audio
    async def audio_stream():
        """Generate streaming audio chunks."""
        sample_rate = 16000
        chunk_duration = 1.0
        num_chunks = 5

        print("\nStreaming audio chunks...")
        for i in range(num_chunks):
            t = np.linspace(0, chunk_duration, int(sample_rate * chunk_duration))
            chunk = np.sin(2 * np.pi * (440 + i * 50) * t).astype(np.float32) * 0.3
            print(f"  Chunk {i + 1}/{num_chunks}")
            yield chunk
            await asyncio.sleep(0.1)

    print("\nProcessing stream...")
    chunk_count = 0
    async for result in recognizer.transcribe_streaming(audio_stream()):
        chunk_count += 1
        print(f"\n  Result {chunk_count}:")
        print(f"    Text: {result.text}")
        print(f"    Confidence: {result.confidence:.2f}")

    await recognizer.close()


async def complete_pipeline_example():
    """Example 6: Complete pipeline with all components."""
    print("\n" + "=" * 60)
    print("Example 6: Complete Speech Recognition Pipeline")
    print("=" * 60)

    # 1. Setup components
    print("\n1. Initializing components...")

    # Speech recognizer
    config = SpeechConfig(
        model_size="base",
        device="cpu",
        child_mode=True,
        age_group="9-10",
    )
    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    # Child speech adapter
    adapter = ChildSpeechAdapter(
        age_group=AgeGroup.LATE_ELEMENTARY,
        enable_formant_adaptation=True,
        enable_rate_normalization=True,
        enable_disfluency_handling=True,
    )

    # Vocabulary manager with context
    context_manager = VocabularyContextManager()
    context_manager.set_context(Subject.MATHEMATICS)

    print("  All components initialized")

    # 2. Setup vocabulary boost
    print("\n2. Setting up vocabulary boost...")
    vocab = context_manager.get_context_vocabulary(max_terms=50)
    recognizer.set_vocabulary_boost(vocab)
    print(f"  Boosted {len(vocab)} educational terms")

    # 3. Process audio
    print("\n3. Processing audio...")

    # Generate sample child speech audio
    sample_rate = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 260 * t).astype(np.float32) * 0.3

    # Apply child speech adaptations
    adapted_audio = adapter.preprocess_audio(audio)
    print("  Applied acoustic adaptations")

    # Transcribe
    result = await recognizer.transcribe(adapted_audio)
    print("  Transcribed audio")

    # Post-process
    processed_text, adjusted_confidence = adapter.postprocess_transcription(
        result.text, result.confidence
    )

    # 4. Display results
    print("\n4. Results:")
    print(f"  Original text: '{result.text}'")
    print(f"  Processed text: '{processed_text}'")
    print(f"  Original confidence: {result.confidence:.2f}")
    print(f"  Adjusted confidence: {adjusted_confidence:.2f}")
    print(f"  Processing time: {result.processing_time:.2f}s")

    if result.word_timestamps:
        print(f"  Word timestamps: {len(result.word_timestamps)} words")

    await recognizer.close()
    print("\n5. Pipeline completed successfully")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("EduLens Child Speech Recognition Examples")
    print("=" * 60)

    try:
        await basic_transcription_example()
        await child_speech_adaptation_example()
        await educational_vocabulary_example()
        await context_aware_vocabulary_example()
        # Note: Uncomment to run streaming and complete pipeline examples
        # await streaming_transcription_example()
        # await complete_pipeline_example()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
