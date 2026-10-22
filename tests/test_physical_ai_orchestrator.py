"""
Unit and Integration Test Suite for ColdChain-MedBot Physical AI Multi-Agent Supervisor.
Verifies:
- USP <1079> Mean Kinetic Temperature (MKT) & A* spatial pathfinding
- Hybrid BM25 + Vector RAG regulatory SOP retrieval
- 4-Agent Bedrock Supervisor orchestration & ISO 3691-4 safety shield overrides
- Closed-loop physical actuator stabilization & AWS IoT TwinMaker / DynamoDB 21 CFR Part 11 ledger
- CloudFormation / CDK zero-trust infrastructure synthesis
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coldchain_medbot.agents.bedrock_supervisor import BedrockPhysicalAISupervisor
from coldchain_medbot.aws.iot_twin_bridge import AWSPhysicalAICloudBridge
from coldchain_medbot.domain.models import ActuatorActionType, ExcursionSeverity
from coldchain_medbot.rag.knowledge_base import HybridColdChainKnowledgeBase
from coldchain_medbot.simulation.edge_physics_engine import (
    WAREHOUSE_ZONES,
    WarehousePhysicsSimulator,
    astar_grid_path,
    compute_mean_kinetic_temperature,
)
from infrastructure.cdk_stack import synthesize_cloudformation_template


def test_mean_kinetic_temperature_and_astar_routing() -> None:
    mkt = compute_mean_kinetic_temperature([-72.0, -68.0, -61.8])
    assert -72.0 <= mkt <= -60.0

    path = astar_grid_path((12.0, 15.0), WAREHOUSE_ZONES["OUTBOUND_AIRLOCK_C"])
    assert len(path) >= 2
    assert path[-1] == WAREHOUSE_ZONES["OUTBOUND_AIRLOCK_C"]


def test_hybrid_rag_retrieves_correct_fda_and_usp_sops() -> None:
    kb = HybridColdChainKnowledgeBase()
    mrna_hits = kb.retrieve(
        "mRNA LNP compressor vibration 142Hz warming excursion",
        payload_class="ULTRACOLD_MRNA_LNP",
        top_k=2,
    )
    assert mrna_hits[0]["doc_id"] == "SOP-USP-1079-MRNA"

    cart_hits = kb.retrieve(
        "CAR-T cryogenic LN2 excursion warmer than -150C quarantine",
        payload_class="CRYOGENIC_CART_LN2",
        top_k=2,
    )
    assert cart_hits[0]["doc_id"] == "SOP-FDA-1271-CART"


def test_multi_agent_supervisor_and_closed_loop_stabilization() -> None:
    sim = WarehousePhysicsSimulator()
    sup = BedrockPhysicalAISupervisor(enable_live_bedrock=False)
    bridge = AWSPhysicalAICloudBridge(enable_live_aws=False)

    # AMR-BETA-02 starts in CRITICAL_EXCURSION (-147.2C > -150.0C ceiling for CAR-T)
    beta_frame = sim.fleet["AMR-BETA-02"]
    res = sup.orchestrate_amr_decision(beta_frame)
    cmd = res["command_object"]

    assert res["severity"] == ExcursionSeverity.CRITICAL_EXCURSION.value
    assert cmd.action_type == ActuatorActionType.REROUTE_TO_CRYO_DOCK
    assert cmd.engage_ln2_backup is True
    assert cmd.safety_shield_verified is True
    # LiDAR is 1.1m (<2.0m corridor congestion), so ISO 3691-4 safety shield clamps velocity <= 0.6 m/s
    assert cmd.max_velocity_mps <= 0.60
    assert len(cmd.regulatory_audit_hash) == 64

    # Sync with AWS Cloud Bridge
    shadow = bridge.publish_iot_core_shadow(beta_frame, cmd)
    twin = bridge.sync_twinmaker_digital_twin(beta_frame, res["severity"], cmd)
    audit = bridge.record_dynamodb_audit_entry(beta_frame, res["severity"], cmd)
    sfn = bridge.trigger_step_functions_if_needed(beta_frame, res["severity"], cmd)

    assert shadow["thingName"] == "AMR-BETA-02"
    assert twin["entityId"] == "ENTITY-AMR-BETA-02"
    assert audit["regulatory_audit_hash"] == cmd.regulatory_audit_hash
    assert sfn is not None and sfn["status"] == "SUCCEEDED"

    # Closed-loop actuation cools the chamber toward -180C target and reroutes to QUARANTINE_ISOLATION_LOCK
    updated = sim.apply_actuator_command(cmd)
    assert updated.cryo.internal_temp_c < -147.2
    assert updated.kinematics.destination_zone == "QUARANTINE_ISOLATION_LOCK"


def test_emergency_stop_when_lidar_blocked() -> None:
    sim = WarehousePhysicsSimulator()
    sup = BedrockPhysicalAISupervisor(enable_live_bedrock=False)

    gamma = sim.fleet["AMR-GAMMA-03"]
    gamma.kinematics.lidar_min_obstacle_dist_m = 0.25  # Below 0.45m ISO 3691-4 hard limit

    res = sup.orchestrate_amr_decision(gamma)
    cmd = res["command_object"]
    assert cmd.action_type == ActuatorActionType.EMERGENCY_STOP
    assert cmd.max_velocity_mps == 0.0


def test_cdk_cloudformation_stack_synthesis() -> None:
    tpl = synthesize_cloudformation_template()
    resources = tpl["Resources"]
    assert "ColdChainKMSKey" in resources
    assert "ColdChainAuditLedgerTable" in resources
    assert "AMRTelemetryIoTTopicRule" in resources
    assert "BedrockSupervisorIAMRole" in resources


def test_fault_injection_and_digital_twin_api() -> None:
    from fastapi.testclient import TestClient
    from coldchain_medbot.api.server import app

    client = TestClient(app)

    # 1. Verify Digital Twin HTML console renders at GET /
    ui_res = client.get("/")
    assert ui_res.status_code == 200
    assert "ColdChain-MedBot Physical AI" in ui_res.text
    assert "twinCanvas" in ui_res.text

    # 2. Inject LIDAR_CORRIDOR_OBSTACLE on AMR-DELTA-04 and run closed-loop step
    inj_res = client.post(
        "/api/v1/fault/inject",
        json={"amr_id": "AMR-DELTA-04", "fault_type": "LIDAR_CORRIDOR_OBSTACLE"},
    )
    assert inj_res.status_code == 200
    assert inj_res.json()["updated_telemetry"]["kinematics"]["lidar_min_obstacle_dist_m"] == 0.32

    step_res = client.post("/api/v1/orchestrate/step?dt_seconds=10")
    assert step_res.status_code == 200
    delta_orc = [
        r for r in step_res.json()["orchestration_results"] if r["amr_id"] == "AMR-DELTA-04"
    ][0]
    assert delta_orc["actuator_command"]["action_type"] == "EMERGENCY_STOP"
    assert delta_orc["actuator_command"]["max_velocity_mps"] == 0.0

    # 3. Reset fleet
    rst_res = client.post("/api/v1/fleet/reset")
    assert rst_res.status_code == 200
    assert rst_res.json()["tick"] == 0

