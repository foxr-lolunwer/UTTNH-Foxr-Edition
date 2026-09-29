tech_map: list = [
    ("fuel_silos", "capacity_industrial_construction"),
    ("concentrated_industry", "concentrated_industry_1"),
    ("concentrated_industry2", "concentrated_industry_2"),
    ("concentrated_industry3", "concentrated_industry_3"),
    ("concentrated_industry4", "concentrated_industry_4"),
    ("concentrated_industry5", "concentrated_industry_5"),
    ("dispersed_industry", "dispersed_industry_1"),
    ("dispersed_industry2", "dispersed_industry_5"),
    ("dispersed_industry3", "dispersed_industry_3"),
    ("dispersed_industry4", "dispersed_industry_4"),
    ("dispersed_industry5", "dispersed_industry_5"),
    ("construction1", "construction_1"),
    ("construction2", "construction_2"),
    ("construction3", "construction_3"),
    ("construction4", "construction_4"),
    ("construction5", "construction_5"),
    ("basic_fortification_tech", "build_tech_bunker_1"),
    ("land_fort_tech_1", "build_tech_bunker_2"),
    ("land_fort_tech_2", "build_tech_bunker_3"),
    ("coastal_fort_tech_1", "build_tech_bunker_2"),
    ("coastal_fort_tech_2", "build_tech_bunker_3"),
    ("fuel_refining", "fuel_refining_1"),
    ("fuel_refining2", "fuel_refining_2"),
    ("fuel_refining3", "fuel_refining_3"),
    ("fuel_refining4", "fuel_refining_4"),
    ("fuel_refining5", "fuel_refining_5"),
    ("improved_equipment_conversion", "coal_energy_1"),
    ("advanced_equipment_conversion", "coal_energy_2"),
    ("excavation1", "excavation_1"),
    ("excavation2", "excavation_2"),
    ("excavation3", "excavation_3"),
    ("excavation4", "excavation_4"),
    ("excavation5", "excavation_5"),
    ("synth_oil_experiments", "synth_oil_1"),
    ("oil_processing", "synth_oil_1"),
    ("improved_oil_processing", "synth_oil_2"),
    ("advanced_oil_processing", "synth_oil_3"),
    ("modern_oil_processing", "synth_oil_4"),
    ("rubber_processing", "resource_expansion_rubber_1"),
    ("improved_rubber_processing", "resource_expansion_rubber_2"),
    ("advanced_rubber_processing", "resource_expansion_rubber_3"),
    ("modern_rubber_processing", "resource_expansion_rubber_4"),
]

def generate_set_flte_tech_from_vanilla():
    lines: list[str] = []
    for vanilla_tech, flte_tech in tech_map:
        lines.append(f"\tif = {{ limit = {{ has_tech = {vanilla_tech} NOT = {{ has_tech = {flte_tech} }} }}")
        lines.append(f"\t\tset_technology = {{ popup = no {flte_tech} = 1 }} }}")
    return lines
l = generate_set_flte_tech_from_vanilla()
print("\n".join(l))