"""
EduLens Pronunciation Rules Engine

Handles specialized pronunciation for educational content including:
- Mathematical symbols and expressions
- Scientific terminology
- Technical vocabulary
- Number and equation reading
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Pattern
import logging


logger = logging.getLogger(__name__)


@dataclass
class PronunciationRule:
    """Single pronunciation rule"""
    pattern: str
    replacement: str
    context: Optional[str] = None  # Optional context requirement
    priority: int = 0  # Higher priority rules applied first


class MathPronunciationEngine:
    """
    Converts mathematical expressions to speakable text

    Handles:
    - Basic operators (+, -, ×, ÷, =)
    - Fractions
    - Exponents
    - Equations
    - Special symbols
    """

    def __init__(self):
        self.symbol_map = self._create_symbol_map()
        self.operator_pronunciations = self._create_operator_pronunciations()
        self.rules: List[PronunciationRule] = []
        self._initialize_rules()

    def _create_symbol_map(self) -> Dict[str, str]:
        """Create mathematical symbol to pronunciation mapping"""
        return {
            '+': 'plus',
            '-': 'minus',
            '−': 'minus',  # Unicode minus
            '×': 'times',
            '*': 'times',
            '÷': 'divided by',
            '/': 'divided by',
            '=': 'equals',
            '≠': 'does not equal',
            '<': 'is less than',
            '>': 'is greater than',
            '≤': 'is less than or equal to',
            '≥': 'is greater than or equal to',
            '√': 'square root of',
            '∛': 'cube root of',
            '²': 'squared',
            '³': 'cubed',
            '∞': 'infinity',
            'π': 'pi',
            '°': 'degrees',
            '%': 'percent',
            '±': 'plus or minus',
            '∑': 'sum of',
            '∏': 'product of',
            '∫': 'integral of',
            '∂': 'partial derivative of',
            '∆': 'delta',
            'Δ': 'delta',
            '≈': 'approximately equals',
            '∈': 'is an element of',
            '∉': 'is not an element of',
            '⊂': 'is a subset of',
            '⊃': 'is a superset of',
            '∪': 'union',
            '∩': 'intersection',
            '∅': 'empty set',
        }

    def _create_operator_pronunciations(self) -> Dict[str, List[str]]:
        """Create context-aware operator pronunciations"""
        return {
            '+': ['plus', 'add', 'and'],
            '-': ['minus', 'subtract', 'take away'],
            '×': ['times', 'multiplied by'],
            '÷': ['divided by', 'over'],
            '=': ['equals', 'is equal to', 'is']
        }

    def _initialize_rules(self):
        """Initialize pronunciation rules in priority order"""

        # Fractions (e.g., 1/2 -> "one half")
        self.rules.append(PronunciationRule(
            pattern=r'(\d+)/(\d+)',
            replacement=self._format_fraction,
            priority=100
        ))

        # Exponents (e.g., x² -> "x squared", x³ -> "x cubed")
        self.rules.append(PronunciationRule(
            pattern=r'(\w+)²',
            replacement=r'\1 squared',
            priority=90
        ))
        self.rules.append(PronunciationRule(
            pattern=r'(\w+)³',
            replacement=r'\1 cubed',
            priority=90
        ))

        # General exponents (e.g., x^2 -> "x to the power of 2")
        self.rules.append(PronunciationRule(
            pattern=r'(\w+)\^(\d+)',
            replacement=r'\1 to the power of \2',
            priority=85
        ))

        # Decimals (e.g., 3.14 -> "three point one four")
        self.rules.append(PronunciationRule(
            pattern=r'(\d+)\.(\d+)',
            replacement=self._format_decimal,
            priority=80
        ))

        # Negative numbers (e.g., -5 -> "negative five")
        self.rules.append(PronunciationRule(
            pattern=r'-(\d+)',
            replacement=r'negative \1',
            priority=75
        ))

        # Parentheses
        self.rules.append(PronunciationRule(
            pattern=r'\(',
            replacement='open parenthesis',
            priority=50
        ))
        self.rules.append(PronunciationRule(
            pattern=r'\)',
            replacement='close parenthesis',
            priority=50
        ))

        # Brackets
        self.rules.append(PronunciationRule(
            pattern=r'\[',
            replacement='open bracket',
            priority=50
        ))
        self.rules.append(PronunciationRule(
            pattern=r'\]',
            replacement='close bracket',
            priority=50
        ))

    def convert_expression(self, expression: str, verbose: bool = True) -> str:
        """
        Convert mathematical expression to speakable text

        Args:
            expression: Mathematical expression
            verbose: Use verbose pronunciations

        Returns:
            Speakable text
        """
        result = expression

        # Apply rules in priority order
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        for rule in sorted_rules:
            if callable(rule.replacement):
                # Custom function replacement
                result = re.sub(rule.pattern, rule.replacement, result)
            else:
                # Simple string replacement
                result = re.sub(rule.pattern, rule.replacement, result)

        # Replace mathematical symbols
        for symbol, pronunciation in self.symbol_map.items():
            result = result.replace(symbol, f' {pronunciation} ')

        # Clean up spacing
        result = re.sub(r'\s+', ' ', result).strip()

        # Convert numbers to words for better pronunciation
        if verbose:
            result = self._numbers_to_words(result)

        return result

    def _format_fraction(self, match: re.Match) -> str:
        """Format fraction as words"""
        numerator = int(match.group(1))
        denominator = int(match.group(2))

        # Special cases
        if numerator == 1 and denominator == 2:
            return "one half"
        elif numerator == 1 and denominator == 3:
            return "one third"
        elif numerator == 1 and denominator == 4:
            return "one quarter"
        elif numerator == 3 and denominator == 4:
            return "three quarters"

        # General fraction
        num_word = self._number_to_word(numerator)
        denom_word = self._ordinal_to_word(denominator)

        if numerator == 1:
            return f"{num_word} {denom_word}"
        else:
            return f"{num_word} {denom_word}s"

    def _format_decimal(self, match: re.Match) -> str:
        """Format decimal as words"""
        integer_part = match.group(1)
        decimal_part = match.group(2)

        # Read decimal digits individually
        decimal_words = ' '.join(self._number_to_word(int(d)) for d in decimal_part)

        return f"{self._number_to_word(int(integer_part))} point {decimal_words}"

    def _numbers_to_words(self, text: str) -> str:
        """Convert standalone numbers to words"""
        def replace_number(match):
            number = int(match.group(0))
            return self._number_to_word(number)

        # Replace standalone numbers
        return re.sub(r'\b\d+\b', replace_number, text)

    def _number_to_word(self, n: int) -> str:
        """Convert number to word (0-999)"""
        if n < 0:
            return f"negative {self._number_to_word(-n)}"

        if n == 0:
            return "zero"

        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                 "sixteen", "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        if n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        elif n < 1000:
            return (ones[n // 100] + " hundred" +
                    (" and " + self._number_to_word(n % 100) if n % 100 else ""))
        else:
            return str(n)  # Fallback for large numbers

    def _ordinal_to_word(self, n: int) -> str:
        """Convert number to ordinal word (first, second, etc.)"""
        ordinals = {
            1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
            11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
            15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
            19: "nineteenth", 20: "twentieth"
        }

        if n in ordinals:
            return ordinals[n]
        else:
            # For larger numbers, use "nth" form
            return f"{self._number_to_word(n)}th"


class SciencePronunciationEngine:
    """
    Handles pronunciation of scientific terms

    Includes:
    - Chemical formulas
    - Scientific notation
    - Units of measurement
    - Technical terminology
    """

    def __init__(self):
        self.element_names = self._create_element_names()
        self.unit_pronunciations = self._create_unit_pronunciations()
        self.term_overrides = self._create_term_overrides()

    def _create_element_names(self) -> Dict[str, str]:
        """Chemical element symbol to name mapping"""
        return {
            'H': 'Hydrogen', 'He': 'Helium', 'Li': 'Lithium', 'Be': 'Beryllium',
            'B': 'Boron', 'C': 'Carbon', 'N': 'Nitrogen', 'O': 'Oxygen',
            'F': 'Fluorine', 'Ne': 'Neon', 'Na': 'Sodium', 'Mg': 'Magnesium',
            'Al': 'Aluminum', 'Si': 'Silicon', 'P': 'Phosphorus', 'S': 'Sulfur',
            'Cl': 'Chlorine', 'Ar': 'Argon', 'K': 'Potassium', 'Ca': 'Calcium',
            'Fe': 'Iron', 'Cu': 'Copper', 'Zn': 'Zinc', 'Ag': 'Silver',
            'Au': 'Gold', 'Hg': 'Mercury', 'Pb': 'Lead'
        }

    def _create_unit_pronunciations(self) -> Dict[str, str]:
        """Unit abbreviation to pronunciation mapping"""
        return {
            'm': 'meters',
            'cm': 'centimeters',
            'mm': 'millimeters',
            'km': 'kilometers',
            'g': 'grams',
            'kg': 'kilograms',
            'mg': 'milligrams',
            'L': 'liters',
            'mL': 'milliliters',
            's': 'seconds',
            'min': 'minutes',
            'h': 'hours',
            'N': 'newtons',
            'J': 'joules',
            'W': 'watts',
            'V': 'volts',
            'A': 'amperes',
            'Ω': 'ohms',
            '°C': 'degrees Celsius',
            '°F': 'degrees Fahrenheit',
            'K': 'kelvin',
            'Pa': 'pascals',
            'Hz': 'hertz',
            'mol': 'moles'
        }

    def _create_term_overrides(self) -> Dict[str, str]:
        """Override pronunciations for tricky scientific terms"""
        return {
            # Biology
            'mitochondria': 'my-toe-CON-dree-uh',
            'photosynthesis': 'foe-toe-SIN-the-sis',
            'chromosome': 'CHROME-uh-soam',

            # Chemistry
            'molecule': 'MOL-uh-kyool',
            'atom': 'AT-um',
            'isotope': 'EYE-so-tope',

            # Physics
            'velocity': 'veh-LOS-ih-tee',
            'acceleration': 'ak-sell-er-AY-shun',
            'momentum': 'moe-MEN-tum',

            # Astronomy
            'galaxy': 'GAL-ack-see',
            'nebula': 'NEB-yoo-luh',
            'asteroid': 'ASS-ter-oid'
        }

    def convert_formula(self, formula: str) -> str:
        """
        Convert chemical formula to speakable text

        Args:
            formula: Chemical formula (e.g., "H2O", "CO2")

        Returns:
            Speakable text
        """
        result = []
        i = 0

        while i < len(formula):
            # Check for element symbol (1-2 characters)
            if i + 1 < len(formula) and formula[i:i+2] in self.element_names:
                element = formula[i:i+2]
                result.append(self.element_names[element])
                i += 2
            elif formula[i] in self.element_names:
                element = formula[i]
                result.append(self.element_names[element])
                i += 1
            # Check for subscript numbers
            elif formula[i].isdigit():
                # Read subscript
                num = ''
                while i < len(formula) and formula[i].isdigit():
                    num += formula[i]
                    i += 1
                if int(num) > 1:
                    result.append(f"with {num} atoms" if len(result) > 0 else num)
            else:
                i += 1

        return ' '.join(result)

    def convert_scientific_notation(self, notation: str) -> str:
        """
        Convert scientific notation to speakable text

        Args:
            notation: Scientific notation (e.g., "3.14e8")

        Returns:
            Speakable text
        """
        match = re.match(r'([\d.]+)e([+-]?\d+)', notation.lower())
        if match:
            coefficient = match.group(1)
            exponent = match.group(2)

            return f"{coefficient} times ten to the power of {exponent}"

        return notation

    def pronounce_term(self, term: str) -> str:
        """
        Get pronunciation for scientific term

        Args:
            term: Scientific term

        Returns:
            Pronunciation guide or original term
        """
        return self.term_overrides.get(term.lower(), term)

    def convert_measurement(self, measurement: str) -> str:
        """
        Convert measurement to speakable text

        Args:
            measurement: Measurement (e.g., "5 km", "3.2 g")

        Returns:
            Speakable text
        """
        match = re.match(r'([\d.]+)\s*([a-zA-Z°Ω]+)', measurement)
        if match:
            value = match.group(1)
            unit = match.group(2)

            unit_text = self.unit_pronunciations.get(unit, unit)
            return f"{value} {unit_text}"

        return measurement


class PhoneticOverrideEngine:
    """
    Handles phonetic overrides for tricky words

    Uses phonetic spelling hints to improve pronunciation
    """

    def __init__(self):
        self.overrides: Dict[str, str] = {}
        self._initialize_common_overrides()

    def _initialize_common_overrides(self):
        """Initialize common pronunciation overrides"""
        self.overrides.update({
            # Common mispronunciations
            'often': 'OFF-en',  # Not OFF-ten
            'nuclear': 'NEW-klee-er',
            'mischievous': 'MISS-chuh-vuss',

            # Educational terms
            'algorithm': 'AL-go-rith-um',
            'arithmetic': 'uh-RITH-meh-tick',
            'geometry': 'jee-AH-meh-tree',

            # Tricky words for kids
            'colonel': 'KER-nul',
            'queue': 'KYOO',
            'recipe': 'RESS-uh-pee',

            # Numbers
            'eighth': 'AYTTH',
            'twelfth': 'TWELFTH',
        })

    def add_override(self, word: str, pronunciation: str):
        """Add custom pronunciation override"""
        self.overrides[word.lower()] = pronunciation
        logger.info(f"Added pronunciation override: {word} -> {pronunciation}")

    def get_override(self, word: str) -> Optional[str]:
        """Get pronunciation override for word"""
        return self.overrides.get(word.lower())

    def apply_overrides(self, text: str) -> str:
        """
        Apply phonetic overrides to text

        Args:
            text: Original text

        Returns:
            Text with overrides applied
        """
        words = text.split()
        result = []

        for word in words:
            # Remove punctuation for lookup
            clean_word = re.sub(r'[^\w]', '', word.lower())
            override = self.get_override(clean_word)

            if override:
                # Preserve original punctuation
                if word[-1] in '.!?,;:':
                    result.append(override + word[-1])
                else:
                    result.append(override)
            else:
                result.append(word)

        return ' '.join(result)


class PronunciationRulesEngine:
    """
    Main pronunciation rules engine

    Combines all pronunciation engines for comprehensive
    educational content pronunciation.
    """

    def __init__(self):
        self.math_engine = MathPronunciationEngine()
        self.science_engine = SciencePronunciationEngine()
        self.phonetic_engine = PhoneticOverrideEngine()

    def process_text(
        self,
        text: str,
        context: Optional[str] = None
    ) -> str:
        """
        Process text with appropriate pronunciation rules

        Args:
            text: Text to process
            context: Context hint (math, science, general)

        Returns:
            Processed text with pronunciation rules applied
        """
        result = text

        # Apply context-specific rules
        if context == 'math':
            result = self.math_engine.convert_expression(result)
        elif context == 'science':
            # Convert scientific notation
            result = re.sub(
                r'[\d.]+e[+-]?\d+',
                lambda m: self.science_engine.convert_scientific_notation(m.group(0)),
                result
            )
            # Convert measurements
            result = re.sub(
                r'[\d.]+\s*[a-zA-Z°Ω]+',
                lambda m: self.science_engine.convert_measurement(m.group(0)),
                result
            )

        # Apply phonetic overrides
        result = self.phonetic_engine.apply_overrides(result)

        return result

    def add_custom_rule(
        self,
        word: str,
        pronunciation: str,
        context: Optional[str] = None
    ):
        """
        Add custom pronunciation rule

        Args:
            word: Word to override
            pronunciation: Phonetic pronunciation
            context: Optional context (math, science, general)
        """
        self.phonetic_engine.add_override(word, pronunciation)
