"""
CLI Runner for ColdChain-MedBot Physical AI Multi-Agent Supervisor.
Executes closed-loop edge-to-cloud simulation cycles and prints structured telemetry,
subagent assessments, AWS IoT TwinMaker states, and FDA 21 CFR Part 11 SHA-256 hashes.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from coldchain_medbot.agents.bedrock_supervisor import BedrockPhysicalAISupervisor
from coldchain_medbot.aws.iot_twin_bridge import AWSPhysicalAICloudBridge
from coldchain_medbot.simulation.edge_physics_engine import WarehousePhysicsSimulator


def run_simulation_cycles(cycles: int = 2, dt_seconds: float = 10.0, as_json: bool = False) -> List[Dict[str, Any]]:
    sim = WarehousePhysicsSimulator()
    sup = BedrockPhysicalAISupervisor()
    bridge = AWSPhysicalAICloudBridge()

    all_history: List[Dict[str, Any]] = []

    for c in range(1, cycles + 1):
        frames = sim.step_physics(dt_seconds=dt_seconds)
        cycle_log: List[Dict[str, Any]] = []

        if not as_json:
            print("=" * 104)
            print(
                f"PHYSICAL AI CLOSED-LOOP CYCLE #{c} | Model: {sup.model_id} | "
                f"TwinMaker Workspace: {bridge.twinmaker_workspace_id}"
            )
            print("=" * 104)

        for frame in frames:
            pre_temp = frame.cryo.internal_temp_c
            pre_zone = frame.kinematics.destination_zone

            res = sup.orchestrate_amr_decision(frame)
            cmd = res.pop("command_object")
            sev = res["severity"]

            bridge.publish_iot_core_shadow(frame, cmd)
            bridge.sync_twinmaker_digital_twin(frame, sev, cmd)
            bridge.record_dynamodb_audit_entry(frame, sev, cmd)
            sfn = bridge.trigger_step_functions_if_needed(frame, sev, cmd)

            updated = sim.apply_actuator_command(cmd)
            res["pre_temp_c"] = pre_temp
            res["post_temp_c"] = updated.cryo.internal_temp_c
            res["pre_zone"] = pre_zone
            res["post_zone"] = updated.kinematics.destination_zone
            res["sfn_execution_arn"] = sfn["executionArn"] if sfn else "NONE"
            cycle_log.append(res)

            if not as_json:
                print(
                    f"[{frame.amr_id}] Batch={frame.cryo.payload_batch_id} ({frame.cryo.payload_class.value}) | "
                    f"Severity={sev}"
                )
                print(
                    f"  • Telemetry : Pose=({frame.kinematics.x_meters}m, {frame.kinematics.y_meters}m) | "
                    f"LiDAR={frame.kinematics.lidar_min_obstacle_dist_m}m | "
                    f"Temp={pre_temp}C -> {updated.cryo.internal_temp_c}C (MKT={frame.cryo.mean_kinetic_temp_c}C) | "
                    f"Vib={frame.cryo.compressor_vibration_hz}Hz"
                )
                for trace in res["subagent_traces"]:
                    print(f"  • [{trace['agent_name']}] {trace['summary']}")
                print(
                    f"  • [PhysicalSafetyShieldVerifier] Action={cmd.action_type.value} | "
                    f"Route={pre_zone} -> {updated.kinematics.destination_zone} | "
                    f"MaxVel={cmd.max_velocity_mps}m/s | LN2_Valve={cmd.engage_ln2_backup}"
                )
                print(
                    f"  • [AWS Cloud Sync] IoT Shadow=$aws/things/{frame.amr_id}/shadow/update | "
                    f"21CFR11_SHA256={cmd.regulatory_audit_hash[:20]}... | "
                    f"StepFn={res['sfn_execution_arn']}"
                )
                print("-" * 104)

        all_history.append({"cycle": c, "decisions": cycle_log})

    if as_json:
        print(json.dumps(all_history, indent=2))
    return all_history


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ColdChain-MedBot Physical AI Multi-Agent Supervisor simulation."
    )
    parser.add_argument("--cycles", type=int, default=2, help="Number of closed-loop simulation cycles")
    parser.add_argument("--dt", type=float, default=10.0, help="Physics timestep in seconds")
    parser.add_argument("--json", action="store_true", help="Output full trace as JSON")
    args = parser.parse_args()
    run_simulation_cycles(cycles=args.cycles, dt_seconds=args.dt, as_json=args.json)


if __name__ == "__main__":
    main()
