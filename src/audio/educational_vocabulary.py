"""
Educational Vocabulary Support for EduLens

Provides subject-specific vocabulary lists, term boosting, and educational
context handling for improved recognition of academic terminology.

Covers common educational vocabulary for elementary students (grades 1-6)
across mathematics, science, reading, and general academic terms.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


class Subject(Enum):
    """Academic subject areas."""

    MATHEMATICS = "mathematics"
    SCIENCE = "science"
    READING = "reading"
    WRITING = "writing"
    SOCIAL_STUDIES = "social_studies"
    GENERAL = "general"


class GradeLevel(Enum):
    """Grade level ranges."""

    GRADE_1_2 = "1-2"
    GRADE_3_4 = "3-4"
    GRADE_5_6 = "5-6"
    ALL = "all"


@dataclass
class VocabularyTerm:
    """Educational vocabulary term with metadata."""

    term: str  # The term itself
    subject: Subject  # Subject area
    grade_level: GradeLevel  # Appropriate grade level
    spoken_forms: List[str] = field(default_factory=list)  # Alternate pronunciations
    phonetic_variants: List[str] = field(default_factory=list)  # Pronunciation variants
    context_hints: List[str] = field(default_factory=list)  # Related terms
    boost_weight: float = 1.0  # Boosting weight (higher = more boost)


# Mathematics Vocabulary
MATH_VOCABULARY = {
    # Numbers and counting
    "numbers": [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
    ],
    # Operations
    "operations": [
        "add",
        "addition",
        "plus",
        "sum",
        "total",
        "subtract",
        "subtraction",
        "minus",
        "difference",
        "take away",
        "multiply",
        "multiplication",
        "times",
        "product",
        "divide",
        "division",
        "divided by",
        "quotient",
        "split",
        "equals",
        "equal to",
        "is",
        "makes",
    ],
    # Fractions and decimals
    "fractions": [
        "fraction",
        "numerator",
        "denominator",
        "whole",
        "part",
        "half",
        "halves",
        "third",
        "thirds",
        "quarter",
        "quarters",
        "fourth",
        "fourths",
        "fifth",
        "fifths",
        "sixth",
        "sixths",
        "eighth",
        "eighths",
        "tenth",
        "tenths",
        "decimal",
        "decimal point",
        "hundredth",
        "thousandth",
        "percent",
        "percentage",
    ],
    # Geometry
    "geometry": [
        "shape",
        "shapes",
        "circle",
        "square",
        "rectangle",
        "triangle",
        "oval",
        "diamond",
        "pentagon",
        "hexagon",
        "octagon",
        "polygon",
        "side",
        "sides",
        "corner",
        "corners",
        "angle",
        "angles",
        "vertex",
        "vertices",
        "line",
        "lines",
        "straight",
        "curved",
        "parallel",
        "perpendicular",
        "symmetry",
        "symmetric",
        "congruent",
        "perimeter",
        "area",
        "volume",
        "length",
        "width",
        "height",
        "depth",
        "radius",
        "diameter",
        "circumference",
    ],
    # Measurement
    "measurement": [
        "measure",
        "measurement",
        "unit",
        "units",
        "inch",
        "inches",
        "foot",
        "feet",
        "yard",
        "yards",
        "mile",
        "miles",
        "centimeter",
        "centimeters",
        "meter",
        "meters",
        "kilometer",
        "kilometers",
        "ounce",
        "ounces",
        "pound",
        "pounds",
        "ton",
        "tons",
        "gram",
        "grams",
        "kilogram",
        "kilograms",
        "cup",
        "cups",
        "pint",
        "pints",
        "quart",
        "quarts",
        "gallon",
        "gallons",
        "liter",
        "liters",
        "milliliter",
        "milliliters",
        "time",
        "hour",
        "hours",
        "minute",
        "minutes",
        "second",
        "seconds",
        "temperature",
        "degree",
        "degrees",
        "Fahrenheit",
        "Celsius",
    ],
    # Data and statistics
    "data": [
        "data",
        "graph",
        "chart",
        "table",
        "diagram",
        "bar graph",
        "line graph",
        "pie chart",
        "pictograph",
        "average",
        "mean",
        "median",
        "mode",
        "range",
        "probability",
        "likely",
        "unlikely",
        "certain",
        "impossible",
    ],
    # Problem solving
    "problem_solving": [
        "problem",
        "solve",
        "solution",
        "answer",
        "question",
        "calculate",
        "computation",
        "estimate",
        "round",
        "approximate",
        "pattern",
        "patterns",
        "sequence",
        "order",
        "compare",
        "greater than",
        "less than",
        "more than",
        "fewer than",
        "equal",
        "same",
        "different",
    ],
}

# Science Vocabulary
SCIENCE_VOCABULARY = {
    # Life science
    "life_science": [
        "living",
        "non-living",
        "alive",
        "life",
        "organism",
        "organisms",
        "plant",
        "plants",
        "animal",
        "animals",
        "human",
        "humans",
        "habitat",
        "environment",
        "ecosystem",
        "food chain",
        "predator",
        "prey",
        "herbivore",
        "carnivore",
        "omnivore",
        "adaptation",
        "camouflage",
        "migration",
        "hibernation",
        "growth",
        "reproduction",
        "life cycle",
        "cell",
        "cells",
        "tissue",
        "organ",
        "system",
    ],
    # Physical science
    "physical_science": [
        "matter",
        "solid",
        "liquid",
        "gas",
        "plasma",
        "property",
        "properties",
        "mass",
        "weight",
        "density",
        "atom",
        "atoms",
        "molecule",
        "molecules",
        "element",
        "elements",
        "force",
        "forces",
        "motion",
        "speed",
        "velocity",
        "acceleration",
        "gravity",
        "friction",
        "magnetism",
        "magnetic",
        "energy",
        "kinetic",
        "potential",
        "thermal",
        "heat",
        "sound",
        "light",
        "wave",
        "waves",
        "frequency",
        "amplitude",
        "electricity",
        "electric",
        "circuit",
        "conductor",
        "insulator",
    ],
    # Earth science
    "earth_science": [
        "Earth",
        "planet",
        "planets",
        "solar system",
        "sun",
        "moon",
        "star",
        "stars",
        "rock",
        "rocks",
        "mineral",
        "minerals",
        "soil",
        "sand",
        "clay",
        "water",
        "ocean",
        "sea",
        "lake",
        "river",
        "stream",
        "weather",
        "climate",
        "temperature",
        "precipitation",
        "rain",
        "snow",
        "sleet",
        "hail",
        "wind",
        "cloud",
        "clouds",
        "season",
        "seasons",
        "summer",
        "winter",
        "spring",
        "fall",
        "autumn",
        "erosion",
        "weathering",
        "sediment",
        "fossil",
        "fossils",
        "volcano",
        "earthquake",
        "mountain",
        "valley",
        "canyon",
    ],
    # Scientific method
    "scientific_method": [
        "science",
        "scientist",
        "experiment",
        "observe",
        "observation",
        "hypothesis",
        "predict",
        "prediction",
        "test",
        "measure",
        "measurement",
        "data",
        "result",
        "results",
        "conclude",
        "conclusion",
        "evidence",
        "variable",
        "control",
        "fair test",
    ],
    # Tools and equipment
    "tools": [
        "microscope",
        "telescope",
        "magnifying glass",
        "thermometer",
        "ruler",
        "scale",
        "balance",
        "beaker",
        "flask",
        "test tube",
        "magnet",
        "compass",
        "timer",
    ],
}

# Reading/Language Arts Vocabulary
READING_VOCABULARY = {
    # Literary terms
    "literary_terms": [
        "story",
        "book",
        "chapter",
        "paragraph",
        "sentence",
        "word",
        "letter",
        "title",
        "author",
        "illustrator",
        "character",
        "characters",
        "setting",
        "plot",
        "problem",
        "solution",
        "theme",
        "beginning",
        "middle",
        "end",
        "first",
        "next",
        "then",
        "last",
        "finally",
        "fiction",
        "non-fiction",
        "fantasy",
        "realistic",
        "poem",
        "poetry",
        "rhyme",
        "rhythm",
        "stanza",
        "verse",
    ],
    # Reading skills
    "reading_skills": [
        "read",
        "reading",
        "decode",
        "comprehend",
        "understand",
        "predict",
        "infer",
        "summarize",
        "retell",
        "main idea",
        "detail",
        "details",
        "fact",
        "opinion",
        "cause",
        "effect",
        "compare",
        "contrast",
        "sequence",
        "visualize",
        "imagine",
        "picture",
    ],
    # Phonics
    "phonics": [
        "phonics",
        "sound",
        "sounds",
        "letter sound",
        "blend",
        "digraph",
        "vowel",
        "vowels",
        "consonant",
        "consonants",
        "short vowel",
        "long vowel",
        "silent e",
        "syllable",
        "syllables",
        "prefix",
        "suffix",
        "root word",
    ],
    # Parts of speech
    "grammar": [
        "noun",
        "verb",
        "adjective",
        "adverb",
        "pronoun",
        "sentence",
        "statement",
        "question",
        "exclamation",
        "command",
        "capital",
        "capitalize",
        "period",
        "comma",
        "quotation marks",
        "singular",
        "plural",
        "past tense",
        "present tense",
        "future tense",
    ],
}

# General Academic Vocabulary
GENERAL_VOCABULARY = [
    "example",
    "explain",
    "describe",
    "define",
    "identify",
    "compare",
    "contrast",
    "analyze",
    "evaluate",
    "because",
    "therefore",
    "however",
    "although",
    "instead",
    "first",
    "second",
    "third",
    "next",
    "finally",
    "important",
    "main",
    "key",
    "significant",
    "similar",
    "different",
    "same",
    "opposite",
    "increase",
    "decrease",
    "change",
    "remain",
    "correct",
    "incorrect",
    "true",
    "false",
    "yes",
    "no",
]

# Spoken form variations for math symbols and operations
MATH_SPOKEN_FORMS = {
    "+": ["plus", "add", "and"],
    "-": ["minus", "subtract", "take away"],
    "×": ["times", "multiply", "multiplied by"],
    "÷": ["divided by", "divide"],
    "=": ["equals", "is", "is equal to"],
    "<": ["less than", "is less than"],
    ">": ["greater than", "is greater than"],
    "≤": ["less than or equal to"],
    "≥": ["greater than or equal to"],
    "≠": ["not equal to", "does not equal"],
    "²": ["squared", "to the power of two"],
    "³": ["cubed", "to the power of three"],
    "½": ["one half", "a half"],
    "¼": ["one quarter", "a quarter"],
    "¾": ["three quarters"],
    "%": ["percent"],
}


class EducationalVocabulary:
    """
    Manager for educational vocabulary and term boosting.

    Provides methods to load, manage, and boost educational vocabulary
    for improved ASR recognition.
    """

    def __init__(self):
        """Initialize educational vocabulary manager."""
        self.vocabulary: Dict[Subject, Set[str]] = {
            Subject.MATHEMATICS: self._build_math_vocabulary(),
            Subject.SCIENCE: self._build_science_vocabulary(),
            Subject.READING: self._build_reading_vocabulary(),
            Subject.GENERAL: set(GENERAL_VOCABULARY),
        }

        self.spoken_forms = MATH_SPOKEN_FORMS.copy()

        logger.info("Initialized EducationalVocabulary")

    def _build_math_vocabulary(self) -> Set[str]:
        """Build complete mathematics vocabulary set."""
        vocab = set()
        for category_terms in MATH_VOCABULARY.values():
            vocab.update(category_terms)
        return vocab

    def _build_science_vocabulary(self) -> Set[str]:
        """Build complete science vocabulary set."""
        vocab = set()
        for category_terms in SCIENCE_VOCABULARY.values():
            vocab.update(category_terms)
        return vocab

    def _build_reading_vocabulary(self) -> Set[str]:
        """Build complete reading vocabulary set."""
        vocab = set()
        for category_terms in READING_VOCABULARY.values():
            vocab.update(category_terms)
        return vocab

    def get_vocabulary(
        self,
        subjects: Optional[List[Subject]] = None,
        grade_level: Optional[GradeLevel] = None,
    ) -> List[str]:
        """
        Get vocabulary for specified subjects and grade level.

        Args:
            subjects: List of subjects to include (all if None)
            grade_level: Grade level filter (all if None)

        Returns:
            List of vocabulary terms
        """
        if subjects is None:
            subjects = [Subject.MATHEMATICS, Subject.SCIENCE, Subject.READING, Subject.GENERAL]

        vocab = set()
        for subject in subjects:
            if subject in self.vocabulary:
                vocab.update(self.vocabulary[subject])

        return sorted(list(vocab))

    def get_subject_vocabulary(self, subject: Subject) -> List[str]:
        """
        Get vocabulary for a specific subject.

        Args:
            subject: Subject area

        Returns:
            List of vocabulary terms for the subject
        """
        return sorted(list(self.vocabulary.get(subject, set())))

    def get_math_vocabulary(self, category: Optional[str] = None) -> List[str]:
        """
        Get mathematics vocabulary, optionally filtered by category.

        Args:
            category: Math category (operations, fractions, geometry, etc.)

        Returns:
            List of math vocabulary terms
        """
        if category and category in MATH_VOCABULARY:
            return MATH_VOCABULARY[category].copy()
        return sorted(list(self.vocabulary[Subject.MATHEMATICS]))

    def get_science_vocabulary(self, category: Optional[str] = None) -> List[str]:
        """
        Get science vocabulary, optionally filtered by category.

        Args:
            category: Science category (life_science, physical_science, etc.)

        Returns:
            List of science vocabulary terms
        """
        if category and category in SCIENCE_VOCABULARY:
            return SCIENCE_VOCABULARY[category].copy()
        return sorted(list(self.vocabulary[Subject.SCIENCE]))

    def get_reading_vocabulary(self, category: Optional[str] = None) -> List[str]:
        """
        Get reading vocabulary, optionally filtered by category.

        Args:
            category: Reading category (literary_terms, phonics, etc.)

        Returns:
            List of reading vocabulary terms
        """
        if category and category in READING_VOCABULARY:
            return READING_VOCABULARY[category].copy()
        return sorted(list(self.vocabulary[Subject.READING]))

    def get_spoken_forms(self, symbol: str) -> List[str]:
        """
        Get spoken forms for a math symbol.

        Args:
            symbol: Mathematical symbol

        Returns:
            List of spoken forms
        """
        return self.spoken_forms.get(symbol, [])

    def add_custom_vocabulary(self, subject: Subject, terms: List[str]) -> None:
        """
        Add custom vocabulary terms.

        Args:
            subject: Subject area
            terms: List of terms to add
        """
        if subject not in self.vocabulary:
            self.vocabulary[subject] = set()

        self.vocabulary[subject].update(terms)
        logger.info(f"Added {len(terms)} custom terms to {subject.value}")

    def load_vocabulary_from_file(self, file_path: Path, subject: Subject) -> None:
        """
        Load vocabulary from a YAML or text file.

        Args:
            file_path: Path to vocabulary file
            subject: Subject area for the vocabulary
        """
        try:
            if file_path.suffix in [".yaml", ".yml"]:
                with open(file_path, "r") as f:
                    data = yaml.safe_load(f)
                    terms = data.get("vocabulary", [])
            else:
                # Plain text file, one term per line
                with open(file_path, "r") as f:
                    terms = [line.strip() for line in f if line.strip()]

            self.add_custom_vocabulary(subject, terms)
            logger.info(f"Loaded vocabulary from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load vocabulary from {file_path}: {e}")

    def create_boost_prompt(
        self,
        subjects: Optional[List[Subject]] = None,
        max_terms: int = 50,
    ) -> str:
        """
        Create a vocabulary boost prompt for ASR.

        This prompt can be used as initial_prompt in Whisper to bias
        recognition toward educational vocabulary.

        Args:
            subjects: Subjects to include in prompt
            max_terms: Maximum number of terms in prompt

        Returns:
            Prompt string with educational vocabulary
        """
        vocab = self.get_vocabulary(subjects)

        # Sample terms if too many
        if len(vocab) > max_terms:
            import random

            vocab = random.sample(vocab, max_terms)

        # Create prompt
        prompt = "Educational terms: " + ", ".join(vocab)
        return prompt

    def is_educational_term(self, word: str, subject: Optional[Subject] = None) -> bool:
        """
        Check if a word is an educational term.

        Args:
            word: Word to check
            subject: Optional subject to check within

        Returns:
            True if word is an educational term
        """
        word_lower = word.lower()

        if subject:
            return word_lower in self.vocabulary.get(subject, set())
        else:
            # Check all subjects
            for vocab_set in self.vocabulary.values():
                if word_lower in vocab_set:
                    return True
            return False

    def suggest_corrections(self, word: str, subject: Optional[Subject] = None) -> List[str]:
        """
        Suggest educational vocabulary corrections for a word.

        Uses simple string similarity to suggest corrections.

        Args:
            word: Potentially misspelled word
            subject: Optional subject to search within

        Returns:
            List of suggested corrections
        """
        word_lower = word.lower()

        # Get vocabulary to search
        if subject:
            vocab = self.vocabulary.get(subject, set())
        else:
            vocab = set()
            for v in self.vocabulary.values():
                vocab.update(v)

        # Find similar words (simple edit distance)
        suggestions = []
        for term in vocab:
            if self._string_similarity(word_lower, term) > 0.7:
                suggestions.append(term)

        return sorted(
            suggestions, key=lambda x: self._string_similarity(word_lower, x), reverse=True
        )[:5]

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity (0.0 to 1.0)."""
        if s1 == s2:
            return 1.0

        # Simple character overlap similarity
        set1 = set(s1)
        set2 = set(s2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0


class VocabularyContextManager:
    """
    Manages vocabulary context for different learning scenarios.

    Provides dynamic vocabulary selection based on current educational
    context (e.g., math lesson, science experiment, reading session).
    """

    def __init__(self):
        """Initialize vocabulary context manager."""
        self.vocab_manager = EducationalVocabulary()
        self.current_context: Optional[Subject] = None
        self.context_history: List[Subject] = []

        logger.info("Initialized VocabularyContextManager")

    def set_context(self, subject: Subject) -> None:
        """
        Set current educational context.

        Args:
            subject: Current subject being studied
        """
        self.current_context = subject
        self.context_history.append(subject)
        logger.info(f"Set vocabulary context to: {subject.value}")

    def get_context_vocabulary(self, max_terms: int = 100) -> List[str]:
        """
        Get vocabulary for current context.

        Args:
            max_terms: Maximum number of terms to return

        Returns:
            List of contextually relevant vocabulary
        """
        if not self.current_context:
            # No context, return general vocabulary
            return self.vocab_manager.get_vocabulary()[:max_terms]

        # Get context-specific vocabulary
        vocab = self.vocab_manager.get_subject_vocabulary(self.current_context)

        # Add general academic vocabulary
        general = self.vocab_manager.get_subject_vocabulary(Subject.GENERAL)
        vocab.extend(general)

        return vocab[:max_terms]

    def create_context_prompt(self) -> str:
        """
        Create vocabulary prompt based on current context.

        Returns:
            Context-appropriate vocabulary prompt
        """
        if not self.current_context:
            return ""

        subjects = [self.current_context, Subject.GENERAL]
        return self.vocab_manager.create_boost_prompt(subjects)

    def clear_context(self) -> None:
        """Clear current context."""
        self.current_context = None
        logger.info("Cleared vocabulary context")
