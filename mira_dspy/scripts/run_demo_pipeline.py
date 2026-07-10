"""Run mira_dspy pipeline on processed demo data.

This script demonstrates the full pipeline using the processed demo data.

Usage:
    cd mira_dspy
    source .venv/bin/activate
    python scripts/run_demo_pipeline.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
from tqdm import tqdm


def load_demo_data():
    """Load processed demo data."""
    data_dir = Path(__file__).parent.parent / "data" / "demo_processed"

    # Load summary
    with open(data_dir / "summary.json") as f:
        summary = json.load(f)

    # Load CSV summary
    df = pd.read_csv(data_dir / "admissions_summary.csv")

    return summary, df


def test_program_with_demo():
    """Test MiraDoctorProgram with demo data inputs."""
    print("="*60)
    print("Running mira_dspy pipeline on demo data")
    print("="*60)

    # Load demo data
    summary, df = load_demo_data()

    print(f"\nLoaded {len(df)} admissions from processed demo data")

    # Import mira_dspy components
    from mira_dspy.program import MiraDoctorProgram
    from mira_dspy.tools import build_tools, tool_catalog_description
    from mira_dspy.metrics import category_f_beta, feedback_text

    # Build tools
    tools = build_tools()
    tool_catalog_desc = tool_catalog_description(tools)

    print(f"\nTools: {len(tools)}")
    print(f"Tool catalog length: {len(tool_catalog_desc)} chars")

    # Create program (without running it - requires API keys)
    program = MiraDoctorProgram(tools=tools, max_iters=5)
    print(f"\nProgram: {program}")

    # Sample a few admissions to show what inputs look like
    print("\n" + "-"*60)
    print("Sample admissions for testing:")
    print("-"*60)

    for idx, row in df.head(5).iterrows():
        print(f"\n[Admission {row['hadm_id']}]")
        print(f"  Diagnosis: {row['diagnosis_name']}")
        print(f"  Chief Complaint: {row['chief_complaint']}")
        print(f"  Labs: {row['lab_events_count']} events")
        print(f"  Medications: {row['medication_count']} orders")
        print(f"  Procedures: {len(eval(str(row['procedure_codes'])))} codes")

        # Show what history_so_far looks like
        history = row['history']
        print(f"  History snippet: {history[:200]}...")

    # Test metrics on synthetic data
    print("\n" + "-"*60)
    print("Testing metrics:")
    print("-"*60)

    # Simulate metric calculation
    print("\nSimulating order-score evaluation:")
    print("  Ground truth labs: ['WBC', 'CRP', 'Lactate', 'Glucose']")
    print("  Predicted labs: ['WBC', 'CRP', 'Blood Culture']")

    score = category_f_beta(
        gt_and_assistant=["WBC", "CRP"],
        gt_only=["Lactate", "Glucose"],
        assistant_only=["Blood Culture"],
        beta=1.0
    )
    print(f"  F1 Score: {score:.2f}")

    feedback = feedback_text(
        "lab",
        gt_and_assistant=["WBC", "CRP"],
        gt_only=["Lactate", "Glucose"],
        assistant_only=["Blood Culture"]
    )
    print(f"  Feedback: {feedback}")

    print("\n" + "="*60)
    print("Pipeline test complete!")
    print("="*60)
    print("""
To run full compilation:
    1. Set environment variables:
       export OPENAI_API_KEY="your-key"
       export OPENAI_BASE_URL="your-endpoint"  # or leave empty for OpenAI

    2. Ensure FHIR server is running:
       export FHIR_BASE_URL="http://localhost:8080"

    3. Run compilation:
       python -m mira_dspy.runs.compile_and_run --variant baseline --compile
    """)


if __name__ == "__main__":
    test_program_with_demo()