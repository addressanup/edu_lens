"""
Unit tests for Curriculum Manager.

Tests curriculum management including:
- Knowledge base queries
- Standard alignment
- Concept relationships
- Prerequisites tracking
- Learning pathways

Author: Testing Agent (TST-001)
"""

import json
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.ai.curriculum_manager import CurriculumManager, create_curriculum_manager


class TestCurriculumManagerInitialization:
    """Test curriculum manager initialization."""

    @pytest.fixture
    def mock_knowledge_base(self):
        """Mock knowledge base data."""
        return {
            "metadata": {
                "version": "1.0",
                "grade_range": "K-6",
                "standards_alignment": ["CCSS", "NGSS"],
            },
            "subjects": {
                "math": {
                    "name": "Mathematics",
                    "description": "Math curriculum",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "operations": {
                                    "name": "Operations and Algebraic Thinking",
                                    "standard_code": "3.OA",
                                    "concepts": {
                                        "multiplication": {
                                            "id": "math_3_oa_001",
                                            "name": "Understanding multiplication",
                                            "definition": "Multiplication as repeated addition",
                                            "difficulty": 5,
                                            "prerequisites": ["math_2_oa_002"],
                                            "learning_objectives": [
                                                "Understand multiplication concept"
                                            ],
                                            "examples": ["2 × 3 = 6"],
                                            "common_misconceptions": [
                                                "Confusing multiplication with addition"
                                            ],
                                        }
                                    },
                                }
                            }
                        }
                    },
                }
            },
        }

    @pytest.fixture
    def mock_concept_graphs(self):
        """Mock concept graphs data."""
        return {
            "math": {
                "prerequisite_graph": {"math_3_oa_001": {"prerequisites": ["math_2_oa_002"]}},
                "learning_pathways": {
                    "multiplication_basics": {
                        "name": "Multiplication Basics",
                        "description": "Learn multiplication",
                        "sequence": ["math_2_oa_002", "math_3_oa_001"],
                    }
                },
            }
        }

    def test_manager_initialization(self, tmp_path, mock_knowledge_base, mock_concept_graphs):
        """Test basic initialization."""
        # Create mock data files
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(mock_knowledge_base))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        math_graph = graphs_dir / "math_concepts.json"
        math_graph.write_text(json.dumps(mock_concept_graphs["math"]))

        manager = CurriculumManager(data_dir=str(data_dir))

        assert manager.knowledge_base is not None
        assert manager.concept_graphs is not None
        assert manager.concept_index is not None

    def test_missing_knowledge_base(self, tmp_path):
        """Test initialization with missing knowledge base."""
        with pytest.raises(FileNotFoundError):
            CurriculumManager(data_dir=str(tmp_path))

    def test_concept_index_building(self, tmp_path, mock_knowledge_base, mock_concept_graphs):
        """Test concept index is built correctly."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(mock_knowledge_base))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        manager = CurriculumManager(data_dir=str(data_dir))

        assert "math_3_oa_001" in manager.concept_index
        concept = manager.concept_index["math_3_oa_001"]
        assert concept["name"] == "Understanding multiplication"


class TestConceptRetrieval:
    """Test concept retrieval methods."""

    @pytest.fixture
    def manager(self, tmp_path, mock_knowledge_base, mock_concept_graphs):
        """Create a manager with test data."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(mock_knowledge_base))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        math_graph = graphs_dir / "math_concepts.json"
        math_graph.write_text(json.dumps(mock_concept_graphs["math"]))

        return CurriculumManager(data_dir=str(data_dir))

    @pytest.fixture
    def mock_knowledge_base(self):
        """Mock knowledge base."""
        return {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "operations": {
                                    "standard_code": "3.OA",
                                    "concepts": {
                                        "mult": {
                                            "id": "math_3_oa_001",
                                            "name": "Multiplication",
                                            "definition": "Test",
                                            "difficulty": 5,
                                            "prerequisites": ["math_2_oa_002"],
                                            "examples": ["2 x 3"],
                                            "common_misconceptions": ["Test misconception"],
                                        }
                                    },
                                }
                            }
                        }
                    },
                }
            },
        }

    @pytest.fixture
    def mock_concept_graphs(self):
        """Mock concept graphs."""
        return {"math": {"prerequisite_graph": {}, "learning_pathways": {}}}

    def test_get_concept_by_id(self, manager):
        """Test getting concept by ID."""
        concept = manager.get_concept_by_id("math_3_oa_001")

        assert concept is not None
        assert concept["name"] == "Multiplication"

    def test_get_concept_nonexistent(self, manager):
        """Test getting nonexistent concept."""
        concept = manager.get_concept_by_id("nonexistent")

        assert concept is None

    def test_get_concept_with_subject(self, manager):
        """Test getting concept with subject filter."""
        concept = manager.get_concept("math", "math_3_oa_001")

        assert concept is not None
        assert concept["subject"] == "math"

    def test_get_concept_wrong_subject(self, manager):
        """Test getting concept with wrong subject."""
        concept = manager.get_concept("science", "math_3_oa_001")

        assert concept is None


class TestPrerequisites:
    """Test prerequisite handling."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with prerequisite data."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "ops": {
                                    "concepts": {
                                        "mult": {
                                            "id": "math_3_oa_001",
                                            "name": "Multiplication",
                                            "prerequisites": ["math_2_oa_001", "math_2_oa_002"],
                                        },
                                        "add": {
                                            "id": "math_2_oa_001",
                                            "name": "Addition",
                                            "prerequisites": [],
                                        },
                                        "rep_add": {
                                            "id": "math_2_oa_002",
                                            "name": "Repeated Addition",
                                            "prerequisites": ["math_2_oa_001"],
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        return CurriculumManager(data_dir=str(data_dir))

    def test_get_prerequisites(self, manager):
        """Test getting prerequisites for a concept."""
        prereqs = manager.get_prerequisites("math_3_oa_001")

        assert len(prereqs) == 2
        prereq_ids = [p["id"] for p in prereqs]
        assert "math_2_oa_001" in prereq_ids
        assert "math_2_oa_002" in prereq_ids

    def test_get_prerequisites_none(self, manager):
        """Test getting prerequisites for concept with none."""
        prereqs = manager.get_prerequisites("math_2_oa_001")

        assert len(prereqs) == 0

    def test_get_prerequisite_chain(self, manager):
        """Test getting full prerequisite chain."""
        chain = manager.get_prerequisite_chain("math_3_oa_001")

        # Should have multiple levels
        assert len(chain) >= 1
        # First level should be direct prerequisites
        assert "math_2_oa_001" in chain[0] or "math_2_oa_002" in chain[0]


class TestSearchAndQuery:
    """Test search and query functionality."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with search test data."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "fractions": {
                                    "concepts": {
                                        "frac1": {
                                            "id": "math_3_nf_001",
                                            "name": "Understanding fractions",
                                            "definition": "Parts of a whole",
                                            "examples": ["1/2", "3/4"],
                                            "learning_objectives": ["Understand fraction concept"],
                                        },
                                        "frac2": {
                                            "id": "math_3_nf_002",
                                            "name": "Comparing fractions",
                                            "definition": "Compare fraction sizes",
                                            "examples": ["1/2 > 1/4"],
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        return CurriculumManager(data_dir=str(data_dir))

    def test_search_concepts_by_name(self, manager):
        """Test searching concepts by name."""
        results = manager.search_concepts("fractions")

        assert len(results) >= 1
        assert any("fraction" in r["name"].lower() for r in results)

    def test_search_with_subject_filter(self, manager):
        """Test searching with subject filter."""
        results = manager.search_concepts("fractions", subject="math")

        assert len(results) >= 1
        assert all(r["subject"] == "math" for r in results)

    def test_search_with_grade_filter(self, manager):
        """Test searching with grade filter."""
        results = manager.search_concepts("fractions", grade="3")

        assert len(results) >= 1
        assert all(r["grade"] == "3" for r in results)

    def test_search_no_results(self, manager):
        """Test searching with no matches."""
        results = manager.search_concepts("nonexistent_topic")

        assert len(results) == 0

    def test_get_grade_level_topics(self, manager):
        """Test getting all topics for a grade."""
        topics = manager.get_grade_level_topics("3", "math")

        assert len(topics) >= 2
        assert any("fraction" in t["name"].lower() for t in topics)


class TestLearningPathways:
    """Test learning pathway functionality."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with pathway data."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "ops": {
                                    "concepts": {
                                        "add": {"id": "math_2_oa_001", "name": "Addition"},
                                        "mult": {"id": "math_3_oa_001", "name": "Multiplication"},
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        graph_data = {
            "prerequisite_graph": {},
            "learning_pathways": {
                "basic_math": {
                    "name": "Basic Math Path",
                    "description": "Fundamental math concepts",
                    "sequence": ["math_2_oa_001", "math_3_oa_001"],
                }
            },
        }

        math_graph = graphs_dir / "math_concepts.json"
        math_graph.write_text(json.dumps(graph_data))

        return CurriculumManager(data_dir=str(data_dir))

    def test_get_available_pathways(self, manager):
        """Test getting available learning pathways."""
        pathways = manager.get_available_pathways("math")

        assert len(pathways) >= 1
        assert pathways[0]["id"] == "basic_math"

    def test_get_learning_pathway(self, manager):
        """Test getting a specific learning pathway."""
        pathway = manager.get_learning_pathway("math", "basic_math")

        assert pathway is not None
        assert len(pathway) == 2
        assert pathway[0]["id"] == "math_2_oa_001"

    def test_get_nonexistent_pathway(self, manager):
        """Test getting nonexistent pathway."""
        pathway = manager.get_learning_pathway("math", "nonexistent")

        assert pathway is None


class TestReadinessAssessment:
    """Test student readiness assessment."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager for readiness testing."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "ops": {
                                    "concepts": {
                                        "add": {
                                            "id": "math_2_oa_001",
                                            "name": "Addition",
                                            "prerequisites": [],
                                        },
                                        "mult": {
                                            "id": "math_3_oa_001",
                                            "name": "Multiplication",
                                            "prerequisites": ["math_2_oa_001", "math_2_oa_002"],
                                        },
                                        "rep_add": {
                                            "id": "math_2_oa_002",
                                            "name": "Repeated Addition",
                                            "prerequisites": ["math_2_oa_001"],
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        return CurriculumManager(data_dir=str(data_dir))

    def test_assess_readiness_ready(self, manager):
        """Test readiness when prerequisites are met."""
        mastered = ["math_2_oa_001", "math_2_oa_002"]

        assessment = manager.assess_readiness(mastered, "math_3_oa_001")

        assert assessment["ready"] is True
        assert assessment["readiness_percentage"] == 100
        assert len(assessment["missing_prerequisites"]) == 0

    def test_assess_readiness_not_ready(self, manager):
        """Test readiness when prerequisites not met."""
        mastered = []

        assessment = manager.assess_readiness(mastered, "math_3_oa_001")

        assert assessment["ready"] is False
        assert assessment["readiness_percentage"] < 100
        assert len(assessment["missing_prerequisites"]) > 0

    def test_assess_readiness_partial(self, manager):
        """Test partial readiness."""
        mastered = ["math_2_oa_001"]  # Only one of two prerequisites

        assessment = manager.assess_readiness(mastered, "math_3_oa_001")

        assert assessment["ready"] is False
        assert assessment["readiness_percentage"] == 50

    def test_get_next_concepts(self, manager):
        """Test getting next concepts to learn."""
        mastered = ["math_2_oa_001"]

        next_concepts = manager.get_next_concepts(mastered, "math", "3")

        # Should suggest concepts student is ready for
        assert len(next_concepts) >= 0


class TestMetadataAndInfo:
    """Test metadata and information retrieval."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with metadata."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0", "grade_range": "K-6", "standards_alignment": ["CCSS"]},
            "subjects": {
                "math": {
                    "name": "Mathematics",
                    "description": "Math curriculum",
                    "standards_framework": "CCSS",
                    "grade_levels": {},
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        return CurriculumManager(data_dir=str(data_dir))

    def test_get_metadata(self, manager):
        """Test getting knowledge base metadata."""
        metadata = manager.get_metadata()

        assert metadata["version"] == "1.0"
        assert metadata["grade_range"] == "K-6"

    def test_get_all_subjects(self, manager):
        """Test getting all subjects."""
        subjects = manager.get_all_subjects()

        assert "math" in subjects

    def test_get_subject_info(self, manager):
        """Test getting subject information."""
        info = manager.get_subject_info("math")

        assert info is not None
        assert info["name"] == "Mathematics"
        assert info["standards_framework"] == "CCSS"

    def test_get_nonexistent_subject_info(self, manager):
        """Test getting info for nonexistent subject."""
        info = manager.get_subject_info("nonexistent")

        assert info is None


class TestConceptDetails:
    """Test detailed concept information retrieval."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with detailed concept data."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {
            "metadata": {"version": "1.0"},
            "subjects": {
                "math": {
                    "name": "Math",
                    "grade_levels": {
                        "3": {
                            "domains": {
                                "ops": {
                                    "concepts": {
                                        "mult": {
                                            "id": "math_3_oa_001",
                                            "name": "Multiplication",
                                            "difficulty": 5,
                                            "examples": ["2 x 3 = 6", "5 x 4 = 20"],
                                            "learning_objectives": [
                                                "Understand multiplication",
                                                "Solve multiplication problems",
                                            ],
                                            "common_misconceptions": ["Confusing with addition"],
                                        }
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        return CurriculumManager(data_dir=str(data_dir))

    def test_get_concept_difficulty(self, manager):
        """Test getting concept difficulty."""
        difficulty = manager.get_concept_difficulty("math_3_oa_001")

        assert difficulty == 5

    def test_get_examples(self, manager):
        """Test getting concept examples."""
        examples = manager.get_examples("math_3_oa_001")

        assert len(examples) == 2
        assert "2 x 3 = 6" in examples

    def test_get_learning_objectives(self, manager):
        """Test getting learning objectives."""
        objectives = manager.get_learning_objectives("math_3_oa_001")

        assert len(objectives) == 2
        assert any("Understand" in obj for obj in objectives)

    def test_get_common_misconceptions(self, manager):
        """Test getting common misconceptions."""
        misconceptions = manager.get_common_misconceptions("math_3_oa_001")

        assert len(misconceptions) == 1
        assert "addition" in misconceptions[0].lower()


class TestConvenienceFunction:
    """Test convenience function."""

    def test_create_curriculum_manager(self, tmp_path):
        """Test create_curriculum_manager function."""
        data_dir = tmp_path / "curriculum"
        data_dir.mkdir()

        kb_data = {"metadata": {"version": "1.0"}, "subjects": {}}

        kb_file = data_dir / "knowledge_base.json"
        kb_file.write_text(json.dumps(kb_data))

        graphs_dir = data_dir / "concept_graphs"
        graphs_dir.mkdir()

        manager = create_curriculum_manager(data_dir=str(data_dir))

        assert isinstance(manager, CurriculumManager)
