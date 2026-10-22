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
  </style>
</head>
<body>
  <header>
    <div class="brand-title">
      <span>ColdChain-MedBot Physical AI</span>
      <span class="badge">Amazon Bedrock (Claude 3.5 Sonnet)</span>
      <span class="badge">AWS IoT TwinMaker + 21 CFR Part 11</span>
    </div>
    <div class="controls-bar">
      <button class="btn-primary" onclick="stepSimulation()">&#9654; Step Closed-Loop Cycle (+10s)</button>
      <button id="autoBtn" onclick="toggleAutoRun()">&#9201; Auto-Loop: OFF</button>
      <button onclick="resetFleet()">&#8635; Reset Warehouse Fleet</button>
    </div>
  </header>

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

    async function fetchTelemetry() {
      const res = await fetch('/api/v1/fleet/telemetry');
      latestTelemetry = await res.json();
      renderFleetCards(latestTelemetry.fleet);
      drawWarehouseTwin();
      document.getElementById('tickCounter').textContent =
        `Tick #${latestTelemetry.tick} | ${latestTelemetry.fleet.length} AMRs Active`;
    }

    async function stepSimulation() {
      const res = await fetch('/api/v1/orchestrate/step?dt_seconds=10', { method: 'POST' });
      const data = await res.json();
      latestOrchestration = data.orchestration_results || [];
      renderTraces(latestOrchestration);
      await fetchTelemetry();
    }

    async function injectFault() {
      const amr_id = document.getElementById('faultAmrSelect').value;
      const fault_type = document.getElementById('faultTypeSelect').value;
      await fetch('/api/v1/fault/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amr_id, fault_type })
      });
      await stepSimulation();
    }

    async function resetFleet() {
      await fetch('/api/v1/fleet/reset', { method: 'POST' });
      latestOrchestration = [];
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
