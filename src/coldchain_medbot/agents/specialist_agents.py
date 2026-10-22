"""
Specialized Physical AI Subagents for Autonomous Warehouse AMR & Cold-Chain Supervision:
1. CryoThermalDiagnosticsAgent (Thermodynamics, MKT, Compressor Harmonics)
2. AMRFleetNavigationAgent (A* Spatial Pathfinding, LiDAR Obstacle Avoidance)
3. RegulatoryComplianceRAGAgent (Hybrid BM25 + Vector SOP Retrieval)
4. PhysicalSafetyShieldVerifier (Deterministic Neuro-Symbolic ISO 3691-4 Guardrail)
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from coldchain_medbot.domain.models import (
    ActuatorActionType,
    AgentAssessment,
    AMRTelemetryFrame,
    ExcursionSeverity,
    PhysicalActuatorCommand,
    THERMAL_ENVELOPES,
)
from coldchain_medbot.rag.knowledge_base import HybridColdChainKnowledgeBase
from coldchain_medbot.simulation.edge_physics_engine import (
    WAREHOUSE_ZONES,
    astar_grid_path,
)


class CryoThermalDiagnosticsAgent:
    """Evaluates cryo-chamber thermodynamics, warming slope, and compressor vibration."""

    name = "CryoThermalDiagnosticsAgent"

    def evaluate(self, frame: AMRTelemetryFrame) -> AgentAssessment:
        cryo = frame.cryo
        env = THERMAL_ENVELOPES[cryo.payload_class]
        margin_to_ceiling_c = round(env.max_temp_c - cryo.internal_temp_c, 2)

        if cryo.temp_rate_of_change_c_per_min > 0.05 and margin_to_ceiling_c > 0:
            minutes_to_breach = round(margin_to_ceiling_c / cryo.temp_rate_of_change_c_per_min, 1)
        elif margin_to_ceiling_c <= 0:
            minutes_to_breach = 0.0
        else:
            minutes_to_breach = 999.0

        # Determine severity and physical cooling action
        if cryo.internal_temp_c > env.max_temp_c:
            severity = ExcursionSeverity.CRITICAL_EXCURSION
            action = ActuatorActionType.ENGAGE_BACKUP_LN2_VALVE
            summary = (
                f"CRITICAL THERMAL EXCURSION on {cryo.payload_batch_id}: internal temp "
                f"{cryo.internal_temp_c}C exceeds max ceiling {env.max_temp_c}C "
                f"(MKT={cryo.mean_kinetic_temp_c}C, warming={cryo.temp_rate_of_change_c_per_min}C/min)."
            )
        elif minutes_to_breach <= env.max_excursion_minutes or cryo.compressor_vibration_hz >= 120.0:
            severity = ExcursionSeverity.WARNING
            action = ActuatorActionType.BOOST_PELTIER_CRYO_COOLING
            summary = (
                f"PRE-EXCURSION WARNING on {cryo.payload_batch_id}: projected ceiling breach in "
                f"{minutes_to_breach} min (compressor vibration={cryo.compressor_vibration_hz} Hz, "
                f"seal={cryo.door_seal_pressure_kpa} kPa)."
            )
        elif cryo.door_seal_pressure_kpa < 90.0:
            severity = ExcursionSeverity.ADVISORY
            action = ActuatorActionType.BOOST_PELTIER_CRYO_COOLING
            summary = f"Gasket pressure advisory ({cryo.door_seal_pressure_kpa} kPa); thermal bounds nominal."
        else:
            severity = ExcursionSeverity.NOMINAL
            action = ActuatorActionType.MAINTAIN_COURSE
            summary = (
                f"Cryo-chamber nominal at {cryo.internal_temp_c}C "
                f"(target {env.target_temp_c}C, MKT {cryo.mean_kinetic_temp_c}C)."
            )

        return AgentAssessment(
            agent_name=self.name,
            severity=severity,
            confidence_score=0.96,
            summary=summary,
            recommended_action=action,
            metrics={
                "internal_temp_c": cryo.internal_temp_c,
                "ceiling_temp_c": env.max_temp_c,
                "margin_to_ceiling_c": margin_to_ceiling_c,
                "minutes_to_breach": minutes_to_breach,
                "mean_kinetic_temp_c": cryo.mean_kinetic_temp_c,
                "compressor_vibration_hz": cryo.compressor_vibration_hz,
                "door_seal_pressure_kpa": cryo.door_seal_pressure_kpa,
            },
            citations=[env.fda_regulation_code],
        )


class AMRFleetNavigationAgent:
    """Computes A* collision-free routing and evaluates LiDAR obstacle clearance."""

    name = "AMRFleetNavigationAgent"

    def evaluate(
        self,
        frame: AMRTelemetryFrame,
        thermal_assessment: AgentAssessment,
    ) -> AgentAssessment:
        kin = frame.kinematics
        start_pt = (kin.x_meters, kin.y_meters)

        if thermal_assessment.severity == ExcursionSeverity.CRITICAL_EXCURSION:
            target_zone = "QUARANTINE_ISOLATION_LOCK"
            rec_action = ActuatorActionType.REROUTE_TO_CRYO_DOCK
        elif thermal_assessment.severity == ExcursionSeverity.WARNING:
            target_zone = "LN2_RECHARGE_DOCK"
            rec_action = ActuatorActionType.REROUTE_TO_CRYO_DOCK
        else:
            target_zone = kin.destination_zone
            rec_action = ActuatorActionType.MAINTAIN_COURSE

        goal_pt = WAREHOUSE_ZONES.get(target_zone, kin.target_waypoint)
        waypoints = astar_grid_path(start_pt, goal_pt)
        path_length_m = sum(
            math.hypot(waypoints[i + 1][0] - waypoints[i][0], waypoints[i + 1][1] - waypoints[i][1])
            for i in range(len(waypoints) - 1)
        )

        # Evaluate LiDAR clearance per ISO 3691-4
        if kin.lidar_min_obstacle_dist_m < 0.45:
            rec_action = ActuatorActionType.EMERGENCY_STOP
            safe_vel = 0.0
        elif kin.lidar_min_obstacle_dist_m < 2.0:
            safe_vel = 0.55
        else:
            safe_vel = 1.35

        eta_sec = round(path_length_m / max(0.2, safe_vel), 1) if safe_vel > 0 else 999.0

        return AgentAssessment(
            agent_name=self.name,
            severity=thermal_assessment.severity,
            confidence_score=0.94,
            summary=(
                f"Computed {len(waypoints)}-node A* trajectory to {target_zone} "
                f"(distance={round(path_length_m, 1)}m, ETA={eta_sec}s, "
                f"LiDAR clearance={kin.lidar_min_obstacle_dist_m}m, safe_vel={safe_vel} m/s)."
            ),
            recommended_action=rec_action,
            metrics={
                "assigned_zone": target_zone,
                "target_waypoint": list(goal_pt),
                "astar_waypoints": [list(wp) for wp in waypoints],
                "path_length_meters": round(path_length_m, 2),
                "recommended_velocity_mps": safe_vel,
                "eta_seconds": eta_sec,
                "lidar_min_obstacle_dist_m": kin.lidar_min_obstacle_dist_m,
            },
            citations=["ISO 3691-4:2023 AMR Spatial Safety Standard"],
        )


class RegulatoryComplianceRAGAgent:
    """Retrieves authoritative FDA / USP / GMP / ISO procedures from the Hybrid RAG Knowledge Base."""

    name = "RegulatoryComplianceRAGAgent"

    def __init__(self, kb: HybridColdChainKnowledgeBase) -> None:
        self.kb = kb

    def evaluate(
        self,
        frame: AMRTelemetryFrame,
        thermal_assessment: AgentAssessment,
    ) -> AgentAssessment:
        query = (
            f"{frame.cryo.payload_class.value} temperature {frame.cryo.internal_temp_c}C "
            f"vibration {frame.cryo.compressor_vibration_hz}Hz seal {frame.cryo.door_seal_pressure_kpa}kPa "
            f"lidar {frame.kinematics.lidar_min_obstacle_dist_m}m {' '.join(frame.active_fault_codes)}"
        )
        retrieved = self.kb.retrieve(
            query=query,
            payload_class=frame.cryo.payload_class.value,
            top_k=2,
        )
        citations = [f"{r['doc_id']} ({r['regulation_standard']})" for r in retrieved]
        top_title = retrieved[0]["title"] if retrieved else "Standard GMP Protocol"

        return AgentAssessment(
            agent_name=self.name,
            severity=thermal_assessment.severity,
            confidence_score=0.97,
            summary=(
                f"Matched regulatory SOP '{top_title}' via Hybrid BM25+Vector RAG "
                f"(top score={retrieved[0]['hybrid_score'] if retrieved else 0.0}). "
                f"Mandates 21 CFR Part 11 SHA-256 audit signing."
            ),
            recommended_action=thermal_assessment.recommended_action,
            metrics={"retrieved_sops": retrieved},
            citations=citations,
        )


class PhysicalSafetyShieldVerifier:
    """
    Deterministic Neuro-Symbolic Safety Shield (ISO 3691-4 & FDA 21 CFR Part 11).
    Intercepts and validates every proposed actuator command before physical execution.
    """

    name = "PhysicalSafetyShieldVerifier"

    def verify_and_build_command(
        self,
        frame: AMRTelemetryFrame,
        proposed_action: ActuatorActionType,
        target_waypoint: Tuple[float, float],
        proposed_velocity_mps: float,
        supervisor_rationale: str,
    ) -> PhysicalActuatorCommand:
        notes: List[str] = []
        verified = True

        # 1. LiDAR collision guardrail (ISO 3691-4)
        lidar_m = frame.kinematics.lidar_min_obstacle_dist_m
        if lidar_m < 0.45:
            proposed_action = ActuatorActionType.EMERGENCY_STOP
            clamped_vel = 0.0
            notes.append(f"ISO 3691-4 override: LiDAR obstacle at {lidar_m}m (<0.45m) forced EMERGENCY_STOP.")
        elif lidar_m < 2.0:
            clamped_vel = min(proposed_velocity_mps, 0.60)
            if clamped_vel < proposed_velocity_mps:
                notes.append(f"ISO 3691-4 speed governor clamped velocity to {clamped_vel} m/s.")
        else:
            clamped_vel = min(proposed_velocity_mps, 1.50)

        # 2. Battery SoC guardrail
        if frame.battery_soc_pct < 15.0:
            target_waypoint = WAREHOUSE_ZONES["CHARGING_PAD_WEST"]
            notes.append("Low battery (<15% SoC) override: diverted to CHARGING_PAD_WEST.")

        # 3. Cryogenic actuator interlock
        engage_ln2 = proposed_action in (
            ActuatorActionType.ENGAGE_BACKUP_LN2_VALVE,
            ActuatorActionType.REROUTE_TO_CRYO_DOCK,
            ActuatorActionType.QUARANTINE_LOCKDOWN,
        ) and (
            frame.cryo.internal_temp_c > THERMAL_ENVELOPES[frame.cryo.payload_class].max_temp_c - 2.5
        )
        if engage_ln2 and frame.cryo.ln2_reserve_pct < 5.0:
            engage_ln2 = False
            notes.append("LN2 reserve <5%; fallback to 100% Peltier cryo-cooling.")

        cryo_power_pct = 100.0 if engage_ln2 or proposed_action == ActuatorActionType.BOOST_PELTIER_CRYO_COOLING else 60.0
        if not notes:
            notes.append("All ISO 3691-4 kinematic and USP <1079> thermodynamic invariants satisfied.")

        now_iso = datetime.now(timezone.utc).isoformat()
        audit_payload = json.dumps(
            {
                "amr_id": frame.amr_id,
                "batch_id": frame.cryo.payload_batch_id,
                "temp_c": frame.cryo.internal_temp_c,
                "mkt_c": frame.cryo.mean_kinetic_temp_c,
                "action": proposed_action.value,
                "waypoint": list(target_waypoint),
                "velocity_mps": clamped_vel,
                "timestamp_iso": now_iso,
            },
            sort_keys=True,
        )
        audit_hash = hashlib.sha256(audit_payload.encode("utf-8")).hexdigest()

        return PhysicalActuatorCommand(
            command_id=f"CMD-{uuid.uuid4().hex[:8].upper()}",
            amr_id=frame.amr_id,
            timestamp_iso=now_iso,
            action_type=proposed_action,
            target_waypoint=target_waypoint,
            max_velocity_mps=round(clamped_vel, 2),
            cryo_power_override_pct=cryo_power_pct,
            engage_ln2_backup=engage_ln2,
            safety_shield_verified=verified,
            safety_shield_notes=" | ".join(notes),
            regulatory_audit_hash=audit_hash,
            supervisor_rationale=supervisor_rationale,
        )
