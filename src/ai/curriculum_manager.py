"""
Curriculum Manager for EduLens AI Agent

This module provides a comprehensive interface for querying the K-6 curriculum knowledge base.
It enables the AI tutoring system to retrieve concept information, understand prerequisites,
find related concepts, and support scaffolded learning.

Author: EduLens AI Team
Version: 1.0.0
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class CurriculumManager:
    """
    Manages curriculum knowledge base and provides query interface for AI tutoring.

    This class loads and indexes the curriculum knowledge base, concept graphs, and
    provides methods to query concepts, prerequisites, related topics, and misconceptions.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the CurriculumManager.

        Args:
            data_dir: Path to curriculum data directory. If None, uses default location.
        """
        if data_dir is None:
            # Default to edu_lens/data/curriculum
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            data_dir = project_root / "data" / "curriculum"

        self.data_dir = Path(data_dir)
        self.knowledge_base: Dict = {}
        self.concept_graphs: Dict[str, Dict] = {}
        self.concept_index: Dict[str, Dict] = {}  # Maps concept_id to full concept data

        self._load_knowledge_base()
        self._load_concept_graphs()
        self._build_concept_index()

    def _load_knowledge_base(self):
        """Load the main knowledge base JSON file."""
        kb_path = self.data_dir / "knowledge_base.json"

        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found at {kb_path}")

        with open(kb_path, "r", encoding="utf-8") as f:
            self.knowledge_base = json.load(f)

    def _load_concept_graphs(self):
        """Load all concept graph files."""
        graph_dir = self.data_dir / "concept_graphs"

        if not graph_dir.exists():
            raise FileNotFoundError(f"Concept graphs directory not found at {graph_dir}")

        graph_files = {
            "math": "math_concepts.json",
            "reading": "reading_concepts.json",
            "science": "science_concepts.json",
            "social_studies": "social_studies_concepts.json",
        }

        for subject, filename in graph_files.items():
            filepath = graph_dir / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    self.concept_graphs[subject] = json.load(f)

    def _build_concept_index(self):
        """Build an index mapping concept IDs to their full data for fast lookup."""
        for subject_name, subject_data in self.knowledge_base["subjects"].items():
            for grade, grade_data in subject_data["grade_levels"].items():
                for domain_name, domain_data in grade_data.get("domains", {}).items():
                    for concept_key, concept_data in domain_data.get("concepts", {}).items():
                        # Use the 'id' field from concept_data as the index key
                        concept_id = concept_data.get("id", concept_key)
                        # Store full concept data with metadata
                        self.concept_index[concept_id] = {
                            **concept_data,
                            "subject": subject_name,
                            "grade": grade,
                            "domain": domain_name,
                            "standard_code": domain_data.get("standard_code", ""),
                        }

    def get_concept(self, subject: str, concept_id: str) -> Optional[Dict]:
        """
        Retrieve a concept by its ID.

        Args:
            subject: Subject area (math, reading, science, social_studies)
            concept_id: Unique concept identifier

        Returns:
            Dictionary containing concept data, or None if not found
        """
        if concept_id in self.concept_index:
            concept = self.concept_index[concept_id]
            # Verify subject matches
            if concept["subject"] == subject:
                return concept

        return None

    def get_concept_by_id(self, concept_id: str) -> Optional[Dict]:
        """
        Retrieve a concept by its ID regardless of subject.

        Args:
            concept_id: Unique concept identifier

        Returns:
            Dictionary containing concept data, or None if not found
        """
        return self.concept_index.get(concept_id)

    def get_prerequisites(self, concept_id: str) -> List[Dict]:
        """
        Get all prerequisite concepts for a given concept.

        Args:
            concept_id: Unique concept identifier

        Returns:
            List of prerequisite concept dictionaries
        """
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            return []

        prereq_ids = concept.get("prerequisites", [])
        prerequisites = []

        for prereq_id in prereq_ids:
            prereq_concept = self.get_concept_by_id(prereq_id)
            if prereq_concept:
                prerequisites.append(prereq_concept)

        return prerequisites

    def get_prerequisite_chain(self, concept_id: str) -> List[List[str]]:
        """
        Get the full prerequisite chain for a concept (all levels).

        Args:
            concept_id: Unique concept identifier

        Returns:
            List of prerequisite levels, where each level is a list of concept IDs
        """
        visited = set()
        levels = []
        current_level = [concept_id]

        while current_level:
            next_level = []
            for cid in current_level:
                if cid in visited:
                    continue
                visited.add(cid)

                concept = self.get_concept_by_id(cid)
                if concept:
                    prereq_ids = concept.get("prerequisites", [])
                    next_level.extend([pid for pid in prereq_ids if pid not in visited])

            if next_level:
                levels.append(next_level)
            current_level = next_level

        return levels

    def get_grade_level_topics(self, grade: str, subject: str) -> List[Dict]:
        """
        Get all topics/concepts for a specific grade level and subject.

        Args:
            grade: Grade level (K, 1, 2, 3, 4, 5, 6, or ranges like K-2, 3-5)
            subject: Subject area (math, reading, science, social_studies)

        Returns:
            List of concept dictionaries for that grade and subject
        """
        concepts = []

        subject_data = self.knowledge_base["subjects"].get(subject, {})
        grade_data = subject_data.get("grade_levels", {}).get(grade, {})

        for domain_name, domain_data in grade_data.get("domains", {}).items():
            for concept_id, concept_data in domain_data.get("concepts", {}).items():
                concepts.append(
                    {
                        "concept_id": concept_id,
                        **concept_data,
                        "domain": domain_name,
                        "domain_name": domain_data.get("name", ""),
                        "standard_code": domain_data.get("standard_code", ""),
                    }
                )

        return concepts

    def find_related_concepts(self, concept_id: str, max_distance: int = 2) -> List[Dict]:
        """
        Find concepts related to a given concept based on prerequisites and dependencies.

        Args:
            concept_id: Unique concept identifier
            max_distance: Maximum graph distance to search (default: 2)

        Returns:
            List of related concept dictionaries with their relationship type
        """
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            return []

        subject = concept["subject"]
        related = []

        # Get concepts from concept graph if available
        if subject in self.concept_graphs:
            prereq_graph = self.concept_graphs[subject].get("prerequisite_graph", {})

            # Find concepts this one enables (forward dependencies)
            for cid, data in prereq_graph.items():
                prereqs = data.get("prerequisites", [])
                if concept_id in prereqs:
                    related_concept = self.get_concept_by_id(cid)
                    if related_concept:
                        related.append(
                            {**related_concept, "relationship": "enables", "distance": 1}
                        )

            # Find prerequisite concepts (backward dependencies)
            prereqs = concept.get("prerequisites", [])
            for prereq_id in prereqs:
                prereq_concept = self.get_concept_by_id(prereq_id)
                if prereq_concept:
                    related.append(
                        {**prereq_concept, "relationship": "prerequisite", "distance": 1}
                    )

        # Also find concepts in same domain/grade
        same_grade_concepts = self.get_grade_level_topics(concept["grade"], subject)
        for same_concept in same_grade_concepts:
            if same_concept["id"] != concept_id:
                # Check if not already in related
                if not any(r.get("id") == same_concept["id"] for r in related):
                    related.append({**same_concept, "relationship": "same_grade", "distance": 1})

        return related

    def get_common_misconceptions(self, concept_id: str) -> List[str]:
        """
        Get common misconceptions for a concept.

        Args:
            concept_id: Unique concept identifier

        Returns:
            List of common misconceptions as strings
        """
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            return []

        return concept.get("common_misconceptions", [])

    def search_concepts(
        self, query: str, subject: Optional[str] = None, grade: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for concepts matching a query string.

        Args:
            query: Search query (searches in name, definition, examples)
            subject: Optional subject filter
            grade: Optional grade level filter

        Returns:
            List of matching concept dictionaries, ranked by relevance
        """
        query_lower = query.lower()
        matches = []

        for concept_id, concept in self.concept_index.items():
            # Apply filters
            if subject and concept["subject"] != subject:
                continue
            if grade and concept["grade"] != grade:
                continue

            # Search in various fields
            score = 0

            # Name match (highest weight)
            if query_lower in concept.get("name", "").lower():
                score += 10

            # Definition match
            if query_lower in concept.get("definition", "").lower():
                score += 5

            # Examples match
            examples = concept.get("examples", [])
            for example in examples:
                if query_lower in str(example).lower():
                    score += 2
                    break

            # Learning objectives match
            objectives = concept.get("learning_objectives", [])
            for obj in objectives:
                if query_lower in obj.lower():
                    score += 3
                    break

            if score > 0:
                matches.append({**concept, "search_score": score})

        # Sort by score (descending)
        matches.sort(key=lambda x: x["search_score"], reverse=True)

        return matches

    def get_learning_pathway(self, subject: str, pathway_name: str) -> Optional[List[Dict]]:
        """
        Get a predefined learning pathway from concept graphs.

        Args:
            subject: Subject area
            pathway_name: Name of the pathway

        Returns:
            List of concepts in the pathway order, or None if pathway not found
        """
        if subject not in self.concept_graphs:
            return None

        pathways = self.concept_graphs[subject].get("learning_pathways", {})
        pathway_data = pathways.get(pathway_name)

        if not pathway_data:
            return None

        # Get sequence of concept IDs
        sequence = pathway_data.get("sequence", [])

        # Retrieve full concept data
        concepts = []
        for concept_id in sequence:
            concept = self.get_concept_by_id(concept_id)
            if concept:
                concepts.append(concept)

        return concepts

    def get_available_pathways(self, subject: str) -> List[Dict]:
        """
        Get all available learning pathways for a subject.

        Args:
            subject: Subject area

        Returns:
            List of pathway information dictionaries
        """
        if subject not in self.concept_graphs:
            return []

        pathways = self.concept_graphs[subject].get("learning_pathways", {})

        pathway_list = []
        for pathway_id, pathway_data in pathways.items():
            pathway_list.append(
                {
                    "id": pathway_id,
                    "name": pathway_data.get("name", pathway_id),
                    "description": pathway_data.get("description", ""),
                    "sequence_length": len(pathway_data.get("sequence", [])),
                }
            )

        return pathway_list

    def assess_readiness(
        self, student_mastered_concepts: List[str], target_concept_id: str
    ) -> Dict:
        """
        Assess if a student is ready for a target concept based on mastered prerequisites.

        Args:
            student_mastered_concepts: List of concept IDs the student has mastered
            target_concept_id: The concept to assess readiness for

        Returns:
            Dictionary with readiness assessment
        """
        concept = self.get_concept_by_id(target_concept_id)
        if not concept:
            return {"ready": False, "error": "Concept not found"}

        prereqs = concept.get("prerequisites", [])

        # If no prerequisites, student is ready
        if not prereqs:
            return {
                "ready": True,
                "missing_prerequisites": [],
                "mastered_prerequisites": [],
                "readiness_percentage": 100,
            }

        # Check which prerequisites are mastered
        mastered = [p for p in prereqs if p in student_mastered_concepts]
        missing = [p for p in prereqs if p not in student_mastered_concepts]

        readiness_pct = (len(mastered) / len(prereqs)) * 100 if prereqs else 100

        # Get full data for missing prerequisites
        missing_concepts = []
        for prereq_id in missing:
            prereq = self.get_concept_by_id(prereq_id)
            if prereq:
                missing_concepts.append(prereq)

        return {
            "ready": len(missing) == 0,
            "missing_prerequisites": missing_concepts,
            "mastered_prerequisites": mastered,
            "readiness_percentage": readiness_pct,
            "total_prerequisites": len(prereqs),
        }

    def get_next_concepts(
        self, student_mastered_concepts: List[str], subject: str, grade: str
    ) -> List[Dict]:
        """
        Suggest next concepts a student should learn based on what they've mastered.

        Args:
            student_mastered_concepts: List of concept IDs the student has mastered
            subject: Subject area
            grade: Current grade level

        Returns:
            List of suggested next concepts with readiness info
        """
        grade_concepts = self.get_grade_level_topics(grade, subject)
        suggestions = []

        for concept in grade_concepts:
            concept_id = concept.get("id")

            # Skip if already mastered
            if concept_id in student_mastered_concepts:
                continue

            # Assess readiness
            readiness = self.assess_readiness(student_mastered_concepts, concept_id)

            # Only suggest if ready or close to ready (80%+)
            if readiness["readiness_percentage"] >= 80:
                suggestions.append({**concept, "readiness": readiness})

        # Sort by readiness percentage (descending)
        suggestions.sort(key=lambda x: x["readiness"]["readiness_percentage"], reverse=True)

        return suggestions

    def get_metadata(self) -> Dict:
        """
        Get curriculum knowledge base metadata.

        Returns:
            Dictionary containing metadata information
        """
        return self.knowledge_base.get("metadata", {})

    def get_all_subjects(self) -> List[str]:
        """
        Get list of all available subjects.

        Returns:
            List of subject identifiers
        """
        return list(self.knowledge_base.get("subjects", {}).keys())

    def get_subject_info(self, subject: str) -> Optional[Dict]:
        """
        Get information about a subject.

        Args:
            subject: Subject identifier

        Returns:
            Dictionary with subject information, or None if not found
        """
        subjects = self.knowledge_base.get("subjects", {})
        if subject not in subjects:
            return None

        subject_data = subjects[subject]
        return {
            "name": subject_data.get("name"),
            "description": subject_data.get("description"),
            "standards_framework": subject_data.get("standards_framework"),
            "grade_levels": list(subject_data.get("grade_levels", {}).keys()),
        }

    def get_concept_difficulty(self, concept_id: str) -> Optional[int]:
        """
        Get the difficulty level of a concept (1-10 scale).

        Args:
            concept_id: Unique concept identifier

        Returns:
            Difficulty level as integer, or None if not found
        """
        concept = self.get_concept_by_id(concept_id)
        if concept:
            return concept.get("difficulty")
        return None

    def get_examples(self, concept_id: str) -> List[str]:
        """
        Get example problems/exercises for a concept.

        Args:
            concept_id: Unique concept identifier

        Returns:
            List of example problems as strings
        """
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            return []

        return concept.get("examples", [])

    def get_learning_objectives(self, concept_id: str) -> List[str]:
        """
        Get learning objectives for a concept.

        Args:
            concept_id: Unique concept identifier

        Returns:
            List of learning objectives as strings
        """
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            return []

        return concept.get("learning_objectives", [])


# Convenience function for easy instantiation
def create_curriculum_manager(data_dir: Optional[str] = None) -> CurriculumManager:
    """
    Create and return a CurriculumManager instance.

    Args:
        data_dir: Optional path to curriculum data directory

    Returns:
        Initialized CurriculumManager instance
    """
    return CurriculumManager(data_dir)


# Example usage and testing
if __name__ == "__main__":
    # Initialize manager
    manager = create_curriculum_manager()

    print("=== EduLens Curriculum Manager ===\n")

    # Get metadata
    metadata = manager.get_metadata()
    print(f"Knowledge Base Version: {metadata.get('version')}")
    print(f"Standards: {metadata.get('standards_alignment')}")
    print(f"Grade Range: {metadata.get('grade_range')}")
    print(f"Subjects: {', '.join(manager.get_all_subjects())}\n")

    # Example: Get a specific concept
    print("--- Example 1: Get Concept ---")
    concept = manager.get_concept("math", "math_3_oa_001")
    if concept:
        print(f"Concept: {concept['name']}")
        print(f"Grade: {concept['grade']}")
        print(f"Definition: {concept['definition']}")
        print(f"Difficulty: {concept.get('difficulty', 'N/A')}/10\n")

    # Example: Get prerequisites
    print("--- Example 2: Prerequisites ---")
    prereqs = manager.get_prerequisites("math_3_oa_001")
    print(f"Prerequisites for 'Understanding multiplication':")
    for prereq in prereqs:
        print(f"  - {prereq['name']} ({prereq['id']})")
    print()

    # Example: Search concepts
    print("--- Example 3: Search Concepts ---")
    results = manager.search_concepts("fraction", subject="math")
    print(f"Search results for 'fraction' in math:")
    for i, result in enumerate(results[:5], 1):
        print(f"  {i}. {result['name']} (Grade {result['grade']})")
    print()

    # Example: Get grade level topics
    print("--- Example 4: Grade Level Topics ---")
    grade_3_math = manager.get_grade_level_topics("3", "math")
    print(f"Grade 3 Math has {len(grade_3_math)} concepts")
    print()

    # Example: Get common misconceptions
    print("--- Example 5: Common Misconceptions ---")
    misconceptions = manager.get_common_misconceptions("math_3_oa_001")
    print(f"Common misconceptions for 'Understanding multiplication':")
    for misc in misconceptions:
        print(f"  - {misc}")
    print()

    # Example: Learning pathway
    print("--- Example 6: Learning Pathway ---")
    pathways = manager.get_available_pathways("math")
    print(f"Available math pathways:")
    for pathway in pathways:
        print(f"  - {pathway['name']}: {pathway['description']}")
    print()

    # Example: Assess readiness
    print("--- Example 7: Assess Readiness ---")
    mastered = ["math_2_oa_002"]  # Student has mastered arrays and repeated addition
    readiness = manager.assess_readiness(mastered, "math_3_oa_001")
    if "error" not in readiness:
        print(
            f"Readiness for 'Understanding multiplication': {readiness.get('readiness_percentage', 0):.0f}%"
        )
        print(f"Ready: {readiness.get('ready', False)}")
        if readiness.get("missing_prerequisites"):
            print("Still need to master:")
            for prereq in readiness["missing_prerequisites"]:
                print(f"  - {prereq.get('name', 'Unknown')}")
    else:
        print(f"Error: {readiness['error']}")
    print()

    print("=== Curriculum Manager Ready ===")
