# ColdChain-MedBot: Autonomous Warehouse AMR & Biopharma Cold-Chain Physical AI Multi-Agent Supervisor

[![AWS Bedrock](https://img.shields.io/badge/Amazon_Bedrock-Anthropic_Claude_3.5_Sonnet-FF9900?logo=amazonaws)](https://aws.amazon.com/bedrock/)
[![Physical AI](https://img.shields.io/badge/Physical_AI-ISO_3691--4_%26_21_CFR_Part_11-007A87)](#system-architecture)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**ColdChain-MedBot** is a production-grade **Physical AI Multi-Agent Supervisor** built on **Amazon Bedrock (Anthropic Claude)**, **AWS IoT Core**, **AWS IoT TwinMaker**, **Hybrid BM25 + Vector RAG**, **Amazon DynamoDB**, and **AWS Step Functions**.

It orchestrates a fleet of **Autonomous Mobile Robots (AMRs)** transporting ultra-cold mRNA lipid nanoparticles (`-80°C` to `-60°C`), cryogenic autologous CAR-T cellular therapies (`-150°C` to `-196°C` vapor-phase $\text{LN}_2$), monoclonal antibodies (`-20°C`), and refrigerated biologics (`+2°C` to `+8°C`) across a $120\text{m} \times 80\text{m}$ biopharma distribution facility.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Edge["Physical Edge Layer (Biopharma Warehouse Floor)"]
        AMR1["AMR-ALPHA-01 (mRNA-LNP -72°C)"]
        AMR2["AMR-BETA-02 (CAR-T Cryo -180°C)"]
        AMR3["AMR-GAMMA-03 (mAb -20°C)"]
        AMR4["AMR-DELTA-04 (Vaccine +5°C)"]
    end

    subgraph AWS_IoT["AWS Edge-to-Cloud Ingestion & Digital Twin"]
        IoTCore["AWS IoT Core (MQTT Telemetry & Device Shadows)"]
        TwinMaker["AWS IoT TwinMaker (3D/2D Spatial Digital Twin)"]
    end

    subgraph Bedrock_MAS["Amazon Bedrock Multi-Agent Supervisor (Claude 3.5 Sonnet)"]
        Sup["BedrockPhysicalAISupervisor (Converse API Orchestrator)"]
        Ag1["CryoThermalDiagnosticsAgent (Newton Cooling & Arrhenius MKT)"]
        Ag2["AMRFleetNavigationAgent (2D A* Pathfinding & LiDAR Envelope)"]
        Ag3["RegulatoryComplianceRAGAgent (Hybrid BM25 + Vector RAG)"]
        Shield["PhysicalSafetyShieldVerifier (ISO 3691-4 & 21 CFR Part 11 Guardrail)"]
    end

    subgraph Governance["Zero-Trust Persistence & Incident Orchestration"]
        DDB["Amazon DynamoDB (Immutable SHA-256 21 CFR Part 11 Ledger)"]
        SFN["AWS Step Functions (Excursion Remediation State Machine)"]
        SNS["Amazon SNS + KMS (Encrypted Critical Excursion Alerts)"]
    end

    Edge -->|MQTT Telemetry 5Hz| IoTCore
    IoTCore --> Sup
    Sup --> Ag1
    Sup --> Ag2
    Sup --> Ag3
    Ag1 & Ag2 & Ag3 --> Shield
    Shield -->|Verified PhysicalActuatorCommand| IoTCore
    IoTCore -->|Shadow Desired State| Edge
    Shield --> TwinMaker
    Shield --> DDB
    Shield --> SFN
    SFN --> SNS
```

---

## Core Physical AI Capabilities

1. **Thermodynamic & Mechanical Diagnostics (`CryoThermalDiagnosticsAgent`)**:
   - Computes real-time **USP `<1079>` Arrhenius Mean Kinetic Temperature (MKT)**:
     $$T_K = \frac{\Delta H / R}{-\ln\left(\frac{1}{n}\sum_{i=1}^{n} e^{-\Delta H / (R \cdot T_i)}\right)}$$
   - Detects Stirling cryo-compressor cavitation ($>120\text{ Hz}$ harmonics), gasket pressure loss ($<90\text{ kPa}$), and projects time-to-ceiling breach in minutes.
2. **Spatial Kinematics & Collision-Free A\* Routing (`AMRFleetNavigationAgent`)**:
   - Plans collision-free 2D trajectories around static warehouse rack obstacles to `LN2_RECHARGE_DOCK`, `QUARANTINE_ISOLATION_LOCK`, or `OUTBOUND_AIRLOCK_C`.
   - Enforces **ISO 3691-4** dynamic speed governing based on 360° LiDAR obstacle proximity.
3. **Hybrid BM25 + Vector Regulatory RAG (`RegulatoryComplianceRAGAgent`)**:
   - Combines lexical BM25 and dense vector cosine similarity with domain payload boosting across **FDA 21 CFR Part 11**, **USP `<1079>`**, **21 CFR 1271.260**, **WHO PQS E003**, and **ISO 3691-4:2023** SOPs.
4. **Deterministic Neuro-Symbolic Safety Shield (`PhysicalSafetyShieldVerifier`)**:
   - Guarantees that no LLM hallucination can ever violate physical safety limits: enforces hard LiDAR emergency stop ($<0.45\text{m} \rightarrow 0.0\text{ m/s}$), corridor speed throttling ($<2.0\text{m} \rightarrow \le 0.6\text{ m/s}$), low-battery diversion ($<15\%\text{ SoC}$), and signs every command with a non-repudiable **SHA-256 cryptographic hash**.

---

## Repository Structure

```text
coldchain-medbot-physical-ai/
├── pyproject.toml
├── README.md
├── docs/
│   └── ARCHITECTURE_AND_PRESALES_BRIEF.md
├── infrastructure/
│   └── cdk_stack.py                         # AWS CDK / CloudFormation Zero-Trust IaC Stack
├── src/
│   └── coldchain_medbot/
│       ├── __init__.py
│       ├── cli.py                           # Closed-loop Physical AI CLI simulation runner
│       ├── domain/
│       │   └── models.py                    # Telemetry schemas, thermal envelopes & actuator commands
│       ├── simulation/
│       │   └── edge_physics_engine.py       # 120m x 80m warehouse kinematics, A* & cryo physics
│       ├── rag/
│       │   └── knowledge_base.py            # Hybrid BM25 + Vector RAG over FDA/USP/ISO SOPs
│       ├── agents/
│       │   ├── specialist_agents.py         # 4 Specialist Physical AI subagents & Safety Shield
│       │   └── bedrock_supervisor.py        # Amazon Bedrock (Claude) Multi-Agent Supervisor
│       ├── aws/
│       │   └── iot_twin_bridge.py           # AWS IoT Core Shadow, TwinMaker, DynamoDB & Step Functions
│       └── api/
│           └── server.py                    # FastAPI REST Control Plane & Digital Twin API
└── tests/
    └── test_physical_ai_orchestrator.py     # Pytest unit & integration verification suite
```

---

## Quickstart & Local Execution

### 1. Run the Closed-Loop Physical AI Multi-Agent Simulation (CLI)
```bash
PYTHONPATH=src python3 -m coldchain_medbot.cli --cycles 2
```

### 2. Run the Test Suite
```bash
PYTHONPATH=src pytest -v
```

### 3. Launch the FastAPI Control Plane & Digital Twin API
```bash
PYTHONPATH=src uvicorn coldchain_medbot.api.server:app --reload --port 8080
```

---

## Author

**Samuel K. Quansah, M.S.**  
*Agentic Cloud Architect | Pre-Sales | Delivery & Program Leadership | Amazon Bedrock | Google Vertex AI | RAG Pipelines | Anthropic Claude | Codex | M.S. Cybersecurity | 2x AWS Certified*  
- GitHub: [github.com/samuelQUANSAH](https://github.com/samuelQUANSAH)
