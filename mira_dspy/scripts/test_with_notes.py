"""Test mira_dspy with real clinical notes from MIMIC demo.

This script demonstrates the pipeline using actual discharge summaries
and radiology reports for richer context.
"""

import json
import os
import sys
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "src" / ".env", override=True)

import dspy

# Configure DSPy with GLM-5.2
lm = dspy.LM(
    'openai/glm-5.2',
    api_key=os.getenv('OPENAI_API_KEY'),
    api_base=os.getenv('OPENAI_BASE_URL'),
)
dspy.configure(lm=lm)

print("="*60)
print("Testing mira_dspy with Real Clinical Notes")
print("="*60)

# Load processed data with notes
data_dir = Path(__file__).parent.parent / "data" / "demo_with_notes"
with open(data_dir / "summary.json") as f:
    summary = json.load(f)

print(f"\n✓ Loaded {summary['total_admissions']} admissions with clinical notes")

# Import components
from mira_dspy.program import MiraDoctorProgram
from mira_dspy.tools import build_tools, tool_catalog_description
from mira_dspy.signatures import PlanDifferentialWorkup

tools = build_tools()
tool_catalog_desc = tool_catalog_description(tools)

# Find a rich case
rich_case = None
for hid in summary['hadm_ids'][:50]:
    with open(data_dir / "records" / f"{hid}.json") as f:
        rec = json.load(f)
    if rec['lab_events_count'] > 100 and len(rec.get('radiology_reports', [])) > 0:
        rich_case = rec
        break

if rich_case:
    print(f"\n" + "-"*60)
    print("Rich Clinical Case")
    print("-"*60)
    print(f"hadm_id: {rich_case['hadm_id']}")
    print(f"Diagnosis: {rich_case['diagnosis_name']}")
    print(f"Chief Complaint: {rich_case['chief_complaint']}")
    print(f"Labs: {rich_case['lab_events_count']} events")
    print(f"Radiology reports: {len(rich_case.get('radiology_reports', []))}")

    # Build comprehensive history
    history = f"""Patient is a {rich_case['age']} year old {rich_case['gender']}.

Chief Complaint: {rich_case['chief_complaint']}

Admission Type: {rich_case['admission_type']}

Clinical History:
{rich_case['history']}

Radiology Findings:
{rich_case['radiology_reports'][0] if rich_case.get('radiology_reports') else 'No imaging available.'}
"""

    print(f"\nHistory length: {len(history)} chars")

    # Test plan generation
    print(f"\n" + "-"*60)
    print("Generating Differential Workup Plan")
    print("-"*60)

    plan_predictor = dspy.ChainOfThought(PlanDifferentialWorkup)

    print(f"\nCalling GLM-5.2 for plan...")

    result = plan_predictor(
        chief_complaint=rich_case['chief_complaint'],
        history_so_far=history[:2000],
        tool_catalog_desc=tool_catalog_desc
    )

    print(f"\n✓ Plan Generated:")
    print(f"\nReasoning:")
    print(result.reasoning[:500])
    print(f"\nWorkup Plan:")
    print(result.plan)

# Test with multiple cases
print(f"\n" + "="*60)
print("Batch Testing (5 cases)")
print("="*60)

plan_predictor = dspy.ChainOfThought(PlanDifferentialWorkup)

results = []
for i, hid in enumerate(summary['hadm_ids'][:5]):
    with open(data_dir / "records" / f"{hid}.json") as f:
        rec = json.load(f)

    history = f"Patient is a {rec['age']} year old {rec['gender']}. Chief Complaint: {rec['chief_complaint']}."

    result = plan_predictor(
        chief_complaint=rec['chief_complaint'],
        history_so_far=history,
        tool_catalog_desc=tool_catalog_desc
    )

    results.append({
        "hadm_id": hid,
        "diagnosis": rec['diagnosis_name'],
        "chief_complaint": rec['chief_complaint'],
        "plan_preview": result.plan[:200] + "...",
    })

    print(f"\n{i+1}. hadm_id={hid}")
    print(f"   Diagnosis: {rec['diagnosis_name'][:50]}")
    print(f"   Plan: {result.plan[:150]}...")

print(f"\n" + "="*60)
print("Complete!")
print("="*60)
print(f"\n✓ Successfully processed {len(results)} cases with GLM-5.2")
print(f"✓ Plan generation working with real clinical notes")
print(f"✓ Ready for GEPA compilation (requires FHIR backend)")