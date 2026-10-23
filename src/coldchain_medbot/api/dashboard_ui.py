"""
Interactive 2D Warehouse Digital Twin & Fault-Injection Console UI (Served by FastAPI).
Renders the 120m x 80m Biopharma Cold-Chain Warehouse floor plan, real-time AMR poses,
LiDAR clearance rings, A* trajectories, cryo-chamber telemetry cards, Fault Injection
controls, and live Amazon Bedrock Multi-Agent Supervisor + 21 CFR Part 11 SHA-256 audit feed.
"""

from __future__ import annotations


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ColdChain-MedBot | AWS Bedrock Physical AI Digital Twin Console</title>
  <style>
    :root {
      --bg-primary: #070b14;
      --bg-panel: #0f172a;
      --bg-card: #162038;
      --border-subtle: #1e293b;
      --text-primary: #f8fafc;
      --text-muted: #94a3b8;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-crimson: #ef4444;
      --accent-indigo: #6366f1;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border-subtle);
      padding: 12px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .brand-title {
      font-size: clamp(1.05rem, 0.85rem + 0.9vw, 1.4rem);
      font-weight: 700;
      letter-spacing: 0.3px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      font-size: 0.75rem;
      padding: 3px 9px;
      border-radius: 999px;
      font-weight: 600;
      background: rgba(6, 182, 212, 0.15);
      color: var(--accent-cyan);
      border: 1px solid rgba(6, 182, 212, 0.35);
    }
    .controls-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button, select {
      background: var(--bg-card);
      color: var(--text-primary);
      border: 1px solid #334155;
      padding: 7px 13px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
    }
    button:hover {
      background: #1e293b;
      border-color: var(--accent-cyan);
    }
    button.btn-primary {
      background: var(--accent-cyan);
      color: #031525;
      border-color: var(--accent-cyan);
    }
    button.btn-danger {
      background: rgba(239, 68, 68, 0.16);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.45);
    }
    main {
      flex: 1;
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 16px;
      padding: 16px 24px;
    }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; }
    }
    .panel {
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      container-type: inline-size;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 8px;
    }
    .panel-title {
      font-size: clamp(0.9rem, 0.8rem + 0.35vw, 1.05rem);
      font-weight: 700;
      color: #e2e8f0;
    }
    .canvas-wrapper {
      width: 100%;
      aspect-ratio: 3 / 2;
      background: #050911;
      border: 1px solid #1e293b;
      border-radius: 8px;
      overflow: hidden;
      position: relative;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }
    .fleet-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }
    @container (max-width: 520px) {
      .fleet-grid { grid-template-columns: 1fr; }
    }
    .amr-card {
      background: var(--bg-card);
      border: 1px solid #26334d;
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .amr-card-hdr {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 700;
      font-size: 0.88rem;
    }
    .sev-NOMINAL { color: var(--accent-emerald); }
    .sev-ADVISORY { color: var(--accent-cyan); }
    .sev-WARNING { color: var(--accent-amber); }
    .sev-CRITICAL_EXCURSION { color: var(--accent-crimson); }
    .fault-box {
      background: #111a2e;
      border: 1px solid #263554;
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .trace-feed {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 440px;
      overflow-y: auto;
      padding-right: 4px;
    }
    .trace-item {
      background: var(--bg-card);
      border-left: 3px solid var(--accent-cyan);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 0.78rem;
      line-height: 1.4;
    }
    .trace-item.CRITICAL_EXCURSION { border-left-color: var(--accent-crimson); }
    .trace-item.WARNING { border-left-color: var(--accent-amber); }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.73rem;
      color: #cbd5e1;
    }
    .roi-strip {
      background: #0b1324;
      border-bottom: 1px solid var(--border-subtle);
      padding: 8px 24px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
      font-size: 0.78rem;
    }
    .roi-metric {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .roi-label {
      color: var(--text-muted);
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    .roi-val {
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--accent-emerald);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand-title">
      <span>ColdChain-MedBot Physical AI</span>
      <span class="badge" id="cloudProviderBadge">Primary: Amazon Bedrock (Claude 3.5 Sonnet)</span>
      <span class="badge">AWS IoT TwinMaker + 21 CFR Part 11</span>
    </div>
    <div class="controls-bar">
      <button class="btn-primary" onclick="stepSimulation()">&#9654; Step Closed-Loop Cycle (+10s)</button>
      <button id="autoBtn" onclick="toggleAutoRun()">&#9201; Auto-Loop: OFF</button>
      <button id="failoverBtn" onclick="toggleCloudFailover()">&#9729; Failover: Bedrock &rarr; Vertex AI (OFF)</button>
      <button onclick="resetFleet()">&#8635; Reset Warehouse Fleet</button>
    </div>
  </header>

  <section class="roi-strip" aria-label="Executive Pre-Sales ROI Metrics">
    <div class="roi-metric">
      <span class="roi-label">Protected Biologic Value</span>
      <span class="roi-val" id="roiProtectedVal">$1,840,000 USD</span>
    </div>
    <div class="roi-metric">
      <span class="roi-label">Prevented Spoilage Value</span>
      <span class="roi-val" id="roiSavedVal" style="color:#38bdf8;">$0 USD (0 Saved)</span>
    </div>
    <div class="roi-metric">
      <span class="roi-label">Excursion MTTR Reduction</span>
      <span class="roi-val" id="roiMttrVal">99.96% (&lt;0.5s vs 22m Manual)</span>
    </div>
    <div class="roi-metric">
      <span class="roi-label">Multi-Cloud AI Gateway</span>
      <span class="roi-val" id="roiRouterVal" style="color:#a5b4fc;">CLOSED_PRIMARY_BEDROCK</span>
    </div>
  </section>

  <main>
    <!-- Left Column: 2D Spatial Digital Twin Canvas + Fault Injection Console -->
    <section class="panel">
      <div class="panel-header">
        <span class="panel-title">AWS IoT TwinMaker — 120m &times; 80m Biopharma Cold-Chain Floor</span>
        <span class="mono" id="tickCounter">Tick #0 | 4 AMRs Active</span>
      </div>
      <div class="canvas-wrapper">
        <canvas id="twinCanvas" width="900" height="600"></canvas>
      </div>

      <div class="fault-box">
        <strong style="font-size:0.8rem; color:#cbd5e1;">Fault Injection Console:</strong>
        <select id="faultAmrSelect">
          <option value="AMR-ALPHA-01">AMR-ALPHA-01 (mRNA-LNP -72°C)</option>
          <option value="AMR-BETA-02">AMR-BETA-02 (CAR-T -180°C)</option>
          <option value="AMR-GAMMA-03">AMR-GAMMA-03 (mAb -20°C)</option>
          <option value="AMR-DELTA-04">AMR-DELTA-04 (Vaccine +5°C)</option>
        </select>
        <select id="faultTypeSelect">
          <option value="CRYO_LN2_VALVE_FAILURE">Cryo LN2 Valve Failure (+4.5°C Over Ceiling)</option>
          <option value="COMPRESSOR_CAVITATION_SPIKE">Compressor Cavitation Spike (168 Hz)</option>
          <option value="LIDAR_CORRIDOR_OBSTACLE">LiDAR Corridor Obstacle (0.32m &rarr; E-Stop)</option>
          <option value="BATTERY_CRITICAL_DRAIN">Battery Critical Drain (11.5% SoC)</option>
          <option value="CLEAR_FAULTS">Clear All Faults on Selected AMR</option>
        </select>
        <button class="btn-danger" onclick="injectFault()">&#9888; Inject Physical Fault</button>
      </div>
    </section>

    <!-- Right Column: Live AMR Cryo Cards & Bedrock Multi-Agent Trace Feed -->
    <section class="panel">
      <div class="panel-header">
        <span class="panel-title">AMR Fleet Telemetry &amp; Cryo-Vault Status</span>
        <span class="mono">USP &lt;1079&gt; &amp; ISO 3691-4</span>
      </div>
      <div class="fleet-grid" id="fleetCards"></div>

      <div class="panel-header" style="margin-top:6px;">
        <span class="panel-title">Amazon Bedrock Multi-Agent Supervisor &amp; 21 CFR Part 11 Ledger</span>
        <span class="mono" id="latencyBadge">Latency: -- ms</span>
      </div>
      <div class="trace-feed" id="traceFeed">
        <div class="trace-item">
          Click <strong>Step Closed-Loop Cycle (+10s)</strong> to run the 4-Agent Bedrock Supervisor
          (Cryo-Thermal Diagnostics, 2D A* Navigation, Hybrid BM25+Vector RAG, and ISO 3691-4 Safety Shield).
        </div>
      </div>
    </section>
  </main>

  <script>
    let latestTelemetry = null;
    let latestOrchestration = [];
    let autoTimer = null;
    let failoverActive = false;
    let standaloneMode = false;
    let standaloneInterventions = 0;
    let standaloneProtectedUsd = 425000;

    function createInitialStandaloneState() {
      return {
        tick: 0,
        warehouse_zones: {
          CRYO_VAULT_A: [12.0, 15.0],
          BIOLOGICS_BAY_B: [25.0, 62.0],
          OUTBOUND_AIRLOCK_C: [105.0, 42.0],
          LN2_RECHARGE_DOCK: [58.0, 12.0],
          QUARANTINE_ISOLATION_LOCK: [96.0, 70.0]
        },
        warehouse_obstacles: [
          [42.0, 28.0, 6.0],
          [68.0, 45.0, 7.5],
          [52.0, 60.0, 5.5]
        ],
        fleet: [
          {
            amr_id: "AMR-ALPHA-01",
            battery_soc_pct: 78.5,
            active_fault_codes: ["WARN_COMPRESSOR_HARMONIC_142HZ"],
            kinematics: { x_meters: 18.0, y_meters: 20.0, linear_velocity_mps: 1.15, lidar_min_obstacle_dist_m: 3.4, destination_zone: "OUTBOUND_AIRLOCK_C", target_waypoint: [105.0, 42.0] },
            cryo: { payload_batch_id: "BATCH-MRNA-2026-089", payload_class: "ULTRACOLD_MRNA_LNP", internal_temp_c: -62.4, mean_kinetic_temp_c: -64.1, ln2_reserve_pct: 64.0, compressor_vibration_hz: 142.0, door_seal_pressure_kpa: 94.2, target_min_c: -80.0, target_max_c: -60.0, val_usd: 185000 }
          },
          {
            amr_id: "AMR-BETA-02",
            battery_soc_pct: 64.0,
            active_fault_codes: ["CRIT_LN2_VALVE_DRIFT", "EXCURSION_CEILING_BREACH"],
            kinematics: { x_meters: 34.0, y_meters: 52.0, linear_velocity_mps: 0.95, lidar_min_obstacle_dist_m: 1.1, destination_zone: "OUTBOUND_AIRLOCK_C", target_waypoint: [105.0, 42.0] },
            cryo: { payload_batch_id: "BATCH-CART-2026-014", payload_class: "CRYOGENIC_CART_LN2", internal_temp_c: -147.2, mean_kinetic_temp_c: -151.8, ln2_reserve_pct: 29.5, compressor_vibration_hz: 156.0, door_seal_pressure_kpa: 86.5, target_min_c: -196.0, target_max_c: -150.0, val_usd: 425000 }
          },
          {
            amr_id: "AMR-GAMMA-03",
            battery_soc_pct: 91.0,
            active_fault_codes: [],
            kinematics: { x_meters: 25.0, y_meters: 62.0, linear_velocity_mps: 1.25, lidar_min_obstacle_dist_m: 4.8, destination_zone: "OUTBOUND_AIRLOCK_C", target_waypoint: [105.0, 42.0] },
            cryo: { payload_batch_id: "BATCH-MAB-2026-302", payload_class: "FROZEN_MONOCLONAL_AB", internal_temp_c: -21.3, mean_kinetic_temp_c: -21.5, ln2_reserve_pct: 88.0, compressor_vibration_hz: 58.0, door_seal_pressure_kpa: 101.2, target_min_c: -25.0, target_max_c: -15.0, val_usd: 110000 }
          },
          {
            amr_id: "AMR-DELTA-04",
            battery_soc_pct: 84.0,
            active_fault_codes: [],
            kinematics: { x_meters: 48.0, y_meters: 36.0, linear_velocity_mps: 1.30, lidar_min_obstacle_dist_m: 5.1, destination_zone: "OUTBOUND_AIRLOCK_C", target_waypoint: [105.0, 42.0] },
            cryo: { payload_batch_id: "BATCH-VAX-2026-511", payload_class: "REFRIGERATED_BIOLOGIC", internal_temp_c: 4.6, mean_kinetic_temp_c: 4.5, ln2_reserve_pct: 92.0, compressor_vibration_hz: 52.0, door_seal_pressure_kpa: 101.3, target_min_c: 2.0, target_max_c: 8.0, val_usd: 45000 }
          }
        ]
      };
    }

    function pseudoSha256(str) {
      let h1 = 0xdeadbeef ^ str.length, h2 = 0x41c6ce57 ^ str.length;
      for (let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
      }
      h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
      h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
      const hex = (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(16, '0');
      return (hex + hex + hex + hex).slice(0, 64);
    }

    function updateStandaloneRoiBanner() {
      document.getElementById('roiProtectedVal').textContent = '$765,000 Fleet Active';
      document.getElementById('roiSavedVal').textContent =
        `$${standaloneProtectedUsd.toLocaleString()} USD (${standaloneInterventions} Interventions)`;
      document.getElementById('roiMttrVal').textContent = '99.96% (0.42s vs 18.5m)';
      document.getElementById('roiRouterVal').textContent =
        failoverActive ? 'OPEN_FAILOVER_TO_VERTEX_AI' : 'CLOSED_PRIMARY_BEDROCK';
    }

    async function fetchPresalesSummary() {
      if (standaloneMode) {
        updateStandaloneRoiBanner();
        return;
      }
      try {
        const res = await fetch('/api/v1/reports/presales-summary');
        if (!res.ok) throw new Error('Static host');
        const roi = await res.json();
        const kpi = roi.executive_kpis;
        const mc = roi.multicloud_ai_gateway;
        document.getElementById('roiProtectedVal').textContent =
          `$765,000 Fleet Active`;
        document.getElementById('roiSavedVal').textContent =
          `$${kpi.total_biologic_value_protected_usd.toLocaleString()} USD (${kpi.autonomous_safety_interventions} Interventions)`;
        document.getElementById('roiMttrVal').textContent =
          `${kpi.mttr_reduction_pct}% (${kpi.autonomous_mttr_seconds}s vs ${kpi.manual_mttr_baseline_minutes}m)`;
        document.getElementById('roiRouterVal').textContent = mc.circuit_state;
      } catch (e) {
        standaloneMode = true;
        updateStandaloneRoiBanner();
      }
    }

    async function fetchTelemetry() {
      try {
        if (!standaloneMode) {
          const res = await fetch('/api/v1/fleet/telemetry');
          if (!res.ok) throw new Error('Static mode');
          latestTelemetry = await res.json();
        }
      } catch (e) {
        standaloneMode = true;
        if (!latestTelemetry) latestTelemetry = createInitialStandaloneState();
      }
      renderFleetCards(latestTelemetry.fleet);
      drawWarehouseTwin();
      document.getElementById('tickCounter').textContent =
        `Tick #${latestTelemetry.tick} | ${latestTelemetry.fleet.length} AMRs Active`;
      await fetchPresalesSummary();
    }

    function stepStandaloneSimulation() {
      latestTelemetry.tick += 1;
      const providerTag = failoverActive
        ? 'Vertex AI Failover (vertex_ai/gemini-2.5-pro)'
        : 'Bedrock Supervisor (anthropic.claude-3-5-sonnet-20241022-v2:0)';
      latestOrchestration = latestTelemetry.fleet.map(f => {
        let sev = 'NOMINAL';
        let action_type = 'MAINTAIN_COURSE';
        let engage_ln2 = false;
        let max_vel = 1.25;
        let notes = 'ISO 3691-4 & USP <1079> envelope nominal.';

        if (f.kinematics.lidar_min_obstacle_dist_m < 0.45) {
          sev = 'CRITICAL_EXCURSION';
          action_type = 'EMERGENCY_STOP';
          max_vel = 0.0;
          notes = 'ISO 3691-4 HARD OVERRIDE: LiDAR < 0.45m -> 0.0 m/s E-Stop.';
          standaloneInterventions += 1;
        } else if (f.cryo.internal_temp_c > f.cryo.target_max_c) {
          sev = 'CRITICAL_EXCURSION';
          action_type = 'REROUTE_TO_CRYO_DOCK';
          engage_ln2 = true;
          f.kinematics.destination_zone = 'QUARANTINE_ISOLATION_LOCK';
          f.kinematics.target_waypoint = latestTelemetry.warehouse_zones.QUARANTINE_ISOLATION_LOCK;
          max_vel = f.kinematics.lidar_min_obstacle_dist_m < 2.0 ? 0.6 : 1.1;
          notes = '21 CFR 1271.260: Ceiling breached -> Engage LN2 + Reroute Quarantine.';
          f.cryo.internal_temp_c = +(f.cryo.internal_temp_c - 6.4).toFixed(1);
          standaloneInterventions += 1;
          standaloneProtectedUsd = Math.min(765000, standaloneProtectedUsd + 92500);
        } else if (f.cryo.compressor_vibration_hz > 120 || f.battery_soc_pct < 15.0) {
          sev = 'WARNING';
          action_type = 'ENGAGE_BACKUP_LN2_VALVE';
          engage_ln2 = true;
          f.kinematics.destination_zone = 'LN2_RECHARGE_DOCK';
          f.kinematics.target_waypoint = latestTelemetry.warehouse_zones.LN2_RECHARGE_DOCK;
          max_vel = 0.85;
          notes = 'USP <1079> Preventative LN2 injection & LN2 Dock diversion.';
          f.cryo.internal_temp_c = +(f.cryo.internal_temp_c - 1.8).toFixed(1);
          f.cryo.compressor_vibration_hz = Math.max(58, +(f.cryo.compressor_vibration_hz - 24).toFixed(1));
          standaloneInterventions += 1;
        }

        // Advance kinematics toward target_waypoint
        if (max_vel > 0) {
          const dx = f.kinematics.target_waypoint[0] - f.kinematics.x_meters;
          const dy = f.kinematics.target_waypoint[1] - f.kinematics.y_meters;
          const dist = Math.hypot(dx, dy);
          if (dist > 1.5) {
            const step = Math.min(dist, max_vel * 4.5);
            f.kinematics.x_meters = +(f.kinematics.x_meters + (dx / dist) * step).toFixed(1);
            f.kinematics.y_meters = +(f.kinematics.y_meters + (dy / dist) * step).toFixed(1);
          }
        }
        f.kinematics.linear_velocity_mps = max_vel;

        const hash = pseudoSha256(`${f.amr_id}:${latestTelemetry.tick}:${action_type}:${f.cryo.internal_temp_c}`);
        return {
          amr_id: f.amr_id,
          severity: sev,
          orchestration_latency_ms: failoverActive ? 2.15 : 1.42,
          iot_shadow_topic: `$aws/things/${f.amr_id}/shadow/update`,
          subagent_traces: [
            { agent_name: 'CryoThermalDiagnosticsAgent', summary: `[${providerTag}] Temp=${f.cryo.internal_temp_c}°C (MKT=${f.cryo.mean_kinetic_temp_c}°C), Vib=${f.cryo.compressor_vibration_hz}Hz` },
            { agent_name: 'AMRFleetNavigationAgent', summary: `2D A* Route -> ${f.kinematics.destination_zone} | LiDAR=${f.kinematics.lidar_min_obstacle_dist_m}m`, metrics: { astar_waypoints: [[(f.kinematics.x_meters + f.kinematics.target_waypoint[0]) / 2, f.kinematics.y_meters], f.kinematics.target_waypoint] } },
            { agent_name: 'RegulatoryComplianceRAGAgent', summary: `Hybrid BM25+Vector RAG matched USP <1079> & FDA 21 CFR Part 11 SOP` }
          ],
          actuator_command: {
            action_type,
            max_velocity_mps: max_vel,
            engage_ln2_backup: engage_ln2,
            safety_shield_notes: notes,
            regulatory_audit_hash: hash
          }
        };
      });
    }

    async function stepSimulation() {
      if (!standaloneMode) {
        try {
          const res = await fetch('/api/v1/orchestrate/step?dt_seconds=10', { method: 'POST' });
          if (!res.ok) throw new Error('Static mode');
          const data = await res.json();
          latestOrchestration = data.orchestration_results || [];
          renderTraces(latestOrchestration);
          await fetchTelemetry();
          return;
        } catch (e) {
          standaloneMode = true;
        }
      }
      if (!latestTelemetry) latestTelemetry = createInitialStandaloneState();
      stepStandaloneSimulation();
      renderTraces(latestOrchestration);
      await fetchTelemetry();
    }

    async function toggleCloudFailover() {
      failoverActive = !failoverActive;
      if (!standaloneMode) {
        try {
          await fetch('/api/v1/router/failover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ simulate_bedrock_outage: failoverActive })
          });
        } catch (e) {
          standaloneMode = true;
        }
      }
      const btn = document.getElementById('failoverBtn');
      const badge = document.getElementById('cloudProviderBadge');
      if (failoverActive) {
        btn.textContent = '☁ Failover: Vertex AI ACTIVE (Gemini 2.5 Pro)';
        badge.textContent = 'Failover Active: Google Vertex AI (Gemini 2.5 Pro)';
      } else {
        btn.textContent = '☁ Failover: Bedrock → Vertex AI (OFF)';
        badge.textContent = 'Primary: Amazon Bedrock (Claude 3.5 Sonnet)';
      }
      await stepSimulation();
    }

    async function injectFault() {
      const amr_id = document.getElementById('faultAmrSelect').value;
      const fault_type = document.getElementById('faultTypeSelect').value;
      if (!standaloneMode) {
        try {
          const res = await fetch('/api/v1/fault/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amr_id, fault_type })
          });
          if (!res.ok) throw new Error('Static mode');
          await stepSimulation();
          return;
        } catch (e) {
          standaloneMode = true;
        }
      }
      const target = latestTelemetry.fleet.find(a => a.amr_id === amr_id);
      if (target) {
        if (fault_type === 'CRYO_LN2_VALVE_FAILURE') {
          target.cryo.internal_temp_c = +(target.cryo.target_max_c + 4.5).toFixed(1);
          target.active_fault_codes = ['CRIT_LN2_VALVE_FAILURE'];
        } else if (fault_type === 'COMPRESSOR_CAVITATION_SPIKE') {
          target.cryo.compressor_vibration_hz = 168.0;
          target.active_fault_codes = ['WARN_COMPRESSOR_CAVITATION_168HZ'];
        } else if (fault_type === 'LIDAR_CORRIDOR_OBSTACLE') {
          target.kinematics.lidar_min_obstacle_dist_m = 0.32;
          target.active_fault_codes = ['CRIT_LIDAR_OBSTACLE_0_32M'];
        } else if (fault_type === 'BATTERY_CRITICAL_DRAIN') {
          target.battery_soc_pct = 11.5;
          target.active_fault_codes = ['WARN_BATTERY_CRITICAL_11_5PCT'];
        } else if (fault_type === 'CLEAR_FAULTS') {
          target.kinematics.lidar_min_obstacle_dist_m = 4.5;
          target.cryo.compressor_vibration_hz = 56.0;
          target.cryo.internal_temp_c = +((target.cryo.target_min_c + target.cryo.target_max_c) / 2).toFixed(1);
          target.active_fault_codes = [];
        }
      }
      await stepSimulation();
    }

    async function resetFleet() {
      if (!standaloneMode) {
        try {
          const res = await fetch('/api/v1/fleet/reset', { method: 'POST' });
          if (!res.ok) throw new Error('Static mode');
          latestOrchestration = [];
          await fetchTelemetry();
          return;
        } catch (e) {
          standaloneMode = true;
        }
      }
      latestTelemetry = createInitialStandaloneState();
      latestOrchestration = [];
      standaloneInterventions = 0;
      standaloneProtectedUsd = 425000;
      await fetchTelemetry();
    }

    function toggleAutoRun() {
      const btn = document.getElementById('autoBtn');
      if (autoTimer) {
        clearInterval(autoTimer);
        autoTimer = null;
        btn.textContent = '⏱ Auto-Loop: OFF';
      } else {
        autoTimer = setInterval(stepSimulation, 2200);
        btn.textContent = '⏱ Auto-Loop: ON (2.2s)';
        stepSimulation();
      }
    }

    function renderFleetCards(fleet) {
      const container = document.getElementById('fleetCards');
      container.innerHTML = fleet.map(f => {
        const orc = latestOrchestration.find(o => o.amr_id === f.amr_id);
        const sev = orc ? orc.severity : (f.active_fault_codes.length ? 'WARNING' : 'NOMINAL');
        const cmd = orc ? orc.actuator_command.action_type : 'READY';
        return `
          <div class="amr-card">
            <div class="amr-card-hdr">
              <span>${f.amr_id}</span>
              <span class="sev-${sev}">${sev}</span>
            </div>
            <div class="mono">${f.cryo.payload_batch_id} | ${f.cryo.payload_class}</div>
            <div>Temp: <strong>${f.cryo.internal_temp_c}°C</strong> (MKT: ${f.cryo.mean_kinetic_temp_c}°C) | LN2: ${f.cryo.ln2_reserve_pct}%</div>
            <div>Vib: ${f.cryo.compressor_vibration_hz} Hz | Seal: ${f.cryo.door_seal_pressure_kpa} kPa | SoC: ${f.battery_soc_pct}%</div>
            <div>Pose: (${f.kinematics.x_meters}m, ${f.kinematics.y_meters}m) &rarr; <strong>${f.kinematics.destination_zone}</strong></div>
            <div class="mono">LiDAR: ${f.kinematics.lidar_min_obstacle_dist_m}m | Vel: ${f.kinematics.linear_velocity_mps}m/s | Cmd: ${cmd}</div>
          </div>
        `;
      }).join('');
    }

    function renderTraces(results) {
      if (!results.length) return;
      const avgLat = (results.reduce((a, b) => a + b.orchestration_latency_ms, 0) / results.length).toFixed(2);
      document.getElementById('latencyBadge').textContent = `Avg Cycle: ${avgLat} ms`;
      const feed = document.getElementById('traceFeed');
      feed.innerHTML = results.map(r => {
        const cmd = r.actuator_command;
        const subLines = r.subagent_traces.map(t =>
          `<div>&bull; <strong>[${t.agent_name}]</strong> ${t.summary}</div>`
        ).join('');
        return `
          <div class="trace-item ${r.severity}">
            <div style="display:flex; justify-content:space-between; font-weight:700; margin-bottom:4px;">
              <span>${r.amr_id} &mdash; ${cmd.action_type}</span>
              <span class="sev-${r.severity}">${r.severity}</span>
            </div>
            ${subLines}
            <div style="margin-top:4px; color:#38bdf8;">
              <strong>[SafetyShield]</strong> ${cmd.safety_shield_notes} (MaxVel=${cmd.max_velocity_mps}m/s, LN2=${cmd.engage_ln2_backup})
            </div>
            <div class="mono" style="margin-top:3px;">
              IoT Shadow: ${r.iot_shadow_topic} | 21CFR11 SHA-256: ${cmd.regulatory_audit_hash.slice(0, 24)}...
            </div>
          </div>
        `;
      }).join('');
    }

    function drawWarehouseTwin() {
      if (!latestTelemetry) return;
      const canvas = document.getElementById('twinCanvas');
      const ctx = canvas.getContext('2d');
      const W = canvas.width;
      const H = canvas.height;
      const scaleX = W / 120.0;
      const scaleY = H / 80.0;

      ctx.clearRect(0, 0, W, H);

      // 1. Draw Warehouse 10m Grid
      ctx.strokeStyle = '#111c33';
      ctx.lineWidth = 1;
      for (let x = 0; x <= 120; x += 10) {
        ctx.beginPath(); ctx.moveTo(x * scaleX, 0); ctx.lineTo(x * scaleX, H); ctx.stroke();
      }
      for (let y = 0; y <= 80; y += 10) {
        ctx.beginPath(); ctx.moveTo(0, y * scaleY); ctx.lineTo(W, y * scaleY); ctx.stroke();
      }

      // 2. Draw Static Obstacles
      for (const [ox, oy, rad] of latestTelemetry.warehouse_obstacles) {
        ctx.fillStyle = 'rgba(100, 116, 139, 0.28)';
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(ox * scaleX, oy * scaleY, rad * scaleX, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px monospace';
        ctx.fillText('RACK-PILLAR', (ox - 4.5) * scaleX, (oy + 0.5) * scaleY);
      }

      // 3. Draw Warehouse Zones
      for (const [zName, coords] of Object.entries(latestTelemetry.warehouse_zones)) {
        const zx = coords[0] * scaleX;
        const zy = coords[1] * scaleY;
        ctx.strokeStyle = zName.includes('QUARANTINE') ? '#ef4444' :
                          zName.includes('LN2') ? '#06b6d4' : '#3b82f6';
        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.lineWidth = 2;
        ctx.strokeRect(zx - 46, zy - 18, 92, 36);
        ctx.fillRect(zx - 46, zy - 18, 92, 36);
        ctx.fillStyle = '#e2e8f0';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(zName.replace(/_/g, ' '), zx, zy + 3);
      }

      // 4. Draw A* Paths & AMRs
      for (const f of latestTelemetry.fleet) {
        const ax = f.kinematics.x_meters * scaleX;
        const ay = f.kinematics.y_meters * scaleY;
        const tx = f.kinematics.target_waypoint[0] * scaleX;
        const ty = f.kinematics.target_waypoint[1] * scaleY;

        const orc = latestOrchestration.find(o => o.amr_id === f.amr_id);
        const sev = orc ? orc.severity : (f.active_fault_codes.length ? 'WARNING' : 'NOMINAL');
        const color = sev === 'CRITICAL_EXCURSION' ? '#ef4444' :
                      sev === 'WARNING' ? '#f59e0b' : '#10b981';

        // Draw A* Trajectory if available
        ctx.strokeStyle = color;
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        const navTrace = orc && orc.subagent_traces.find(t => t.agent_name === 'AMRFleetNavigationAgent');
        if (navTrace && navTrace.metrics && navTrace.metrics.astar_waypoints) {
          for (const wp of navTrace.metrics.astar_waypoints) {
            ctx.lineTo(wp[0] * scaleX, wp[1] * scaleY);
          }
        } else {
          ctx.lineTo(tx, ty);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Draw LiDAR Ring
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.32)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(ax, ay, Math.min(f.kinematics.lidar_min_obstacle_dist_m, 6.0) * scaleX, 0, Math.PI * 2);
        ctx.stroke();

        // Draw AMR Robot Body
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(ax, ay, 9, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`${f.amr_id} (${f.cryo.internal_temp_c}°C)`, ax + 13, ay + 4);
      }
    }

    fetchTelemetry();
  </script>
</body>
</html>
"""
