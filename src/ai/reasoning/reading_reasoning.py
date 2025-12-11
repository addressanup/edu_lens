"""
Reading Reasoning Module for EduLens AI Agent

This module provides specialized reasoning capabilities for reading education,
including comprehension strategies, vocabulary support, passage analysis,
and reading guidance for K-6 students.

Author: EduLens AI Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class TextType(Enum):
    """Types of reading texts."""
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    POETRY = "poetry"
    INFORMATIONAL = "informational"
    NARRATIVE = "narrative"


class ComprehensionLevel(Enum):
    """Levels of reading comprehension."""
    LITERAL = "literal"  # What the text says
    INFERENTIAL = "inferential"  # Reading between the lines
    EVALUATIVE = "evaluative"  # Forming opinions and judgments
    ANALYTICAL = "analytical"  # Deep analysis of structure and meaning


class ReadingStrategy(Enum):
    """Reading comprehension strategies."""
    PREDICT = "predict"
    QUESTION = "question"
    CLARIFY = "clarify"
    SUMMARIZE = "summarize"
    VISUALIZE = "visualize"
    CONNECT = "connect"
    INFER = "infer"


@dataclass
class VocabularyExplanation:
    """Explanation of a vocabulary word."""
    word: str
    definition: str
    context_clues: List[str]
    example_sentence: str
    synonyms: List[str]
    student_friendly_definition: str


@dataclass
class ComprehensionCheck:
    """Comprehension check question and guidance."""
    question: str
    question_type: str
    expected_thinking: str
    hints: List[str]
    difficulty_level: int


class ReadingReasoner:
    """
    Specialized reasoning engine for reading education.

    Provides passage analysis, comprehension strategies, vocabulary support,
    and reading guidance for K-6 students.
    """

    def __init__(self, curriculum_manager=None):
        """
        Initialize the ReadingReasoner.

        Args:
            curriculum_manager: Optional CurriculumManager instance
        """
        self.curriculum_manager = curriculum_manager
        self.reading_strategies = self._initialize_reading_strategies()
        self.question_stems = self._initialize_question_stems()
        self.text_features = self._initialize_text_features()

    def analyze_passage(
        self,
        passage: str,
        grade_level: str,
        text_type: Optional[TextType] = None
    ) -> Dict[str, Any]:
        """
        Analyze a reading passage to understand its structure and features.

        Args:
            passage: The text to analyze
            grade_level: Student's grade level (K-6)
            text_type: Type of text (auto-detected if None)

        Returns:
            Dictionary containing passage analysis:
                - text_type: Type of text (fiction, non-fiction, etc.)
                - reading_level: Estimated reading level
                - key_features: Important text features
                - vocabulary: Notable vocabulary words
                - themes: Main themes or topics
                - structure: Text structure (narrative, sequential, etc.)
                - complexity: Reading complexity factors
        """
        logger.info(f"Analyzing passage for grade {grade_level}")

        # Auto-detect text type if not provided
        if text_type is None:
            text_type = self._detect_text_type(passage)

        # Analyze reading level
        reading_level = self._estimate_reading_level(passage)

        # Identify text features
        features = self._identify_text_features(passage, text_type)

        # Extract notable vocabulary
        vocabulary = self._extract_vocabulary(passage, grade_level)

        # Identify themes/topics
        themes = self._identify_themes(passage)

        # Determine text structure
        structure = self._determine_structure(passage, text_type)

        # Assess complexity
        complexity = self._assess_complexity(passage, grade_level)

        return {
            'text_type': text_type.value,
            'reading_level': reading_level,
            'key_features': features,
            'notable_vocabulary': vocabulary,
            'themes': themes,
            'structure': structure,
            'complexity': complexity,
            'word_count': len(passage.split()),
            'sentence_count': len(re.findall(r'[.!?]+', passage))
        }

    def identify_main_idea(
        self,
        passage: str,
        student_age: int,
        provide_guidance: bool = True
    ) -> Dict[str, Any]:
        """
        Extract and explain the main idea of a passage.

        Args:
            passage: The text to analyze
            student_age: Student's age for appropriate guidance
            provide_guidance: Whether to provide guidance vs. direct answer

        Returns:
            Dictionary with main idea analysis and guidance
        """
        logger.info("Identifying main idea")

        # Analyze the passage
        text_type = self._detect_text_type(passage)

        # Extract potential main ideas
        main_idea_candidates = self._extract_main_idea_candidates(passage)

        # Generate guiding questions
        guiding_questions = self._generate_main_idea_questions(
            passage, text_type, student_age
        )

        # Identify key details that support main idea
        supporting_details = self._identify_supporting_details(passage)

        result = {
            'text_type': text_type.value,
            'guiding_questions': guiding_questions,
            'key_details': supporting_details[:5],  # Top 5 details
            'thinking_strategy': self._get_main_idea_strategy(text_type, student_age)
        }

        # Only include direct main idea if not providing guidance
        if not provide_guidance:
            result['main_idea'] = main_idea_candidates[0] if main_idea_candidates else None

        return result

    def explain_vocabulary(
        self,
        word: str,
        context_sentence: str,
        student_age: int,
        passage: Optional[str] = None
    ) -> VocabularyExplanation:
        """
        Provide context-appropriate vocabulary explanation.

        Args:
            word: The vocabulary word to explain
            context_sentence: Sentence containing the word
            student_age: Student's age for appropriate explanation
            passage: Full passage for additional context (optional)

        Returns:
            VocabularyExplanation object with detailed word information
        """
        logger.info(f"Explaining vocabulary word: {word}")

        # Find context clues in the sentence
        context_clues = self._find_context_clues(word, context_sentence)

        # Generate age-appropriate definition
        definition = self._get_definition(word, student_age)
        student_friendly = self._simplify_definition(definition, student_age)

        # Find synonyms appropriate for age
        synonyms = self._get_age_appropriate_synonyms(word, student_age)

        # Create example sentence
        example = self._create_example_sentence(word, student_age)

        return VocabularyExplanation(
            word=word,
            definition=definition,
            context_clues=context_clues,
            example_sentence=example,
            synonyms=synonyms,
            student_friendly_definition=student_friendly
        )

    def guide_comprehension(
        self,
        passage: str,
        student_response: str,
        question: str,
        grade_level: str,
        student_age: int
    ) -> Dict[str, Any]:
        """
        Guide student toward better reading comprehension.

        Args:
            passage: The reading passage
            student_response: Student's answer to question
            question: The comprehension question asked
            grade_level: Student's grade level
            student_age: Student's age

        Returns:
            Dictionary with comprehension guidance:
                - feedback: Feedback on student's response
                - guiding_questions: Questions to improve understanding
                - strategy_suggestion: Recommended reading strategy
                - text_evidence: Where to look in the text
                - hints: Progressive hints
        """
        logger.info("Guiding reading comprehension")

        # Analyze the question type
        question_type = self._classify_question_type(question)

        # Evaluate student response
        response_quality = self._evaluate_response(
            student_response, question, passage, question_type
        )

        # Generate feedback
        feedback = self._generate_reading_feedback(
            response_quality, student_age
        )

        # Suggest appropriate reading strategy
        strategy = self._suggest_reading_strategy(question_type, passage)

        # Identify where to find evidence
        text_evidence_location = self._locate_text_evidence(
            question, passage, question_type
        )

        # Generate guiding questions
        guiding_questions = self._generate_guiding_questions(
            question, passage, question_type, student_age
        )

        # Create progressive hints
        hints = self._create_progressive_hints(
            question, passage, question_type, student_age
        )

        return {
            'feedback': feedback,
            'response_quality': response_quality,
            'guiding_questions': guiding_questions,
            'strategy_suggestion': strategy,
            'text_evidence_location': text_evidence_location,
            'hints': hints,
            'question_type': question_type
        }

    def check_understanding(
        self,
        passage: str,
        student_summary: str,
        grade_level: str
    ) -> Dict[str, Any]:
        """
        Verify student's reading comprehension.

        Args:
            passage: The original passage
            student_summary: Student's summary or response
            grade_level: Student's grade level

        Returns:
            Dictionary with understanding assessment:
                - comprehension_level: Assessed comprehension level
                - key_elements_included: Important elements mentioned
                - key_elements_missing: Important elements not mentioned
                - accuracy_score: 0.0-1.0 score
                - feedback: Constructive feedback
        """
        logger.info("Checking reading understanding")

        # Extract key elements from passage
        key_elements = self._extract_key_elements(passage)

        # Check which elements are in student's summary
        included_elements = self._find_included_elements(
            student_summary, key_elements
        )

        missing_elements = [
            elem for elem in key_elements if elem not in included_elements
        ]

        # Calculate accuracy
        accuracy = len(included_elements) / max(len(key_elements), 1)

        # Assess comprehension level
        comp_level = self._assess_comprehension_level(
            student_summary, passage
        )

        # Generate feedback
        feedback = self._generate_comprehension_feedback(
            accuracy, included_elements, missing_elements, grade_level
        )

        return {
            'comprehension_level': comp_level.value,
            'key_elements_included': included_elements,
            'key_elements_missing': missing_elements,
            'accuracy_score': accuracy,
            'feedback': feedback,
            'demonstrates_understanding': accuracy >= 0.6
        }

    def suggest_reading_strategy(
        self,
        passage: str,
        difficulty_area: str,
        student_age: int
    ) -> Dict[str, Any]:
        """
        Suggest appropriate reading strategy for comprehension.

        Args:
            passage: The reading passage
            difficulty_area: Area of difficulty (vocabulary, main idea, etc.)
            student_age: Student's age

        Returns:
            Dictionary with strategy recommendation:
                - strategy_name: Name of strategy
                - description: How to use the strategy
                - steps: Specific steps to follow
                - when_to_use: When this strategy helps
                - practice_example: Example of using the strategy
        """
        logger.info(f"Suggesting reading strategy for: {difficulty_area}")

        # Select appropriate strategy
        strategy = self._select_strategy_for_difficulty(difficulty_area)

        # Get age-appropriate description
        description = self._get_strategy_description(strategy, student_age)

        # Get implementation steps
        steps = self._get_strategy_steps(strategy, student_age)

        # Explain when to use
        when_to_use = self._explain_strategy_usage(strategy)

        # Create practice example
        practice = self._create_strategy_example(strategy, passage, student_age)

        return {
            'strategy_name': strategy.value,
            'description': description,
            'steps': steps,
            'when_to_use': when_to_use,
            'practice_example': practice,
            'visual_aid': self._get_strategy_visual_aid(strategy)
        }

    def analyze_character(
        self,
        passage: str,
        character_name: str,
        student_age: int
    ) -> Dict[str, Any]:
        """
        Analyze a character from a narrative passage.

        Args:
            passage: The narrative text
            character_name: Name of character to analyze
            student_age: Student's age

        Returns:
            Dictionary with character analysis guidance
        """
        logger.info(f"Analyzing character: {character_name}")

        # Find character mentions
        mentions = self._find_character_mentions(passage, character_name)

        # Analyze character traits
        traits = self._identify_character_traits(passage, character_name)

        # Identify character's actions
        actions = self._identify_character_actions(passage, character_name)

        # Character's feelings/emotions
        feelings = self._infer_character_feelings(passage, character_name)

        # Guiding questions for analysis
        questions = self._generate_character_questions(
            character_name, student_age
        )

        return {
            'character_name': character_name,
            'mentions_count': len(mentions),
            'traits': traits,
            'actions': actions,
            'feelings': feelings,
            'guiding_questions': questions,
            'evidence_locations': self._find_evidence_sentences(
                passage, character_name
            )
        }

    # Private helper methods

    def _detect_text_type(self, passage: str) -> TextType:
        """Detect the type of text."""
        passage_lower = passage.lower()

        # Fiction indicators
        fiction_indicators = ['once upon', 'said', 'character', 'story']
        fiction_score = sum(1 for ind in fiction_indicators if ind in passage_lower)

        # Non-fiction indicators
        nonfiction_indicators = ['fact', 'information', 'because', 'example']
        nonfiction_score = sum(1 for ind in nonfiction_indicators if ind in passage_lower)

        # Poetry indicators
        poetry_indicators = ['\n\n', 'verse', 'stanza']
        is_poetry = any(ind in passage for ind in poetry_indicators)

        if is_poetry:
            return TextType.POETRY
        elif nonfiction_score > fiction_score:
            return TextType.NON_FICTION
        else:
            return TextType.FICTION

    def _estimate_reading_level(self, passage: str) -> str:
        """Estimate reading level using simplified metrics."""
        words = passage.split()
        sentences = re.findall(r'[.!?]+', passage)

        if not sentences:
            return "K-1"

        avg_words_per_sentence = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)

        # Simple estimation
        if avg_words_per_sentence < 8 and avg_word_length < 4:
            return "K-1"
        elif avg_words_per_sentence < 12 and avg_word_length < 5:
            return "2-3"
        elif avg_words_per_sentence < 15 and avg_word_length < 6:
            return "4-5"
        else:
            return "6+"

    def _identify_text_features(
        self,
        passage: str,
        text_type: TextType
    ) -> List[str]:
        """Identify important text features."""
        features = []

        # Check for dialogue
        if '"' in passage or "'" in passage:
            features.append("dialogue")

        # Check for headings (simple check)
        if '\n\n' in passage:
            features.append("paragraphs")

        # Check for questions
        if '?' in passage:
            features.append("questions")

        # Type-specific features
        if text_type == TextType.NON_FICTION:
            if any(word in passage.lower() for word in ['first', 'next', 'then', 'finally']):
                features.append("sequence words")
            if any(word in passage.lower() for word in ['because', 'so', 'since']):
                features.append("cause and effect")

        return features

    def _extract_vocabulary(
        self,
        passage: str,
        grade_level: str
    ) -> List[str]:
        """Extract notable vocabulary words."""
        words = re.findall(r'\b[a-zA-Z]+\b', passage)

        # Find longer, potentially challenging words
        notable = []
        for word in set(words):
            if len(word) > 7 and word.lower() not in ['together', 'everyone', 'something']:
                notable.append(word.lower())

        return notable[:10]  # Return top 10

    def _identify_themes(self, passage: str) -> List[str]:
        """Identify potential themes."""
        themes = []
        passage_lower = passage.lower()

        theme_keywords = {
            'friendship': ['friend', 'together', 'help'],
            'courage': ['brave', 'courage', 'fear'],
            'learning': ['learn', 'discover', 'understand'],
            'nature': ['animal', 'plant', 'forest', 'ocean'],
            'family': ['family', 'mother', 'father', 'sister', 'brother']
        }

        for theme, keywords in theme_keywords.items():
            if any(keyword in passage_lower for keyword in keywords):
                themes.append(theme)

        return themes

    def _determine_structure(
        self,
        passage: str,
        text_type: TextType
    ) -> str:
        """Determine text structure."""
        passage_lower = passage.lower()

        if text_type == TextType.FICTION:
            return "narrative"

        # Check for different structures
        if any(word in passage_lower for word in ['first', 'second', 'next', 'finally']):
            return "sequential"
        elif any(word in passage_lower for word in ['because', 'due to', 'as a result']):
            return "cause_and_effect"
        elif any(word in passage_lower for word in ['alike', 'different', 'both', 'whereas']):
            return "compare_and_contrast"
        elif any(word in passage_lower for word in ['problem', 'solution', 'solve']):
            return "problem_solution"
        else:
            return "descriptive"

    def _assess_complexity(
        self,
        passage: str,
        grade_level: str
    ) -> Dict[str, Any]:
        """Assess reading complexity."""
        words = passage.split()
        sentences = len(re.findall(r'[.!?]+', passage))

        return {
            'total_words': len(words),
            'unique_words': len(set(words)),
            'sentence_count': sentences,
            'avg_sentence_length': len(words) / max(sentences, 1),
            'complexity_rating': 'moderate'  # Simplified
        }

    def _extract_main_idea_candidates(self, passage: str) -> List[str]:
        """Extract potential main ideas."""
        # Simplified - would use more sophisticated NLP in production
        sentences = passage.split('.')
        return [s.strip() for s in sentences[:2] if s.strip()]

    def _generate_main_idea_questions(
        self,
        passage: str,
        text_type: TextType,
        age: int
    ) -> List[str]:
        """Generate questions to help identify main idea."""
        questions = [
            "What is this mostly about?",
            "What happens in this text?",
        ]

        if text_type == TextType.FICTION:
            questions.append("What is the most important thing that happens?")
        else:
            questions.append("What is the author teaching us?")

        return questions

    def _identify_supporting_details(self, passage: str) -> List[str]:
        """Identify supporting details."""
        sentences = passage.split('.')
        return [s.strip() for s in sentences if s.strip()][:5]

    def _get_main_idea_strategy(
        self,
        text_type: TextType,
        age: int
    ) -> str:
        """Get strategy for finding main idea."""
        if text_type == TextType.FICTION:
            return "Think about who the story is about and what happens to them."
        else:
            return "Look for the topic that appears most often. What is the author teaching about this topic?"

    def _find_context_clues(
        self,
        word: str,
        sentence: str
    ) -> List[str]:
        """Find context clues around a word."""
        clues = []

        # Simple context clue detection
        sentence_lower = sentence.lower()
        word_lower = word.lower()

        # Definition clues
        if ' is ' in sentence_lower or ' means ' in sentence_lower:
            clues.append("definition clue in sentence")

        # Example clues
        if 'such as' in sentence_lower or 'like' in sentence_lower:
            clues.append("example clue")

        # Surrounding words
        words = sentence.split()
        if word in words:
            idx = words.index(word)
            if idx > 0:
                clues.append(f"word before: {words[idx-1]}")
            if idx < len(words) - 1:
                clues.append(f"word after: {words[idx+1]}")

        return clues

    def _get_definition(self, word: str, age: int) -> str:
        """Get definition of word."""
        # Placeholder - production would use dictionary API
        return f"Definition of {word}"

    def _simplify_definition(self, definition: str, age: int) -> str:
        """Simplify definition for age."""
        # Placeholder - would use actual simplification logic
        return f"A simple way to understand {definition}"

    def _get_age_appropriate_synonyms(
        self,
        word: str,
        age: int
    ) -> List[str]:
        """Get synonyms appropriate for age."""
        # Placeholder - would use thesaurus with age filtering
        return ["similar word 1", "similar word 2"]

    def _create_example_sentence(self, word: str, age: int) -> str:
        """Create example sentence using word."""
        return f"Here is an example sentence using {word}."

    def _classify_question_type(self, question: str) -> str:
        """Classify comprehension question type."""
        question_lower = question.lower()

        if any(word in question_lower for word in ['who', 'what', 'when', 'where']):
            return "literal"
        elif any(word in question_lower for word in ['why', 'how']):
            return "inferential"
        elif 'main idea' in question_lower or 'mostly about' in question_lower:
            return "main_idea"
        elif 'feel' in question_lower or 'emotion' in question_lower:
            return "emotional"
        else:
            return "general"

    def _evaluate_response(
        self,
        response: str,
        question: str,
        passage: str,
        question_type: str
    ) -> str:
        """Evaluate quality of student's response."""
        # Simplified evaluation
        if len(response.split()) < 3:
            return "incomplete"
        elif len(response.split()) < 10:
            return "basic"
        else:
            return "detailed"

    def _generate_reading_feedback(
        self,
        quality: str,
        age: int
    ) -> str:
        """Generate feedback on reading response."""
        feedback_map = {
            "incomplete": "Can you tell me more? Let's look at the text together.",
            "basic": "Good start! Can you add more details from the story?",
            "detailed": "Great job explaining your thinking!"
        }
        return feedback_map.get(quality, "Let's think about this together.")

    def _suggest_reading_strategy(
        self,
        question_type: str,
        passage: str
    ) -> str:
        """Suggest appropriate reading strategy."""
        strategy_map = {
            "literal": "Look carefully at the words in the text.",
            "inferential": "Think about clues in the story. What does the author want you to understand?",
            "main_idea": "Think about what the whole text is mostly about.",
            "emotional": "Put yourself in the character's shoes. How would you feel?"
        }
        return strategy_map.get(question_type, "Read carefully and think about what you learned.")

    def _locate_text_evidence(
        self,
        question: str,
        passage: str,
        question_type: str
    ) -> str:
        """Help locate where to find evidence."""
        return "Look at the beginning, middle, or end of the passage for clues."

    def _generate_guiding_questions(
        self,
        question: str,
        passage: str,
        question_type: str,
        age: int
    ) -> List[str]:
        """Generate guiding questions."""
        return [
            "What does the text tell us?",
            "What clues can we find?",
            "What do we already know that can help?"
        ]

    def _create_progressive_hints(
        self,
        question: str,
        passage: str,
        question_type: str,
        age: int
    ) -> List[str]:
        """Create progressive hints."""
        return [
            "Think about what you just read.",
            "Look for key words in the question and find them in the text.",
            "The answer is in the text. Let's read that part again together."
        ]

    def _extract_key_elements(self, passage: str) -> List[str]:
        """Extract key elements from passage."""
        # Simplified - would be more sophisticated in production
        sentences = passage.split('.')
        return [s.strip() for s in sentences if len(s.strip()) > 20][:5]

    def _find_included_elements(
        self,
        summary: str,
        key_elements: List[str]
    ) -> List[str]:
        """Find which key elements are in summary."""
        included = []
        summary_lower = summary.lower()

        for element in key_elements:
            # Simple word overlap check
            element_words = set(element.lower().split())
            summary_words = set(summary_lower.split())
            overlap = len(element_words & summary_words)

            if overlap >= len(element_words) * 0.3:  # 30% word overlap
                included.append(element)

        return included

    def _assess_comprehension_level(
        self,
        summary: str,
        passage: str
    ) -> ComprehensionLevel:
        """Assess level of comprehension demonstrated."""
        # Simplified assessment
        if len(summary.split()) < 10:
            return ComprehensionLevel.LITERAL
        elif any(word in summary.lower() for word in ['because', 'so', 'reason']):
            return ComprehensionLevel.INFERENTIAL
        else:
            return ComprehensionLevel.LITERAL

    def _generate_comprehension_feedback(
        self,
        accuracy: float,
        included: List[str],
        missing: List[str],
        grade_level: str
    ) -> str:
        """Generate feedback on comprehension."""
        if accuracy >= 0.8:
            return "Excellent understanding! You captured the main ideas."
        elif accuracy >= 0.6:
            return "Good job! You got many of the important ideas."
        else:
            return "Let's read the passage again and look for the main ideas together."

    def _select_strategy_for_difficulty(
        self,
        difficulty_area: str
    ) -> ReadingStrategy:
        """Select strategy based on difficulty."""
        strategy_map = {
            'vocabulary': ReadingStrategy.CLARIFY,
            'main_idea': ReadingStrategy.SUMMARIZE,
            'details': ReadingStrategy.QUESTION,
            'understanding': ReadingStrategy.VISUALIZE,
            'predictions': ReadingStrategy.PREDICT
        }
        return strategy_map.get(difficulty_area, ReadingStrategy.QUESTION)

    def _get_strategy_description(
        self,
        strategy: ReadingStrategy,
        age: int
    ) -> str:
        """Get strategy description."""
        descriptions = {
            ReadingStrategy.PREDICT: "Guess what will happen next based on clues!",
            ReadingStrategy.QUESTION: "Ask yourself questions while you read.",
            ReadingStrategy.CLARIFY: "Stop and figure out words or parts you don't understand.",
            ReadingStrategy.SUMMARIZE: "Tell the main ideas in your own words.",
            ReadingStrategy.VISUALIZE: "Make a picture in your mind of what's happening.",
            ReadingStrategy.CONNECT: "Connect the story to your own life.",
            ReadingStrategy.INFER: "Use clues to figure out things the author doesn't say directly."
        }
        return descriptions.get(strategy, "Think carefully about what you read.")

    def _get_strategy_steps(
        self,
        strategy: ReadingStrategy,
        age: int
    ) -> List[str]:
        """Get steps for using strategy."""
        steps_map = {
            ReadingStrategy.VISUALIZE: [
                "Stop and close your eyes",
                "Picture what's happening in your mind",
                "Think about colors, shapes, and actions you see",
                "Keep that picture in mind as you keep reading"
            ],
            ReadingStrategy.QUESTION: [
                "Before reading, ask 'What will this be about?'",
                "During reading, ask 'What is happening?'",
                "After reading, ask 'What did I learn?'"
            ]
        }
        return steps_map.get(strategy, ["Use this strategy as you read."])

    def _explain_strategy_usage(self, strategy: ReadingStrategy) -> str:
        """Explain when to use strategy."""
        return f"Use {strategy.value} when you need to understand the text better."

    def _create_strategy_example(
        self,
        strategy: ReadingStrategy,
        passage: str,
        age: int
    ) -> str:
        """Create example of using strategy."""
        return f"Example: When reading this passage, you can {strategy.value}..."

    def _get_strategy_visual_aid(self, strategy: ReadingStrategy) -> str:
        """Get visual aid suggestion for strategy."""
        return "Draw pictures or make notes to help you remember."

    def _find_character_mentions(
        self,
        passage: str,
        character_name: str
    ) -> List[str]:
        """Find mentions of character."""
        mentions = []
        sentences = passage.split('.')

        for sentence in sentences:
            if character_name.lower() in sentence.lower():
                mentions.append(sentence.strip())

        return mentions

    def _identify_character_traits(
        self,
        passage: str,
        character_name: str
    ) -> List[str]:
        """Identify character traits."""
        # Simplified - would be more sophisticated in production
        traits = []
        trait_words = ['brave', 'kind', 'smart', 'funny', 'helpful', 'curious']

        passage_lower = passage.lower()
        for trait in trait_words:
            if trait in passage_lower:
                traits.append(trait)

        return traits

    def _identify_character_actions(
        self,
        passage: str,
        character_name: str
    ) -> List[str]:
        """Identify character's actions."""
        actions = []
        mentions = self._find_character_mentions(passage, character_name)

        # Extract verbs near character mentions
        for mention in mentions:
            words = mention.split()
            actions.append(mention)  # Simplified

        return actions[:3]

    def _infer_character_feelings(
        self,
        passage: str,
        character_name: str
    ) -> List[str]:
        """Infer character's feelings."""
        feelings = []
        emotion_words = ['happy', 'sad', 'angry', 'excited', 'worried', 'surprised']

        passage_lower = passage.lower()
        for emotion in emotion_words:
            if emotion in passage_lower:
                feelings.append(emotion)

        return feelings

    def _generate_character_questions(
        self,
        character_name: str,
        age: int
    ) -> List[str]:
        """Generate questions about character."""
        return [
            f"What does {character_name} do in the story?",
            f"How does {character_name} feel?",
            f"What kind of person is {character_name}?",
            f"What can we learn from {character_name}?"
        ]

    def _find_evidence_sentences(
        self,
        passage: str,
        character_name: str
    ) -> List[str]:
        """Find sentences with evidence about character."""
        return self._find_character_mentions(passage, character_name)

    def _initialize_reading_strategies(self) -> Dict:
        """Initialize reading strategies database."""
        return {
            strategy: {
                'name': strategy.value,
                'description': f"Strategy for {strategy.value}",
                'when_to_use': f"Use when needed for {strategy.value}"
            }
            for strategy in ReadingStrategy
        }

    def _initialize_question_stems(self) -> Dict:
        """Initialize question stems for comprehension."""
        return {
            'literal': ['Who', 'What', 'When', 'Where'],
            'inferential': ['Why', 'How', 'What if'],
            'evaluative': ['Do you think', 'Would you', 'Should']
        }

    def _initialize_text_features(self) -> Dict:
        """Initialize text features database."""
        return {
            'narrative': ['characters', 'setting', 'plot', 'problem', 'solution'],
            'informational': ['headings', 'facts', 'details', 'examples'],
            'poetry': ['rhyme', 'rhythm', 'stanzas', 'imagery']
        }


def create_reading_reasoner(curriculum_manager=None) -> ReadingReasoner:
    """
    Convenience function to create a ReadingReasoner instance.

    Args:
        curriculum_manager: Optional CurriculumManager instance

    Returns:
        Initialized ReadingReasoner instance
    """
    return ReadingReasoner(curriculum_manager)


# Example usage
if __name__ == "__main__":
    reasoner = create_reading_reasoner()

    print("=== Reading Reasoning Module ===\n")

    # Example passage
    passage = """
    Sarah loved to read books. Every day after school, she would sit under
    the big oak tree in her backyard and read for hours. Her favorite books
    were adventure stories about brave heroes. Sarah dreamed that one day
    she would have her own adventure.
    """

    # Example 1: Analyze passage
    print("--- Example 1: Passage Analysis ---")
    analysis = reasoner.analyze_passage(passage, grade_level="3")
    print(f"Text Type: {analysis['text_type']}")
    print(f"Reading Level: {analysis['reading_level']}")
    print(f"Themes: {', '.join(analysis['themes'])}")
    print()

    # Example 2: Identify main idea
    print("--- Example 2: Main Idea Guidance ---")
    main_idea = reasoner.identify_main_idea(passage, student_age=8)
    print("Guiding Questions:")
    for q in main_idea['guiding_questions']:
        print(f"  - {q}")
    print()

    # Example 3: Vocabulary explanation
    print("--- Example 3: Vocabulary Support ---")
    vocab = reasoner.explain_vocabulary(
        word="adventure",
        context_sentence="Her favorite books were adventure stories.",
        student_age=8
    )
    print(f"Word: {vocab.word}")
    print(f"Student-Friendly: {vocab.student_friendly_definition}")
    print()

    # Example 4: Reading strategy suggestion
    print("--- Example 4: Strategy Suggestion ---")
    strategy = reasoner.suggest_reading_strategy(
        passage=passage,
        difficulty_area="main_idea",
        student_age=8
    )
    print(f"Strategy: {strategy['strategy_name']}")
    print(f"Description: {strategy['description']}")
    print()

    print("=== Reading Reasoner Ready ===")
