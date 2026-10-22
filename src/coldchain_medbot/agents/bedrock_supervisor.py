"""
Amazon Bedrock Multi-Agent Supervisor (Anthropic Claude 3.5 Sonnet / Converse API).
Coordinates the 4 specialized Physical AI agents, synthesizes neuro-symbolic decisions,
invokes Amazon Bedrock when AWS credentials are active, and guarantees deterministic
safety-shielded actuator command generation in both cloud and edge-offline modes.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    boto3 = None  # type: ignore
    BotoCoreError = Exception  # type: ignore
    ClientError = Exception  # type: ignore

from coldchain_medbot.agents.multicloud_router import MultiCloudModelRouter
from coldchain_medbot.agents.specialist_agents import (
    AMRFleetNavigationAgent,
    CryoThermalDiagnosticsAgent,
    PhysicalSafetyShieldVerifier,
    RegulatoryComplianceRAGAgent,
)
from coldchain_medbot.domain.models import (
    ActuatorActionType,
    AgentAssessment,
    AMRTelemetryFrame,
    ExcursionSeverity,
    PhysicalActuatorCommand,
)
from coldchain_medbot.rag.knowledge_base import HybridColdChainKnowledgeBase


class BedrockPhysicalAISupervisor:
    """
    Multi-Agent Supervisor powered by Amazon Bedrock (`anthropic.claude-3-5-sonnet-20241022-v2:0`)
    with automatic circuit-breaker failover to Google Cloud Vertex AI (`vertex_ai/gemini-2.5-pro`).
    Orchestrates:
      1. CryoThermalDiagnosticsAgent
      2. AMRFleetNavigationAgent
      3. RegulatoryComplianceRAGAgent (Hybrid BM25 + Vector RAG)
      4. PhysicalSafetyShieldVerifier (ISO 3691-4 & 21 CFR Part 11 Guardrail)
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name: Optional[str] = None,
        enable_live_bedrock: Optional[bool] = None,
    ) -> None:
        self.model_id = os.getenv("BEDROCK_MODEL_ID", model_id)
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        if enable_live_bedrock is None:
            self.enable_live_bedrock = os.getenv("ENABLE_LIVE_BEDROCK", "false").lower() == "true"
        else:
            self.enable_live_bedrock = enable_live_bedrock

        self.router = MultiCloudModelRouter(
            primary_bedrock_model=self.model_id,
            aws_region=self.region_name,
            enable_live_cloud=self.enable_live_bedrock,
        )
        self.kb = HybridColdChainKnowledgeBase()
        self.thermal_agent = CryoThermalDiagnosticsAgent()
        self.nav_agent = AMRFleetNavigationAgent()
        self.rag_agent = RegulatoryComplianceRAGAgent(self.kb)
        self.safety_shield = PhysicalSafetyShieldVerifier()

    def orchestrate_amr_decision(self, frame: AMRTelemetryFrame) -> Dict[str, Any]:
        """
        Executes the full 4-agent workflow for a single AMR telemetry frame and returns
        the complete multi-agent trace, multi-cloud router telemetry, and the safety-verified
        PhysicalActuatorCommand.
        """
        t0 = time.perf_counter()

        # Step 1: Cryo-Thermal Diagnostics Subagent
        thermal_res = self.thermal_agent.evaluate(frame)

        # Step 2: AMR Fleet Kinematic & A* Navigation Subagent
        nav_res = self.nav_agent.evaluate(frame, thermal_res)

        # Step 3: Regulatory & SOP Compliance Hybrid RAG Subagent
        rag_res = self.rag_agent.evaluate(frame, thermal_res)

        assessments = [thermal_res, nav_res, rag_res]

        # Step 4: Supervisor Decision Synthesis via Multi-Cloud Router (Amazon Bedrock -> Vertex AI Failover)
        proposed_action = thermal_res.recommended_action
        if nav_res.recommended_action == ActuatorActionType.EMERGENCY_STOP:
            proposed_action = ActuatorActionType.EMERGENCY_STOP
        elif (
            thermal_res.severity in (ExcursionSeverity.CRITICAL_EXCURSION, ExcursionSeverity.WARNING)
            and nav_res.recommended_action == ActuatorActionType.REROUTE_TO_CRYO_DOCK
        ):
            proposed_action = ActuatorActionType.REROUTE_TO_CRYO_DOCK

        target_wp_list = nav_res.metrics["target_waypoint"]
        target_wp: Tuple[float, float] = (float(target_wp_list[0]), float(target_wp_list[1]))
        rec_vel = float(nav_res.metrics["recommended_velocity_mps"])

        citations_str = ", ".join(rag_res.citations)
        default_rationale = (
            f"[Bedrock Supervisor ({self.model_id})] Synthesized {thermal_res.severity.value} "
            f"state for {frame.amr_id} ({frame.cryo.payload_batch_id}): {thermal_res.summary} "
            f"Executing {proposed_action.value} toward {nav_res.metrics['assigned_zone']} "
            f"at {rec_vel} m/s per {citations_str}."
        )
        system_prompt = (
            "You are the Amazon Bedrock Physical AI Supervisor for an autonomous biopharma "
            "cold-chain warehouse AMR fleet. Synthesize the specialist subagent assessments "
            "into a concise 2-sentence operational directive citing the regulatory standard."
        )
        routed = self.router.route_supervisor_synthesis(
            system_prompt=system_prompt,
            payload_dict={
                "amr_id": frame.amr_id,
                "batch_id": frame.cryo.payload_batch_id,
                "subagent_assessments": [asdict(a) for a in assessments],
            },
            deterministic_fallback_text=default_rationale,
        )
        supervisor_rationale = routed["text"]

        # Step 5: Deterministic Physical Safety Shield Verification
        verified_cmd: PhysicalActuatorCommand = self.safety_shield.verify_and_build_command(
            frame=frame,
            proposed_action=proposed_action,
            target_waypoint=target_wp,
            proposed_velocity_mps=rec_vel,
            supervisor_rationale=supervisor_rationale,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return {
            "amr_id": frame.amr_id,
            "severity": thermal_res.severity.value,
            "orchestration_latency_ms": latency_ms,
            "multicloud_inference": routed["telemetry"],
            "subagent_traces": [
                {
                    "agent_name": a.agent_name,
                    "severity": a.severity.value,
                    "confidence_score": a.confidence_score,
                    "summary": a.summary,
                    "recommended_action": a.recommended_action.value,
                    "citations": a.citations,
                    "metrics": a.metrics,
                }
                for a in assessments
            ],
            "actuator_command": verified_cmd.to_dict(),
            "command_object": verified_cmd,
        }
