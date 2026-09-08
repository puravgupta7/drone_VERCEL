/**
 * Simulated MWIR Thermal Radiometric Camera & Tactical HUD Canvas.
 * Renders high-altitude infrared signatures, hot motor cores, cold snow contrast,
 * window defrosting/frosting states, and micro-radian targeting reticle.
 */

class ThermalCanvasSimulator {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        
        // Target tracking smoothed screen coordinates
        this.targetScreenX = this.width / 2;
        this.targetScreenY = this.height / 2;
        this.targetSize = 28;
    }

    render(telemetry) {
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;

        const optics = telemetry.sensors.optics;
        const target = telemetry.target;
        const gimbal = telemetry.gimbal;
        const frostPct = optics.frost_pct;

        // 1. Clear background: Cold mountain radiometric gradient (black/deep indigo)
        const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
        bgGrad.addColorStop(0, '#040810');
        bgGrad.addColorStop(0.7, '#070f1a');
        bgGrad.addColorStop(1, '#0e1824');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, w, h);

        // 2. Simulated mountain ridge silhouettes in infrared (cold = dark)
        ctx.fillStyle = '#060d16';
        ctx.beginPath();
        ctx.moveTo(0, h * 0.75);
        ctx.lineTo(w * 0.25, h * 0.58);
        ctx.lineTo(w * 0.55, h * 0.68);
        ctx.lineTo(w * 0.85, h * 0.52);
        ctx.lineTo(w, h * 0.65);
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        ctx.fill();

        // 3. Calculate target pixel offset from boresight
        // Difference between target Az/El and Gimbal pointing angles
        const deltaAz = (target.az_deg - gimbal.az_deg) * (Math.PI / 180);
        const deltaEl = (target.el_deg - gimbal.el_deg) * (Math.PI / 180);

        // Optical FOV scaling (approx 6 deg vertical FOV)
        const fovRad = 0.10;
        const targetX = w / 2 + (deltaAz / fovRad) * (w / 2);
        const targetY = h / 2 - (deltaEl / fovRad) * (h / 2);

        // Smooth position
        this.targetScreenX += (targetX - this.targetScreenX) * 0.35;
        this.targetScreenY += (targetY - this.targetScreenY) * 0.35;

        // Target size based on range
        const range = Math.max(100, target.range_m);
        const size = Math.max(10, Math.min(48, (1200 / range) * 35));

        // 4. Render Thermal Drone Signature (White-Hot Infrared Palette)
        if (optics.visible && frostPct < 85) {
            ctx.save();
            ctx.translate(this.targetScreenX, this.targetScreenY);

            // Cold drone body (grey carbon fiber)
            ctx.fillStyle = 'rgba(140, 160, 180, 0.4)';
            ctx.fillRect(-size * 0.4, -size * 0.2, size * 0.8, size * 0.4);

            // 4 Hot BLDC Motor Nodes (Glowing White/Amber thermal bloom)
            const motorDist = size * 0.5;
            const motorPositions = [
                [-motorDist, -motorDist * 0.6],
                [motorDist, -motorDist * 0.6],
                [-motorDist, motorDist * 0.6],
                [motorDist, motorDist * 0.6]
            ];

            motorPositions.forEach(([mx, my]) => {
                // Motor bloom glow
                const glow = ctx.createRadialGradient(mx, my, 1, mx, my, size * 0.35);
                glow.addColorStop(0, '#ffffff');
                glow.addColorStop(0.3, '#ffea75');
                glow.addColorStop(0.7, 'rgba(255, 120, 0, 0.6)');
                glow.addColorStop(1, 'transparent');
                ctx.fillStyle = glow;
                ctx.beginPath();
                ctx.arc(mx, my, size * 0.35, 0, Math.PI * 2);
                ctx.fill();
            });

            // Battery / ESC hot core
            const coreGlow = ctx.createRadialGradient(0, 0, 1, 0, 0, size * 0.25);
            coreGlow.addColorStop(0, '#ffffff');
            coreGlow.addColorStop(0.5, '#ff8000');
            coreGlow.addColorStop(1, 'transparent');
            ctx.fillStyle = coreGlow;
            ctx.beginPath();
            ctx.arc(0, 0, size * 0.25, 0, Math.PI * 2);
            ctx.fill();

            // Tracking gate box around drone
            ctx.strokeStyle = '#00ff9d';
            ctx.lineWidth = 1;
            const boxMargin = size * 0.75;
            ctx.strokeRect(-boxMargin, -boxMargin, boxMargin * 2, boxMargin * 2);

            ctx.restore();
        }

        // 5. Tactical Crosshair & Reticle Overlay
        ctx.strokeStyle = 'rgba(0, 243, 255, 0.45)';
        ctx.lineWidth = 1;

        // Center Boresight
        const cx = w / 2;
        const cy = h / 2;
        ctx.beginPath();
        // Crosshair marks
        ctx.moveTo(cx - 30, cy); ctx.lineTo(cx - 8, cy);
        ctx.moveTo(cx + 8, cy); ctx.lineTo(cx + 30, cy);
        ctx.moveTo(cx, cy - 30); ctx.lineTo(cx, cy - 8);
        ctx.moveTo(cx, cy + 8); ctx.lineTo(cx, cy + 30);
        ctx.stroke();

        // 50 µrad Precision Stadiametric Circle
        ctx.strokeStyle = 'rgba(0, 255, 157, 0.4)';
        ctx.beginPath();
        ctx.arc(cx, cy, 18, 0, Math.PI * 2);
        ctx.stroke();

        // Lead Angle Prediction Circle
        const fc = telemetry.neutralization.fire_control;
        if (fc.locked) {
            const leadPxX = cx + (fc.aim_az_deg - gimbal.az_deg) * (w / (fovRad * 180 / Math.PI));
            const leadPxY = cy - (fc.aim_el_deg - gimbal.el_deg) * (h / (fovRad * 180 / Math.PI));
            ctx.strokeStyle = '#ffb700';
            ctx.beginPath();
            ctx.arc(leadPxX, leadPxY, 8, 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillStyle = '#ffb700';
            ctx.font = '8px JetBrains Mono';
            ctx.fillText('LEAD', leadPxX + 10, leadPxY + 3);
        }

        // 6. Sensor Thermal NETD Noise
        ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
        for (let i = 0; i < 70; i++) {
            const rx = Math.random() * w;
            const ry = Math.random() * h;
            ctx.fillRect(rx, ry, 1.5, 1.5);
        }

        // 7. Window Frost / Ice Obscuration Layer (if heaters off)
        if (frostPct > 1.0) {
            ctx.fillStyle = `rgba(180, 220, 255, ${frostPct * 0.009})`;
            ctx.fillRect(0, 0, w, h);

            // Crystalline frost edges
            ctx.strokeStyle = `rgba(255, 255, 255, ${frostPct * 0.012})`;
            ctx.lineWidth = 2;
            for (let i = 0; i < 8; i++) {
                ctx.beginPath();
                ctx.moveTo(0, i * 30);
                ctx.lineTo(w * (frostPct / 200), i * 30 + 15);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(w, i * 30);
                ctx.lineTo(w - w * (frostPct / 200), i * 30 + 15);
                ctx.stroke();
            }

            // Frost Warning Banner
            ctx.fillStyle = 'rgba(255, 51, 102, 0.85)';
            ctx.font = 'bold 9px JetBrains Mono';
            ctx.fillText(`! WINDOW FROSTING: ${frostPct.toFixed(1)}% !`, 12, 22);
        }

        // 8. HUD Corner Details
        ctx.fillStyle = '#8ba1b7';
        ctx.font = '8px JetBrains Mono';
        ctx.fillText(`FOV: 6.2° [MWIR 3-5µm]`, 8, h - 8);
        ctx.fillText(`NUC: AUTO`, w - 55, h - 8);
    }
}
window.ThermalCanvasSimulator = ThermalCanvasSimulator;
