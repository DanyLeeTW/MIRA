"""Un-uncomment if you want to generate the enums and code maps.
However, these are already generated and saved in the 'MimicEnums' folder."""

# import os

# import pandas as pd
# from tqdm import tqdm

# tqdm.pandas()

# import os
# from concurrent.futures import ThreadPoolExecutor
# from typing import Iterable

# import pandas as pd
# from code_maps import *
# from codes.medication_codes import (
#     UMLS_API_KEY,
#     get_loinc_code_from_modality_region,
#     get_snomed_code_from_modality_region,
#     get_umls_tgt,
# )
# from dataset.data import BASE_HOSP, BASE_NOTE
# from dataset.radiology import process_radiology, sanitize_radiology_entries
# from tqdm import tqdm

# LAB_EVENTS_ENUM_TOPK = 400


# def generate_lab_events_enums(d_labitems_path, d_labitems_to_loinc_path):
#     """
#     Generate enums for lab events.
#     """
#     # load d_labitems and the loinc mappings
#     d_labitems = pd.read_csv(BASE_HOSP.joinpath(d_labitems_path))
#     d_labitems_to_loinc = pd.read_csv(d_labitems_to_loinc_path)
#     d_labitems_to_loinc.rename(
#         columns={"itemid (omop_source_code)": "itemid"}, inplace=True
#     )

#     # merge both tables
#     d_labitems_loinc_omop = d_labitems.merge(
#         d_labitems_to_loinc[
#             [
#                 "itemid",
#                 "label",
#                 "fluid",
#                 "category",
#                 "omop_concept_id",
#                 "omop_concept_name",
#                 "omop_concept_code",
#             ]
#         ],
#         left_on=["itemid", "label", "fluid", "category"],
#         right_on=["itemid", "label", "fluid", "category"],
#         how="left",
#     )

#     # map d_labitems 'itemid' to 'omop_concept_code'
#     # remove a few samples where label is NaN ?!
#     print("Labels that are NA will be dropped:")
#     print(d_labitems_loinc_omop[d_labitems_loinc_omop.label.isna()])

#     d_labitems_loinc_omop = d_labitems_loinc_omop[d_labitems_loinc_omop.label.notna()]
#     lab_itemid_to_omop_concept = d_labitems_loinc_omop.set_index("itemid")[
#         "omop_concept_code"
#     ].to_dict()

#     # itemid -> LOIC OMOP seems to be a many to one mapping.. Before assert that itemid's are not duplicated
#     duplicate_itemids = d_labitems_loinc_omop[
#         d_labitems_loinc_omop.duplicated(subset=["itemid"], keep=False)
#     ]
#     assert (
#         duplicate_itemids.empty
#     ), "There are duplicate 'itemid's in the labitems dataframe"

#     # generate on valid Enum for each possible fluid we want to have lab values for
#     unique_fluids = d_labitems_loinc_omop.fluid.unique().tolist()

#     #########################################################################################
#     # return d_labitems_loinc_omop
#     print("Loading labevents and d_labitems .csv. ... This might take a while.")
#     labevents_path = (
#         "labevents.csv"  # https://mimic.mit.edu/docs/iv/modules/hosp/labevents/
#     )
#     lab_events = pd.read_csv(BASE_HOSP.joinpath(labevents_path))
#     d_labitems = pd.read_csv(BASE_HOSP.joinpath("d_labitems.csv"))
#     lab_events_annot = lab_events.merge(d_labitems, on="itemid", how="left")
#     #########################################################################################

#     _code = "from enum import Enum\n\n"
#     for fluid in unique_fluids:
#         d_labitems_fluid = d_labitems_loinc_omop[d_labitems_loinc_omop.fluid == fluid]
#         d_labitems_fluid = d_labitems_fluid.drop_duplicates(
#             subset=["label"]
#         )  # remove duplicates from the same fluid

#         #########################################################################################
#         lab_events_fluid = lab_events_annot[lab_events_annot.fluid == fluid]
#         topk_labels = (
#             lab_events_fluid.label.value_counts()
#             .nlargest(LAB_EVENTS_ENUM_TOPK)
#             .index.tolist()
#         )
#         if len(topk_labels) == 0:
#             print(f"No lab events found for {fluid} -> Irrelevant. Skipping.")
#             continue
#         print(f"Generating Enum for {fluid} with {len(topk_labels)} labels:")
#         print(topk_labels)
#         d_labitems_fluid = d_labitems_fluid[d_labitems_fluid.label.isin(topk_labels)]
#         d_labitems_fluid = (
#             d_labitems_fluid.set_index("label").loc[topk_labels].reset_index()
#         )
#         #########################################################################################

#         fluid_name = fluid.replace(" ", "")
#         # Dynamically create the {fluid_name}Value Enum class with itemid and label from the subsetted dataframe
#         _code += f"class {fluid_name}Value(str, Enum):\n"
#         for item in d_labitems_fluid.itertuples():
#             label = item.label
#             if f", {fluid}" in label:
#                 label = label.replace(f", {fluid}", "")
#             _code += f'    _{item.itemid} = "{label}"\n'
#         _code += "\n\n"

#     # Write the class definitions to a .py file
#     os.makedirs("MimicEnums", exist_ok=True)
#     with open(f"MimicEnums/LabEventsEnums.py", "w") as file:
#         file.write(_code)

#     with open("code_maps.py", mode="a") as file:
#         file.write("\n\n")
#         file.write("lab_itemid_to_omop_concept = {\n")
#         for key, value in lab_itemid_to_omop_concept.items():
#             file.write(f"    '_{key}': '{value}',\n")
#         file.write("}\n")


# def generate_microbiology_enum(microbiologyevents_path):
#     """
#     Generate a mapping between 'test_itemid' and 'test_name' in MIMIC 'microbiologyevents.csv' and write them as an Enum to 'MicrobiologyEnum.py'
#     """

#     # https://mimic.mit.edu/fhir/ValueSet-mimic-microbiology-test.html
#     microbiology = pd.read_csv(BASE_HOSP.joinpath(microbiologyevents_path))
#     microbiology = microbiology[["test_itemid", "test_name"]]
#     microbiology = microbiology.dropna(subset=["test_itemid", "test_name"])

#     # Sort the microbiology table by the most frequent "test_name"
#     microbiology_counts = microbiology["test_name"].value_counts().reset_index()
#     microbiology_counts.columns = ["test_name", "counts"]
#     microbiology = microbiology.merge(microbiology_counts, on="test_name")
#     microbiology = microbiology.sort_values(by="counts", ascending=False)
#     microbiology = microbiology.drop(columns="counts")
#     microbiology = microbiology.drop_duplicates(subset=["test_itemid", "test_name"])
#     print("Microbiology table top 10 requests")
#     print(microbiology.head(10))  # Print the top 10 most frequent test_names

#     assert microbiology[
#         "test_itemid"
#     ].is_unique, "There are duplicates in the test_itemid column"

#     _code = "from enum import Enum\n\n"
#     _code += f"class MicroBiologyValue(str, Enum):\n"
#     for item in microbiology.itertuples():
#         label, test_name = item.test_itemid, item.test_name
#         if test_name.strip() == "":
#             continue
#         _code += f'    _{label} = "{test_name}"\n'
#     _code += "\n\n"

#     os.makedirs("MimicEnums", exist_ok=True)
#     with open(f"MimicEnums/MicrobiologyEnum.py", "w") as file:
#         file.write(_code)

#     return None


# def generate_medication_route_enum(
#     prescriptions_path: str, mapping: dict = route_to_snomed_ct, max_items=None
# ):
#     """Generate a mapping between 'route' field in MIMIC 'prescriptions.csv' and SNOMED CT codes.
#     Routes from MIMIC table have been manually mapped to SNOMED CT descriptions.
#     We now map these from 'codes_map.route_to_snomed_ct codes and write them as an Enum to 'RouteEnum.py'
#     """

#     prescriptions = pd.read_csv(BASE_HOSP / prescriptions_path)

#     routes = prescriptions.route.value_counts().to_dict()
#     routes = list(routes.keys())[:max_items]

#     # control that both have the same content
#     assert (
#         len(set(routes).intersection(set(mapping.keys())))
#         == len(set(routes))
#         == len(set(mapping.keys()))
#     ), "Invalid routes ..."

#     # read in the SNOMED mappings from https://build.fhir.org/valueset-route-codes.html
#     medication_routes_to_snomed = pd.read_csv("resources/medication_routes.csv")
#     medication_routes_to_snomed["route"] = medication_routes_to_snomed[
#         "route"
#     ].str.strip()
#     # get unique values
#     unique_route_to_snomed = set(
#         sum(
#             [
#                 sublist if isinstance(sublist, list) else [sublist]
#                 for sublist in mapping.values()
#             ],
#             [],
#         )
#     )

#     # write the enum to .py file
#     _code = "from enum import Enum\n\n"
#     _code += f"class RouteUnit(str, Enum):\n"
#     _code += f"    # https://build.fhir.org/valueset-route-codes.html\n"
#     _code += f"    # Mapping of MIMIC prescriptions.csv abbreviations to SNOMED CT routes via manual lookup from 'code_maps.route_to_snomed_ct'\n"
#     for route in unique_route_to_snomed:
#         route = route.strip()
#         if route.strip() == "" or route == "<UNKNOWN>":
#             continue
#         snomed_code = medication_routes_to_snomed[
#             medication_routes_to_snomed.route == route
#         ]["snomed_code"].values[0]
#         route = route.replace("route", "").replace("use", "").strip()  # simplify it
#         _code += f'    _{snomed_code} = "{route}"\n'
#     _code += "\n\n"

#     os.makedirs("MimicEnums", exist_ok=True)
#     with open(f"MimicEnums/RouteEnum.py", mode="a") as file:
#         file.write(_code)

#     return None


# def get_radiology_codes(unique_combinations, tgt):
#     """
#     Get SNOMED CT and LOINC codes for radiology data.
#     """
#     snomed_code_cache = {}
#     loinc_code_cache = {}

#     def get_snomed_code(modality, region, tgt):
#         """
#         Get SNOMED CT code for a given modality and region.
#         """
#         key = modality.strip().replace(" ", ""), region.strip().replace(" ", "")
#         code = get_snomed_code_from_modality_region(modality, region, tgt)
#         snomed_code_cache[key] = code
#         return

#     def get_loinc_code(modality, region, tgt):
#         """
#         Get LOINC code for a given modality and region.
#         """
#         key = modality.strip().replace(" ", ""), region.strip().replace(" ", "")
#         code = get_loinc_code_from_modality_region(modality, region, tgt)
#         loinc_code_cache[key] = code
#         return

#     def _process_combination(combination):
#         """
#         Process a combination of modality and region.
#         """
#         region, modality = combination
#         get_snomed_code(modality, region, tgt)
#         get_loinc_code(modality, region, tgt)

#     with ThreadPoolExecutor(max_workers=8) as executor:
#         list(
#             tqdm(
#                 executor.map(_process_combination, unique_combinations),
#                 total=len(unique_combinations),
#                 desc="Processing SNOMED and LOINC radiology codes",
#             )
#         )

#     return snomed_code_cache, loinc_code_cache


# def generate_radiology_modality_enum(modalities: Iterable):
#     """
#     Generate a mapping between 'modality' field in MIMIC 'radiology.csv' and SNOMED CT codes.
#     Modality from MIMIC table have been manually mapped to SNOMED CT descriptions.
#     We now map these from 'codes_map.radiology_modality_to_snomed_ct codes and write them as an Enum to 'RadiologyModalityEnum.py'
#     """
#     assert len(modalities) == len(
#         set(modalities)
#     ), "There are duplicates in the modalities"

#     _code = "from enum import Enum\n\n"
#     _code += f"class RadiologyModalityValue(str, Enum):\n"

#     for item in modalities:
#         _code += f'    {item.strip().replace(" ", "")} = "{item.strip()}"\n'
#     _code += "\n\n"

#     os.makedirs("MimicEnums", exist_ok=True)
#     with open(f"MimicEnums/RadiologyModalityEnum.py", "w") as file:
#         file.write(_code)

#     return None


# def generate_radiology_region_enum(regions: Iterable):
#     """
#     Generate a mapping between 'region' field in MIMIC 'radiology.csv' and SNOMED CT codes.
#     Region from MIMIC table have been manually mapped to SNOMED CT descriptions.
#     We now map these from 'codes_map.radiology_region_to_snomed_ct codes and write them as an Enum to 'RadiologyRegionEnum.py'
#     """
#     assert len(regions) == len(set(regions)), "There are duplicates in the regions"

#     _code = "from enum import Enum\n\n"
#     _code += f"class RadiologyRegionValue(str, Enum):\n"

#     for item in regions:
#         _code += f'    {item.strip().replace(" ", "")} = "{item.strip()}"\n'
#     _code += "\n\n"

#     os.makedirs("MimicEnums", exist_ok=True)
#     with open(f"MimicEnums/RadiologyRegionEnum.py", "w") as file:
#         file.write(_code)

#     return None


# def generate_radiology_enums_and_mappings():
#     """
#     Generate enums and code maps for radiology data.
#     """
#     radiology_path = "radiology.csv"
#     radiologydetail_path = "radiology_detail.csv"

#     radiology = pd.read_csv(BASE_NOTE.joinpath(radiology_path))
#     radiology_detail = pd.read_csv(BASE_NOTE.joinpath(radiologydetail_path))

#     radiology["charttime"] = pd.to_datetime(radiology["charttime"])

#     radiology_hadm_ids = process_radiology(radiology, radiology_detail, hadm_ids=None)
#     radiology_hadm_ids = sanitize_radiology_entries(radiology_hadm_ids)

#     unique_modalities = radiology_hadm_ids["modality"].value_counts().index.tolist()
#     unique_regions = radiology_hadm_ids["region"].value_counts().index.tolist()

#     print("unique modalities: ", len(unique_modalities))
#     print("unique regions: ", len(unique_regions))

#     unique_combinations = [
#         (region, modality)
#         for region in unique_regions
#         for modality in unique_modalities
#     ]
#     print("unique combinations: ", len(unique_combinations))

#     tgt = get_umls_tgt(UMLS_API_KEY)

#     snomed_code_cache, loinc_code_cache = get_radiology_codes(unique_combinations, tgt)

#     print("Generating enums")
#     generate_radiology_modality_enum(unique_modalities)
#     generate_radiology_region_enum(unique_regions)

#     print("Generating code maps")
#     with open("code_maps.py", mode="a") as file:
#         file.write("\n\n")
#         file.write("radiology_modality_and_region_to_snomed_concept = {\n")
#         for key, value in snomed_code_cache.items():
#             file.write(f"    '{'_'.join(key)}': '{value}',\n")
#         file.write("}\n")

#     with open("code_maps.py", mode="a") as file:
#         file.write("\n\n")
#         file.write("radiology_modality_and_region_to_loinc_concept = {\n")
#         for key, value in loinc_code_cache.items():
#             file.write(f"    '{'_'.join(key)}': '{value}',\n")
#         file.write("}\n")


# if __name__ == "__main__":
#     print("Generating enums for lab events")
#     generate_lab_events_enums(
#         "d_labitems.csv",
#         "/dataset/labitems_map/d_labitems_to_loinc.csv",
#     )
#     print("Generating enum for microbiology")
#     generate_microbiology_enum("microbiologyevents.csv")

#     # # print("Generating enum for medication routes")
#     # # generate_medication_route_enum("prescriptions.csv")
#     # # print("Generating enums and code maps for radiology")
#     # generate_radiology_enums_and_mappings()
