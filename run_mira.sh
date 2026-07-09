#!/bin/bash
# MIRA 快速启动脚本
# 用法: ./run_mira.sh [--diagnosis DIAGNOSIS] [--max-patients N]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DIAGNOSIS="appendicitis"
MAX_PATIENTS=2
PROJECT_ROOT="/Volumes/Work/Project/---Agent/MIRA"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}              MIRA Medical AI Agent Simulation${NC}"
echo -e "${BLUE}============================================================${NC}"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --diagnosis) DIAGNOSIS="$2"; shift 2 ;;
        --max-patients) MAX_PATIENTS="$2"; shift 2 ;;
        --help)
            echo "用法: ./run_mira.sh [选项]"
            echo "  --diagnosis DIAG   诊断类型 (默认: appendicitis)"
            echo "  --max-patients N   最大患者数 (默认: 2)"
            exit 0 ;;
        *) echo -e "${RED}未知参数: $1${NC}"; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT"

# 激活环境
source src/.venv/bin/activate
echo -e "${GREEN}✓ Python 环境已激活${NC}"

# 检查服务
echo -e "${BLUE}检查服务...${NC}"

if curl -s http://localhost:8080/fhir/metadata > /dev/null 2>&1; then
    echo -e "${GREEN}✓ FHIR Server 运行中${NC}"
else
    echo -e "${YELLOW}启动 FHIR Server...${NC}"
    cd src && docker compose -f backend/hapi-fhir-server/docker-compose.yml up -d 2>/dev/null && cd ..
    sleep 10
fi

if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Qdrant 运行中${NC}"
else
    echo -e "${YELLOW}启动 Qdrant...${NC}"
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
        -v "$(pwd)/src/raw/runtime/qdrant/main:/qdrant/storage" \
        -e QDRANT__TELEMETRY_DISABLED=true qdrant/qdrant 2>/dev/null || true
    sleep 5
fi

# 设置环境
export MIRA_DIAGNOSIS_DATASETS_DIR="$PROJECT_ROOT/src/raw/derived/diagnosis_datasets"
export MIRA_DATASET_DIAGNOSES="$DIAGNOSIS"
export MIRA_MAX_HADM_IDS_PER_DIAGNOSIS="$MAX_PATIENTS"

echo ""
echo -e "${BLUE}配置:${NC}"
echo "  诊断: $DIAGNOSIS"
echo "  患者数: $MAX_PATIENTS"

# 测试 API
echo ""
echo -e "${BLUE}测试 GLM-5.2 API...${NC}"

API_TEST=$(cd src && python -c "
from assistants import _create_openai_client
client = _create_openai_client()
r = client.chat.completions.create(
    model='glm-5.2',
    messages=[{'role': 'user', 'content': 'Say OK'}],
    max_tokens=5
)
print(r.choices[0].message.content)
" 2>/dev/null)

if [ -n "$API_TEST" ]; then
    echo -e "${GREEN}✓ GLM-5.2 API 正常${NC}"
else
    echo -e "${RED}✗ API 连接失败${NC}"
    exit 1
fi

# 运行模拟
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}开始模拟${NC}"
echo -e "${BLUE}============================================================${NC}"

cd src

python << 'PYEOF'
import os, asyncio, sys
os.environ['MIRA_DIAGNOSIS_DATASETS_DIR'] = os.environ.get('MIRA_DIAGNOSIS_DATASETS_DIR', '')

import pandas as pd
import visualisations
from assistants import _create_openai_client, MedAssistant, PatientAssistant, PatientContext
from config import MEDICAL_ASSISTANT_MODEL, PATIENT_ASSISTANT_MODEL, MEDICAL_ASSISTANT_TEMPERATURE, PATIENT_ASSISTANT_TEMPERATURE
from openai import pydantic_function_tool
from tools import Finish, LabRequestList, RadiologyRequestFHIR, PhysicalExamination
from termcolor import colored

client = _create_openai_client()

tools = [pydantic_function_tool(t) for t in [RadiologyRequestFHIR, LabRequestList, PhysicalExamination, Finish]]

class MockSession:
    def post(self, url, json, headers, timeout=None):
        import requests
        return requests.post(url, json=json, headers=headers, timeout=timeout)

class MockPatient:
    patients = pd.DataFrame([{'subject_id': 10000000, 'gender': 'M', 'anchor_age': 45}])
    admissions = pd.DataFrame([{'hadm_id': 20000000}])
    triage = type('t', (), {'chiefcomplaint': pd.Series(['RLQ abdominal pain'])})()
    history_pe_admedication_diagnosis = {
        'extracted_history': pd.Series(['Patient with RLQ pain']),
        'admission_medication': pd.Series(['No meds']),
    }

collector = visualisations.EvaluationOutputCollector('mock', '0000')

patient_context = PatientContext(
    patient_id='20000000', patient_hadm_id='0',
    organization_id='org', practitioner_id='prac',
    session=MockSession(), headersList={},
    patient_data=MockPatient(), tools=[],
)

med = MedAssistant(
    client=client, name='Doctor', model=MEDICAL_ASSISTANT_MODEL,
    instructions='ER physician. Ask symptoms, order tests, call Finish when done.',
    completion_prompt='Wrap up.',
    tools=tools, func_name_to_func={
        'PhysicalExamination': lambda **k: {'exam': 'RLQ tenderness'},
        'LabRequestList': lambda **k: {'labs': 'CBC ordered'},
        'RadiologyRequestFHIR': lambda **k: {'imaging': 'CT ordered'},
        'Finish': lambda **k: {'done': True},
    },
    temperature=MEDICAL_ASSISTANT_TEMPERATURE,
    max_steps=5, patient_context=patient_context,
    message_collector=collector,
)

patient = PatientAssistant(
    client=client, name='Patient', model=PATIENT_ASSISTANT_MODEL,
    instructions='45yo male with sharp RLQ abdominal pain. Answer questions naturally.',
    temperature=PATIENT_ASSISTANT_TEMPERATURE,
    message_collector=collector,
)

print(f'Doctor: {MEDICAL_ASSISTANT_MODEL}')
print(f'Patient: {PATIENT_ASSISTANT_MODEL}')

async def run():
    from conv import run_simulation
    await run_simulation(med, patient, 'RLQ abdominal pain')
    print()
    print(colored('Simulation complete!', 'green'))

asyncio.run(run())
PYEOF

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}完成!${NC}"
echo -e "${GREEN}============================================================${NC}"