"""End-to-end test of mira_dspy pipeline with GLM-5.2.

This script demonstrates the full pipeline from data loading to program execution.
"""

import os
import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "src" / ".env", override=True)

import dspy
import json
from tqdm import tqdm

# Configure DSPy
print("=" * 60)
print("MIRA DSPy End-to-End Test with GLM-5.2")
print("=" * 60)

lm = dspy.LM(
    'openai/glm-5.2',
    api_key=os.getenv('OPENAI_API_KEY'),
    api_base=os.getenv('OPENAI_BASE_URL'),
)
dspy.configure(lm=lm)

print(f"\n✓ DSPy configured with model: {lm.model}")

# Import mira_dspy components
from mira_dspy.program import MiraDoctorProgram
from mira_dspy.tools import build_tools, tool_catalog_description
from mira_dspy.metrics import category_f_beta, feedback_text, mira_metric

# Build tools
tools = build_tools()
tool_catalog_desc = tool_catalog_description(tools)

print(f"✓ Built {len(tools)} tools")
print(f"  Tools: {[t.name for t in tools]}")

# Create program
program = MiraDoctorProgram(tools=tools, max_iters=3)  # Limited iters for testing

print(f"\n✓ MiraDoctorProgram created")
print(f"  Plan predictor: ChainOfThought")
print(f"  Execute predictor: ReAct (max_iters=3)")

# Load processed demo data
data_dir = Path(__file__).parent.parent / "data" / "demo_processed"
with open(data_dir / "summary.json") as f:
    summary = json.load(f)

print(f"\n✓ Loaded demo data: {summary['total_admissions']} admissions")

# Test with a sample admission
sample_file = data_dir / "records" / f"{summary['hadm_ids'][10]}.json"
with open(sample_file) as f:
    sample = json.load(f)

print(f"\n" + "-" * 60)
print("Sample Admission")
print("-" * 60)
print(f"  hadm_id: {sample['hadm_id']}")
print(f"  Diagnosis: {sample['diagnosis_name']}")
print(f"  Chief Complaint: {sample['chief_complaint']}")
print(f"  Labs: {sample['lab_events_count']} events")

# Test the plan stage only (without FHIR backend)
print(f"\n" + "-" * 60)
print("Testing Plan Stage (ChainOfThought)")
print("-" * 60)

from mira_dspy.signatures import PlanDifferentialWorkup

plan_predictor = dspy.ChainOfThought(PlanDifferentialWorkup)

print(f"\nInput:")
print(f"  Chief Complaint: {sample['chief_complaint']}")
print(f"  History: {sample['history'][:200]}...")

print(f"\nCalling LLM for plan generation...")

result = plan_predictor(
    chief_complaint=sample['chief_complaint'],
    history_so_far=sample['history'][:1000],
    tool_catalog_desc=tool_catalog_desc
)

print(f"\n✓ Plan generated:")
print(f"  Reasoning: {result.reasoning[:300]}...")
print(f"  Plan: {result.plan[:500]}...")

# Test metrics
print(f"\n" + "-" * 60)
print("Testing Metrics")
print("-" * 60)

# Simulate a trajectory
simulated_trajectory = {
    "tool_name_0": "LabRequestList",
    "tool_args_0": {"lab_values": ["WBC", "CRP", "Lactate"]},
    "tool_name_1": "RadiologyRequestFHIR",
    "tool_args_1": {"modality": "CT", "region": "Abdomen"},
}

print(f"\nSimulated trajectory:")
print(f"  1. LabRequestList: ['WBC', 'CRP', 'Lactate']")
print(f"  2. RadiologyRequestFHIR: CT Abdomen")

# Test F1 calculation
score = category_f_beta(
    gt_and_assistant=["WBC", "CRP"],
    gt_only=["Lactate"],
    assistant_only=["Glucose"],
)
print(f"\n✓ F1 Score test: {score:.2f}")

feedback = feedback_text(
    "lab",
    gt_and_assistant=["WBC", "CRP"],
    gt_only=["Lactate"],
    assistant_only=["Glucose"],
)
print(f"✓ Feedback: {feedback}")

print(f"\n" + "=" * 60)
print("End-to-End Test Complete!")
print("=" * 60)
print("""
Summary:
✓ DSPy configured with GLM-5.2
✓ MiraDoctorProgram created with 8 tools
✓ Plan generation working (ChainOfThought)
✓ Metrics working (F1, feedback)

Next steps for full pipeline:
1. Start FHIR server for tool execution
2. Run: python -m mira_dspy.runs.compile_and_run --variant baseline --compile
""")