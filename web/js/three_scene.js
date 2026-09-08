/**
 * Three.js High-Altitude 3D Tactical Battlefield Digital Twin.
 * Renders Himalayan terrain, 2-DOF articulated turret, thin-air target drone,
 * radar/jammer/laser beam visualizers, and mountain blizzard snowstorm.
 */

class TacticalThreeScene {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.cameraMode = 'free'; // 'free', 'turret', 'drone'
        
        this.initScene();
        this.buildTerrain();
        this.buildTurret();
        this.buildTargetDrone();
        this.buildTacticalBeams();
        this.buildSnowstorm();
        
        // Handle window resizing
        window.addEventListener('resize', () => this.onResize());
        
        // Start render loop
        this.animate();
    }

    initScene() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x040810);
        this.scene.fog = new THREE.FogExp2(0x08101a, 0.00035);

        // Camera
        this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 15000);
        this.camera.position.set(120, 95, 180);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);

        // Orbit Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxDistance = 6000;
        this.controls.minDistance = 5;
        this.controls.target.set(0, 15, 0);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x3a506b, 1.2);
        this.scene.add(ambientLight);

        const sunLight = new THREE.DirectionalLight(0xdcefff, 2.0);
        sunLight.position.set(400, 800, 300);
        sunLight.castShadow = true;
        this.scene.add(sunLight);

        const fillLight = new THREE.DirectionalLight(0x00f3ff, 0.4);
        fillLight.position.set(-300, 200, -200);
        this.scene.add(fillLight);
    }

    buildTerrain() {
        // Procedural Himalayan Mountain Ridges
        const terrainSize = 7000;
        const segments = 90;
        const geometry = new THREE.PlaneGeometry(terrainSize, terrainSize, segments, segments);
        geometry.rotateX(-Math.PI / 2);

        const pos = geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            const x = pos.getX(i);
            const z = pos.getZ(i);
            const distFromOrigin = Math.hypot(x, z);

            // Flat clearing for anti-drone base station at center
            if (distFromOrigin < 140) {
                pos.setY(i, 0);
            } else {
                // Procedural peaks and ridges
                const ridge1 = Math.sin(x * 0.0018) * Math.cos(z * 0.0018) * 380;
                const ridge2 = Math.sin(x * 0.004 + z * 0.003) * 160;
                const mountainSlope = (distFromOrigin / terrainSize) * 650;
                const y = Math.max(0, ridge1 + ridge2 + mountainSlope - 60);
                pos.setY(i, y);
            }
        }
        geometry.computeVertexNormals();

        // High-altitude mountain material (snow peaks + dark rock slopes)
        const material = new THREE.MeshStandardMaterial({
            color: 0x1a2634,
            roughness: 0.85,
            metalness: 0.1,
            flatShading: true
        });
        const terrain = new THREE.Mesh(geometry, material);
        terrain.receiveShadow = true;
        this.scene.add(terrain);

        // Wireframe Tactical Contour Grid
        const wireMat = new THREE.MeshBasicMaterial({
            color: 0x00f3ff,
            wireframe: true,
            transparent: true,
            opacity: 0.07
        });
        const wireTerrain = new THREE.Mesh(geometry, wireMat);
        this.scene.add(wireTerrain);

        // Circular Tactical Defense Perimeter Grid
        const gridHelper = new THREE.PolarGridHelper(350, 16, 8, 64, 0x00f3ff, 0x162333);
        gridHelper.position.y = 0.5;
        this.scene.add(gridHelper);
    }

    buildTurret() {
        // Master Turret Base Station Group
        this.turretGroup = new THREE.Group();
        this.turretGroup.position.set(0, 0, 0);
        this.scene.add(this.turretGroup);

        // 1. Concrete Platform & Heavy Foundation
        const platGeo = new THREE.CylinderGeometry(14, 16, 2.5, 32);
        const platMat = new THREE.MeshStandardMaterial({ color: 0x222d3a, roughness: 0.9 });
        const platform = new THREE.Mesh(platGeo, platMat);
        platform.position.y = 1.25;
        this.turretGroup.add(platform);

        // 2. Tower Pedestal Mast
        const mastGeo = new THREE.CylinderGeometry(2.8, 3.8, 12, 24);
        const mastMat = new THREE.MeshStandardMaterial({ color: 0x141e2a, metalness: 0.6, roughness: 0.4 });
        const mast = new THREE.Mesh(mastGeo, mastMat);
        mast.position.y = 8.5;
        this.turretGroup.add(mast);

        // 3. Azimuth Rotating Yoke / Fork Assembly
        this.azimuthFork = new THREE.Group();
        this.azimuthFork.position.set(0, 14.5, 0);
        this.turretGroup.add(this.azimuthFork);

        const forkBaseGeo = new THREE.CylinderGeometry(3.6, 3.6, 2.0, 32);
        const forkBase = new THREE.Mesh(forkBaseGeo, mastMat);
        this.azimuthFork.add(forkBase);

        // Fork Arms (left & right supports)
        const armGeo = new THREE.BoxGeometry(1.2, 7.5, 2.2);
        const leftArm = new THREE.Mesh(armGeo, mastMat);
        leftArm.position.set(-3.2, 4.2, 0);
        const rightArm = new THREE.Mesh(armGeo, mastMat);
        rightArm.position.set(3.2, 4.2, 0);
        this.azimuthFork.add(leftArm);
        this.azimuthFork.add(rightArm);

        // 4. Elevation Tilting Sensor Pod
        this.elevationPod = new THREE.Group();
        this.elevationPod.position.set(0, 6.2, 0);
        this.azimuthFork.add(this.elevationPod);

        // Central Housing
        const podHousingGeo = new THREE.BoxGeometry(5.2, 4.2, 5.0);
        const podMat = new THREE.MeshStandardMaterial({ color: 0x1e2b3b, metalness: 0.7, roughness: 0.3 });
        const podHousing = new THREE.Mesh(podHousingGeo, podMat);
        this.elevationPod.add(podHousing);

        // Planar Array 3D Radar Antenna (Flat Ku-band Face)
        const radarArrayGeo = new THREE.BoxGeometry(4.6, 3.6, 0.4);
        const radarMat = new THREE.MeshStandardMaterial({ color: 0x00f3ff, roughness: 0.2, metalness: 0.8 });
        const radarArray = new THREE.Mesh(radarArrayGeo, radarMat);
        radarArray.position.set(0, 0, 2.6);
        this.elevationPod.add(radarArray);

        // Dual Optical Apertures (Visible HD & Cooled MWIR Thermal)
        const opticBarrelGeo = new THREE.CylinderGeometry(0.7, 0.7, 1.2, 24);
        opticBarrelGeo.rotateX(Math.PI / 2);
        const opticMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 0.1 });

        const opticLeft = new THREE.Mesh(opticBarrelGeo, opticMat);
        opticLeft.position.set(-1.4, 0.8, 2.8);
        const opticRight = new THREE.Mesh(opticBarrelGeo, opticMat);
        opticRight.position.set(1.4, 0.8, 2.8);
        this.elevationPod.add(opticLeft);
        this.elevationPod.add(opticRight);

        // 4-Element RF Jammer Horn Array (Mounted on outriggers)
        const hornGeo = new THREE.ConeGeometry(0.9, 2.5, 4);
        hornGeo.rotateX(Math.PI / 2);
        const hornMat = new THREE.MeshStandardMaterial({ color: 0xffb700, metalness: 0.9, roughness: 0.2 });

        const hornPositions = [
            [-3.8, 1.2, 1.0], [-3.8, -1.2, 1.0],
            [3.8, 1.2, 1.0], [3.8, -1.2, 1.0]
        ];
        hornPositions.forEach(([hx, hy, hz]) => {
            const horn = new THREE.Mesh(hornGeo, hornMat);
            horn.position.set(hx, hy, hz);
            this.elevationPod.add(horn);
        });
    }

    buildTargetDrone() {
        this.droneGroup = new THREE.Group();
        this.scene.add(this.droneGroup);

        // Drone Central Fuselage
        const bodyGeo = new THREE.BoxGeometry(2.4, 0.8, 2.4);
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.8, roughness: 0.2 });
        const droneBody = new THREE.Mesh(bodyGeo, bodyMat);
        this.droneGroup.add(droneBody);

        // 4 Carbon Fiber Rotor Arms
        const armGeo = new THREE.CylinderGeometry(0.12, 0.12, 3.8, 12);
        armGeo.rotateZ(Math.PI / 2);
        const armMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.5 });

        const arm1 = new THREE.Mesh(armGeo, armMat);
        arm1.rotation.y = Math.PI / 4;
        const arm2 = new THREE.Mesh(armGeo, armMat);
        arm2.rotation.y = -Math.PI / 4;
        this.droneGroup.add(arm1);
        this.droneGroup.add(arm2);

        // 4 Rotor Discs (Spinning high-RPM discs)
        this.rotors = [];
        const rotorGeo = new THREE.CylinderGeometry(1.2, 1.2, 0.05, 16);
        const rotorMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff, transparent: true, opacity: 0.45 });

        const rotorOffsets = [
            [-1.8, 0.5, -1.8], [1.8, 0.5, -1.8],
            [-1.8, 0.5, 1.8], [1.8, 0.5, 1.8]
        ];
        rotorOffsets.forEach(([rx, ry, rz]) => {
            const rotor = new THREE.Mesh(rotorGeo, rotorMat);
            rotor.position.set(rx, ry, rz);
            this.droneGroup.add(rotor);
            this.rotors.push(rotor);
        });

        // Drone Target Flight Path Trail
        const trailMaxPoints = 120;
        this.trailPositions = new Float32Array(trailMaxPoints * 3);
        const trailGeo = new THREE.BufferGeometry();
        trailGeo.setAttribute('position', new THREE.BufferAttribute(this.trailPositions, 3));
        const trailMat = new THREE.LineBasicMaterial({ color: 0xff3366, transparent: true, opacity: 0.65 });
        this.trailLine = new THREE.Line(trailGeo, trailMat);
        this.scene.add(this.trailLine);
        this.trailIndex = 0;
    }

    buildTacticalBeams() {
        // 1. Radar Track Frustum / Beam
        const radarGeo = new THREE.ConeGeometry(30, 200, 16, 1, true);
        radarGeo.rotateX(Math.PI / 2);
        radarGeo.translate(0, 0, 100);
        const radarMat = new THREE.MeshBasicMaterial({
            color: 0x00f3ff,
            transparent: true,
            opacity: 0.12,
            wireframe: true
        });
        this.radarBeam = new THREE.Mesh(radarGeo, radarMat);
        this.elevationPod.add(this.radarBeam);

        // 2. Optical Line-of-Sight Laser Vector
        const losGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(0, 0, 500)
        ]);
        const losMat = new THREE.LineBasicMaterial({ color: 0x00ff9d, transparent: true, opacity: 0.8 });
        this.losLine = new THREE.Line(losGeo, losMat);
        this.elevationPod.add(this.losLine);

        // 3. Conical High-Altitude RF Jamming Envelope
        const jamGeo = new THREE.ConeGeometry(55, 300, 24, 1, true);
        jamGeo.rotateX(Math.PI / 2);
        jamGeo.translate(0, 0, 150);
        const jamMat = new THREE.MeshBasicMaterial({
            color: 0x9d4edd,
            transparent: true,
            opacity: 0.18,
            side: THREE.DoubleSide
        });
        this.jamBeam = new THREE.Mesh(jamGeo, jamMat);
        this.elevationPod.add(this.jamBeam);
    }

    buildSnowstorm() {
        // 1,500 particles driven by high-altitude wind
        const particleCount = 1500;
        const geometry = new THREE.BufferGeometry();
        this.snowPositions = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount * 3; i += 3) {
            this.snowPositions[i] = (Math.random() - 0.5) * 800;
            this.snowPositions[i + 1] = Math.random() * 250;
            this.snowPositions[i + 2] = (Math.random() - 0.5) * 800;
        }
        geometry.setAttribute('position', new THREE.BufferAttribute(this.snowPositions, 3));

        const material = new THREE.PointsMaterial({
            color: 0xffffff,
            size: 1.8,
            transparent: true,
            opacity: 0.65
        });
        this.snowParticles = new THREE.Points(geometry, material);
        this.scene.add(this.snowParticles);
    }

    update(telemetry) {
        if (!telemetry) return;

        const gimbal = telemetry.gimbal;
        const target = telemetry.target;
        const wind = telemetry.wind;
        const neutralization = telemetry.neutralization;

        // 1. Articulate Turret Gimbal
        // Azimuth (Pan)
        this.azimuthFork.rotation.y = -gimbal.az_deg * (Math.PI / 180);
        // Elevation (Tilt)
        this.elevationPod.rotation.x = -gimbal.el_deg * (Math.PI / 180);

        // 2. Position Target Drone
        // Scale 3D coordinates for realistic viewport framing
        const targetPos = new THREE.Vector3(target.pos[0] * 0.1, target.pos[2] * 0.1, target.pos[1] * 0.1);
        this.droneGroup.position.copy(targetPos);

        // Orient drone towards its velocity vector
        if (target.vel && (Math.abs(target.vel[0]) > 0.1 || Math.abs(target.vel[1]) > 0.1)) {
            const heading = Math.atan2(target.vel[1], target.vel[0]);
            this.droneGroup.rotation.y = -heading;
        }

        // Spin rotors at altitude RPM
        const rpmSpeed = (target.rpm / 60) * 0.05;
        this.rotors.forEach(r => r.rotation.y += rpmSpeed);

        // Update Target Flight Trail
        const posAttr = this.trailLine.geometry.attributes.position;
        posAttr.setXYZ(this.trailIndex % 120, targetPos.x, targetPos.y, targetPos.z);
        posAttr.needsUpdate = true;
        this.trailIndex++;

        // 3. Dynamic Beams
        const dist = targetPos.length();
        // Adjust beam lengths to reach drone
        this.radarBeam.scale.set(dist / 200, dist / 200, dist / 200);
        this.jamBeam.scale.set(dist / 300, dist / 300, dist / 300);
        this.jamBeam.visible = neutralization.jamming_active;

        // Pulsing animation on jammer cone
        if (this.jamBeam.visible) {
            this.jamBeam.material.opacity = 0.15 + 0.1 * Math.sin(Date.now() * 0.008);
        }

        // 4. Update Snowstorm Wind Particles
        const windSpeed = wind.speed_ms || 12.0;
        const windDirRad = (wind.direction_deg || 45) * (Math.PI / 180);
        const dx = Math.sin(windDirRad) * (windSpeed * 0.04);
        const dz = Math.cos(windDirRad) * (windSpeed * 0.04);

        const posArray = this.snowParticles.geometry.attributes.position.array;
        for (let i = 0; i < posArray.length; i += 3) {
            posArray[i] += dx;
            posArray[i + 1] -= 0.8 + Math.random() * 0.4;
            posArray[i + 2] += dz;

            // Reset boundary wrap
            if (posArray[i + 1] < 0) {
                posArray[i + 1] = 250;
                posArray[i] = (Math.random() - 0.5) * 800;
                posArray[i + 2] = (Math.random() - 0.5) * 800;
            }
        }
        this.snowParticles.geometry.attributes.position.needsUpdate = true;

        // 5. Camera Tracking Modes
        if (this.cameraMode === 'turret') {
            // First-person view from the optical sensor pod
            const worldPos = new THREE.Vector3();
            this.elevationPod.getWorldPosition(worldPos);
            this.camera.position.copy(worldPos).add(new THREE.Vector3(0, 1.0, 0));
            this.controls.target.copy(targetPos);
        } else if (this.cameraMode === 'drone') {
            // Chase camera behind drone
            this.camera.position.copy(targetPos).add(new THREE.Vector3(15, 8, 25));
            this.controls.target.copy(targetPos);
        }
    }

    setCameraMode(mode) {
        this.cameraMode = mode;
        if (mode === 'free') {
            this.camera.position.set(120, 95, 180);
            this.controls.target.set(0, 15, 0);
        }
    }

    onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}
window.TacticalThreeScene = TacticalThreeScene;
