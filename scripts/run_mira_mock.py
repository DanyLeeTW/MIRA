#!/usr/bin/env python3
"""
MIRA 模拟运行脚本 (使用模拟数据)

这个脚本使用模拟数据运行 MIRA 医疗代理模拟，
用于测试整个 pipeline 是否正常工作。

使用方法:
    cd src
    python ../scripts/run_mira_mock.py --diagnosis appendicitis --max-patients 1
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

# Set environment for mock data
os.environ.setdefault(
    "MIRA_DIAGNOSIS_DATASETS_DIR",
    "/Volumes/Work/Project/---Agent/MIRA/src/raw/derived/diagnosis_datasets/demo_test"
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np
from openai import pydantic_function_tool

from config import (
    MEDICAL_ASSISTANT_MODEL,
    MEDICAL_ASSISTANT_TEMPERATURE,
    PATIENT_ASSISTANT_MODEL,
    PATIENT_ASSISTANT_TEMPERATURE,
    SAVE_DIR,
)
from assistants import MedAssistant, PatientAssistant, PatientContext, _create_openai_client
from tools import (
    Finish,
    LabRequestList,
    MedicationRequestList,
    MicrobiologyRequestList,
    PhysicalExamination,
    ProcedureRequestFHIR,
    ProcedureSearch,
    RadiologyRequestFHIR,
    UrineRequestList,
    Plan,
    PatientHistory,
)
from termcolor import colored


def create_mock_patient_context(diagnosis: str, patient_idx: int = 0):
    """创建模拟患者上下文"""

    # 模拟患者数据
    patient_data = {
        "subject_id": 10000000 + patient_idx,
        "hadm_id": 20000000 + patient_idx,
        "gender": "M" if patient_idx % 2 == 0 else "F",
        "age": 45 + patient_idx * 5,
    }

    # 模拟入院信息
    chief_complaint = {
        "appendicitis": "Right lower quadrant abdominal pain for 12 hours",
        "cholecystitis": "Right upper quadrant abdominal pain with nausea",
        "diverticulitis": "Left lower quadrant abdominal pain and fever",
        "pancreatitis": "Epigastric pain radiating to back",
        "uti": "Dysuria and frequency for 3 days",
        "pneumonia": "Cough, fever, and shortness of breath",
        "pulmonary_embolism": "Sudden onset shortness of breath and chest pain",
        "pancreatic_cancer": "Jaundice and weight loss",
    }

    class MockPatientData:
        def __init__(self, diagnosis, idx):
            self.diagnosis = diagnosis
            self.idx = idx
            self.patients = pd.DataFrame([{
                "subject_id": 10000000 + idx,
                "gender": "M" if idx % 2 == 0 else "F",
                "anchor_age": 45 + idx * 5,
            }])
            self.admissions = pd.DataFrame([{
                "hadm_id": 20000000 + idx,
            }])
            self.triage = pd.DataFrame([{
                "chiefcomplaint": [chief_complaint.get(diagnosis, "General malaise")],
            }])
            self.history_pe_admedication_diagnosis = {
                "extracted_history": pd.DataFrame([{
                    "text": f"Patient presents with {chief_complaint.get(diagnosis, 'symptoms')}. "
                            f"Medical history includes hypertension and diabetes. "
                            f"Physical examination reveals mild tenderness."
                }]),
                "admission_medication": pd.DataFrame([{
                    "medication": "Metformin 500mg, Lisinopril 10mg"
                }]),
            }

    return MockPatientData(diagnosis, patient_idx), chief_complaint.get(diagnosis, "General symptoms")


async def run_mock_simulation(diagnosis: str, max_steps: int = 5):
    """运行模拟对话"""

    print(colored(f"\n{'='*60}", "blue"))
    print(colored(f"开始 MIRA 模拟测试 - 诊断: {diagnosis}", "blue"))
    print(colored(f"{'='*60}\n", "blue"))

    # 创建 OpenAI 客户端
    client = _create_openai_client()

    # 准备工具
    tools = [
        pydantic_function_tool(tool)
        for tool in [
            RadiologyRequestFHIR,
            MedicationRequestList,
            LabRequestList,
            MicrobiologyRequestList,
            PhysicalExamination,
            ProcedureRequestFHIR,
            ProcedureSearch,
            UrineRequestList,
            Finish,
        ]
    ]

    # 模拟医患对话
    medical_prompt = """You are an emergency medicine physician conducting a patient consultation.

Your role:
1. Take a focused history based on the chief complaint
2. Perform relevant physical examinations
3. Order appropriate diagnostic tests (labs, imaging)
4. Make a diagnosis and treatment plan
5. Call Finish when you have completed the consultation

Be thorough but efficient. Use the available tools to gather information.
"""

    patient_prompt = """You are a patient in the emergency department.

Chief complaint: {primary_symptom}

You should respond naturally to the physician's questions.
Provide relevant information about your symptoms, medical history, and current medications.
Be cooperative but only share information when asked.
"""

    # 创建模拟患者数据
    patient_data, chief_complaint = create_mock_patient_context(diagnosis, 0)

    # 模拟患者上下文
    class MockSession:
        def post(self, url, json, headers, timeout=None):
            import requests
            return requests.post(url, json=json, headers=headers, timeout=timeout)

    patient_context = PatientContext(
        patient_id=str(20000000),
        patient_hadm_id="0",
        organization_id="mock-org",
        practitioner_id="mock-practitioner",
        session=MockSession(),
        headersList={},
        patient_data=patient_data,
        tools=[],
    )

    # 初始化医疗助手
    medical_assistant = MedAssistant(
        client=client,
        name="Medical Doctor",
        model=MEDICAL_ASSISTANT_MODEL,
        instructions=medical_prompt,
        completion_prompt="Please wrap up the consultation and provide your final assessment.",
        tools=tools,
        func_name_to_func={
            "PhysicalExamination": lambda *args, **kwargs: {"result": "Normal physical exam findings"},
            "LabRequestList": lambda *args, **kwargs: {"result": "Labs ordered: CBC, BMP, LFTs"},
            "RadiologyRequestFHIR": lambda *args, **kwargs: {"result": "Imaging ordered: CT Abdomen"},
            "Finish": lambda *args, **kwargs: {"result": "Consultation completed"},
        },
        temperature=MEDICAL_ASSISTANT_TEMPERATURE,
        max_steps=max_steps,
        patient_context=patient_context,
        message_collector=None,  # Disable output collector for mock test
    )

    # 初始化患者助手
    patient_instructions = patient_prompt.format(
        primary_symptom=chief_complaint,
        anamnesis_summary="Patient with relevant medical history",
        clinical_history_summary="No significant past medical history",
    )

    patient_assistant = PatientAssistant(
        client=client,
        name="Patient",
        model=PATIENT_ASSISTANT_MODEL,
        instructions=patient_instructions,
        temperature=PATIENT_ASSISTANT_TEMPERATURE,
    )

    print(colored(f"医疗助手模型: {MEDICAL_ASSISTANT_MODEL}", "green"))
    print(colored(f"患者助手模型: {PATIENT_ASSISTANT_MODEL}", "green"))
    print(colored(f"主诉: {chief_complaint}", "yellow"))
    print()

    # 开始对话
    try:
        # 医生问候
        print(colored("\n[医生] 你好，我是急诊科医生。请告诉我你今天来就诊的主要原因。", "cyan"))

        # 患者回应
        patient_response = patient_assistant.chat_completion("医生问你：你今天来就诊的主要原因是什么？")
        print(colored(f"[患者] {patient_response.messages}", "white"))

        # 医生继续问诊
        for step in range(max_steps):
            print(colored(f"\n--- 第 {step + 1} 轮对话 ---", "blue"))

            # 医生回应
            response = await medical_assistant.chat_completion(None)

            if response.type == "assistant_response":
                print(colored(f"[医生] {response.messages}", "cyan"))

                # 患者回应
                patient_response = patient_assistant.chat_completion(response.messages)
                print(colored(f"[患者] {patient_response.messages}", "white"))

            elif response.type == "terminated":
                print(colored("\n[系统] 会诊结束", "green"))
                break

        print(colored("\n" + "="*60, "green"))
        print(colored("模拟测试完成!", "green"))
        print(colored("="*60, "green"))

        return True

    except Exception as e:
        print(colored(f"\n错误: {e}", "red"))
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="运行 MIRA 模拟测试")
    parser.add_argument("--diagnosis", type=str, default="appendicitis", help="诊断类型")
    parser.add_argument("--max-steps", type=int, default=5, help="最大对话轮数")
    args = parser.parse_args()

    asyncio.run(run_mock_simulation(args.diagnosis, args.max_steps))


if __name__ == "__main__":
    main()