"""
Demo Script for Layout Analysis and Problem Segmentation

This script demonstrates how to use the EduLens layout analyzer and
problem segmenter to analyze educational worksheets.

Author: Vision Processing Agent (VIS-001)
Task: VIS-001-T3
"""

import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV not available. Some features will be limited.")

from src.vision import (
    LayoutAnalyzer,
    ProblemSegmenter,
    RegionType,
    ProblemFormat,
    segment_worksheet,
    get_problems_by_format
)


def create_sample_worksheet():
    """Create a sample worksheet image for demonstration."""
    if not CV2_AVAILABLE:
        print("Cannot create sample worksheet without OpenCV")
        return None

    # Create blank white image
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255

    # Add header
    cv2.putText(image, "Math Worksheet - Grade 3", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

    # Add instructions
    cv2.putText(image, "Directions: Solve the following problems.", (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    # Problem 1 - Simple calculation
    cv2.putText(image, "1. What is 5 + 3?", (50, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.rectangle(image, (50, 180), (300, 220), (200, 200, 200), 2)

    # Problem 2 - Multiple choice
    cv2.putText(image, "2. Which is larger?", (50, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(image, "A. 5", (80, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(image, "B. 8", (80, 360),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(image, "C. 3", (80, 400),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

    # Problem 3 - Fill in blank
    cv2.putText(image, "3. The capital of France is ______.", (50, 480),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Problem 4 - With diagram
    cv2.putText(image, "4. Count the shapes:", (50, 580),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # Draw simple shapes
    cv2.circle(image, (150, 650), 30, (0, 0, 0), 2)
    cv2.rectangle(image, (220, 620), (280, 680), (0, 0, 0), 2)
    cv2.circle(image, (350, 650), 30, (0, 0, 0), 2)

    # Footer
    cv2.putText(image, "Page 1", (370, 950),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    return image


def demo_layout_analysis():
    """Demonstrate layout analysis functionality."""
    print("=" * 70)
    print("EduLens Layout Analysis Demo")
    print("=" * 70)
    print()

    # Create sample worksheet
    print("1. Creating sample worksheet image...")
    worksheet_image = create_sample_worksheet()

    if worksheet_image is None:
        print("Failed to create sample worksheet. OpenCV may not be installed.")
        return

    print(f"   Created {worksheet_image.shape[0]}x{worksheet_image.shape[1]} image")
    print()

    # Initialize layout analyzer
    print("2. Initializing LayoutAnalyzer...")
    analyzer = LayoutAnalyzer(
        min_region_size=100,
        merge_threshold=0.5,
        whitespace_threshold=20
    )
    print("   LayoutAnalyzer ready")
    print()

    # Analyze layout
    print("3. Analyzing document layout...")
    structure = analyzer.analyze_layout(worksheet_image)

    print(f"   Detected {len(structure.regions)} regions")
    print(f"   Number of columns: {structure.num_columns}")
    print(f"   Layout type: {structure.layout_type}")
    print()

    # Display regions by type
    print("4. Regions detected by type:")
    region_types = {}
    for region in structure.regions:
        region_type = region.region_type.value
        region_types[region_type] = region_types.get(region_type, 0) + 1

    for rtype, count in sorted(region_types.items()):
        print(f"   - {rtype}: {count}")
    print()

    # Show reading order
    print("5. Reading order:")
    for idx, region_id in enumerate(structure.reading_order[:10], 1):
        region = structure.get_region_by_id(region_id)
        if region:
            text_preview = region.text_content[:50] if region.text_content else "(no text)"
            print(f"   {idx}. [{region.region_type.value}] {text_preview}")
    print()

    # Display hierarchical structure
    print("6. Hierarchical structure:")
    for parent_id, children_ids in list(structure.hierarchy.items())[:5]:
        parent = structure.get_region_by_id(parent_id)
        if parent:
            print(f"   {parent.region_type.value} -> {len(children_ids)} children")
    print()

    return worksheet_image, structure


def demo_problem_segmentation(worksheet_image=None, structure=None):
    """Demonstrate problem segmentation functionality."""
    print("=" * 70)
    print("EduLens Problem Segmentation Demo")
    print("=" * 70)
    print()

    if worksheet_image is None:
        print("Creating sample worksheet...")
        worksheet_image = create_sample_worksheet()
        if worksheet_image is None:
            print("Failed to create worksheet.")
            return

    # Initialize problem segmenter
    print("1. Initializing ProblemSegmenter...")
    segmenter = ProblemSegmenter(min_problem_size=200)
    print("   ProblemSegmenter ready")
    print()

    # Segment problems
    print("2. Segmenting problems from worksheet...")
    problems = segmenter.segment_problems(worksheet_image, document_structure=structure)

    print(f"   Found {problems.total_count} problems")
    print()

    # Display format distribution
    print("3. Problem format distribution:")
    for format_type, count in problems.format_distribution.items():
        print(f"   - {format_type.value}: {count}")
    print()

    # Display individual problems
    print("4. Problem details:")
    for idx, problem in enumerate(problems.problems[:5], 1):
        print(f"   Problem {problem.problem_number}:")
        print(f"      Format: {problem.problem_format.value}")
        print(f"      Question: {problem.question_text[:60]}...")
        print(f"      Parts: {len(problem.parts)}")
        if problem.choices:
            print(f"      Choices: {len(problem.choices)}")
        if problem.diagram:
            print(f"      Has diagram: Yes")
        print(f"      Difficulty: {problem.difficulty.value}")
        print()

    # Filter by format
    print("5. Filtering problems by format:")
    mc_problems = get_problems_by_format(problems, ProblemFormat.MULTIPLE_CHOICE)
    print(f"   Multiple choice problems: {len(mc_problems)}")

    calc_problems = get_problems_by_format(problems, ProblemFormat.CALCULATION)
    print(f"   Calculation problems: {len(calc_problems)}")

    fill_problems = get_problems_by_format(problems, ProblemFormat.FILL_IN_BLANK)
    print(f"   Fill-in-blank problems: {len(fill_problems)}")
    print()

    return problems


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("=" * 70)
    print("Convenience Functions Demo")
    print("=" * 70)
    print()

    worksheet_image = create_sample_worksheet()
    if worksheet_image is None:
        print("Cannot run demo without OpenCV")
        return

    # Use convenience function to segment in one call
    print("1. Using segment_worksheet() convenience function...")
    problems = segment_worksheet(worksheet_image)
    print(f"   Found {problems.total_count} problems")
    print()

    # Convert to dictionary for serialization
    print("2. Converting to dictionary format...")
    problems_dict = problems.to_dict()
    print(f"   Total count: {problems_dict['total_count']}")
    print(f"   Keys: {list(problems_dict.keys())}")
    print()


def demo_visualization(worksheet_image, structure):
    """Visualize the analysis results (if OpenCV available)."""
    if not CV2_AVAILABLE:
        print("Visualization requires OpenCV")
        return

    print("=" * 70)
    print("Visualization Demo")
    print("=" * 70)
    print()

    # Create visualization
    vis_image = worksheet_image.copy()

    # Draw bounding boxes for each region type with different colors
    colors = {
        RegionType.HEADER: (255, 0, 0),      # Blue
        RegionType.QUESTION: (0, 255, 0),    # Green
        RegionType.ANSWER_SPACE: (0, 0, 255), # Red
        RegionType.MULTIPLE_CHOICE: (255, 255, 0), # Cyan
        RegionType.DIAGRAM: (255, 0, 255),   # Magenta
        RegionType.INSTRUCTION: (0, 255, 255), # Yellow
    }

    for region in structure.regions:
        color = colors.get(region.region_type, (128, 128, 128))
        x1, y1, x2, y2 = region.bounding_box.to_coordinates()
        cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)

        # Add label
        label = region.region_type.value
        cv2.putText(vis_image, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    print("Visualization created with colored bounding boxes:")
    for region_type, color in colors.items():
        print(f"   {region_type.value}: RGB{color}")
    print()

    # Optionally save the visualization
    output_path = Path(__file__).parent / "layout_visualization.png"
    cv2.imwrite(str(output_path), vis_image)
    print(f"Saved visualization to: {output_path}")
    print()


def main():
    """Run all demos."""
    print()
    print("#" * 70)
    print("#" + " " * 68 + "#")
    print("#  EduLens Layout Analysis & Problem Segmentation Demo" + " " * 13 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    print()

    try:
        # Demo 1: Layout Analysis
        worksheet_image, structure = demo_layout_analysis()

        # Demo 2: Problem Segmentation
        problems = demo_problem_segmentation(worksheet_image, structure)

        # Demo 3: Convenience Functions
        demo_convenience_functions()

        # Demo 4: Visualization
        if CV2_AVAILABLE and worksheet_image is not None and structure is not None:
            demo_visualization(worksheet_image, structure)

        print("=" * 70)
        print("Demo Complete!")
        print("=" * 70)
        print()
        print("Key Features Demonstrated:")
        print("  ✓ Document layout analysis")
        print("  ✓ Region detection and classification")
        print("  ✓ Hierarchical structure extraction")
        print("  ✓ Reading order determination")
        print("  ✓ Problem segmentation")
        print("  ✓ Problem format classification")
        print("  ✓ Multiple choice detection")
        print("  ✓ Difficulty estimation")
        print("  ✓ Diagram association")
        print()

    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
