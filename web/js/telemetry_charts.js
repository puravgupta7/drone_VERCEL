/**
 * Telemetry Strip Charts & Phase-Plane Visualizers (Chart.js)
 * Displays Real-Time Pointing Jitter (ADRC vs PID) and Cable Hysteresis.
 */

class TelemetryCharts {
    constructor() {
        this.maxDataPoints = 40;
        this.jitterLabels = Array(this.maxDataPoints).fill('');
        this.adrcData = Array(this.maxDataPoints).fill(18.0);
        this.pidData = Array(this.maxDataPoints).fill(350.0);
        
        this.initJitterChart();
        this.initCableChart();
    }

    initJitterChart() {
        const ctx = document.getElementById('jitterChart').getContext('2d');
        this.jitterChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.jitterLabels,
                datasets: [
                    {
                        label: 'ADRC Tracking Error',
                        data: this.adrcData,
                        borderColor: '#00ff9d',
                        backgroundColor: 'rgba(0, 255, 157, 0.08)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.25,
                        fill: true
                    },
                    {
                        label: 'Standard PID Error',
                        data: this.pidData,
                        borderColor: '#ff3366',
                        backgroundColor: 'rgba(255, 51, 102, 0.05)',
                        borderWidth: 1.5,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        tension: 0.25,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#8ba1b7',
                            font: { family: 'JetBrains Mono', size: 9 },
                            boxWidth: 10
                        }
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        min: 0,
                        max: 500,
                        grid: { color: '#162333' },
                        ticks: {
                            color: '#566b82',
                            font: { family: 'JetBrains Mono', size: 9 },
                            stepSize: 100
                        },
                        title: {
                            display: true,
                            text: 'JITTER (µrad)',
                            color: '#566b82',
                            font: { family: 'JetBrains Mono', size: 8 }
                        }
                    }
                }
            }
        });
    }

    initCableChart() {
        const ctx = document.getElementById('cableChart').getContext('2d');
        // Phase plane points: Angle vs Restoring Torque
        this.cablePoints = [];
        for (let i = 0; i < 25; i++) {
            this.cablePoints.push({ x: (i - 12) * 1.5, y: 0.0 });
        }

        this.cableChart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'T_cable (N·m)',
                    data: this.cablePoints,
                    borderColor: '#00f3ff',
                    backgroundColor: '#00f3ff',
                    showLine: true,
                    borderWidth: 2,
                    pointRadius: 2,
                    tension: 0.2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: '#162333' },
                        ticks: { color: '#566b82', font: { family: 'JetBrains Mono', size: 8 } },
                        title: { display: true, text: 'Elevation Angle (°)', color: '#566b82', font: { size: 8 } }
                    },
                    y: {
                        min: -4.0,
                        max: 4.0,
                        grid: { color: '#162333' },
                        ticks: { color: '#566b82', font: { family: 'JetBrains Mono', size: 8 } },
                        title: { display: true, text: 'Torque (N·m)', color: '#566b82', font: { size: 8 } }
                    }
                }
            }
        });
    }

    update(adrcError, pidError, elevationDeg, cableTorqueNm) {
        // Shift time series
        this.adrcData.shift();
        this.adrcData.push(Math.min(500, Math.max(0, adrcError)));

        this.pidData.shift();
        this.pidData.push(Math.min(500, Math.max(0, pidError)));

        this.jitterChart.update('none');

        // Update cable hysteresis scatter
        this.cablePoints.shift();
        this.cablePoints.push({ x: elevationDeg, y: cableTorqueNm });
        this.cableChart.update('none');
    }
}
window.TelemetryCharts = TelemetryCharts;
