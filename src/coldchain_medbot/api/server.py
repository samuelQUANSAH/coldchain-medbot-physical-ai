"""
FastAPI Control Plane & Digital Twin Telemetry Server for ColdChain-MedBot Physical AI.
Exposes REST endpoints for AMR fleet telemetry, multi-agent Bedrock orchestration cycles,
AWS IoT TwinMaker entity inspection, Hybrid RAG SOP queries, and 21 CFR Part 11 audit logs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from coldchain_medbot.agents.bedrock_supervisor import BedrockPhysicalAISupervisor
from coldchain_medbot.api.dashboard_ui import DASHBOARD_HTML
from coldchain_medbot.aws.iot_twin_bridge import AWSPhysicalAICloudBridge
from coldchain_medbot.reporting.presales_roi_engine import generate_presales_roi_report
from coldchain_medbot.simulation.edge_physics_engine import (
    WAREHOUSE_OBSTACLES,
    WAREHOUSE_ZONES,
    WarehousePhysicsSimulator,
)

app = FastAPI(
    title="ColdChain-MedBot Physical AI Multi-Agent Supervisor API",
    version="1.2.0",
    description=(
        "Autonomous Biopharma Warehouse AMR & Cold-Chain Telemetry Supervisor powered by "
        "Amazon Bedrock (Anthropic Claude), Google Vertex AI Failover, AWS IoT Core, IoT TwinMaker, "
        "Hybrid RAG, and Step Functions."
    ),
)

simulator = WarehousePhysicsSimulator()
supervisor = BedrockPhysicalAISupervisor()
cloud_bridge = AWSPhysicalAICloudBridge()


class RAGSearchRequest(BaseModel):
    query: str
    payload_class: Optional[str] = None
    top_k: int = 3


class FaultInjectionRequest(BaseModel):
    amr_id: str
    fault_type: str


class FailoverToggleRequest(BaseModel):
    simulate_bedrock_outage: bool


@app.get("/", response_class=HTMLResponse)
def serve_digital_twin_dashboard() -> HTMLResponse:
    """Serves the interactive 2D Warehouse Digital Twin & Fault-Injection Console."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "coldchain-medbot-physical-ai",
        "bedrock_model": supervisor.model_id,
        "multicloud_circuit": supervisor.router.circuit_state,
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


@app.post("/api/v1/fault/inject")
def inject_physical_fault(req: FaultInjectionRequest) -> Dict[str, Any]:
    """Injects a physical fault scenario into a target AMR for live Digital Twin testing."""
    try:
        frame = simulator.inject_fault(req.amr_id, req.fault_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "injected",
        "amr_id": req.amr_id,
        "fault_type": req.fault_type,
        "updated_telemetry": frame.to_dict(),
    }


@app.post("/api/v1/fleet/reset")
def reset_warehouse_fleet() -> Dict[str, Any]:
    """Resets all 4 AMRs and Digital Twin state to initial warehouse parameters."""
    frames = simulator.reset_simulation()
    return {
        "status": "reset",
        "tick": simulator.tick_count,
        "fleet": [f.to_dict() for f in frames],
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


@app.post("/api/v1/router/failover")
def toggle_multicloud_failover(req: FailoverToggleRequest) -> Dict[str, Any]:
    """Toggles simulated Amazon Bedrock regional outage to test Google Cloud Vertex AI failover."""
    supervisor.router.simulated_primary_outage = req.simulate_bedrock_outage
    return supervisor.router.get_router_summary()


@app.get("/api/v1/reports/presales-summary")
def get_executive_presales_roi_summary() -> Dict[str, Any]:
    """Generates the Executive Pre-Sales ROI & FDA 21 CFR Part 11 Compliance Summary."""
    return generate_presales_roi_report(
        audit_ledger=cloud_bridge.dynamodb_audit_ledger,
        step_functions_executions=cloud_bridge.step_functions_executions,
        router_summary=supervisor.router.get_router_summary(),
    )
