#!/usr/bin/env python3
"""
EduLens Demo Script - Test the AI Tutor

This script allows you to test the EduLens tutoring system without smart glasses hardware.
It supports three modes:
1. Text mode - Type questions directly
2. Image mode - Upload homework images for OCR
3. Full simulation - Webcam + microphone (if available)

Usage:
    python scripts/demo_tutor.py --mode text
    python scripts/demo_tutor.py --mode image --image path/to/homework.jpg
    python scripts/demo_tutor.py --mode interactive

Environment variables:
    LLM_PROVIDER: anthropic, openai, google, deepseek, ollama (default: anthropic)
    ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.: Your API key
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()


def get_tutor_engine():
    """Initialize the tutor engine with configured provider."""
    from src.ai import create_tutor_engine

    provider = os.getenv("LLM_PROVIDER", "anthropic")
    print(f"\n🎓 Initializing EduLens Tutor with {provider}...")

    try:
        engine = create_tutor_engine(llm_provider=provider)
        print(f"✅ Tutor ready! Using {provider}\n")
        return engine
    except Exception as e:
        print(f"❌ Failed to initialize tutor: {e}")
        print("\nMake sure you have set your API key:")
        print("  export ANTHROPIC_API_KEY=your-key")
        print("  export OPENAI_API_KEY=your-key")
        print("  export DEEPSEEK_API_KEY=your-key")
        sys.exit(1)


def text_mode():
    """Interactive text-based tutoring session."""
    print("=" * 60)
    print("📚 EduLens AI Tutor - Text Mode")
    print("=" * 60)
    print("\nAsk me any homework question! I'll help you learn.")
    print("Type 'quit' to exit, 'clear' to start fresh.\n")

    engine = get_tutor_engine()

    # Default context for a student
    context = {"age": 8, "grade": "3", "subject": "general"}

    while True:
        try:
            query = input("🧒 You: ").strip()

            if not query:
                continue
            if query.lower() == "quit":
                print("\n👋 Goodbye! Keep learning!")
                break
            if query.lower() == "clear":
                engine.conversation_history.clear()
                print("🔄 Conversation cleared!\n")
                continue

            # Detect subject from query
            query_lower = query.lower()
            if any(
                word in query_lower
                for word in [
                    "math",
                    "add",
                    "subtract",
                    "multiply",
                    "divide",
                    "number",
                    "plus",
                    "minus",
                ]
            ):
                context["subject"] = "math"
            elif any(word in query_lower for word in ["read", "word", "spell", "story", "book"]):
                context["subject"] = "reading"
            elif any(
                word in query_lower for word in ["science", "plant", "animal", "weather", "body"]
            ):
                context["subject"] = "science"

            # Generate response
            print("\n🤖 EduLens: ", end="", flush=True)
            result = engine.generate_response(query, context)
            print(result["response"])
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def image_mode(image_path: str):
    """Process a homework image and answer questions about it."""
    print("=" * 60)
    print("📷 EduLens AI Tutor - Image Mode")
    print("=" * 60)

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)

    print(f"\n📄 Processing image: {image_path}")

    # Try to use OCR
    try:
        from src.vision.ocr_engine import OCREngine

        ocr = OCREngine()
        print("🔍 Running OCR...")

        # Load and process image
        import cv2

        image = cv2.imread(image_path)
        if image is None:
            print("❌ Could not load image")
            sys.exit(1)

        result = ocr.extract_text(image)
        extracted_text = result.get("text", "")

        if extracted_text:
            print(f"\n📝 Detected text:\n{'-' * 40}")
            print(extracted_text[:500])  # First 500 chars
            if len(extracted_text) > 500:
                print("...")
            print(f"{'-' * 40}\n")
        else:
            print("⚠️ No text detected in image")
            extracted_text = "homework problem"

    except ImportError:
        print("⚠️ OCR not available, using placeholder")
        extracted_text = "math homework problem"
    except Exception as e:
        print(f"⚠️ OCR failed: {e}")
        extracted_text = "homework problem"

    # Start tutoring session with image context
    engine = get_tutor_engine()

    context = {"age": 8, "grade": "3", "subject": "math", "problem_statement": extracted_text}

    print("💬 Now you can ask questions about this homework!\n")

    while True:
        try:
            query = input("🧒 You: ").strip()

            if not query:
                continue
            if query.lower() == "quit":
                print("\n👋 Goodbye!")
                break

            # Include problem context in first query
            if len(engine.conversation_history) == 0:
                full_query = f"Looking at this problem: {extracted_text[:200]}. {query}"
            else:
                full_query = query

            print("\n🤖 EduLens: ", end="", flush=True)
            result = engine.generate_response(full_query, context)
            print(result["response"])
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break


def interactive_mode():
    """Full interactive mode with webcam and microphone (if available)."""
    print("=" * 60)
    print("🎤 EduLens AI Tutor - Interactive Mode")
    print("=" * 60)
    print("\n⚠️ This mode requires:")
    print("   - Webcam (for homework capture)")
    print("   - Microphone (for voice input)")
    print("   - Speakers (for voice output)")
    print("\nNote: For full smart glasses experience, use the device runtime.")
    print("This demo uses your computer's camera and microphone.\n")

    # Check for required hardware
    try:
        import cv2
        import sounddevice as sd

        # Check camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ No camera detected")
            cap.release()
            print("\nFalling back to text mode...")
            text_mode()
            return
        cap.release()
        print("✅ Camera detected")

        # Check microphone
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if not input_devices:
            print("❌ No microphone detected")
            print("\nFalling back to text mode...")
            text_mode()
            return
        print("✅ Microphone detected")

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nFalling back to text mode...")
        text_mode()
        return

    print("\n🚀 Starting interactive session...")
    print("Press 'c' to capture image, 'q' to quit\n")

    # For now, fall back to text mode with instructions
    print("📝 Interactive mode with full hardware integration coming soon!")
    print("For now, use text mode or image mode.\n")
    text_mode()


def quick_test():
    """Quick test to verify LLM connection works."""
    print("=" * 60)
    print("🧪 EduLens Quick Test")
    print("=" * 60)

    engine = get_tutor_engine()

    context = {"age": 8, "grade": "3", "subject": "math"}

    test_questions = [
        "What is 5 + 3?",
        "Can you help me understand fractions?",
        "Why is the sky blue?",
    ]

    print("\nRunning test queries...\n")

    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}: {question}")
        try:
            result = engine.generate_response(question, context)
            print(f"Response: {result['response'][:200]}...")
            print(f"Type: {result['response_type']}")
            print("✅ Success\n")
        except Exception as e:
            print(f"❌ Failed: {e}\n")

    print("=" * 60)
    print("Test complete!")


def main():
    parser = argparse.ArgumentParser(
        description="EduLens AI Tutor Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo_tutor.py --mode text
  python scripts/demo_tutor.py --mode image --image homework.jpg
  python scripts/demo_tutor.py --test

Environment:
  LLM_PROVIDER=deepseek python scripts/demo_tutor.py --mode text
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["text", "image", "interactive"],
        default="text",
        help="Demo mode (default: text)",
    )
    parser.add_argument("--image", type=str, help="Path to homework image (for image mode)")
    parser.add_argument("--test", action="store_true", help="Run quick test to verify setup")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "google", "deepseek", "ollama"],
        help="LLM provider (overrides LLM_PROVIDER env var)",
    )

    args = parser.parse_args()

    # Set provider if specified
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    print("\n" + "=" * 60)
    print("🎓 Welcome to EduLens AI Tutor")
    print("=" * 60)

    if args.test:
        quick_test()
    elif args.mode == "text":
        text_mode()
    elif args.mode == "image":
        if not args.image:
            print("❌ Image mode requires --image path/to/image.jpg")
            sys.exit(1)
        image_mode(args.image)
    elif args.mode == "interactive":
        interactive_mode()


if __name__ == "__main__":
    main()
