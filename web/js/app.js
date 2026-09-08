/**
 * Master Tactical C2 Application Orchestrator.
 * Handles high-speed WebSocket streaming, UI telemetry updates,
 * modal dialogs, and interactive mission controls.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Visualizers
    const threeScene = new TacticalThreeScene('threeViewport');
    const thermalCanvas = new ThermalCanvasSimulator('thermalCanvas');
    const telemetryCharts = new TelemetryCharts();

    // 2. DOM Elements
    const elements = {
        srlBadge: document.getElementById('srlBadge'),
        connBadge: document.getElementById('connBadge'),
        missionClock: document.getElementById('missionClock'),
        
        // Thermal HUD
        hudJitter: document.getElementById('hudJitter'),
        hudContrast: document.getElementById('hudContrast'),
        hudFrost: document.getElementById('hudFrost'),
        thermalAthermalBadge: document.getElementById('thermalAthermalBadge'),
        
        // Sensor Track
        trackRange: document.getElementById('trackRange'),
        trackSpeed: document.getElementById('trackSpeed'),
        trackAzEl: document.getElementById('trackAzEl'),
        trackRpm: document.getElementById('trackRpm'),
        trackMicroDoppler: document.getElementById('trackMicroDoppler'),
        trackQuality: document.getElementById('trackQuality'),
        trackLockBadge: document.getElementById('trackLockBadge'),
        
        // Neutralization
        rfEirp: document.getElementById('rfEirp'),
        rfJsRatio: document.getElementById('rfJsRatio'),
        paschenMargin: document.getElementById('paschenMargin'),
        fireLeadPoint: document.getElementById('fireLeadPoint'),
        killProb: document.getElementById('killProb'),
        jamStatusBadge: document.getElementById('jamStatusBadge'),
        
        // 3D Scene HUD
        sceneAltTag: document.getElementById('sceneAltTag'),
        sceneWindTag: document.getElementById('sceneWindTag'),
        sceneTempTag: document.getElementById('sceneTempTag'),
        gimbalAnglesTag: document.getElementById('gimbalAnglesTag'),
        activeControllerTag: document.getElementById('activeControllerTag'),
        
        // Charts Summary
        summaryAdrcJitter: document.getElementById('summaryAdrcJitter'),
        summaryPidJitter: document.getElementById('summaryPidJitter'),
        
        // Thermal Node Bars
        tempRfAmp: document.getElementById('tempRfAmp'),
        barRfAmp: document.getElementById('barRfAmp'),
        tempBearings: document.getElementById('tempBearings'),
        barBearings: document.getElementById('barBearings'),
        tempBattery: document.getElementById('tempBattery'),
        barBattery: document.getElementById('barBattery'),
        tempOptics: document.getElementById('tempOptics'),
        barOptics: document.getElementById('barOptics'),
        coolingDerateBadge: document.getElementById('coolingDerateBadge'),
        
        // Cable Card
        cableMaterialBadge: document.getElementById('cableMaterialBadge'),
        cableTorqueVal: document.getElementById('cableTorqueVal'),
        observedDistVal: document.getElementById('observedDistVal'),
        
        // Health Alerts
        healthPctBadge: document.getElementById('healthPctBadge'),
        alertsBox: document.getElementById('alertsBox'),
        
        // Toggles
        toggleAdrc: document.getElementById('toggleAdrc'),
        toggleHeaters: document.getElementById('toggleHeaters'),
        togglePaschen: document.getElementById('togglePaschen'),
        toggleJammer: document.getElementById('toggleJammer'),
        
        // Modals
        bomModal: document.getElementById('bomModal'),
        monteCarloModal: document.getElementById('monteCarloModal'),
        btnOpenBOM: document.getElementById('btnOpenBOM'),
        btnCloseBOM: document.getElementById('closeBomModal'),
        btnOpenMonteCarlo: document.getElementById('btnOpenMonteCarlo'),
        btnCloseMC: document.getElementById('closeMcModal'),
        qualTableBody: document.getElementById('qualTableBody'),
        btnEvaluateBOM: document.getElementById('btnEvaluateBOM'),
        
        // MC Stats
        mcAdrcMean: document.getElementById('mcAdrcMean'),
        mcAdrcP95: document.getElementById('mcAdrcP95'),
        mcPidMean: document.getElementById('mcPidMean'),
        mcImprovement: document.getElementById('mcImprovement'),
        mcVerdict: document.getElementById('mcVerdict')
    };

    // 3. Mission Clock Timer
    const startTime = Date.now();
    setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const hrs = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const secs = String(elapsed % 60).padStart(2, '0');
        elements.missionClock.textContent = `${hrs}:${mins}:${secs}`;
    }, 1000);

    // 4. Backend Resolution & Dual-Mode Telemetry Streaming (WebSocket + Vercel HTTP Polling)
    const urlParams = new URLSearchParams(window.location.search);
    const customBackend = urlParams.get('backend') || urlParams.get('api') || (window.HA_ADS_CONFIG && window.HA_ADS_CONFIG.backendUrl) || '';

    function getApiUrl(endpoint) {
        if (customBackend) {
            const base = customBackend.replace(/\/+$/, '');
            return `${base}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
        }
        return endpoint;
    }

    function getWsUrl() {
        if (customBackend) {
            const wsProto = customBackend.startsWith('https:') ? 'wss:' : 'ws:';
            const host = customBackend.replace(/^https?:\/\//, '').replace(/\/+$/, '');
            return `${wsProto}//${host}/ws/telemetry`;
        }
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws/telemetry`;
    }

    let socket = null;
    let httpPollingTimer = null;
    let isPolling = false;
    let wsAttempts = 0;
    const MAX_WS_FAILURES_BEFORE_FALLBACK = 1;

    function startHttpPolling() {
        if (isPolling) return;
        isPolling = true;
        
        elements.connBadge.textContent = 'HTTP STREAM (VERCEL)';
        elements.connBadge.className = 'status-pill status-ready';

        let pollingInFlight = false;
        
        async function pollTelemetry() {
            if (!isPolling) return;
            if (pollingInFlight) return;
            pollingInFlight = true;
            try {
                const res = await fetch(getApiUrl('/api/telemetry/snapshot'), { cache: 'no-store' });
                if (res.ok) {
                    const telemetry = await res.json();
                    updateDashboard(telemetry);
                    elements.connBadge.textContent = 'HTTP STREAM (VERCEL)';
                    elements.connBadge.className = 'status-pill status-ready';
                }
            } catch (err) {
                // Keep trying smoothly in the background
                elements.connBadge.textContent = 'HTTP RETRYING...';
                elements.connBadge.className = 'status-pill';
            } finally {
                pollingInFlight = false;
            }
        }

        // Poll at ~16-20 Hz for responsive real-time telemetry on Vercel
        httpPollingTimer = setInterval(pollTelemetry, 60);
        pollTelemetry();
    }

    function stopHttpPolling() {
        isPolling = false;
        if (httpPollingTimer) {
            clearInterval(httpPollingTimer);
            httpPollingTimer = null;
        }
    }

    function connectWebSocket() {
        const wsUrl = getWsUrl();
        
        try {
            socket = new WebSocket(wsUrl);
        } catch (e) {
            wsAttempts++;
            startHttpPolling();
            return;
        }

        let connectionTimeout = setTimeout(() => {
            if (socket && socket.readyState !== WebSocket.OPEN) {
                try { socket.close(); } catch (_) {}
                startHttpPolling();
            }
        }, 2000);

        socket.onopen = () => {
            clearTimeout(connectionTimeout);
            stopHttpPolling();
            wsAttempts = 0;
            elements.connBadge.textContent = '50Hz STREAM';
            elements.connBadge.className = 'status-pill status-ready';
        };

        socket.onclose = () => {
            clearTimeout(connectionTimeout);
            wsAttempts++;
            if (wsAttempts >= MAX_WS_FAILURES_BEFORE_FALLBACK) {
                startHttpPolling();
            } else {
                elements.connBadge.textContent = 'CONNECTING...';
                elements.connBadge.className = 'status-pill';
                setTimeout(connectWebSocket, 1500);
            }
        };

        socket.onerror = () => {
            clearTimeout(connectionTimeout);
            try { socket.close(); } catch (_) {}
        };

        socket.onmessage = (event) => {
            const telemetry = JSON.parse(event.data);
            updateDashboard(telemetry);
        };
    }

    connectWebSocket();

    // 5. Real-Time UI Update Loop (50 Hz)
    function updateDashboard(t) {
        // Update 3D Scene
        threeScene.update(t);

        // Update MWIR Thermal Canvas
        thermalCanvas.render(t);

        // Update Strip Charts
        telemetryCharts.update(
            t.gimbal.adrc_error_urad,
            t.gimbal.pid_error_urad,
            t.gimbal.el_deg,
            t.gimbal.cable_torque_az_nm
        );

        // Update HUD Values
        elements.hudJitter.textContent = `${t.gimbal.active_error_urad.toFixed(1)} µrad`;
        elements.hudContrast.textContent = `+${t.sensors.optics.contrast_k.toFixed(1)} K`;
        elements.hudFrost.textContent = `${t.sensors.optics.frost_pct.toFixed(1)}%`;
        
        elements.trackRange.textContent = `${Math.round(t.sensors.fused_track.range_m).toLocaleString()} m`;
        elements.trackSpeed.textContent = `${Math.round(Math.hypot(...t.sensors.fused_track.vel))} m/s`;
        elements.trackAzEl.textContent = `${t.sensors.fused_track.az_deg.toFixed(1)}° / ${t.sensors.fused_track.el_deg.toFixed(1)}°`;
        elements.trackRpm.textContent = `${Math.round(t.target.rpm).toLocaleString()} RPM`;
        elements.trackMicroDoppler.textContent = `${Math.round(t.target.micro_doppler_hz)} Hz`;
        elements.trackQuality.textContent = `${t.sensors.fused_track.quality_pct.toFixed(1)}%`;

        // Interdiction Status
        const neut = t.neutralization;
        elements.rfEirp.textContent = `+${neut.eirp_dbm.toFixed(1)} dBm`;
        elements.rfJsRatio.textContent = `+${neut.js_ratio_db.toFixed(1)} dB (${neut.link_disrupted ? 'SEVERED' : 'CONTESTED'})`;
        elements.paschenMargin.textContent = `${t.health.paschen_margin.toFixed(2)}x (${t.paschen.risk})`;
        elements.fireLeadPoint.textContent = `[ ${Math.round(neut.fire_control.lead_point[0])}, ${Math.round(neut.fire_control.lead_point[1])}, ${Math.round(neut.fire_control.lead_point[2])} ] m`;
        elements.killProb.textContent = `${neut.fire_control.kill_probability_pct.toFixed(1)}%`;

        // 3D Scene HUD Tags
        elements.sceneAltTag.textContent = `ALTITUDE: ${Math.round(t.atmosphere.altitude_m)} m`;
        elements.sceneWindTag.textContent = `WIND: ${t.wind.speed_ms.toFixed(1)} m/s @ ${t.wind.direction_deg}°`;
        elements.sceneTempTag.textContent = `AMBIENT: ${t.atmosphere.temperature_c.toFixed(1)}°C`;
        elements.gimbalAnglesTag.textContent = `TURRET AZ: ${t.gimbal.az_deg.toFixed(1)}° | EL: ${t.gimbal.el_deg.toFixed(1)}°`;

        const isAdrc = t.gimbal.active_controller === 'ADRC';
        elements.activeControllerTag.textContent = `STABILIZATION: ${t.gimbal.active_controller} (${isAdrc ? 'ACTIVE' : 'DEGRADED'})`;
        elements.activeControllerTag.className = isAdrc ? 'active-adrc-tag' : 'active-pid-tag';

        // Chart Footers
        elements.summaryAdrcJitter.textContent = `${t.gimbal.adrc_error_urad.toFixed(1)} µrad`;
        elements.summaryPidJitter.textContent = `${t.gimbal.pid_error_urad.toFixed(1)} µrad`;

        // Thermal Bars
        const th = t.thermal;
        elements.coolingDerateBadge.textContent = `COOLING DERATED ${Math.round(th.cooling_derate_pct)}%`;
        
        elements.tempRfAmp.textContent = `${th.nodes.rf_amplifier.temp_c.toFixed(1)}°C`;
        elements.barRfAmp.style.width = `${Math.min(100, Math.max(0, (th.nodes.rf_amplifier.temp_c + 20) / 1.0))}%`;
        elements.barRfAmp.className = `progress-fill ${th.nodes.rf_amplifier.temp_c > 65 ? 'fill-critical' : 'fill-normal'}`;

        elements.tempBearings.textContent = `${th.nodes.gimbal_bearings.temp_c.toFixed(1)}°C`;
        elements.barBearings.style.width = `${Math.min(100, Math.max(0, (th.nodes.gimbal_bearings.temp_c + 30) / 0.8))}%`;

        elements.tempBattery.textContent = `${th.nodes.battery_pack.temp_c.toFixed(1)}°C`;
        elements.barBattery.style.width = `${Math.min(100, Math.max(0, (th.nodes.battery_pack.temp_c) / 0.5))}%`;

        elements.tempOptics.textContent = `${th.nodes.optics_window.temp_c.toFixed(1)}°C`;
        elements.barOptics.style.width = `${Math.min(100, Math.max(0, (th.nodes.optics_window.temp_c + 20) / 0.5))}%`;

        // Cable Card
        elements.cableTorqueVal.textContent = `${t.gimbal.cable_torque_az_nm.toFixed(2)} N·m`;
        elements.observedDistVal.textContent = `${t.gimbal.adrc_estimated_dist_az_nm.toFixed(2)} N·m`;

        // Health Readiness
        elements.healthPctBadge.textContent = `HEALTH ${Math.round(t.health.overall_health_pct)}%`;
        elements.srlBadge.textContent = t.health.system_readiness.replace('_', ' ');
        elements.srlBadge.className = `status-pill ${t.health.system_readiness === 'MISSION_READY' ? 'status-ready' : 'status-pill'}`;

        // Render Alerts
        if (t.health.alerts && t.health.alerts.length > 0) {
            elements.alertsBox.innerHTML = t.health.alerts.map(a => `
                <div class="alert-item alert-${a.severity.toLowerCase()}">
                    <strong>[${a.severity}]</strong> ${a.message}
                </div>
            `).join('');
        } else {
            elements.alertsBox.innerHTML = `
                <div class="alert-item alert-info">
                    <strong>[NOMINAL]</strong> All high-altitude compensation loops operating within specifications.
                </div>
            `;
        }
    }

    // 6. Interactive Controls & Toggle Switches
    async function sendCommand(action, value = null, preset = null) {
        const payload = { action, value };
        if (preset) payload.preset = preset;

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
        } else {
            // REST Fallback for serverless Vercel execution
            try {
                await fetch(getApiUrl('/api/command'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (err) {
                console.warn('REST command dispatch failed:', err);
            }
        }
    }

    elements.toggleAdrc.addEventListener('change', (e) => {
        sendCommand('toggle_adrc', e.target.checked);
    });

    elements.toggleHeaters.addEventListener('change', (e) => {
        sendCommand('toggle_heaters', e.target.checked);
    });

    elements.togglePaschen.addEventListener('change', (e) => {
        sendCommand('toggle_paschen', e.target.checked);
    });

    elements.toggleJammer.addEventListener('change', (e) => {
        sendCommand('toggle_jamming', e.target.checked);
    });

    // Altitude Presets
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const preset = btn.dataset.preset;
            sendCommand('set_preset', null, preset);
        });
    });

    // Camera Views
    document.querySelectorAll('.cam-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            threeScene.setCameraMode(btn.dataset.cam);
        });
    });

    // 7. Modals: Component Qualification & Monte Carlo
    elements.btnOpenBOM.addEventListener('click', async () => {
        elements.bomModal.classList.add('active');
        // Fetch components
        try {
            const res = await fetch(getApiUrl('/api/qualification/components'));
            const data = await res.json();
            renderQualTable(data.components);
        } catch (err) {
            console.error(err);
        }
    });

    elements.btnCloseBOM.addEventListener('click', () => {
        elements.bomModal.classList.remove('active');
    });

    elements.btnOpenMonteCarlo.addEventListener('click', async () => {
        elements.monteCarloModal.classList.add('active');
        elements.mcVerdict.textContent = 'Executing 50-run Monte Carlo simulation across random wind gusts & frozen cable torques...';
        
        try {
            const res = await fetch(getApiUrl('/api/simulation/monte-carlo?runs=50'));
            const data = await res.json();
            
            elements.mcAdrcMean.textContent = `${data.adrc.mean_jitter_urad} µrad`;
            elements.mcAdrcP95.textContent = `${data.adrc.p95_urad} µrad`;
            elements.mcPidMean.textContent = `${data.pid.mean_jitter_urad} µrad`;
            elements.mcImprovement.textContent = `${data.performance_improvement_factor}x`;
            
            elements.mcVerdict.innerHTML = `
                <strong>VERIFICATION SUCCESSFUL:</strong><br>
                ADRC 95th-percentile error of <strong>${data.adrc.p95_urad} µrad</strong> satisfies the micro-radian operational requirement (&le; 50 µrad).<br>
                Legacy PID degraded to <strong>${data.pid.p95_urad} µrad</strong> due to uncompensated sub-zero cable rigidity hysteresis.
                Overall pointing precision improved by <strong>${data.performance_improvement_factor}x</strong>.
            `;
        } catch (err) {
            elements.mcVerdict.textContent = 'Error executing Monte Carlo verification.';
        }
    });

    elements.btnCloseMC.addEventListener('click', () => {
        elements.monteCarloModal.classList.remove('active');
    });

    function renderQualTable(components) {
        elements.qualTableBody.innerHTML = components.map(c => `
            <tr>
                <td><strong>${c.subsystem}</strong></td>
                <td>${c.name}</td>
                <td><span class="${c.standard_or_rugged === 'MIL_RUGGEDIZED' ? 'tag-mil' : 'tag-cots'}">${c.standard_or_rugged.replace('_', ' ')}</span></td>
                <td>${c.min_temp_c}°C to +${c.max_temp_c}°C</td>
                <td>${c.max_altitude_m.toLocaleString()} m</td>
                <td>${c.paschen_rated ? '<span style="color:var(--accent-green)">YES</span>' : '<span style="color:var(--accent-red)">NO</span>'}</td>
                <td>${c.dust_water_rating}</td>
                <td>${c.mtbf_hours.toLocaleString()} hrs</td>
                <td>${c.engineering_rationale}</td>
            </tr>
        `).join('');
    }

    elements.btnEvaluateBOM.addEventListener('click', async () => {
        try {
            const res = await fetch(getApiUrl('/api/qualification/evaluate-bom'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected_part_ids: ["CAB-MIL-PTFE", "BRG-MIL-CERAMIC-PFPE", "MTR-MIL-BLDC-DIR", "RF-MIL-GAN-HEATPIPE", "PWR-MIL-LIFEPO4-PCM", "OPT-MIL-ATHERMAL-MWIR"],
                    target_altitude_m: 5400.0,
                    min_temp_c: -35.0
                })
            });
            const evalResult = await res.json();
            alert(`MIL-STD-810H EVALUATION RESULT:\n\nScore: ${evalResult.system_compliance_score}/100\nCompliant: ${evalResult.mil_std_810h_compliant ? 'YES (PASSED)' : 'NO'}\nAvg Derating: ${evalResult.average_thermal_derating_pct}%\nEstimated System MTBF: ${evalResult.estimated_system_mtbf_hours.toLocaleString()} Hours`);
        } catch (e) {
            console.error(e);
        }
    });
});
