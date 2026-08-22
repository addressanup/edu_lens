"""
Tutoring LLM Infrastructure Demo

This script demonstrates the tutoring infrastructure for EduLens,
showing how the TutorEngine generates Socratic-method responses.

Run: python examples/tutoring_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.prompt_templates import HintLevel, PromptTemplateManager
from src.ai.response_validator import validate_educational_response
from src.ai.tutor_inference import ResponseType, create_tutor_engine


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_result(label: str, value):
    """Print a labeled result."""
    print(f"{label}: {value}")


def demo_basic_response():
    """Demo: Basic response generation."""
    print_section("Demo 1: Basic Socratic Response")

    engine = create_tutor_engine()

    context = {"age": 8, "grade": "3", "subject": "math", "concept_id": "math_3_oa_001"}

    result = engine.generate_response(student_query="What is 5 times 3?", context=context)

    print_result("Student Query", "What is 5 times 3?")
    print_result("Response Type", result["response_type"])
    print_result("Tutor Response", result["response"])
    print_result("Hint Level", result["metadata"]["hint_level"] or "N/A")
    print_result("Difficulty", result["metadata"]["difficulty"])
    print_result("Turn Count", result["metadata"]["turn_count"])


def demo_multi_turn_guidance():
    """Demo: Multi-turn guidance with hint progression."""
    print_section("Demo 2: Multi-turn Guidance with Hint Progression")

    engine = create_tutor_engine()

    context = {"age": 9, "grade": "4", "subject": "math", "concept_id": "math_4_nbt_001"}

    # Simulate multiple attempts
    attempts = ["700", "790", "801"]

    print_result("Problem", "What is 234 + 567?")
    print()

    for i, attempt in enumerate(attempts, 1):
        print(f"--- Attempt {i}: {attempt} ---")

        guidance = engine.guide_to_answer(
            problem_statement="What is 234 + 567?", student_attempts=attempts[:i], context=context
        )

        print_result("Hint Level", guidance["metadata"]["hint_level"])
        print_result("Guidance", guidance["response"])
        print()


def demo_concept_explanation():
    """Demo: Concept explanation at appropriate level."""
    print_section("Demo 3: Age-Appropriate Concept Explanation")

    engine = create_tutor_engine()

    ages = [7, 9, 11]

    for age in ages:
        print(f"--- Explanation for {age}-year-old ---")

        explanation = engine.explain_concept(
            concept_id="math_3_oa_001",
            student_age=age,
            current_understanding="I know that multiplication is like adding",
        )

        print_result("Age", age)
        print_result("Explanation", explanation["response"])
        print()


def demo_comprehension_check():
    """Demo: Comprehension checking."""
    print_section("Demo 4: Comprehension Check")

    engine = create_tutor_engine()

    context = {"age": 8, "grade": "3", "subject": "math", "concept_id": "math_3_oa_001"}

    responses = ["Multiplication is repeated addition", "It makes numbers bigger", "I don't know"]

    for student_response in responses:
        print(f"--- Student Response: '{student_response}' ---")

        check = engine.check_understanding(
            concept_id="math_3_oa_001", student_response=student_response, context=context
        )

        print_result("Tutor Check", check["response"])
        print()


def demo_validation():
    """Demo: Response validation."""
    print_section("Demo 5: Response Validation")

    test_cases = [
        {
            "name": "Good Socratic Response",
            "response": (
                "Great question! What do you already know about multiplication? "
                "Can you think of it as groups of things? "
                "Try drawing 5 groups with 3 items in each!"
            ),
            "age": 8,
            "subject": "math",
        },
        {
            "name": "Bad: Direct Answer",
            "response": "The answer is 15. You multiply 5 times 3.",
            "age": 8,
            "subject": "math",
        },
        {
            "name": "Bad: Too Complex",
            "response": (
                "Multiplication represents the mathematical operation "
                "of iterative summation utilizing multiplicative factors."
            ),
            "age": 7,
            "subject": "math",
        },
    ]

    for test in test_cases:
        print(f"--- {test['name']} ---")
        print_result("Response", test["response"])

        result = validate_educational_response(
            response=test["response"], age=test["age"], subject=test["subject"]
        )

        print_result("Valid", result["is_valid"])
        print_result("Overall Score", f"{result['overall_score']:.2f}")

        if result["issues"]:
            print_result("Issues", ", ".join(result["issues"]))

        if result["warnings"]:
            print_result("Warnings", ", ".join(result["warnings"][:2]))

        print("\nDetailed Scores:")
        for key, score in result["scores"].items():
            print(f"  - {key}: {score:.2f}")

        print()


def demo_prompt_templates():
    """Demo: Prompt template system."""
    print_section("Demo 6: Prompt Template System")

    manager = PromptTemplateManager()

    # Show subject-specific templates
    subjects = ["math", "reading", "science"]

    for subject in subjects:
        template = manager.get_template(subject, "socratic_question")
        print(f"--- {subject.title()} Template (first 200 chars) ---")
        print(template[:200] + "...")
        print()

    # Show age-appropriate guidelines
    print("--- Age-Appropriate Language Guidelines ---")
    ages = [7, 9, 11]

    for age in ages:
        guidelines = manager.get_age_appropriate_guidelines(age)
        print(f"\nAge {age}:")
        print(guidelines[:150] + "...")

    # Show Socratic patterns
    print("\n--- Socratic Questioning Patterns ---")
    patterns = ["prior_knowledge", "break_down", "visualization", "reasoning"]

    for pattern in patterns:
        question = manager.get_socratic_pattern(pattern)
        print(f"  • {pattern}: {question}")

    # Show encouragement
    print("\n--- Encouragement Examples (5 of many) ---")
    encouragements = manager.get_encouragement()
    for enc in encouragements[:5]:
        print(f"  • {enc}")


def demo_difficulty_adjustment():
    """Demo: Adaptive difficulty adjustment."""
    print_section("Demo 7: Adaptive Difficulty Adjustment")

    engine = create_tutor_engine()

    scenarios = [
        {
            "name": "High Success Rate",
            "performance": {"correct_attempts": 8, "total_attempts": 10, "time_spent": 300},
        },
        {
            "name": "Struggling Student",
            "performance": {"correct_attempts": 2, "total_attempts": 10, "time_spent": 600},
        },
        {
            "name": "Moderate Performance",
            "performance": {"correct_attempts": 6, "total_attempts": 10, "time_spent": 400},
        },
    ]

    for scenario in scenarios:
        print(f"--- {scenario['name']} ---")

        perf = scenario["performance"]
        success_rate = perf["correct_attempts"] / perf["total_attempts"]

        print_result("Correct/Total", f"{perf['correct_attempts']}/{perf['total_attempts']}")
        print_result("Success Rate", f"{success_rate:.0%}")

        new_difficulty = engine.adjust_difficulty(scenario["performance"])

        print_result("New Difficulty", new_difficulty.name)
        print()


def demo_conversation_flow():
    """Demo: Full conversation flow."""
    print_section("Demo 8: Full Conversation Flow")

    engine = create_tutor_engine()

    context = {"age": 8, "grade": "3", "subject": "reading", "concept_id": "reading_3_001"}

    conversation = [
        "What does the word 'gleaming' mean?",
        "Is it something shiny?",
        "Oh, so the knight's armor was shining!",
    ]

    print("=== Simulated Reading Tutoring Session ===\n")

    for i, query in enumerate(conversation, 1):
        print(f"Turn {i}")
        print(f"Student: {query}")

        result = engine.generate_response(student_query=query, context=context)

        print(f"Tutor: {result['response']}")
        print()

    print(f"Total turns: {len(engine.conversation_history) // 2}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  EDULENS TUTORING LLM INFRASTRUCTURE DEMO")
    print("  Socratic Method Educational AI Tutor")
    print("=" * 70)

    try:
        # Run demos
        demo_basic_response()
        demo_multi_turn_guidance()
        demo_concept_explanation()
        demo_comprehension_check()
        demo_validation()
        demo_prompt_templates()
        demo_difficulty_adjustment()
        demo_conversation_flow()

        print_section("Demo Complete")
        print("All tutoring infrastructure components demonstrated successfully!")
        print("\nThe tutoring system is ready for:")
        print("  • Socratic method question generation")
        print("  • Multi-turn guided discovery")
        print("  • Age-appropriate concept explanations")
        print("  • Comprehension checking")
        print("  • Response validation")
        print("  • Adaptive difficulty adjustment")
        print("\nNext steps:")
        print("  1. Fine-tune base LLM with training data")
        print("  2. Deploy to edge devices")
        print("  3. Integrate with vision/audio systems")
        print("  4. Run quality assurance testing")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
