"""
Defense Industry MIL-STD-810H & MIL-STD-461G Component Qualification Database.
Comprehensive trade study, component selection, derating matrices, and
Bill-of-Materials (BOM) qualification engine for high-altitude anti-drone systems.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ComponentSpec:
    subsystem: str
    part_id: str
    name: str
    technology: str
    standard_or_rugged: str  # "COTS_STANDARD" vs "MIL_RUGGEDIZED"
    min_temp_c: float
    max_temp_c: float
    max_altitude_m: float
    paschen_rated: bool
    dust_water_rating: str  # e.g. "IP54", "IP68"
    mtbf_hours: int
    thermal_derating_pct: float
    mil_std_compliance: List[str]
    engineering_rationale: str


COMPONENTS_DATABASE: List[ComponentSpec] = [
    # 1. Cable Harnesses
    ComponentSpec(
        subsystem="Cables & Harnesses",
        part_id="CAB-PVC-01",
        name="Standard PVC Multi-Core Flex Cable",
        technology="Polyvinyl Chloride (PVC) outer jacket with copper stranded braid",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=-15.0,
        max_temp_c=70.0,
        max_altitude_m=3000.0,
        paschen_rated=False,
        dust_water_rating="IP54",
        mtbf_hours=12000,
        thermal_derating_pct=65.0,
        mil_std_compliance=["None (Commercial)"],
        engineering_rationale="Unsuitable for high altitude. Glass transition at -10°C causes severe embrittlement, cracked insulation, and extreme torsional rigidity that overloads gimbal servo drives."
    ),
    ComponentSpec(
        subsystem="Cables & Harnesses",
        part_id="CAB-MIL-PTFE",
        name="MIL-W-22759/33 Dual-Shielded PTFE/ETFE Harness",
        technology="Extruded fluoropolymer ETFE insulation with silver-plated high-strength copper alloy",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-65.0,
        max_temp_c=200.0,
        max_altitude_m=12000.0,
        paschen_rated=True,
        dust_water_rating="IP68 (Hermetic)",
        mtbf_hours=95000,
        thermal_derating_pct=5.0,
        mil_std_compliance=["MIL-STD-810H Meth. 502.7", "MIL-W-22759", "MIL-STD-202"],
        engineering_rationale="Optimal high-altitude choice. Retains superior flexural flexibility down to -65°C without cracking, minimizing gimbal hysteresis torque and ensuring sub-50 urad pointing accuracy."
    ),

    # 2. Bearings & Lubricants
    ComponentSpec(
        subsystem="Bearings & Lubrication",
        part_id="BRG-STD-MINERAL",
        name="Standard Deep-Groove Ball Bearings (Mineral Grease)",
        technology="Chrome steel raceways with standard lithium-soap mineral base grease",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=-20.0,
        max_temp_c=85.0,
        max_altitude_m=2500.0,
        paschen_rated=False,
        dust_water_rating="IP54",
        mtbf_hours=18000,
        thermal_derating_pct=70.0,
        mil_std_compliance=["None"],
        engineering_rationale="Grease congeals below -20°C, increasing startup friction torque by 800% and causing thermal seizure and high servo hunting jitter."
    ),
    ComponentSpec(
        subsystem="Bearings & Lubrication",
        part_id="BRG-MIL-CERAMIC-PFPE",
        name="Hybrid Ceramic Bearings with Krytox 205 / Aeroshell 28 PFPE Grease",
        technology="Silicon Nitride (Si3N4) ceramic balls with perfluoropolyether synthetic lubricant",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-60.0,
        max_temp_c=180.0,
        max_altitude_m=15000.0,
        paschen_rated=True,
        dust_water_rating="IP68 (Hermetic sealed labyrinth)",
        mtbf_hours=120000,
        thermal_derating_pct=8.0,
        mil_std_compliance=["MIL-STD-810H Meth. 500.6", "MIL-G-27617", "MIL-PRF-23827"],
        engineering_rationale="Zero risk of cold seizure down to -60°C. Ceramic balls prevent cold-welding in low-pressure thin air and eliminate thermal expansion mismatch with the titanium gimbal housing."
    ),

    # 3. Direct-Drive Motors & Positioning
    ComponentSpec(
        subsystem="Positioning Motors",
        part_id="MTR-STD-STEPPER",
        name="Commercial Microstepping Motor with Planetary Gearbox",
        technology="2-phase stepper motor with multi-stage spur/planetary reduction gearbox",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=-10.0,
        max_temp_c=65.0,
        max_altitude_m=3000.0,
        paschen_rated=False,
        dust_water_rating="IP50",
        mtbf_hours=15000,
        thermal_derating_pct=50.0,
        mil_std_compliance=["None"],
        engineering_rationale="Gearbox backlash (> 1.5 mrad) and cold gear oil stiction completely prevent micro-radian tracking precision."
    ),
    ComponentSpec(
        subsystem="Positioning Motors",
        part_id="MTR-MIL-BLDC-DIR",
        name="Frameless Direct-Drive BLDC Torque Motor + 26-bit Optical Encoder",
        technology="High-pole slotless neodymium BLDC torque motor with vacuum-rated optical absolute encoder",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-55.0,
        max_temp_c=125.0,
        max_altitude_m=10000.0,
        paschen_rated=True,
        dust_water_rating="IP67",
        mtbf_hours=110000,
        thermal_derating_pct=10.0,
        mil_std_compliance=["MIL-STD-810H Meth. 514.8", "MIL-STD-461G", "MIL-DTL-24308"],
        engineering_rationale="Direct-drive eliminates gear backlash entirely. 26-bit encoder delivers sub-micro-radian angular resolution (0.09 urad/count) required for high-altitude weapon pointing."
    ),

    # 4. RF Power Amplifiers
    ComponentSpec(
        subsystem="RF Transmitters",
        part_id="RF-STD-LDMOS",
        name="Silicon LDMOS 100W SSPA Module (Forced Air)",
        technology="Silicon LDMOS power transistor with extruded aluminum heatsink and high-speed fan",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=-10.0,
        max_temp_c=60.0,
        max_altitude_m=2000.0,
        paschen_rated=False,
        dust_water_rating="IP42",
        mtbf_hours=22000,
        thermal_derating_pct=45.0,
        mil_std_compliance=["None"],
        engineering_rationale="In thin air (5000m), air density drops by 40%, reducing cooling efficiency and causing thermal runaway within 4 minutes. Standard unpotted connectors arc via Paschen breakdown."
    ),
    ComponentSpec(
        subsystem="RF Transmitters",
        part_id="RF-MIL-GAN-HEATPIPE",
        name="Gallium Nitride (GaN-on-SiC) SSPA with Sealed Vapor-Chamber Heat Pipes",
        technology="High-efficiency GaN-on-SiC with vacuum-soldered copper-water heat pipes and hermetic SMA potting",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-45.0,
        max_temp_c=95.0,
        max_altitude_m=12000.0,
        paschen_rated=True,
        dust_water_rating="IP67 (Nitrogen purged)",
        mtbf_hours=85000,
        thermal_derating_pct=12.0,
        mil_std_compliance=["MIL-STD-810H Meth. 500.6", "MIL-STD-461G RE102/RS103"],
        engineering_rationale="Heat pipes bypass low convective air density by transferring heat directly to a large exterior cold plate. Dielectrically potted RF cavities prevent Paschen corona discharge at 25,000 ft."
    ),

    # 5. Battery & Power Storage
    ComponentSpec(
        subsystem="Power Subsystem",
        part_id="PWR-STD-LIPO",
        name="Commercial LiPo Battery Pack (24V 20Ah)",
        technology="Standard pouch-cell Lithium Polymer battery",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=0.0,
        max_temp_c=45.0,
        max_altitude_m=3000.0,
        paschen_rated=False,
        dust_water_rating="IP44",
        mtbf_hours=8000,
        thermal_derating_pct=75.0,
        mil_std_compliance=["UN 38.3"],
        engineering_rationale="Capacity drops by 70% at -20°C due to lithium ion freezing in electrolyte; pouch cells swell and rupture in low atmospheric pressure."
    ),
    ComponentSpec(
        subsystem="Power Subsystem",
        part_id="PWR-MIL-LIFEPO4-PCM",
        name="Ruggedized LiFePO4 Battery with Self-Heating Jacket & Aerogel Insulation",
        technology="Lithium Iron Phosphate cylindrical cells surrounded by Phase-Change Material (PCM) and automatic 45W PTC heating blanket",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-45.0,
        max_temp_c=65.0,
        max_altitude_m=10000.0,
        paschen_rated=True,
        dust_water_rating="IP68 (Pressure-equalized Gore-Tex vent)",
        mtbf_hours=65000,
        thermal_derating_pct=12.0,
        mil_std_compliance=["MIL-STD-810H Meth. 502.7/500.6", "MIL-PRF-32052"],
        engineering_rationale="Gore-Tex vents safely handle rapid barometric altitude changes. Integrated heating jacket keeps cells at +20°C even in -45°C blizzard, sustaining full combat duration."
    ),

    # 6. Optical Lenses & Infrared Sensors
    ComponentSpec(
        subsystem="Electro-Optical / Infrared",
        part_id="OPT-STD-GLASS",
        name="Standard Fixed-Mount Optical Zoom Camera",
        technology="Commercial multi-element glass lenses in standard aluminum barrel",
        standard_or_rugged="COTS_STANDARD",
        min_temp_c=-10.0,
        max_temp_c=50.0,
        max_altitude_m=3000.0,
        paschen_rated=False,
        dust_water_rating="IP54",
        mtbf_hours=20000,
        thermal_derating_pct=55.0,
        mil_std_compliance=["None"],
        engineering_rationale="Thermal defocusing blurs image when temperature deviates by >15°C. Unheated front window freezes solid with mountain frost within 10 minutes."
    ),
    ComponentSpec(
        subsystem="Electro-Optical / Infrared",
        part_id="OPT-MIL-ATHERMAL-MWIR",
        name="Active Athermalized Cooled MWIR Camera + Conductive Heated Sapphire Window",
        technology="Continuous motorized athermalization lens group with ITO-coated heated sapphire de-icing front window and cooled InSb 640x512 FPA",
        standard_or_rugged="MIL_RUGGEDIZED",
        min_temp_c=-46.0,
        max_temp_c=71.0,
        max_altitude_m=12000.0,
        paschen_rated=True,
        dust_water_rating="IP68 (Hermetically sealed)",
        mtbf_hours=55000,
        thermal_derating_pct=4.0,
        mil_std_compliance=["MIL-STD-810H Meth. 502.7/510.7", "MIL-STD-461G"],
        engineering_rationale="Maintains diffraction-limited micro-radian focus across -46°C to +71°C. High-strength sapphire window resists abrasive mountain wind-blown grit and melts ice buildup."
    )
]


class MILSTDQualificationMatrix:
    """
    MIL-STD-810H qualification testing and Bill of Materials assessment engine.
    """

    @classmethod
    def get_all_components(cls) -> List[Dict[str, Any]]:
        return [c.__dict__ for c in COMPONENTS_DATABASE]

    @classmethod
    def evaluate_bom(cls, selected_part_ids: List[str], target_altitude_m: float, min_temp_c: float) -> Dict[str, Any]:
        """
        Evaluates a candidate Bill of Materials for operational deployment suitability.
        """
        selected_specs = [c for c in COMPONENTS_DATABASE if c.part_id in selected_part_ids]
        
        passed_altitude = True
        passed_temperature = True
        total_mtbf = 0
        derating_scores = []
        non_compliant_reasons = []
        
        for comp in selected_specs:
            total_mtbf += comp.mtbf_hours
            derating_scores.append(comp.thermal_derating_pct)
            
            if comp.max_altitude_m < target_altitude_m:
                passed_altitude = False
                non_compliant_reasons.append(
                    f"{comp.name}: Rated max altitude {comp.max_altitude_m}m is below mission altitude {target_altitude_m}m."
                )
            if comp.min_temp_c > min_temp_c:
                passed_temperature = False
                non_compliant_reasons.append(
                    f"{comp.name}: Rated min temp {comp.min_temp_c}°C cannot survive mission temp {min_temp_c}°C."
                )
                
        avg_derating = sum(derating_scores) / max(1, len(derating_scores))
        system_compliance_score = max(0.0, 100.0 - avg_derating - (0.0 if (passed_altitude and passed_temperature) else 35.0))
        
        return {
            "mission_altitude_m": target_altitude_m,
            "mission_min_temp_c": min_temp_c,
            "qualification_passed": passed_altitude and passed_temperature,
            "system_compliance_score": round(system_compliance_score, 1),
            "average_thermal_derating_pct": round(avg_derating, 1),
            "estimated_system_mtbf_hours": total_mtbf // max(1, len(selected_specs)),
            "deficiencies": non_compliant_reasons,
            "mil_std_810h_compliant": passed_altitude and passed_temperature and avg_derating < 15.0
        }
