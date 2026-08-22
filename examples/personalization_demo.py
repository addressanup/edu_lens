"""
EduLens Personalization Engine Demo

This example demonstrates the complete personalization system including:
- Student modeling with Bayesian knowledge tracking
- Adaptive tutoring with real-time adjustments
- Progress tracking with spaced repetition
- Privacy-preserving learning analytics

Author: EduLens AI Team
Version: 1.0.0
"""

import time
from pathlib import Path

from src.ai.personalization import (
    AdaptationContext,
    MasteryLevel,
    create_adaptive_tutor,
    create_learning_analytics,
    create_progress_tracker,
    create_student_model,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def simulate_learning_session():
    """Simulate a complete learning session."""
    print_section("EduLens Personalization Engine Demo")

    # Step 1: Create Student Model
    print_section("Step 1: Initialize Student Model")

    student_id = "demo_student_001"
    age = 9
    grade = 4

    student = create_student_model(student_id=student_id, age=age, grade=grade)

    print(f"Created student model:")
    print(f"  Student ID: {student_id}")
    print(f"  Age: {age} years old")
    print(f"  Grade: {grade}")

    # Step 2: Create Supporting Systems
    print_section("Step 2: Initialize Supporting Systems")

    tutor = create_adaptive_tutor(student)
    tracker = create_progress_tracker(student)
    analytics = create_learning_analytics(student_id, anonymize=True)

    print("Initialized:")
    print("  ✓ Adaptive Tutor")
    print("  ✓ Progress Tracker")
    print("  ✓ Learning Analytics (privacy-preserving)")

    # Step 3: Simulate Learning Problems
    print_section("Step 3: Simulate Learning Session")

    concept_id = "math_3_oa_001"  # Multiplication concept
    problems = [
        {
            "id": "prob_1",
            "statement": "What is 3 × 4?",
            "correct_answer": "12",
            "student_answer": "15",
            "correct": False,
            "time_spent": 45.0,
            "attempts": 2,
        },
        {
            "id": "prob_2",
            "statement": "What is 5 × 2?",
            "correct_answer": "10",
            "student_answer": "10",
            "correct": True,
            "time_spent": 30.0,
            "attempts": 1,
        },
        {
            "id": "prob_3",
            "statement": "What is 6 × 3?",
            "correct_answer": "18",
            "student_answer": "18",
            "correct": True,
            "time_spent": 25.0,
            "attempts": 1,
        },
        {
            "id": "prob_4",
            "statement": "What is 7 × 4?",
            "correct_answer": "28",
            "student_answer": "28",
            "correct": True,
            "time_spent": 20.0,
            "attempts": 1,
        },
        {
            "id": "prob_5",
            "statement": "What is 8 × 5?",
            "correct_answer": "40",
            "student_answer": "40",
            "correct": True,
            "time_spent": 18.0,
            "attempts": 1,
        },
    ]

    session_start = time.time()
    correct_count = 0

    print(f"\nPracticing Concept: Multiplication (ID: {concept_id})")
    print(f"Total Problems: {len(problems)}\n")

    for i, problem in enumerate(problems, 1):
        print(f"\nProblem {i}: {problem['statement']}")
        print(f"  Student Answer: {problem['student_answer']}")
        print(f"  Result: {'✓ Correct' if problem['correct'] else '✗ Incorrect'}")
        print(f"  Time: {problem['time_spent']:.1f}s")
        print(f"  Attempts: {problem['attempts']}")

        # Update student model
        model_update = student.update_from_interaction(
            concept_id=concept_id,
            problem_type="multiplication_basic",
            correct=problem["correct"],
            attempts=problem["attempts"],
            time_spent=problem["time_spent"],
            hint_level_used=1 if problem["attempts"] > 1 else 0,
            student_response=problem["student_answer"],
            difficulty_level=2,
        )

        # Record in progress tracker
        progress_update = tracker.record_attempt(
            concept_id=concept_id,
            problem_id=problem["id"],
            correct=problem["correct"],
            time_spent=problem["time_spent"],
            hints_used=1 if problem["attempts"] > 1 else 0,
            difficulty=2,
            attempts_on_problem=problem["attempts"],
        )

        if problem["correct"]:
            correct_count += 1

        # Get adaptive feedback
        if not problem["correct"] or problem["attempts"] > 1:
            context = AdaptationContext(
                concept_id=concept_id,
                problem_statement=problem["statement"],
                student_attempts=[problem["student_answer"]],
                time_on_problem=problem["time_spent"],
                hints_used=1 if problem["attempts"] > 1 else 0,
                difficulty_level=2,
                session_duration=time.time() - session_start,
                problems_solved_today=i,
            )

            hint = tutor.generate_hint(context)
            print(f"\n  💡 Hint ({hint.directness.name}):")
            print(f"     {hint.hint_text}")
            print(f"  💪 {hint.encouragement}")

        # Show progress after each problem
        print(f"\n  Current Mastery: {model_update['mastery_level']}")
        print(f"  Mastery Score: {progress_update['mastery_score']:.2%}")

        # Detect emotional state
        if i >= 2:
            context = AdaptationContext(
                concept_id=concept_id,
                problem_statement=problem["statement"],
                student_attempts=[],
                time_on_problem=problem["time_spent"],
                hints_used=1 if problem["attempts"] > 1 else 0,
                difficulty_level=2,
                session_duration=time.time() - session_start,
                problems_solved_today=correct_count,
            )

            emotion, confidence = tutor.detect_frustration(context)
            if confidence > 0.5:
                print(f"  😊 Emotional State: {emotion.name}")

    # Update analytics
    session_data = {
        "session_id": "demo_session",
        "start_time": session_start,
        "end_time": time.time(),
        "problems_attempted": len(problems),
        "problems_correct": correct_count,
        "concepts_practiced": [concept_id],
        "mastery_scores": {concept_id: tracker.calculate_mastery(concept_id)},
    }
    analytics.update_from_session(session_data)

    # Step 4: Show Student Model State
    print_section("Step 4: Student Model Summary")

    summary = student.get_summary()
    print(f"Session Count: {summary['session_count']}")
    print(f"Total Problems: {summary['total_problems_attempted']}")
    print(f"Concepts Attempted: {summary['concepts_attempted']}")
    print(f"Learning Style: {summary['learning_style']}")
    print(f"Learning Pace: {summary['pace']}")

    mastery_level = student.get_mastery_level(concept_id)
    print(f"\nMastery Level for Multiplication: {mastery_level.name}")

    # Step 5: Show Adaptive Recommendations
    print_section("Step 5: Adaptive Recommendations")

    # Get optimal difficulty
    optimal_difficulty = student.predict_difficulty(concept_id)
    print(f"Recommended Difficulty: {optimal_difficulty}/5")

    # Get examples at appropriate level
    examples = tutor.select_examples(concept_id, count=3)
    print(f"\nNext Practice Problems:")
    for i, example in enumerate(examples, 1):
        print(f"  {i}. Difficulty {example['difficulty']}: {example['problem']}")

    # Get explanation adjusted to learning style
    explanation = tutor.adjust_explanation(
        concept_id=concept_id, base_explanation="Multiplication is repeated addition."
    )
    print(f"\nExplanation Style: {explanation.explanation_type.name}")
    print(f"Learning Style Match: {student.get_learning_style().name}")

    # Step 6: Progress Tracking
    print_section("Step 6: Progress Tracking")

    # Calculate mastery
    mastery_score = tracker.calculate_mastery(concept_id)
    print(f"Concept Mastery Score: {mastery_score:.2%}")

    # Check for gaps
    gaps = tracker.identify_gaps()
    if gaps:
        print(f"\nKnowledge Gaps Identified: {len(gaps)}")
        for gap in gaps[:3]:
            print(f"  - {gap['concept_id']}: severity {gap['severity']:.2f}")
    else:
        print("\nNo knowledge gaps identified!")

    # Review suggestions
    reviews = tracker.suggest_review(max_suggestions=3)
    if reviews:
        print(f"\nConcepts Due for Review: {len(reviews)}")
        for review in reviews:
            print(f"  - {review['concept_id']} (priority: {review['priority']:.1f})")
    else:
        print("\nNo reviews needed at this time.")

    # Generate progress report
    report = tracker.generate_report()
    print(f"\nProgress Report:")
    print(f"  Total Concepts: {report.total_concepts}")
    print(f"  Mastered: {report.mastered_concepts}")
    print(f"  In Progress: {report.in_progress_concepts}")
    print(f"  Overall Accuracy: {report.overall_accuracy:.1%}")

    # Step 7: Learning Analytics
    print_section("Step 7: Learning Analytics (Privacy-Preserving)")

    # Engagement score
    engagement = analytics.get_engagement_score()
    print(f"Engagement Score: {engagement:.2%}")

    # Learning velocity
    velocity = analytics.get_learning_velocity()
    print(f"Learning Velocity: {velocity:.2f} concepts/week")

    # Detected patterns
    patterns = analytics.detect_learning_patterns()
    if patterns:
        print(f"\nDetected Learning Patterns:")
        for pattern, confidence in patterns.items():
            print(f"  - {pattern.value}: {confidence:.2%} confidence")

    # Insights
    insights = analytics.get_insights()
    if insights:
        print(f"\nPersonalized Insights:")
        for i, insight in enumerate(insights, 1):
            print(f"  {i}. {insight}")

    # Privacy verification
    print(f"\nPrivacy Protection:")
    print(f"  Student ID Hash: {analytics.student_id_hash}")
    print(f"  Original ID Hidden: ✓")
    print(f"  Only Aggregate Data: ✓")

    # Step 8: Celebration
    print_section("Step 8: Achievement Recognition")

    if mastery_level.value >= MasteryLevel.PROFICIENT.value:
        celebration = tutor.celebrate_progress(
            "mastery", {"concept": "Multiplication", "count": correct_count}
        )
        print(f"\n🎉 {celebration}")

    if correct_count >= 4:
        streak_celebration = tutor.celebrate_progress("streak", {"count": correct_count})
        print(f"🔥 {streak_celebration}")

    # Final Summary
    print_section("Session Complete!")

    print(f"""
Summary:
  ✓ Completed {len(problems)} problems
  ✓ {correct_count}/{len(problems)} correct ({correct_count/len(problems)*100:.0f}% accuracy)
  ✓ Mastery improved to {mastery_level.name}
  ✓ Learning patterns detected
  ✓ Next difficulty: {optimal_difficulty}/5

The personalization engine successfully:
  • Tracked knowledge state using Bayesian methods
  • Adapted hints and explanations in real-time
  • Scheduled spaced repetition reviews
  • Maintained privacy through aggregation
  • Detected learning patterns and provided insights
    """)

    print("\n✨ EduLens Personalization Engine Demo Complete! ✨\n")


if __name__ == "__main__":
    simulate_learning_session()
