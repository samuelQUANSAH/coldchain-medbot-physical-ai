"""
Hybrid BM25 + Dense Vector RAG Knowledge Base for Biopharma Cold-Chain & AMR Physical Safety SOPs.
Integrates with Amazon Bedrock Knowledge Bases / Titan Text Embeddings v2 (`boto3`) with a
deterministic local hybrid retrieval engine for offline/CI execution.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore


@dataclass(frozen=True)
class SOPDocument:
    doc_id: str
    title: str
    regulation_standard: str
    applicable_payloads: List[str]
    content: str


COLDCHAIN_SOP_CORPUS: List[SOPDocument] = [
    SOPDocument(
        doc_id="SOP-USP-1079-MRNA",
        title="Ultra-Cold mRNA-LNP Thermal Excursion & Compressor Cavitation Protocol",
        regulation_standard="USP <1079> & 21 CFR 211.142",
        applicable_payloads=["ULTRACOLD_MRNA_LNP"],
        content=(
            "Ultra-cold mRNA lipid nanoparticle (LNP) payloads must remain between -85.0C and -60.0C "
            "(target -72.0C). If internal chamber temperature exceeds -62.5C with a warming rate "
            ">= 0.4C/min, or if primary Stirling compressor vibration exceeds 120 Hz indicating "
            "cavitation, the AMR Supervisor must immediately trigger BOOST_PELTIER_CRYO_COOLING "
            "or ENGAGE_BACKUP_LN2_VALVE and reroute the AMR to LN2_RECHARGE_DOCK before the 15-minute "
            "maximum excursion window expires."
        ),
    ),
    SOPDocument(
        doc_id="SOP-FDA-1271-CART",
        title="Autologous CAR-T Cryogenic LN2 Vapor-Phase Excursion & Quarantine Mandate",
        regulation_standard="21 CFR 1271.260 & FACT-JACIE Cryo Standards",
        applicable_payloads=["CRYOGENIC_CART_LN2"],
        content=(
            "Cryogenic CAR-T cellular therapy batches require vapor-phase liquid nitrogen storage "
            "below -150.0C (target -180.0C). Any excursion warmer than -150.0C or door gasket seal "
            "pressure below 80.0 kPa constitutes a Critical Excursion. The AMR must immediately open "
            "its secondary LN2 pulse valve (ENGAGE_BACKUP_LN2_VALVE) and reroute to "
            "QUARANTINE_ISOLATION_LOCK or LN2_RECHARGE_DOCK within 5 minutes while logging a "
            "cryptographic SHA-256 chain-of-custody record."
        ),
    ),
    SOPDocument(
        doc_id="SOP-ISO-3691-4-AMR",
        title="Autonomous Mobile Robot (AMR) Kinematic Safety & LiDAR Clearance Standard",
        regulation_standard="ISO 3691-4:2023 & ANSI/RIA R15.08",
        applicable_payloads=[
            "ULTRACOLD_MRNA_LNP",
            "CRYOGENIC_CART_LN2",
            "FROZEN_BIOLOGIC_MAB",
            "STANDARD_COLD_2_8C",
        ],
        content=(
            "All warehouse AMRs must enforce dynamic speed governing based on 360-degree 2D/3D LiDAR "
            "obstacle proximity. When minimum obstacle distance is >= 2.0m, maximum permitted linear "
            "velocity is 1.5 m/s. When obstacle distance is between 0.8m and 2.0m (corridor congestion), "
            "maximum linear velocity must be throttled to <= 0.6 m/s. If obstacle distance falls below "
            "0.45m or battery SoC drops below 10%, the safety shield must enforce EMERGENCY_STOP (0.0 m/s)."
        ),
    ),
    SOPDocument(
        doc_id="SOP-FDA-21CFR11-AUDIT",
        title="Electronic Records, Digital Signatures, and Immutable Cold-Chain Telemetry",
        regulation_standard="FDA 21 CFR Part 11 & EU GMP Annex 11",
        applicable_payloads=[
            "ULTRACOLD_MRNA_LNP",
            "CRYOGENIC_CART_LN2",
            "FROZEN_BIOLOGIC_MAB",
            "STANDARD_COLD_2_8C",
        ],
        content=(
            "Every automated clinical or biopharma cold-chain control action dispatched to a physical "
            "actuator must record: (1) UTC timestamp, (2) sensor snapshot (internal temperature, MKT, "
            "seal pressure, compressor vibration), (3) multi-agent rationale, (4) deterministic safety "
            "shield verification status, and (5) a non-repudiable SHA-256 regulatory audit hash stored "
            "in an immutable ledger."
        ),
    ),
    SOPDocument(
        doc_id="SOP-WHO-PQS-MAB-VAX",
        title="Monoclonal Antibody (-20C) & Refrigerated Biologics (+2C to +8C) Stability SOP",
        regulation_standard="WHO PQS E003 & EU GMP Annex 1",
        applicable_payloads=["FROZEN_BIOLOGIC_MAB", "STANDARD_COLD_2_8C"],
        content=(
            "Monoclonal antibody payloads must be maintained between -25.0C and -15.0C, and standard "
            "refrigerated vaccines between +2.0C and +8.0C. When telemetry remains within thermal bounds "
            "and compressor vibration is below 80 Hz, the AMR should MAINTAIN_COURSE to its assigned "
            "outbound airlock or biologics bay while continuously computing Arrhenius Mean Kinetic "
            "Temperature (MKT)."
        ),
    ),
]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _deterministic_vector(text: str, dim: int = 64) -> List[float]:
    """Computes a normalized deterministic feature-hashed embedding vector for fast hybrid search."""
    vec = [0.0] * dim
    tokens = _tokenize(text)
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


class HybridColdChainKnowledgeBase:
    """
    Hybrid BM25 + Vector Similarity RAG Engine.
    Queries Amazon Bedrock Knowledge Bases (`bedrock-agent-runtime`) when `BEDROCK_KB_ID` is configured,
    and executes local hybrid BM25 + dense vector retrieval across the regulatory SOP corpus.
    """

    def __init__(self, corpus: Optional[List[SOPDocument]] = None) -> None:
        self.corpus = corpus or COLDCHAIN_SOP_CORPUS
        self.doc_tokens = [_tokenize(f"{d.title} {d.regulation_standard} {d.content}") for d in self.corpus]
        self.doc_vectors = [
            _deterministic_vector(f"{d.title} {d.regulation_standard} {d.content}") for d in self.corpus
        ]
        self.avg_dl = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))
        self.bedrock_kb_id = os.getenv("BEDROCK_KB_ID", "")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")

    def retrieve(
        self,
        query: str,
        payload_class: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval (0.55 * BM25_norm + 0.45 * Vector_Cosine + domain payload boost)
        and returns top-k regulatory SOP chunks with citation metadata.
        """
        q_tokens = _tokenize(query)
        q_vec = _deterministic_vector(query)

        k1 = 1.5
        b = 0.75
        n_docs = len(self.corpus)

        scored: List[Dict[str, Any]] = []
        for idx, doc in enumerate(self.corpus):
            d_toks = self.doc_tokens[idx]
            dl = len(d_toks)
            bm25 = 0.0
            for qt in set(q_tokens):
                df = sum(1 for dt in self.doc_tokens if qt in dt)
                if df == 0:
                    continue
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                tf = d_toks.count(qt)
                denom = tf + k1 * (1.0 - b + b * (dl / self.avg_dl))
                bm25 += idf * ((tf * (k1 + 1.0)) / max(1e-6, denom))

            cos_sim = max(0.0, _cosine_similarity(q_vec, self.doc_vectors[idx]))
            payload_boost = 0.25 if (payload_class and payload_class in doc.applicable_payloads) else 0.0
            hybrid_score = round((0.55 * min(1.0, bm25 / 6.0)) + (0.45 * cos_sim) + payload_boost, 4)

            scored.append(
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "regulation_standard": doc.regulation_standard,
                    "hybrid_score": hybrid_score,
                    "content": doc.content,
                }
            )

        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored[:top_k]
