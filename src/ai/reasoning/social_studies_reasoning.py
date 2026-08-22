"""
Social Studies Reasoning Module for EduLens AI Agent

This module provides specialized reasoning capabilities for social studies education,
including historical context, geographical understanding, civic concepts, timeline support,
and cultural awareness for K-6 students.

Author: EduLens AI Team
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SocialStudiesDomain(Enum):
    """Social studies subject domains."""

    HISTORY = "history"
    GEOGRAPHY = "geography"
    CIVICS = "civics"
    ECONOMICS = "economics"
    CULTURE = "culture"


class TimelinePeriod(Enum):
    """Historical time periods."""

    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"


class GeographicFeature(Enum):
    """Types of geographic features."""

    LANDFORMS = "landforms"
    WATER_BODIES = "water_bodies"
    CLIMATE = "climate"
    REGIONS = "regions"


@dataclass
class HistoricalContext:
    """Historical context information."""

    event_name: str
    time_period: str
    key_people: List[str]
    important_places: List[str]
    why_significant: str
    connection_to_today: str
    age_appropriate_explanation: str


@dataclass
class GeographicExplanation:
    """Geographic concept explanation."""

    feature_name: str
    definition: str
    visual_description: str
    examples: List[str]
    where_found: List[str]
    importance: str


@dataclass
class CivicConcept:
    """Civic education concept."""

    concept_name: str
    simple_definition: str
    why_it_matters: str
    real_life_examples: List[str]
    student_role: str


class SocialStudiesReasoner:
    """
    Specialized reasoning engine for social studies education.

    Provides historical context, geographic understanding, civic concepts,
    timeline support, and cultural awareness for K-6 students.
    """

    def __init__(self, curriculum_manager=None):
        """
        Initialize the SocialStudiesReasoner.

        Args:
            curriculum_manager: Optional CurriculumManager instance
        """
        self.curriculum_manager = curriculum_manager
        self.historical_periods = self._initialize_historical_periods()
        self.geographic_terms = self._initialize_geographic_terms()
        self.civic_vocabulary = self._initialize_civic_vocabulary()

    def provide_context(
        self, topic: str, domain: SocialStudiesDomain, grade_level: str, student_age: int
    ) -> Dict[str, Any]:
        """
        Provide historical, geographical, or cultural context for a topic.

        Args:
            topic: The topic needing context
            domain: Which domain (history, geography, etc.)
            grade_level: Student's grade level (K-6)
            student_age: Student's age for language level

        Returns:
            Dictionary with comprehensive context:
                - background: Background information
                - key_points: Important points to understand
                - connections: Connections to student's life
                - vocabulary: Important terms
                - guiding_questions: Questions to deepen understanding
        """
        logger.info(f"Providing context for: {topic} ({domain.value})")

        # Generate background information
        background = self._generate_background(topic, domain, student_age)

        # Identify key points
        key_points = self._identify_key_points(topic, domain, grade_level)

        # Create personal connections
        connections = self._create_personal_connections(topic, domain, student_age)

        # Extract important vocabulary
        vocabulary = self._extract_important_vocabulary(topic, domain)

        # Generate guiding questions
        questions = self._generate_context_questions(topic, domain, student_age)

        return {
            "topic": topic,
            "domain": domain.value,
            "background": background,
            "key_points": key_points,
            "connections_to_today": connections,
            "vocabulary": vocabulary,
            "guiding_questions": questions,
            "additional_resources": self._suggest_resources(topic, domain),
        }

    def explain_concepts(
        self,
        concept: str,
        domain: SocialStudiesDomain,
        student_age: int,
        include_examples: bool = True,
    ) -> Dict[str, Any]:
        """
        Explain social studies concepts (civics, economics, geography, history).

        Args:
            concept: The concept to explain
            domain: Which domain the concept belongs to
            student_age: Student's age
            include_examples: Whether to include examples

        Returns:
            Dictionary with concept explanation
        """
        logger.info(f"Explaining concept: {concept}")

        if domain == SocialStudiesDomain.CIVICS:
            return self._explain_civic_concept(concept, student_age, include_examples)
        elif domain == SocialStudiesDomain.GEOGRAPHY:
            return self._explain_geographic_concept(concept, student_age, include_examples)
        elif domain == SocialStudiesDomain.HISTORY:
            return self._explain_historical_concept(concept, student_age, include_examples)
        elif domain == SocialStudiesDomain.ECONOMICS:
            return self._explain_economic_concept(concept, student_age, include_examples)
        else:
            return self._explain_general_concept(concept, student_age, include_examples)

    def analyze_maps(
        self,
        map_description: str,
        map_type: str,
        student_age: int,
        learning_goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Provide map reading assistance and guidance.

        Args:
            map_description: Description of the map
            map_type: Type of map (political, physical, etc.)
            student_age: Student's age
            learning_goal: What student should learn from map

        Returns:
            Dictionary with map analysis guidance:
                - what_to_look_for: Key features to identify
                - map_elements: Important map elements (legend, scale, etc.)
                - questions_to_ask: Questions while reading map
                - interpretation_help: Help understanding the map
                - practice_skills: Map skills to practice
        """
        logger.info(f"Analyzing {map_type} map")

        # Identify key features
        features = self._identify_map_features(map_type, map_description)

        # Explain map elements
        elements = self._explain_map_elements(map_type, student_age)

        # Generate map reading questions
        questions = self._generate_map_questions(map_type, student_age)

        # Provide interpretation help
        interpretation = self._guide_map_interpretation(map_type, map_description, student_age)

        # Identify skills to practice
        skills = self._identify_map_skills(map_type, student_age)

        return {
            "map_type": map_type,
            "what_to_look_for": features,
            "map_elements": elements,
            "questions_to_ask": questions,
            "interpretation_help": interpretation,
            "practice_skills": skills,
            "map_reading_tips": self._get_map_reading_tips(student_age),
        }

    def timeline_support(
        self, events: List[Dict[str, str]], student_age: int, time_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide chronological understanding and timeline support.

        Args:
            events: List of events with 'name' and optionally 'date'
            student_age: Student's age
            time_period: Optional time period context

        Returns:
            Dictionary with timeline support:
                - organized_events: Events in chronological order
                - time_relationships: How events relate in time
                - cause_effect: Cause and effect relationships
                - memory_aids: Ways to remember sequence
                - guiding_questions: Questions about chronology
        """
        logger.info("Providing timeline support")

        # Organize events chronologically
        organized = self._organize_chronologically(events)

        # Identify time relationships
        relationships = self._identify_time_relationships(organized, student_age)

        # Find cause and effect
        cause_effect = self._identify_cause_effect(organized)

        # Create memory aids
        memory_aids = self._create_timeline_memory_aids(organized, student_age)

        # Generate questions
        questions = self._generate_timeline_questions(organized, student_age)

        return {
            "organized_events": organized,
            "time_relationships": relationships,
            "cause_and_effect": cause_effect,
            "memory_aids": memory_aids,
            "guiding_questions": questions,
            "time_concepts": self._explain_time_concepts(student_age),
        }

    def explain_perspectives(
        self, topic: str, student_age: int, grade_level: str
    ) -> Dict[str, Any]:
        """
        Help students understand different perspectives and viewpoints.

        Args:
            topic: The topic or issue
            student_age: Student's age
            grade_level: Student's grade level

        Returns:
            Dictionary with perspective guidance:
                - what_are_perspectives: Explanation of perspectives
                - why_perspectives_matter: Why different views exist
                - questions_to_consider: Questions to understand perspectives
                - empathy_guidance: How to see other viewpoints
                - discussion_prompts: Prompts for thinking about perspectives
        """
        logger.info(f"Explaining perspectives on: {topic}")

        # Explain what perspectives are
        explanation = self._explain_perspectives_concept(student_age)

        # Explain why perspectives matter
        importance = self._explain_perspective_importance(student_age)

        # Generate perspective questions
        questions = self._generate_perspective_questions(topic, student_age)

        # Provide empathy guidance
        empathy = self._create_empathy_guidance(student_age)

        # Create discussion prompts
        prompts = self._create_discussion_prompts(topic, student_age)

        return {
            "what_are_perspectives": explanation,
            "why_perspectives_matter": importance,
            "questions_to_consider": questions,
            "empathy_guidance": empathy,
            "discussion_prompts": prompts,
            "thinking_stems": self._get_perspective_thinking_stems(student_age),
        }

    def community_connections(
        self, concept: str, student_age: int, grade_level: str
    ) -> Dict[str, Any]:
        """
        Connect social studies concepts to student's community and life.

        Args:
            concept: The concept to connect
            student_age: Student's age
            grade_level: Student's grade level

        Returns:
            Dictionary with community connections:
                - in_my_community: How concept appears locally
                - in_my_life: Personal connections
                - people_who_help: Community helpers related to concept
                - ways_to_participate: How students can be involved
                - observation_activities: What to observe in community
        """
        logger.info(f"Creating community connections for: {concept}")

        # Community examples
        community_examples = self._find_community_examples(concept, student_age)

        # Personal connections
        personal = self._create_personal_life_connections(concept, student_age)

        # Identify relevant community helpers
        helpers = self._identify_community_helpers(concept)

        # Suggest participation opportunities
        participation = self._suggest_participation(concept, student_age)

        # Create observation activities
        observations = self._create_observation_activities(concept, student_age)

        return {
            "in_my_community": community_examples,
            "in_my_life": personal,
            "people_who_help": helpers,
            "ways_to_participate": participation,
            "observation_activities": observations,
            "discussion_questions": self._create_community_questions(concept, student_age),
        }

    def explain_historical_significance(
        self, event: str, student_age: int, grade_level: str
    ) -> HistoricalContext:
        """
        Explain the historical significance of an event.

        Args:
            event: The historical event
            student_age: Student's age
            grade_level: Student's grade level

        Returns:
            HistoricalContext object with event information
        """
        logger.info(f"Explaining historical significance: {event}")

        # Determine time period
        time_period = self._identify_time_period(event)

        # Identify key people
        key_people = self._identify_key_people(event)

        # Identify important places
        places = self._identify_important_places(event)

        # Explain significance
        significance = self._explain_significance(event, student_age)

        # Connect to today
        connection = self._connect_to_present(event, student_age)

        # Create age-appropriate explanation
        explanation = self._create_age_appropriate_explanation(event, time_period, student_age)

        return HistoricalContext(
            event_name=event,
            time_period=time_period,
            key_people=key_people,
            important_places=places,
            why_significant=significance,
            connection_to_today=connection,
            age_appropriate_explanation=explanation,
        )

    def cultural_awareness(
        self, culture_topic: str, student_age: int, focus: str = "general"
    ) -> Dict[str, Any]:
        """
        Provide cultural awareness and understanding.

        Args:
            culture_topic: The cultural topic or tradition
            student_age: Student's age
            focus: Focus area (traditions, celebrations, daily life, etc.)

        Returns:
            Dictionary with cultural information and guidance
        """
        logger.info(f"Providing cultural awareness: {culture_topic}")

        # Provide respectful overview
        overview = self._create_respectful_overview(culture_topic, student_age)

        # Identify similarities and differences
        comparisons = self._create_respectful_comparisons(culture_topic, student_age)

        # Provide appreciation guidance
        appreciation = self._guide_cultural_appreciation(student_age)

        # Generate understanding questions
        questions = self._create_cultural_questions(culture_topic, student_age)

        # Suggest learning activities
        activities = self._suggest_cultural_learning(culture_topic, student_age)

        return {
            "overview": overview,
            "similarities_and_differences": comparisons,
            "how_to_appreciate": appreciation,
            "questions_for_understanding": questions,
            "learning_activities": activities,
            "important_values": self._identify_cultural_values(student_age),
        }

    # Private helper methods

    def _generate_background(self, topic: str, domain: SocialStudiesDomain, age: int) -> str:
        """Generate background information."""
        if age <= 7:
            return f"{topic} is something important to learn about!"
        else:
            return f"{topic} is an important part of {domain.value} that helps us understand our world."

    def _identify_key_points(
        self, topic: str, domain: SocialStudiesDomain, grade: str
    ) -> List[str]:
        """Identify key points to understand."""
        return [
            "Main idea about this topic",
            "Why this topic matters",
            "How this connects to our lives",
        ]

    def _create_personal_connections(
        self, topic: str, domain: SocialStudiesDomain, age: int
    ) -> List[str]:
        """Create connections to student's life."""
        return [
            "You see this in your community",
            "This affects your daily life",
            "Your family might experience this",
        ]

    def _extract_important_vocabulary(self, topic: str, domain: SocialStudiesDomain) -> List[str]:
        """Extract important vocabulary words."""
        vocab_by_domain = {
            SocialStudiesDomain.HISTORY: ["past", "present", "timeline", "change"],
            SocialStudiesDomain.GEOGRAPHY: ["map", "location", "place", "region"],
            SocialStudiesDomain.CIVICS: ["citizen", "community", "rules", "rights"],
            SocialStudiesDomain.ECONOMICS: ["needs", "wants", "goods", "services"],
        }

        return vocab_by_domain.get(domain, ["community", "people", "place"])[:4]

    def _generate_context_questions(
        self, topic: str, domain: SocialStudiesDomain, age: int
    ) -> List[str]:
        """Generate questions to deepen understanding."""
        return [
            f"What do you already know about {topic}?",
            f"How does {topic} connect to your life?",
            "What would you like to learn more about?",
        ]

    def _suggest_resources(self, topic: str, domain: SocialStudiesDomain) -> List[str]:
        """Suggest additional learning resources."""
        return ["Books from the library", "Educational videos", "Community field trips"]

    def _explain_civic_concept(self, concept: str, age: int, examples: bool) -> Dict[str, Any]:
        """Explain civic concept."""
        definition = f"{concept} is an important idea about being part of a community."

        result = {
            "concept": concept,
            "definition": definition,
            "why_it_matters": f"{concept} helps us live together peacefully.",
            "student_role": "You can practice this every day!",
        }

        if examples:
            result["examples"] = ["In your classroom", "In your neighborhood", "In your family"]

        return result

    def _explain_geographic_concept(self, concept: str, age: int, examples: bool) -> Dict[str, Any]:
        """Explain geographic concept."""
        result = {
            "concept": concept,
            "definition": f"{concept} is a geography term that helps us understand places.",
            "visual_description": f"Picture {concept} in your mind - where it is and what it looks like.",
        }

        if examples:
            result["examples"] = [
                "Places near you",
                "Places you've visited",
                "Places you've learned about",
            ]

        return result

    def _explain_historical_concept(self, concept: str, age: int, examples: bool) -> Dict[str, Any]:
        """Explain historical concept."""
        return {
            "concept": concept,
            "definition": f"{concept} helps us understand the past.",
            "why_study_history": "Learning about the past helps us understand today!",
            "time_connection": "This happened in the past, but affects us now.",
        }

    def _explain_economic_concept(self, concept: str, age: int, examples: bool) -> Dict[str, Any]:
        """Explain economic concept."""
        return {
            "concept": concept,
            "definition": f"{concept} is about how people get what they need and want.",
            "in_daily_life": f"You see {concept} when you shop, save, or share!",
            "simple_examples": ["At the store", "At home", "At school"],
        }

    def _explain_general_concept(self, concept: str, age: int, examples: bool) -> Dict[str, Any]:
        """Explain general social studies concept."""
        return {
            "concept": concept,
            "definition": f"{concept} is an important social studies idea.",
            "why_learn_it": "This helps us understand people and places!",
        }

    def _identify_map_features(self, map_type: str, description: str) -> List[str]:
        """Identify key features to look for on map."""
        features = ["title", "legend/key", "compass rose", "scale"]

        if "physical" in map_type.lower():
            features.extend(["mountains", "rivers", "landforms"])
        elif "political" in map_type.lower():
            features.extend(["borders", "cities", "countries"])

        return features

    def _explain_map_elements(self, map_type: str, age: int) -> Dict[str, str]:
        """Explain important map elements."""
        return {
            "title": "Tells you what the map shows",
            "legend": "Explains the symbols and colors",
            "compass rose": "Shows directions (North, South, East, West)",
            "scale": "Shows how distances on the map match real distances",
        }

    def _generate_map_questions(self, map_type: str, age: int) -> List[str]:
        """Generate questions for reading maps."""
        return [
            "What does the title tell you?",
            "What do the colors and symbols mean?",
            "Which direction is north?",
            "What can you find on this map?",
        ]

    def _guide_map_interpretation(self, map_type: str, description: str, age: int) -> str:
        """Guide interpretation of map."""
        return "Start by reading the title and legend. Then look at the map to find interesting features!"

    def _identify_map_skills(self, map_type: str, age: int) -> List[str]:
        """Identify map skills to practice."""
        return [
            "Finding locations using the legend",
            "Using the compass rose to identify directions",
            "Understanding symbols and colors",
            "Comparing distances using the scale",
        ]

    def _get_map_reading_tips(self, age: int) -> List[str]:
        """Get tips for reading maps."""
        return [
            "Always read the title first",
            "Check the legend to understand symbols",
            "Use the compass rose to find directions",
            "Take your time and look carefully",
        ]

    def _organize_chronologically(self, events: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Organize events in chronological order."""
        # Simple organization - production would parse dates
        return events

    def _identify_time_relationships(self, events: List[Dict], age: int) -> List[str]:
        """Identify how events relate in time."""
        return [
            "This happened first, then this happened next",
            "These events happened around the same time",
            "This event led to this other event",
        ]

    def _identify_cause_effect(self, events: List[Dict]) -> List[Dict[str, str]]:
        """Identify cause and effect relationships."""
        return [{"cause": "This happened", "effect": "So this happened next"}]

    def _create_timeline_memory_aids(self, events: List[Dict], age: int) -> List[str]:
        """Create aids for remembering sequence."""
        return [
            "Make up a story connecting the events",
            "Draw pictures of each event in order",
            "Create a rhyme or song about the sequence",
        ]

    def _generate_timeline_questions(self, events: List[Dict], age: int) -> List[str]:
        """Generate questions about timeline."""
        return [
            "Which event happened first?",
            "What happened after that?",
            "Why did events happen in this order?",
            "How are these events connected?",
        ]

    def _explain_time_concepts(self, age: int) -> Dict[str, str]:
        """Explain time concepts for age."""
        if age <= 7:
            return {
                "past": "Things that already happened",
                "present": "Right now",
                "future": "Things that haven't happened yet",
            }
        else:
            return {
                "chronological": "In time order",
                "sequence": "What happened first, next, then, last",
                "cause and effect": "One thing makes another thing happen",
            }

    def _explain_perspectives_concept(self, age: int) -> str:
        """Explain what perspectives are."""
        if age <= 7:
            return "Different people can see things in different ways!"
        else:
            return "A perspective is how someone sees or thinks about something based on their experiences."

    def _explain_perspective_importance(self, age: int) -> str:
        """Explain why perspectives matter."""
        return "Understanding different perspectives helps us be kind and fair to everyone!"

    def _generate_perspective_questions(self, topic: str, age: int) -> List[str]:
        """Generate questions about perspectives."""
        return [
            "How might different people feel about this?",
            "Why might someone think differently than you?",
            "What experiences might change how someone sees this?",
            "How would you feel if you were in their shoes?",
        ]

    def _create_empathy_guidance(self, age: int) -> List[str]:
        """Create guidance for understanding other viewpoints."""
        return [
            "Try to imagine how the other person feels",
            "Think about their experiences and background",
            "Listen to their ideas without judging",
            "Ask questions to understand better",
        ]

    def _create_discussion_prompts(self, topic: str, age: int) -> List[str]:
        """Create prompts for discussing perspectives."""
        return [
            f"One way to think about {topic} is...",
            "Another person might see it differently because...",
            "I can understand why someone might think...",
            "This reminds me of...",
        ]

    def _get_perspective_thinking_stems(self, age: int) -> List[str]:
        """Get sentence stems for perspective thinking."""
        return [
            "From my point of view...",
            "I think... because...",
            "Someone else might think...",
            "This could also mean...",
        ]

    def _find_community_examples(self, concept: str, age: int) -> List[str]:
        """Find examples in student's community."""
        return [
            "In your neighborhood",
            "At local businesses",
            "At community centers",
            "In local government",
        ]

    def _create_personal_life_connections(self, concept: str, age: int) -> List[str]:
        """Create personal connections."""
        return [
            "At home with your family",
            "At school with your classmates",
            "Playing with friends",
            "In your daily activities",
        ]

    def _identify_community_helpers(self, concept: str) -> List[str]:
        """Identify relevant community helpers."""
        return [
            "Teachers and principals",
            "Police officers and firefighters",
            "Doctors and nurses",
            "Community leaders",
        ]

    def _suggest_participation(self, concept: str, age: int) -> List[str]:
        """Suggest ways to participate."""
        return [
            "Follow rules and be respectful",
            "Help others in your community",
            "Take care of shared spaces",
            "Speak up about what's important",
        ]

    def _create_observation_activities(self, concept: str, age: int) -> List[str]:
        """Create activities to observe concept."""
        return [
            f"Look for examples of {concept} in your neighborhood",
            f"Draw or take pictures of {concept} you see",
            f"Talk to family about {concept}",
            f"Think about how {concept} affects your day",
        ]

    def _create_community_questions(self, concept: str, age: int) -> List[str]:
        """Create questions about community connections."""
        return [
            f"Where do you see {concept} in your community?",
            f"Who helps with {concept} where you live?",
            f"How does {concept} make your community better?",
            f"What can you do to help with {concept}?",
        ]

    def _identify_time_period(self, event: str) -> str:
        """Identify time period of event."""
        # Simplified - production would use actual historical data
        return "the past"

    def _identify_key_people(self, event: str) -> List[str]:
        """Identify key people in event."""
        return ["important people who were involved"]

    def _identify_important_places(self, event: str) -> List[str]:
        """Identify important places."""
        return ["places where this happened"]

    def _explain_significance(self, event: str, age: int) -> str:
        """Explain why event is significant."""
        return f"{event} is important because it changed things or taught us something valuable."

    def _connect_to_present(self, event: str, age: int) -> str:
        """Connect historical event to present."""
        return f"This event from the past still affects us today!"

    def _create_age_appropriate_explanation(self, event: str, period: str, age: int) -> str:
        """Create age-appropriate explanation."""
        if age <= 7:
            return f"{event} happened a long time ago and is important to remember."
        else:
            return f"{event} was a significant event in {period} that helps us understand history."

    def _create_respectful_overview(self, topic: str, age: int) -> str:
        """Create respectful cultural overview."""
        return f"{topic} is a special part of culture that people value and celebrate."

    def _create_respectful_comparisons(self, topic: str, age: int) -> Dict[str, List[str]]:
        """Create respectful similarities/differences."""
        return {
            "similarities": [
                "All people have traditions",
                "Everyone celebrates special occasions",
                "Families are important in all cultures",
            ],
            "differences": [
                "Different ways of celebrating",
                "Different foods and customs",
                "Different languages and expressions",
            ],
        }

    def _guide_cultural_appreciation(self, age: int) -> List[str]:
        """Guide cultural appreciation."""
        return [
            "Show respect for all cultures",
            "Be curious and ask questions politely",
            "Celebrate differences while recognizing similarities",
            "Learn from people who are different from you",
        ]

    def _create_cultural_questions(self, topic: str, age: int) -> List[str]:
        """Create questions for cultural understanding."""
        return [
            f"What is special about {topic}?",
            "How is this similar to or different from your own traditions?",
            "What can we learn from this?",
            "How does this show what people value?",
        ]

    def _suggest_cultural_learning(self, topic: str, age: int) -> List[str]:
        """Suggest cultural learning activities."""
        return [
            "Read books about different cultures",
            "Try foods from different places",
            "Learn words in different languages",
            "Celebrate cultural holidays with respect",
        ]

    def _identify_cultural_values(self, age: int) -> List[str]:
        """Identify important cultural values."""
        return [
            "Respect for all people",
            "Curiosity about differences",
            "Kindness and understanding",
            "Appreciation of diversity",
        ]

    def _initialize_historical_periods(self) -> Dict[str, str]:
        """Initialize historical periods information."""
        return {
            "long_ago": "A very long time in the past",
            "recent_past": "Not too long ago, maybe when your parents were young",
            "present": "Right now, today",
            "future": "Time that hasn't happened yet",
        }

    def _initialize_geographic_terms(self) -> Dict[str, str]:
        """Initialize geographic terminology."""
        return {
            "map": "A drawing that shows where places are",
            "globe": "A round model of Earth",
            "location": "Where something is",
            "region": "An area with similar features",
            "landform": "Natural features of land like mountains or valleys",
        }

    def _initialize_civic_vocabulary(self) -> Dict[str, str]:
        """Initialize civic education vocabulary."""
        return {
            "citizen": "A person who belongs to a community or country",
            "rights": "Things people should be able to do",
            "responsibilities": "Things people should do to help",
            "community": "A group of people who live in the same area",
            "government": "People who make rules and decisions for everyone",
        }


def create_social_studies_reasoner(curriculum_manager=None) -> SocialStudiesReasoner:
    """
    Convenience function to create a SocialStudiesReasoner instance.

    Args:
        curriculum_manager: Optional CurriculumManager instance

    Returns:
        Initialized SocialStudiesReasoner instance
    """
    return SocialStudiesReasoner(curriculum_manager)


# Example usage
if __name__ == "__main__":
    reasoner = create_social_studies_reasoner()

    print("=== Social Studies Reasoning Module ===\n")

    # Example 1: Provide context
    print("--- Example 1: Historical Context ---")
    context = reasoner.provide_context(
        topic="American Revolution",
        domain=SocialStudiesDomain.HISTORY,
        grade_level="5",
        student_age=10,
    )
    print(f"Topic: {context['topic']}")
    print(f"Background: {context['background']}")
    print(f"Key Points: {len(context['key_points'])} identified")
    print()

    # Example 2: Map analysis
    print("--- Example 2: Map Reading Guidance ---")
    map_help = reasoner.analyze_maps(
        map_description="Political map of United States", map_type="political", student_age=8
    )
    print("What to look for:")
    for feature in map_help["what_to_look_for"][:3]:
        print(f"  - {feature}")
    print()

    # Example 3: Timeline support
    print("--- Example 3: Timeline Support ---")
    events = [
        {"name": "Colonies formed", "date": "1600s"},
        {"name": "Declaration of Independence", "date": "1776"},
        {"name": "Constitution written", "date": "1787"},
    ]
    timeline = reasoner.timeline_support(events, student_age=10)
    print("Time Relationships:")
    for rel in timeline["time_relationships"][:2]:
        print(f"  - {rel}")
    print()

    # Example 4: Community connections
    print("--- Example 4: Community Connections ---")
    community = reasoner.community_connections(
        concept="citizenship", student_age=8, grade_level="3"
    )
    print("In My Community:")
    for example in community["in_my_community"][:2]:
        print(f"  - {example}")
    print()

    print("=== Social Studies Reasoner Ready ===")
