"""
Demonstration of Subject-Specific Reasoning Modules

This example shows how the reasoning modules integrate with the tutoring system
to provide specialized educational guidance for K-6 students.

Author: EduLens AI Team
"""

from src.ai.reasoning import create_all_reasoners
from src.ai.reasoning import (
    MathProblemType,
    TextType,
    ExperimentPhase,
    SocialStudiesDomain
)


def main():
    """Demonstrate reasoning modules in action."""
    
    print("=" * 70)
    print("EDULENS SUBJECT-SPECIFIC REASONING DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Create all reasoning modules
    reasoners = create_all_reasoners()
    
    # ========================================================================
    # MATH REASONING DEMONSTRATION
    # ========================================================================
    print("1. MATH REASONING - Helping with a Word Problem")
    print("-" * 70)
    
    math_problem = "Maria has 12 cookies. She gives 5 to her friend. How many cookies does she have left?"
    
    # Analyze the problem
    analysis = reasoners['math'].analyze_problem(math_problem, grade_level="2")
    print(f"Problem Type: {analysis['problem_type']}")
    print(f"Operations: {', '.join(analysis['operations'])}")
    
    # Generate solution steps
    steps = reasoners['math'].generate_steps(math_problem, grade_level="2", student_age=7)
    print(f"\nStep-by-Step Guidance ({len(steps)} steps):")
    for i, step in enumerate(steps[:3], 1):
        print(f"   {i}. {step.student_friendly}")
    
    # Suggest strategy
    strategy = reasoners['math'].suggest_strategy(math_problem, grade_level="2", student_age=7)
    print(f"\nRecommended Strategy: {strategy['strategy_name']}")
    print(f"Description: {strategy['description']}")
    print()
    
    # ========================================================================
    # READING REASONING DEMONSTRATION
    # ========================================================================
    print("2. READING REASONING - Understanding a Story")
    print("-" * 70)
    
    passage = """
    Tommy loved adventure. Every Saturday, he would explore the forest near
    his house. He discovered birds, squirrels, and interesting plants. Tommy
    always brought his notebook to draw what he found.
    """
    
    # Analyze the passage
    analysis = reasoners['reading'].analyze_passage(passage, grade_level="3")
    print(f"Text Type: {analysis['text_type']}")
    print(f"Reading Level: {analysis['reading_level']}")
    print(f"Themes: {', '.join(analysis['themes'])}")
    
    # Guide to main idea
    main_idea = reasoners['reading'].identify_main_idea(passage, student_age=8)
    print(f"\nGuiding Questions for Main Idea:")
    for q in main_idea['guiding_questions']:
        print(f"   - {q}")
    
    # Vocabulary support
    vocab = reasoners['reading'].explain_vocabulary(
        word="adventure",
        context_sentence="Tommy loved adventure.",
        student_age=8
    )
    print(f"\nVocabulary Support:")
    print(f"   Word: {vocab.word}")
    print(f"   Student-Friendly Definition: {vocab.student_friendly_definition}")
    print()
    
    # ========================================================================
    # SCIENCE REASONING DEMONSTRATION
    # ========================================================================
    print("3. SCIENCE REASONING - Guiding an Experiment")
    print("-" * 70)
    
    experiment_question = "Do plants need sunlight to grow?"
    
    # Explain the concept
    concept = reasoners['science'].explain_concept(
        "plant growth",
        grade_level="2",
        student_age=7
    )
    print(f"Concept: {concept.concept_name}")
    print(f"Simple Definition: {concept.simple_definition}")
    
    # Guide hypothesis phase
    guidance = reasoners['science'].guide_experiment(
        experiment_question,
        ExperimentPhase.HYPOTHESIS,
        student_age=8,
        grade_level="3"
    )
    print(f"\nExperiment Phase: {guidance.phase.value}")
    print(f"Instructions: {guidance.instructions}")
    print(f"Guiding Questions:")
    for q in guidance.guiding_questions[:2]:
        print(f"   - {q}")
    
    # Check hypothesis quality
    hypothesis = "If I put a plant in the dark, then it will not grow as well."
    check = reasoners['science'].check_hypothesis(
        hypothesis,
        experiment_question,
        student_age=8
    )
    print(f"\nHypothesis Check:")
    print(f"   Quality: {check['overall_quality']}")
    print(f"   Feedback: {check['feedback']}")
    print()
    
    # ========================================================================
    # SOCIAL STUDIES REASONING DEMONSTRATION
    # ========================================================================
    print("4. SOCIAL STUDIES REASONING - Understanding Maps & History")
    print("-" * 70)
    
    # Map reading guidance
    map_guidance = reasoners['social_studies'].analyze_maps(
        "United States map showing states",
        "political",
        student_age=9
    )
    print("Map Reading Guidance:")
    print(f"   What to look for: {', '.join(map_guidance['what_to_look_for'][:3])}")
    
    # Historical context
    context = reasoners['social_studies'].provide_context(
        "community helpers",
        SocialStudiesDomain.CIVICS,
        grade_level="2",
        student_age=7
    )
    print(f"\nHistorical/Civic Context:")
    print(f"   Topic: {context['topic']}")
    print(f"   Background: {context['background']}")
    
    # Community connections
    community = reasoners['social_studies'].community_connections(
        "being a good citizen",
        student_age=8,
        grade_level="3"
    )
    print(f"\nCommunity Connections:")
    print(f"   In My Community: {community['in_my_community'][0]}")
    print(f"   Ways to Participate: {community['ways_to_participate'][0]}")
    print()
    
    # ========================================================================
    # INTEGRATION EXAMPLE
    # ========================================================================
    print("5. CROSS-SUBJECT INTEGRATION")
    print("-" * 70)
    
    word_problem = "The science class planted 15 seeds. 9 seeds grew into plants. How many seeds did not grow?"
    
    # Use math reasoning for the calculation
    math_analysis = reasoners['math'].analyze_problem(word_problem, grade_level="3")
    print(f"Math Analysis: {math_analysis['problem_type']}")
    
    # Use reading reasoning for comprehension
    reading_analysis = reasoners['reading'].analyze_passage(word_problem, grade_level="3")
    print(f"Reading Analysis: {reading_analysis['word_count']} words")
    
    # Use science reasoning for the concept
    science_concept = reasoners['science'].explain_concept(
        "seed germination",
        grade_level="3",
        student_age=8
    )
    print(f"Science Concept: {science_concept.concept_name}")
    
    print("\nThis problem integrates:")
    print("   - Math: Subtraction word problem")
    print("   - Reading: Comprehension of the scenario")
    print("   - Science: Understanding plant growth")
    print()
    
    print("=" * 70)
    print("✓ DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nThe reasoning modules work together to provide comprehensive")
    print("educational support across all K-6 subject areas!")


if __name__ == "__main__":
    main()
