"""
Domain Models & Telemetry Schemas for Physical AI AMR Fleet & Cryo-Payload Supervision.
Defines strict physical invariants, sensor payloads, digital twin states, and actuator commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PayloadClass(str, Enum):
    MRNA_LIPID_NANOPARTICLE = "ULTRACOLD_MRNA_LNP"       # Target: -80.0°C to -60.0°C
    MONOCLONAL_ANTIBODY = "FROZEN_BIOLOGIC_MAB"          # Target: -25.0°C to -15.0°C
    CAR_T_CELL_THERAPY = "CRYOGENIC_CART_LN2"            # Target: -150.0°C to -196.0°C
    REFRIGERATED_VACCINE = "STANDARD_COLD_2_8C"          # Target: +2.0°C to +8.0°C


class ExcursionSeverity(str, Enum):
    NOMINAL = "NOMINAL"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL_EXCURSION = "CRITICAL_EXCURSION"


class ActuatorActionType(str, Enum):
    MAINTAIN_COURSE = "MAINTAIN_COURSE"
    BOOST_PELTIER_CRYO_COOLING = "BOOST_PELTIER_CRYO_COOLING"
    ENGAGE_BACKUP_LN2_VALVE = "ENGAGE_BACKUP_LN2_VALVE"
    REROUTE_TO_CRYO_DOCK = "REROUTE_TO_CRYO_DOCK"
    QUARANTINE_LOCKDOWN = "QUARANTINE_LOCKDOWN"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass(frozen=True)
class ThermalEnvelope:
    payload_class: PayloadClass
    min_temp_c: float
    max_temp_c: float
    target_temp_c: float
    max_excursion_minutes: float
    fda_regulation_code: str


THERMAL_ENVELOPES: Dict[PayloadClass, ThermalEnvelope] = {
    PayloadClass.MRNA_LIPID_NANOPARTICLE: ThermalEnvelope(
        payload_class=PayloadClass.MRNA_LIPID_NANOPARTICLE,
        min_temp_c=-85.0,
        max_temp_c=-60.0,
        target_temp_c=-72.0,
        max_excursion_minutes=15.0,
        fda_regulation_code="21 CFR 211.142 & USP <1079> Ultra-Cold Biologics",
    ),
    PayloadClass.MONOCLONAL_ANTIBODY: ThermalEnvelope(
        payload_class=PayloadClass.MONOCLONAL_ANTIBODY,
        min_temp_c=-25.0,
        max_temp_c=-15.0,
        target_temp_c=-20.0,
        max_excursion_minutes=30.0,
        fda_regulation_code="21 CFR 600.15 & EU GMP Annex 1 Biologics Cold-Chain",
    ),
    PayloadClass.CAR_T_CELL_THERAPY: ThermalEnvelope(
        payload_class=PayloadClass.CAR_T_CELL_THERAPY,
        min_temp_c=-196.0,
        max_temp_c=-150.0,
        target_temp_c=-180.0,
        max_excursion_minutes=5.0,
        fda_regulation_code="21 CFR 1271.260 Autologous Cellular Therapy Cryo-Chain",
    ),
    PayloadClass.REFRIGERATED_VACCINE: ThermalEnvelope(
        payload_class=PayloadClass.REFRIGERATED_VACCINE,
        min_temp_c=2.0,
        max_temp_c=8.0,
        target_temp_c=5.0,
        max_excursion_minutes=45.0,
        fda_regulation_code="WHO PQS E003 & USP <1079> Refrigerated Immunologics",
    ),
}


@dataclass
class KinematicState:
    """2D Pose and LiDAR spatial telemetry for an Autonomous Mobile Robot (AMR)."""
    x_meters: float
    y_meters: float
    heading_rad: float
    linear_velocity_mps: float
    angular_velocity_rps: float
    lidar_min_obstacle_dist_m: float
    wheel_slip_ratio: float
    destination_zone: str
    target_waypoint: Tuple[float, float]


@dataclass
class CryoChamberTelemetry:
    """Thermodynamic and mechanical sensor readings from the AMR onboard cryo-vault."""
    payload_batch_id: str
    payload_class: PayloadClass
    internal_temp_c: float
    ambient_warehouse_temp_c: float
    temp_rate_of_change_c_per_min: float
    mean_kinetic_temp_c: float
    chamber_humidity_pct: float
    compressor_vibration_hz: float
    door_seal_pressure_kpa: float
    ln2_reserve_pct: float


@dataclass
class AMRTelemetryFrame:
    """Unified edge-to-cloud telemetry packet published to AWS IoT Core (`amr/+/telemetry`)."""
    amr_id: str
    timestamp_iso: str
    sequence_num: int
    battery_soc_pct: float
    cpu_temp_c: float
    kinematics: KinematicState
    cryo: CryoChamberTelemetry
    active_fault_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["cryo"]["payload_class"] = self.cryo.payload_class.value
        return data


@dataclass
class AgentAssessment:
    """Structured output emitted by a specialized Physical AI subagent."""
    agent_name: str
    severity: ExcursionSeverity
    confidence_score: float
    summary: str
    recommended_action: ActuatorActionType
    metrics: Dict[str, Any]
    citations: List[str] = field(default_factory=list)


@dataclass
class PhysicalActuatorCommand:
    """Verified closed-loop command dispatched via AWS IoT Core Shadow to the physical AMR."""
    command_id: str
    amr_id: str
    timestamp_iso: str
    action_type: ActuatorActionType
    target_waypoint: Tuple[float, float]
    max_velocity_mps: float
    cryo_power_override_pct: float
    engage_ln2_backup: bool
    safety_shield_verified: bool
    safety_shield_notes: str
    regulatory_audit_hash: str
    supervisor_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        d["target_waypoint"] = list(self.target_waypoint)
        return d
