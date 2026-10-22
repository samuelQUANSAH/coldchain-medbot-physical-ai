"""
FastAPI Control Plane & Digital Twin Telemetry Server for ColdChain-MedBot Physical AI.
Exposes REST endpoints for AMR fleet telemetry, multi-agent Bedrock orchestration cycles,
AWS IoT TwinMaker entity inspection, Hybrid RAG SOP queries, and 21 CFR Part 11 audit logs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from coldchain_medbot.agents.bedrock_supervisor import BedrockPhysicalAISupervisor
from coldchain_medbot.aws.iot_twin_bridge import AWSPhysicalAICloudBridge
from coldchain_medbot.simulation.edge_physics_engine import (
    WAREHOUSE_OBSTACLES,
    WAREHOUSE_ZONES,
    WarehousePhysicsSimulator,
)

app = FastAPI(
    title="ColdChain-MedBot Physical AI Multi-Agent Supervisor API",
    version="1.0.0",
    description=(
        "Autonomous Biopharma Warehouse AMR & Cold-Chain Telemetry Supervisor powered by "
        "Amazon Bedrock (Anthropic Claude), AWS IoT Core, IoT TwinMaker, Hybrid RAG, and Step Functions."
    ),
)

simulator = WarehousePhysicsSimulator()
supervisor = BedrockPhysicalAISupervisor()
cloud_bridge = AWSPhysicalAICloudBridge()


class RAGSearchRequest(BaseModel):
    query: str
    payload_class: Optional[str] = None
    top_k: int = 3


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "coldchain-medbot-physical-ai",
        "bedrock_model": supervisor.model_id,
        "active_amrs": len(simulator.fleet),
        "simulation_tick": simulator.tick_count,
    }


@app.get("/api/v1/fleet/telemetry")
def get_fleet_telemetry() -> Dict[str, Any]:
    return {
        "tick": simulator.tick_count,
        "warehouse_zones": {k: list(v) for k, v in WAREHOUSE_ZONES.items()},
        "warehouse_obstacles": [list(o) for o in WAREHOUSE_OBSTACLES],
        "fleet": [frame.to_dict() for frame in simulator.fleet.values()],
    }


@app.post("/api/v1/orchestrate/step")
def run_closed_loop_orchestration_step(
    dt_seconds: float = Query(default=10.0, ge=1.0, le=120.0),
) -> Dict[str, Any]:
    """
    Advances the physical AMR warehouse simulation by `dt_seconds`, runs the 4-agent
    Amazon Bedrock Supervisor on every AMR frame, syncs AWS IoT Core Shadows + TwinMaker
    Digital Twin + DynamoDB 21 CFR Part 11 Ledger + Step Functions, and applies the
    verified physical actuator commands back to the edge AMRs.
    """
    frames = simulator.step_physics(dt_seconds=dt_seconds)
    cycle_results: List[Dict[str, Any]] = []

    for frame in frames:
        decision = supervisor.orchestrate_amr_decision(frame)
        cmd_obj = decision.pop("command_object")
        severity = decision["severity"]

        shadow = cloud_bridge.publish_iot_core_shadow(frame, cmd_obj)
        twin = cloud_bridge.sync_twinmaker_digital_twin(frame, severity, cmd_obj)
        audit = cloud_bridge.record_dynamodb_audit_entry(frame, severity, cmd_obj)
        sfn = cloud_bridge.trigger_step_functions_if_needed(frame, severity, cmd_obj)

        # Closed-loop actuation back into physical simulator
        updated_frame = simulator.apply_actuator_command(cmd_obj)

        decision["iot_shadow_topic"] = shadow["topic"]
        decision["twinmaker_entity_id"] = twin["entityId"]
        decision["dynamodb_audit_pk"] = audit["pk"]
        decision["step_functions_execution"] = sfn["executionArn"] if sfn else None
        decision["post_actuation_temp_c"] = updated_frame.cryo.internal_temp_c
        decision["post_actuation_zone"] = updated_frame.kinematics.destination_zone
        cycle_results.append(decision)

    return {
        "simulation_tick": simulator.tick_count,
        "dt_seconds": dt_seconds,
        "orchestration_results": cycle_results,
    }


@app.get("/api/v1/twinmaker/state")
def get_twinmaker_digital_twin_state() -> Dict[str, Any]:
    return {
        "workspace_id": cloud_bridge.twinmaker_workspace_id,
        "entities": cloud_bridge.twinmaker_entities,
        "iot_device_shadows": cloud_bridge.iot_device_shadows,
    }


@app.get("/api/v1/audit/ledger")
def get_21cfr11_audit_ledger() -> Dict[str, Any]:
    return {
        "table_name": cloud_bridge.dynamodb_table_name,
        "total_records": len(cloud_bridge.dynamodb_audit_ledger),
        "step_functions_executions": cloud_bridge.step_functions_executions,
        "records": cloud_bridge.dynamodb_audit_ledger[-25:],
    }


@app.post("/api/v1/rag/query")
def query_regulatory_rag(req: RAGSearchRequest) -> Dict[str, Any]:
    hits = supervisor.kb.retrieve(
        query=req.query,
        payload_class=req.payload_class,
        top_k=req.top_k,
    )
    return {"query": req.query, "results": hits}
