"""
Math Reasoning Module for EduLens AI Agent

This module provides specialized reasoning capabilities for mathematics education,
including step-by-step problem solving, equation handling, error identification,
and strategy recommendations for K-6 mathematics.

Author: EduLens AI Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class MathProblemType(Enum):
    """Types of math problems."""
    ARITHMETIC = "arithmetic"
    FRACTIONS = "fractions"
    DECIMALS = "decimals"
    GEOMETRY = "geometry"
    WORD_PROBLEM = "word_problem"
    MEASUREMENT = "measurement"
    DATA_ANALYSIS = "data_analysis"
    ALGEBRA_INTRO = "algebra_intro"


class MathOperation(Enum):
    """Mathematical operations."""
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"
    MIXED = "mixed"


@dataclass
class MathStep:
    """Represents a single step in problem solving."""
    step_number: int
    description: str
    operation: str
    reasoning: str
    student_friendly: str  # Age-appropriate explanation


@dataclass
class ErrorAnalysis:
    """Analysis of student's mathematical error."""
    error_type: str
    location: str
    misconception: Optional[str]
    correction_hint: str
    severity: str  # 'minor', 'moderate', 'major'


class MathReasoner:
    """
    Specialized reasoning engine for mathematics education.

    Provides step-by-step problem solving, error identification,
    strategy recommendations, and grade-appropriate mathematical guidance.
    """

    def __init__(self, curriculum_manager=None):
        """
        Initialize the MathReasoner.

        Args:
            curriculum_manager: Optional CurriculumManager instance for concept lookup
        """
        self.curriculum_manager = curriculum_manager
        self.common_errors = self._initialize_common_errors()
        self.strategies = self._initialize_strategies()
        self.vocabulary = self._initialize_math_vocabulary()

    def analyze_problem(
        self,
        problem_statement: str,
        grade_level: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a math problem to understand its structure and requirements.

        Args:
            problem_statement: The math problem text
            grade_level: Student's grade level (K-6)
            context: Optional additional context

        Returns:
            Dictionary containing problem analysis:
                - problem_type: Type of math problem
                - operations: Required operations
                - difficulty: Estimated difficulty
                - key_concepts: Concepts involved
                - prerequisites: Required prior knowledge
                - keywords: Important keywords in the problem
        """
        logger.info(f"Analyzing math problem for grade {grade_level}")

        # Detect problem type
        problem_type = self._detect_problem_type(problem_statement)

        # Identify operations needed
        operations = self._identify_operations(problem_statement)

        # Extract key numbers and units
        numbers = self._extract_numbers(problem_statement)
        units = self._extract_units(problem_statement)

        # Identify keywords
        keywords = self._identify_keywords(problem_statement)

        # Determine difficulty
        difficulty = self._estimate_difficulty(
            problem_type, operations, len(numbers), grade_level
        )

        # Identify key concepts
        key_concepts = self._identify_concepts(problem_type, operations, keywords)

        return {
            'problem_type': problem_type.value,
            'operations': [op.value for op in operations],
            'difficulty': difficulty,
            'key_concepts': key_concepts,
            'numbers': numbers,
            'units': units,
            'keywords': keywords,
            'is_word_problem': problem_type == MathProblemType.WORD_PROBLEM,
            'prerequisites': self._get_prerequisites(key_concepts)
        }

    def generate_steps(
        self,
        problem_statement: str,
        grade_level: str,
        student_age: int,
        problem_analysis: Optional[Dict] = None
    ) -> List[MathStep]:
        """
        Generate step-by-step solution path for a math problem.

        Args:
            problem_statement: The math problem text
            grade_level: Student's grade level
            student_age: Student's age for language appropriateness
            problem_analysis: Pre-computed problem analysis (optional)

        Returns:
            List of MathStep objects representing the solution path
        """
        logger.info("Generating solution steps")

        # Analyze problem if not provided
        if problem_analysis is None:
            problem_analysis = self.analyze_problem(problem_statement, grade_level)

        problem_type = problem_analysis['problem_type']
        operations = problem_analysis['operations']

        # Generate steps based on problem type
        if problem_type == 'word_problem':
            steps = self._generate_word_problem_steps(
                problem_statement, operations, student_age
            )
        elif problem_type == 'arithmetic':
            steps = self._generate_arithmetic_steps(
                problem_statement, operations, student_age
            )
        elif problem_type == 'fractions':
            steps = self._generate_fraction_steps(
                problem_statement, operations, student_age
            )
        elif problem_type == 'geometry':
            steps = self._generate_geometry_steps(
                problem_statement, student_age
            )
        else:
            steps = self._generate_general_steps(
                problem_statement, operations, student_age
            )

        return steps

    def check_work(
        self,
        problem_statement: str,
        student_solution: str,
        expected_answer: Optional[str] = None,
        grade_level: str = "3"
    ) -> Dict[str, Any]:
        """
        Verify student's work and identify correctness.

        Args:
            problem_statement: The original problem
            student_solution: Student's answer or work shown
            expected_answer: The correct answer (optional)
            grade_level: Student's grade level

        Returns:
            Dictionary with verification results:
                - is_correct: Boolean indicating correctness
                - confidence: Confidence level (0.0-1.0)
                - partial_credit: Percentage if partially correct
                - correct_steps: Steps that are correct
                - incorrect_steps: Steps that need work
                - feedback: Constructive feedback
        """
        logger.info("Checking student work")

        # Extract the final answer from student solution
        student_answer = self._extract_answer(student_solution)

        # Check if answer is correct
        is_correct = False
        confidence = 0.8

        if expected_answer:
            is_correct = self._compare_answers(student_answer, expected_answer)

        # Analyze solution steps if work is shown
        steps_analysis = self._analyze_solution_steps(
            problem_statement, student_solution
        )

        # Calculate partial credit
        partial_credit = self._calculate_partial_credit(
            is_correct, steps_analysis
        )

        # Generate feedback
        feedback = self._generate_verification_feedback(
            is_correct, steps_analysis, grade_level
        )

        return {
            'is_correct': is_correct,
            'confidence': confidence,
            'partial_credit': partial_credit,
            'correct_steps': steps_analysis.get('correct_steps', []),
            'incorrect_steps': steps_analysis.get('incorrect_steps', []),
            'feedback': feedback,
            'student_answer': student_answer,
            'shows_work': len(student_solution.split()) > 5
        }

    def identify_errors(
        self,
        problem_statement: str,
        student_work: str,
        correct_answer: Optional[str] = None,
        grade_level: str = "3"
    ) -> List[ErrorAnalysis]:
        """
        Identify common mathematical errors and misconceptions.

        Args:
            problem_statement: The original problem
            student_work: Student's work and answer
            correct_answer: The correct answer (optional)
            grade_level: Student's grade level

        Returns:
            List of ErrorAnalysis objects describing identified errors
        """
        logger.info("Identifying mathematical errors")

        errors = []

        # Analyze problem to understand what should happen
        problem_analysis = self.analyze_problem(problem_statement, grade_level)

        # Check for common computational errors
        computational_errors = self._check_computational_errors(
            student_work, problem_analysis
        )
        errors.extend(computational_errors)

        # Check for conceptual errors
        conceptual_errors = self._check_conceptual_errors(
            student_work, problem_analysis
        )
        errors.extend(conceptual_errors)

        # Check for procedural errors
        procedural_errors = self._check_procedural_errors(
            student_work, problem_analysis
        )
        errors.extend(procedural_errors)

        # Check for reading comprehension errors (word problems)
        if problem_analysis['is_word_problem']:
            reading_errors = self._check_word_problem_errors(
                problem_statement, student_work
            )
            errors.extend(reading_errors)

        return errors

    def suggest_strategy(
        self,
        problem_statement: str,
        grade_level: str,
        student_age: int,
        previous_attempts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recommend a problem-solving approach or strategy.

        Args:
            problem_statement: The math problem
            grade_level: Student's grade level
            student_age: Student's age
            previous_attempts: Previous solution attempts (optional)

        Returns:
            Dictionary with strategy recommendations:
                - strategy_name: Name of recommended strategy
                - description: Age-appropriate description
                - steps: How to apply the strategy
                - visual_aids: Suggested visual representations
                - examples: Similar example problems
        """
        logger.info("Suggesting problem-solving strategy")

        # Analyze the problem
        problem_analysis = self.analyze_problem(problem_statement, grade_level)

        # Determine best strategy based on problem type and operations
        strategy = self._select_strategy(
            problem_analysis, grade_level, previous_attempts
        )

        # Get age-appropriate explanation
        description = self._get_strategy_description(
            strategy, student_age
        )

        # Generate strategy steps
        steps = self._get_strategy_steps(strategy, student_age)

        # Suggest visual aids
        visual_aids = self._suggest_visual_aids(
            problem_analysis['problem_type'], strategy
        )

        return {
            'strategy_name': strategy,
            'description': description,
            'steps': steps,
            'visual_aids': visual_aids,
            'why_this_strategy': self._explain_strategy_choice(
                strategy, problem_analysis, student_age
            ),
            'alternative_strategies': self._get_alternative_strategies(
                problem_analysis, strategy
            )
        }

    def explain_concept(
        self,
        concept_name: str,
        student_age: int,
        include_examples: bool = True
    ) -> Dict[str, Any]:
        """
        Provide age-appropriate explanation of a math concept.

        Args:
            concept_name: Name of the math concept
            student_age: Student's age for language level
            include_examples: Whether to include examples

        Returns:
            Dictionary with concept explanation
        """
        logger.info(f"Explaining math concept: {concept_name}")

        # Get concept definition
        definition = self._get_concept_definition(concept_name, student_age)

        # Get visual representations
        visual_description = self._get_visual_representation(concept_name)

        # Get real-world connections
        real_world = self._get_real_world_examples(concept_name, student_age)

        result = {
            'concept': concept_name,
            'definition': definition,
            'visual_representation': visual_description,
            'real_world_examples': real_world,
            'key_vocabulary': self._get_concept_vocabulary(concept_name)
        }

        if include_examples:
            result['practice_examples'] = self._generate_practice_examples(
                concept_name, student_age
            )

        return result

    # Private helper methods

    def _detect_problem_type(self, problem: str) -> MathProblemType:
        """Detect the type of math problem."""
        problem_lower = problem.lower()

        # Check for word problem indicators
        word_indicators = ['how many', 'how much', 'if', 'have', 'each', 'total']
        if any(indicator in problem_lower for indicator in word_indicators):
            return MathProblemType.WORD_PROBLEM

        # Check for fraction indicators
        if '/' in problem or 'fraction' in problem_lower or 'half' in problem_lower:
            return MathProblemType.FRACTIONS

        # Check for decimal indicators
        if '.' in problem and any(c.isdigit() for c in problem):
            return MathProblemType.DECIMALS

        # Check for geometry indicators
        geometry_words = ['shape', 'area', 'perimeter', 'angle', 'circle', 'square']
        if any(word in problem_lower for word in geometry_words):
            return MathProblemType.GEOMETRY

        # Default to arithmetic
        return MathProblemType.ARITHMETIC

    def _identify_operations(self, problem: str) -> List[MathOperation]:
        """Identify mathematical operations needed."""
        operations = []
        problem_lower = problem.lower()

        # Addition indicators
        if any(word in problem_lower for word in ['add', 'plus', 'sum', 'total', 'altogether', '+']):
            operations.append(MathOperation.ADDITION)

        # Subtraction indicators
        if any(word in problem_lower for word in ['subtract', 'minus', 'difference', 'less', 'left', '-']):
            operations.append(MathOperation.SUBTRACTION)

        # Multiplication indicators
        if any(word in problem_lower for word in ['multiply', 'times', 'product', 'each', 'groups of', '*', 'x']):
            operations.append(MathOperation.MULTIPLICATION)

        # Division indicators
        if any(word in problem_lower for word in ['divide', 'split', 'share', 'per', 'each', '/', '÷']):
            operations.append(MathOperation.DIVISION)

        return operations if operations else [MathOperation.ADDITION]

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numerical values from text."""
        # Find all numbers (integers and decimals)
        number_pattern = r'\b\d+\.?\d*\b'
        matches = re.findall(number_pattern, text)
        return [float(n) for n in matches]

    def _extract_units(self, text: str) -> List[str]:
        """Extract measurement units from text."""
        units = []
        common_units = [
            'inches', 'feet', 'yards', 'miles', 'centimeters', 'meters',
            'pounds', 'ounces', 'grams', 'kilograms',
            'cups', 'pints', 'quarts', 'gallons', 'liters',
            'dollars', 'cents', 'minutes', 'hours', 'days'
        ]

        text_lower = text.lower()
        for unit in common_units:
            if unit in text_lower:
                units.append(unit)

        return units

    def _identify_keywords(self, problem: str) -> List[str]:
        """Identify important mathematical keywords."""
        keywords = []
        keyword_list = [
            'total', 'sum', 'difference', 'product', 'quotient',
            'more', 'less', 'equal', 'each', 'every', 'per',
            'altogether', 'left', 'remaining', 'how many', 'how much'
        ]

        problem_lower = problem.lower()
        for keyword in keyword_list:
            if keyword in problem_lower:
                keywords.append(keyword)

        return keywords

    def _estimate_difficulty(
        self,
        problem_type: MathProblemType,
        operations: List[MathOperation],
        number_count: int,
        grade_level: str
    ) -> int:
        """Estimate problem difficulty on scale of 1-10."""
        difficulty = 3  # Base difficulty

        # Adjust for problem type
        type_difficulty = {
            MathProblemType.ARITHMETIC: 0,
            MathProblemType.WORD_PROBLEM: 2,
            MathProblemType.FRACTIONS: 3,
            MathProblemType.DECIMALS: 2,
            MathProblemType.GEOMETRY: 2,
        }
        difficulty += type_difficulty.get(problem_type, 1)

        # Adjust for number of operations
        if len(operations) > 1:
            difficulty += 1

        # Adjust for number count
        if number_count > 3:
            difficulty += 1

        return min(10, max(1, difficulty))

    def _identify_concepts(
        self,
        problem_type: MathProblemType,
        operations: List[MathOperation],
        keywords: List[str]
    ) -> List[str]:
        """Identify key mathematical concepts in the problem."""
        concepts = []

        # Add concepts based on operations
        operation_concepts = {
            MathOperation.ADDITION: 'addition',
            MathOperation.SUBTRACTION: 'subtraction',
            MathOperation.MULTIPLICATION: 'multiplication',
            MathOperation.DIVISION: 'division'
        }

        for op in operations:
            if op in operation_concepts:
                concepts.append(operation_concepts[op])

        # Add concepts based on problem type
        if problem_type == MathProblemType.WORD_PROBLEM:
            concepts.append('word_problem_solving')

        if problem_type == MathProblemType.FRACTIONS:
            concepts.append('fractions')

        if problem_type == MathProblemType.GEOMETRY:
            concepts.append('geometry')

        return list(set(concepts))  # Remove duplicates

    def _get_prerequisites(self, concepts: List[str]) -> List[str]:
        """Get prerequisite concepts."""
        prerequisite_map = {
            'multiplication': ['addition', 'skip_counting'],
            'division': ['multiplication', 'subtraction'],
            'fractions': ['division', 'equal_parts'],
            'decimals': ['place_value', 'fractions'],
            'word_problem_solving': ['reading_comprehension', 'basic_operations']
        }

        prerequisites = []
        for concept in concepts:
            if concept in prerequisite_map:
                prerequisites.extend(prerequisite_map[concept])

        return list(set(prerequisites))

    def _generate_word_problem_steps(
        self,
        problem: str,
        operations: List[MathOperation],
        age: int
    ) -> List[MathStep]:
        """Generate steps for word problems."""
        steps = []

        # Step 1: Read and understand
        steps.append(MathStep(
            step_number=1,
            description="Read the problem carefully",
            operation="comprehension",
            reasoning="Understanding what the problem is asking",
            student_friendly="Let's read the problem together and figure out what it's asking!"
        ))

        # Step 2: Identify what we know
        steps.append(MathStep(
            step_number=2,
            description="Identify known information",
            operation="information_gathering",
            reasoning="Find the numbers and facts given in the problem",
            student_friendly="What numbers do we see? What do we already know?"
        ))

        # Step 3: Identify what we need to find
        steps.append(MathStep(
            step_number=3,
            description="Identify what to find",
            operation="goal_setting",
            reasoning="Determine what the question is asking for",
            student_friendly="What is the problem asking us to find?"
        ))

        # Step 4: Choose a strategy
        steps.append(MathStep(
            step_number=4,
            description="Choose a solving strategy",
            operation="strategy_selection",
            reasoning="Determine which operation(s) to use",
            student_friendly="How can we solve this? What operation should we use?"
        ))

        # Step 5: Solve
        operation_value = operations[0].value if operations and isinstance(operations[0], MathOperation) else (operations[0] if operations else "calculation")
        steps.append(MathStep(
            step_number=5,
            description="Solve the problem",
            operation=operation_value,
            reasoning="Perform the necessary calculations",
            student_friendly="Let's do the math step by step!"
        ))

        # Step 6: Check answer
        steps.append(MathStep(
            step_number=6,
            description="Check your answer",
            operation="verification",
            reasoning="Verify the answer makes sense",
            student_friendly="Does our answer make sense? Let's check!"
        ))

        return steps

    def _generate_arithmetic_steps(
        self,
        problem: str,
        operations: List,
        age: int
    ) -> List[MathStep]:
        """Generate steps for arithmetic problems."""
        steps = []

        # Get first operation - handle both string and enum
        operation = operations[0] if operations else "addition"
        if isinstance(operation, MathOperation):
            operation = operation.value

        if operation in ["addition", MathOperation.ADDITION.value]:
            steps.extend(self._get_addition_steps(age))
        elif operation in ["subtraction", MathOperation.SUBTRACTION.value]:
            steps.extend(self._get_subtraction_steps(age))
        elif operation in ["multiplication", MathOperation.MULTIPLICATION.value]:
            steps.extend(self._get_multiplication_steps(age))
        elif operation in ["division", MathOperation.DIVISION.value]:
            steps.extend(self._get_division_steps(age))

        return steps

    def _generate_fraction_steps(
        self,
        problem: str,
        operations: List[MathOperation],
        age: int
    ) -> List[MathStep]:
        """Generate steps for fraction problems."""
        return [
            MathStep(
                step_number=1,
                description="Understand the fractions",
                operation="comprehension",
                reasoning="Identify numerators and denominators",
                student_friendly="Let's look at the parts of each fraction!"
            ),
            MathStep(
                step_number=2,
                description="Check if denominators are the same",
                operation="comparison",
                reasoning="Same denominators make fractions easier to work with",
                student_friendly="Do the bottom numbers match?"
            ),
            MathStep(
                step_number=3,
                description="Perform the operation",
                operation="calculation",
                reasoning="Apply the appropriate fraction operation",
                student_friendly="Now let's solve it step by step!"
            )
        ]

    def _generate_geometry_steps(
        self,
        problem: str,
        age: int
    ) -> List[MathStep]:
        """Generate steps for geometry problems."""
        return [
            MathStep(
                step_number=1,
                description="Draw or visualize the shape",
                operation="visualization",
                reasoning="Visual representation helps understanding",
                student_friendly="Let's draw the shape or picture it in our minds!"
            ),
            MathStep(
                step_number=2,
                description="Label known measurements",
                operation="information_organization",
                reasoning="Organize given information",
                student_friendly="What measurements do we know? Let's label them!"
            ),
            MathStep(
                step_number=3,
                description="Apply the formula or method",
                operation="calculation",
                reasoning="Use appropriate geometric formula",
                student_friendly="Now let's use what we know to find the answer!"
            )
        ]

    def _generate_general_steps(
        self,
        problem: str,
        operations: List[MathOperation],
        age: int
    ) -> List[MathStep]:
        """Generate general problem-solving steps."""
        return [
            MathStep(
                step_number=1,
                description="Understand the problem",
                operation="comprehension",
                reasoning="Read carefully and identify what's being asked",
                student_friendly="What is this problem asking us to do?"
            ),
            MathStep(
                step_number=2,
                description="Plan your approach",
                operation="strategy",
                reasoning="Decide how to solve the problem",
                student_friendly="What's our plan to solve this?"
            ),
            MathStep(
                step_number=3,
                description="Solve step by step",
                operation="calculation",
                reasoning="Work through the problem systematically",
                student_friendly="Let's solve it one step at a time!"
            )
        ]

    def _get_addition_steps(self, age: int) -> List[MathStep]:
        """Get addition-specific steps."""
        return [
            MathStep(
                step_number=1,
                description="Line up the numbers",
                operation="preparation",
                reasoning="Align place values for accurate addition",
                student_friendly="Let's line up the ones, tens, and other place values!"
            ),
            MathStep(
                step_number=2,
                description="Add from right to left",
                operation="addition",
                reasoning="Start with ones place and move to higher places",
                student_friendly="Start with the ones place and add each column!"
            ),
            MathStep(
                step_number=3,
                description="Regroup if needed",
                operation="regrouping",
                reasoning="Carry over when sum exceeds 9",
                student_friendly="If you get 10 or more, remember to carry over!"
            )
        ]

    def _get_subtraction_steps(self, age: int) -> List[MathStep]:
        """Get subtraction-specific steps."""
        return [
            MathStep(
                step_number=1,
                description="Line up the numbers",
                operation="preparation",
                reasoning="Align place values",
                student_friendly="Line up the numbers by place value!"
            ),
            MathStep(
                step_number=2,
                description="Subtract from right to left",
                operation="subtraction",
                reasoning="Start with ones place",
                student_friendly="Start subtracting from the ones place!"
            ),
            MathStep(
                step_number=3,
                description="Borrow if needed",
                operation="borrowing",
                reasoning="Regroup when top number is smaller",
                student_friendly="If the top number is smaller, borrow from the next place!"
            )
        ]

    def _get_multiplication_steps(self, age: int) -> List[MathStep]:
        """Get multiplication-specific steps."""
        return [
            MathStep(
                step_number=1,
                description="Understand as groups",
                operation="conceptualization",
                reasoning="Think of multiplication as repeated addition",
                student_friendly="Think about groups! How many groups? How many in each?"
            ),
            MathStep(
                step_number=2,
                description="Multiply each place",
                operation="multiplication",
                reasoning="Multiply digits systematically",
                student_friendly="Multiply one place value at a time!"
            ),
            MathStep(
                step_number=3,
                description="Add partial products",
                operation="addition",
                reasoning="Combine results from each place value",
                student_friendly="Add up all the parts to get the final answer!"
            )
        ]

    def _get_division_steps(self, age: int) -> List[MathStep]:
        """Get division-specific steps."""
        return [
            MathStep(
                step_number=1,
                description="Set up the division",
                operation="preparation",
                reasoning="Organize dividend and divisor",
                student_friendly="Let's set up our division problem!"
            ),
            MathStep(
                step_number=2,
                description="Divide step by step",
                operation="division",
                reasoning="Work from left to right",
                student_friendly="Divide one place at a time, starting from the left!"
            ),
            MathStep(
                step_number=3,
                description="Check with multiplication",
                operation="verification",
                reasoning="Multiply quotient by divisor to verify",
                student_friendly="Let's check our answer by multiplying!"
            )
        ]

    def _extract_answer(self, solution: str) -> Optional[str]:
        """Extract the final answer from student's solution."""
        # Look for explicit answer indicators
        answer_patterns = [
            r'answer[:\s]*([0-9.,]+)',
            r'=\s*([0-9.,]+)\s*$',
            r'([0-9.,]+)\s*$'
        ]

        for pattern in answer_patterns:
            match = re.search(pattern, solution, re.IGNORECASE)
            if match:
                return match.group(1)

        # If no explicit answer, try to get the last number
        numbers = re.findall(r'\b\d+\.?\d*\b', solution)
        return numbers[-1] if numbers else None

    def _compare_answers(self, student_answer: str, expected: str) -> bool:
        """Compare student answer with expected answer."""
        if not student_answer or not expected:
            return False

        try:
            # Convert to float for numerical comparison
            student_val = float(student_answer.replace(',', ''))
            expected_val = float(expected.replace(',', ''))

            # Allow small floating point differences
            return abs(student_val - expected_val) < 0.01
        except (ValueError, AttributeError):
            # Fall back to string comparison
            return student_answer.strip() == expected.strip()

    def _analyze_solution_steps(
        self,
        problem: str,
        solution: str
    ) -> Dict[str, List[str]]:
        """Analyze individual steps in student's solution."""
        # This is a simplified version
        # In production, would use more sophisticated parsing
        return {
            'correct_steps': [],
            'incorrect_steps': [],
            'missing_steps': []
        }

    def _calculate_partial_credit(
        self,
        is_correct: bool,
        steps_analysis: Dict
    ) -> float:
        """Calculate partial credit percentage."""
        if is_correct:
            return 100.0

        # Award partial credit for correct steps
        correct = len(steps_analysis.get('correct_steps', []))
        incorrect = len(steps_analysis.get('incorrect_steps', []))
        total = correct + incorrect

        if total == 0:
            return 0.0

        return (correct / total) * 100.0

    def _generate_verification_feedback(
        self,
        is_correct: bool,
        steps_analysis: Dict,
        grade_level: str
    ) -> str:
        """Generate constructive feedback on student work."""
        if is_correct:
            return "Great job! Your answer is correct!"

        feedback_parts = []

        correct_steps = steps_analysis.get('correct_steps', [])
        if correct_steps:
            feedback_parts.append(
                f"You're on the right track with {len(correct_steps)} step(s)!"
            )

        feedback_parts.append(
            "Let's look at the problem again and think about what we need to do."
        )

        return " ".join(feedback_parts)

    def _check_computational_errors(
        self,
        work: str,
        analysis: Dict
    ) -> List[ErrorAnalysis]:
        """Check for computational errors."""
        errors = []

        # Check for basic arithmetic errors
        # This is a placeholder - production would be more sophisticated
        if 'addition' in analysis['operations']:
            # Check common addition errors
            pass

        return errors

    def _check_conceptual_errors(
        self,
        work: str,
        analysis: Dict
    ) -> List[ErrorAnalysis]:
        """Check for conceptual misunderstandings."""
        return []

    def _check_procedural_errors(
        self,
        work: str,
        analysis: Dict
    ) -> List[ErrorAnalysis]:
        """Check for procedural errors."""
        return []

    def _check_word_problem_errors(
        self,
        problem: str,
        work: str
    ) -> List[ErrorAnalysis]:
        """Check for word problem comprehension errors."""
        errors = []

        # Check if student used wrong operation
        # This is simplified - production version would be more comprehensive

        return errors

    def _select_strategy(
        self,
        analysis: Dict,
        grade_level: str,
        previous_attempts: Optional[List[str]]
    ) -> str:
        """Select appropriate problem-solving strategy."""
        problem_type = analysis['problem_type']

        # Strategy selection based on problem type
        strategies = {
            'arithmetic': 'break_apart',
            'word_problem': 'draw_picture',
            'fractions': 'visual_model',
            'geometry': 'draw_and_label'
        }

        return strategies.get(problem_type, 'step_by_step')

    def _get_strategy_description(self, strategy: str, age: int) -> str:
        """Get age-appropriate strategy description."""
        descriptions = {
            'break_apart': "Break the numbers into smaller, easier parts!",
            'draw_picture': "Draw a picture to help you see what's happening!",
            'visual_model': "Use a picture or model to see the fractions!",
            'draw_and_label': "Draw the shape and label what you know!",
            'step_by_step': "Take it one step at a time!"
        }

        return descriptions.get(strategy, "Let's solve this together!")

    def _get_strategy_steps(self, strategy: str, age: int) -> List[str]:
        """Get steps for applying the strategy."""
        steps_map = {
            'break_apart': [
                "Break the numbers into tens and ones",
                "Work with the easier parts",
                "Put the parts back together"
            ],
            'draw_picture': [
                "Draw what the problem is describing",
                "Label the important numbers",
                "Use your picture to solve"
            ],
            'visual_model': [
                "Draw circles or rectangles to show the whole",
                "Divide them into equal parts",
                "Shade the parts you're working with"
            ]
        }

        return steps_map.get(strategy, ["Think it through step by step"])

    def _suggest_visual_aids(self, problem_type: str, strategy: str) -> List[str]:
        """Suggest helpful visual aids."""
        aids = {
            'arithmetic': ['number line', 'base-10 blocks', 'counters'],
            'word_problem': ['drawings', 'diagrams', 'charts'],
            'fractions': ['fraction bars', 'circles', 'rectangles'],
            'geometry': ['grid paper', 'ruler', 'protractor']
        }

        return aids.get(problem_type, ['paper and pencil'])

    def _explain_strategy_choice(
        self,
        strategy: str,
        analysis: Dict,
        age: int
    ) -> str:
        """Explain why this strategy was chosen."""
        return f"This strategy works well for {analysis['problem_type']} problems!"

    def _get_alternative_strategies(
        self,
        analysis: Dict,
        current_strategy: str
    ) -> List[str]:
        """Get alternative strategies."""
        all_strategies = [
            'break_apart', 'draw_picture', 'visual_model',
            'number_line', 'counting', 'fact_families'
        ]

        # Return strategies other than current one
        return [s for s in all_strategies if s != current_strategy][:2]

    def _get_concept_definition(self, concept: str, age: int) -> str:
        """Get age-appropriate definition."""
        # Simplified - production would have comprehensive definitions
        return f"A clear, simple explanation of {concept}"

    def _get_visual_representation(self, concept: str) -> str:
        """Get visual representation description."""
        return "Imagine drawing this concept to help you see it!"

    def _get_real_world_examples(self, concept: str, age: int) -> List[str]:
        """Get real-world examples of concept."""
        return [
            "Sharing cookies with friends",
            "Counting items at the store",
            "Measuring ingredients for cooking"
        ]

    def _get_concept_vocabulary(self, concept: str) -> List[str]:
        """Get key vocabulary for concept."""
        return ['add', 'sum', 'total', 'plus']

    def _generate_practice_examples(
        self,
        concept: str,
        age: int
    ) -> List[str]:
        """Generate practice examples."""
        return [
            "5 + 3 = ?",
            "10 - 4 = ?",
            "2 × 6 = ?"
        ]

    def _initialize_common_errors(self) -> Dict[str, List[str]]:
        """Initialize database of common math errors."""
        return {
            'addition': [
                'Forgetting to regroup',
                'Adding digits without considering place value',
                'Misaligning numbers'
            ],
            'subtraction': [
                'Not borrowing when needed',
                'Subtracting smaller from larger regardless of position',
                'Misaligning numbers'
            ],
            'multiplication': [
                'Thinking multiplication is the same as addition',
                'Forgetting to add zero when multiplying by tens',
                'Confusing multiplication with repeated addition'
            ],
            'division': [
                'Thinking division always makes numbers smaller',
                'Confusing division with subtraction',
                'Not understanding remainders'
            ]
        }

    def _initialize_strategies(self) -> Dict[str, Dict]:
        """Initialize problem-solving strategies."""
        return {
            'break_apart': {
                'name': 'Break Apart',
                'description': 'Break numbers into easier parts',
                'best_for': ['addition', 'subtraction', 'multiplication']
            },
            'draw_picture': {
                'name': 'Draw a Picture',
                'description': 'Visualize the problem',
                'best_for': ['word_problem', 'geometry']
            },
            'number_line': {
                'name': 'Use a Number Line',
                'description': 'Show numbers and operations on a line',
                'best_for': ['addition', 'subtraction']
            }
        }

    def _initialize_math_vocabulary(self) -> Dict[str, List[str]]:
        """Initialize math vocabulary by concept."""
        return {
            'addition': ['sum', 'plus', 'add', 'total', 'altogether'],
            'subtraction': ['difference', 'minus', 'subtract', 'less', 'take away'],
            'multiplication': ['product', 'times', 'multiply', 'groups of'],
            'division': ['quotient', 'divide', 'split', 'share equally']
        }


def create_math_reasoner(curriculum_manager=None) -> MathReasoner:
    """
    Convenience function to create a MathReasoner instance.

    Args:
        curriculum_manager: Optional CurriculumManager instance

    Returns:
        Initialized MathReasoner instance
    """
    return MathReasoner(curriculum_manager)


# Example usage
if __name__ == "__main__":
    reasoner = create_math_reasoner()

    print("=== Math Reasoning Module ===\n")

    # Example 1: Analyze a word problem
    print("--- Example 1: Problem Analysis ---")
    problem = "Sarah has 5 apples. She buys 3 more apples. How many apples does she have now?"
    analysis = reasoner.analyze_problem(problem, grade_level="1")
    print(f"Problem: {problem}")
    print(f"Type: {analysis['problem_type']}")
    print(f"Operations: {analysis['operations']}")
    print(f"Difficulty: {analysis['difficulty']}/10")
    print()

    # Example 2: Generate solution steps
    print("--- Example 2: Solution Steps ---")
    steps = reasoner.generate_steps(problem, grade_level="1", student_age=6)
    print("Steps to solve:")
    for step in steps:
        print(f"  {step.step_number}. {step.student_friendly}")
    print()

    # Example 3: Suggest strategy
    print("--- Example 3: Strategy Suggestion ---")
    strategy = reasoner.suggest_strategy(problem, grade_level="1", student_age=6)
    print(f"Recommended Strategy: {strategy['strategy_name']}")
    print(f"Description: {strategy['description']}")
    print(f"Visual Aids: {', '.join(strategy['visual_aids'])}")
    print()

    # Example 4: Check student work
    print("--- Example 4: Check Work ---")
    student_solution = "5 + 3 = 8 apples"
    check_result = reasoner.check_work(problem, student_solution, expected_answer="8")
    print(f"Student Answer: {student_solution}")
    print(f"Is Correct: {check_result['is_correct']}")
    print(f"Feedback: {check_result['feedback']}")
    print()

    print("=== Math Reasoner Ready ===")
