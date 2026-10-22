"""
Edge Physical AI Simulator: AMR Kinematics, A* Spatial Pathfinding, and Cryo-Thermodynamics.
Models a 120m x 80m Biopharma Cold-Chain Warehouse with 4 Autonomous Mobile Robots (AMRs).
"""

from __future__ import annotations

import heapq
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from coldchain_medbot.domain.models import (
    ActuatorActionType,
    AMRTelemetryFrame,
    CryoChamberTelemetry,
    KinematicState,
    PayloadClass,
    PhysicalActuatorCommand,
    THERMAL_ENVELOPES,
)

# Warehouse spatial landmarks (x_meters, y_meters) inside a 120m x 80m facility
WAREHOUSE_ZONES: Dict[str, Tuple[float, float]] = {
    "CRYO_VAULT_A": (12.0, 15.0),
    "LN2_RECHARGE_DOCK": (28.0, 68.0),
    "BIOLOGICS_BAY_B": (64.0, 22.0),
    "QUARANTINE_ISOLATION_LOCK": (96.0, 70.0),
    "OUTBOUND_AIRLOCK_C": (108.0, 18.0),
    "CHARGING_PAD_WEST": (10.0, 65.0),
}

# Static rack obstacles represented as (center_x, center_y, radius_m)
WAREHOUSE_OBSTACLES: List[Tuple[float, float, float]] = [
    (40.0, 35.0, 6.0),
    (55.0, 50.0, 7.5),
    (80.0, 40.0, 6.5),
]


def compute_mean_kinetic_temperature(temp_history_c: List[float], delta_h_kj: float = 83.144) -> float:
    """
    Calculates USP <1079> Mean Kinetic Temperature (MKT) in Celsius using the Haynes Arrhenius equation:
    MKT = (dH / R) / -ln( sum(exp(-dH / (R * T_i))) / n ) - 273.15
    """
    if not temp_history_c:
        return 0.0
    r_gas_kJ = 0.008314472
    dh_over_r = delta_h_kj / r_gas_kJ
    exp_terms = []
    for t_c in temp_history_c:
        t_k = max(50.0, t_c + 273.15)
        # Clamp exponent to avoid overflow at ultra-low temperatures
        exponent = max(-500.0, min(500.0, -dh_over_r / t_k))
        exp_terms.append(math.exp(exponent))
    mean_exp = sum(exp_terms) / len(exp_terms)
    if mean_exp <= 0:
        return sum(temp_history_c) / len(temp_history_c)
    mkt_k = dh_over_r / (-math.log(mean_exp))
    return round(mkt_k - 273.15, 2)


def astar_grid_path(
    start: Tuple[float, float],
    goal: Tuple[float, float],
    grid_step: float = 4.0,
) -> List[Tuple[float, float]]:
    """
    Computes a collision-free 2D waypoint path using A* search across the 120m x 80m warehouse floor,
    maintaining a safety clearance buffer around static rack obstacles.
    """
    def to_cell(pt: Tuple[float, float]) -> Tuple[int, int]:
        return (int(round(pt[0] / grid_step)), int(round(pt[1] / grid_step)))

    def to_world(cell: Tuple[int, int]) -> Tuple[float, float]:
        return (round(cell[0] * grid_step, 2), round(cell[1] * grid_step, 2))

    def is_blocked(cell: Tuple[int, int]) -> bool:
        wx, wy = to_world(cell)
        if wx < 2.0 or wx > 118.0 or wy < 2.0 or wy > 78.0:
            return True
        for ox, oy, rad in WAREHOUSE_OBSTACLES:
            if math.hypot(wx - ox, wy - oy) < (rad + 2.0):
                return True
        return False

    start_c = to_cell(start)
    goal_c = to_cell(goal)
    if start_c == goal_c:
        return [goal]

    open_heap: List[Tuple[float, Tuple[int, int]]] = [(0.0, start_c)]
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], float] = {start_c: 0.0}
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    visited = 0
    while open_heap and visited < 1500:
        visited += 1
        _, current = heapq.heappop(open_heap)
        if current == goal_c:
            path = [goal]
            while current in came_from:
                current = came_from[current]
                path.append(to_world(current))
            path.reverse()
            return path

        for dx, dy in neighbors:
            nxt = (current[0] + dx, current[1] + dy)
            if nxt != goal_c and is_blocked(nxt):
                continue
            step_cost = math.hypot(dx, dy)
            tentative_g = g_score[current] + step_cost
            if tentative_g < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative_g
                h = math.hypot(nxt[0] - goal_c[0], nxt[1] - goal_c[1])
                heapq.heappush(open_heap, (tentative_g + h, nxt))

    return [start, goal]


class WarehousePhysicsSimulator:
    """
    Stateful closed-loop Physical AI simulator for a fleet of 4 Biopharma Cold-Chain AMRs.
    Supports fault injection (cryo-seal breach, compressor bearing cavitation, LiDAR obstruction)
    and closed-loop actuator execution from the AWS Bedrock Multi-Agent Supervisor.
    """

    def __init__(self) -> None:
        self.tick_count: int = 0
        self.temp_histories: Dict[str, List[float]] = {}
        self.fleet: Dict[str, AMRTelemetryFrame] = {}
        self._init_default_fleet()

    def _init_default_fleet(self) -> None:
        configs = [
            {
                "amr_id": "AMR-ALPHA-01",
                "batch_id": "BATCH-MRNA-9041",
                "payload_class": PayloadClass.MRNA_LIPID_NANOPARTICLE,
                "pos": (34.0, 26.0),
                "dest_zone": "OUTBOUND_AIRLOCK_C",
                "temp_c": -61.8,  # Drifting dangerously close to -60.0°C ceiling!
                "rate_c_min": 0.68,
                "vibration_hz": 142.5,
                "seal_kpa": 84.2,
                "ln2_pct": 78.0,
                "battery_pct": 82.0,
                "lidar_m": 3.4,
                "faults": ["CRYO_COMPRESSOR_CAVITATION", "DOOR_GASKET_PRESSURE_DROP"],
            },
            {
                "amr_id": "AMR-BETA-02",
                "batch_id": "BATCH-CART-3310",
                "payload_class": PayloadClass.CAR_T_CELL_THERAPY,
                "pos": (52.0, 44.0),
                "dest_zone": "OUTBOUND_AIRLOCK_C",
                "temp_c": -147.2,  # Exceeded -150.0°C cryogenic threshold!
                "rate_c_min": 1.15,
                "vibration_hz": 98.0,
                "seal_kpa": 76.5,
                "ln2_pct": 64.0,
                "battery_pct": 74.0,
                "lidar_m": 1.1,
                "faults": ["CRYO_THERMAL_EXCURSION", "LIDAR_CORRIDOR_CONGESTION"],
            },
            {
                "amr_id": "AMR-GAMMA-03",
                "batch_id": "BATCH-MAB-7720",
                "payload_class": PayloadClass.MONOCLONAL_ANTIBODY,
                "pos": (72.0, 24.0),
                "dest_zone": "BIOLOGICS_BAY_B",
                "temp_c": -20.1,
                "rate_c_min": 0.02,
                "vibration_hz": 44.0,
                "seal_kpa": 101.3,
                "ln2_pct": 91.0,
                "battery_pct": 89.0,
                "lidar_m": 5.8,
                "faults": [],
            },
            {
                "amr_id": "AMR-DELTA-04",
                "batch_id": "BATCH-VAX-1184",
                "payload_class": PayloadClass.REFRIGERATED_VACCINE,
                "pos": (22.0, 52.0),
                "dest_zone": "OUTBOUND_AIRLOCK_C",
                "temp_c": 4.8,
                "rate_c_min": 0.01,
                "vibration_hz": 39.5,
                "seal_kpa": 101.1,
                "ln2_pct": 95.0,
                "battery_pct": 93.0,
                "lidar_m": 6.2,
                "faults": [],
            },
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        for cfg in configs:
            amr_id = cfg["amr_id"]
            p_class = cfg["payload_class"]
            env = THERMAL_ENVELOPES[p_class]
            self.temp_histories[amr_id] = [env.target_temp_c, cfg["temp_c"]]
            mkt = compute_mean_kinetic_temperature(self.temp_histories[amr_id])
            dest_wp = WAREHOUSE_ZONES[cfg["dest_zone"]]
            dx = dest_wp[0] - cfg["pos"][0]
            dy = dest_wp[1] - cfg["pos"][1]

            self.fleet[amr_id] = AMRTelemetryFrame(
                amr_id=amr_id,
                timestamp_iso=now_iso,
                sequence_num=1,
                battery_soc_pct=cfg["battery_pct"],
                cpu_temp_c=51.2,
                kinematics=KinematicState(
                    x_meters=cfg["pos"][0],
                    y_meters=cfg["pos"][1],
                    heading_rad=round(math.atan2(dy, dx), 3),
                    linear_velocity_mps=1.2 if cfg["lidar_m"] > 1.5 else 0.4,
                    angular_velocity_rps=0.05,
                    lidar_min_obstacle_dist_m=cfg["lidar_m"],
                    wheel_slip_ratio=0.02,
                    destination_zone=cfg["dest_zone"],
                    target_waypoint=dest_wp,
                ),
                cryo=CryoChamberTelemetry(
                    payload_batch_id=cfg["batch_id"],
                    payload_class=p_class,
                    internal_temp_c=cfg["temp_c"],
                    ambient_warehouse_temp_c=18.5,
                    temp_rate_of_change_c_per_min=cfg["rate_c_min"],
                    mean_kinetic_temp_c=mkt,
                    chamber_humidity_pct=32.0,
                    compressor_vibration_hz=cfg["vibration_hz"],
                    door_seal_pressure_kpa=cfg["seal_kpa"],
                    ln2_reserve_pct=cfg["ln2_pct"],
                ),
                active_fault_codes=list(cfg["faults"]),
            )

    def step_physics(self, dt_seconds: float = 10.0) -> List[AMRTelemetryFrame]:
        """Advances the physical warehouse simulation by `dt_seconds`."""
        self.tick_count += 1
        now_iso = datetime.now(timezone.utc).isoformat()
        dt_min = dt_seconds / 60.0

        for amr_id, frame in self.fleet.items():
            frame.sequence_num += 1
            frame.timestamp_iso = now_iso

            # 1. Kinematic integration toward target waypoint
            kin = frame.kinematics
            tx, ty = kin.target_waypoint
            dist = math.hypot(tx - kin.x_meters, ty - kin.y_meters)
            if dist > 0.5 and kin.linear_velocity_mps > 0.0:
                heading = math.atan2(ty - kin.y_meters, tx - kin.x_meters)
                kin.heading_rad = round(heading, 3)
                step_d = min(dist, kin.linear_velocity_mps * dt_seconds)
                kin.x_meters = round(kin.x_meters + step_d * math.cos(heading), 2)
                kin.y_meters = round(kin.y_meters + step_d * math.sin(heading), 2)

            # 2. Thermodynamic integration
            cryo = frame.cryo
            cryo.internal_temp_c = round(
                cryo.internal_temp_c + cryo.temp_rate_of_change_c_per_min * dt_min, 2
            )
            self.temp_histories[amr_id].append(cryo.internal_temp_c)
            if len(self.temp_histories[amr_id]) > 30:
                self.temp_histories[amr_id].pop(0)
            cryo.mean_kinetic_temp_c = compute_mean_kinetic_temperature(self.temp_histories[amr_id])

            # 3. Battery discharge
            frame.battery_soc_pct = round(max(5.0, frame.battery_soc_pct - 0.08 * dt_min), 2)

        return list(self.fleet.values())

    def apply_actuator_command(self, cmd: PhysicalActuatorCommand) -> AMRTelemetryFrame:
        """
        Executes a verified PhysicalActuatorCommand on the target AMR in the simulator,
        modifying its cryo-cooling valves, target waypoint, and velocity envelope.
        """
        frame = self.fleet[cmd.amr_id]
        kin = frame.kinematics
        cryo = frame.cryo
        env = THERMAL_ENVELOPES[cryo.payload_class]

        kin.target_waypoint = cmd.target_waypoint
        kin.linear_velocity_mps = cmd.max_velocity_mps

        # Reverse-lookup zone name if waypoint matches a known landmark
        for z_name, z_coords in WAREHOUSE_ZONES.items():
            if math.hypot(z_coords[0] - cmd.target_waypoint[0], z_coords[1] - cmd.target_waypoint[1]) < 1.0:
                kin.destination_zone = z_name
                break

        if cmd.engage_ln2_backup or cmd.action_type in (
            ActuatorActionType.ENGAGE_BACKUP_LN2_VALVE,
            ActuatorActionType.BOOST_PELTIER_CRYO_COOLING,
            ActuatorActionType.REROUTE_TO_CRYO_DOCK,
        ):
            # Active cryogenic stabilization pulls internal temperature back toward target
            cryo.temp_rate_of_change_c_per_min = -1.45
            cryo.internal_temp_c = round(
                cryo.internal_temp_c + (env.target_temp_c - cryo.internal_temp_c) * 0.35, 2
            )
            cryo.ln2_reserve_pct = round(max(10.0, cryo.ln2_reserve_pct - 3.5), 1)
            if "CRYO_STABILIZATION_ACTIVE" not in frame.active_fault_codes:
                frame.active_fault_codes = [
                    f for f in frame.active_fault_codes if f != "CRYO_THERMAL_EXCURSION"
                ]

        if cmd.action_type == ActuatorActionType.EMERGENCY_STOP:
            kin.linear_velocity_mps = 0.0

        return frame
