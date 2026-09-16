import datetime
import re

from mnd.integration.mims.mims_service import mims_product_details

# key is (section_code, cde_code), value is pdf form element
_single_section_field_mappings = {
    # My legal docs
    ("myLegalDocs", "legalQuestions", "mndACD"): "acd",
    ("myLegalDocs", "legalQuestions", "mndLDocs"): "checkbox_mappings",
    ("myLegalDocs", "legalQuestions", "mndDocLocation"): "pDocuments",
    # My recent symptoms
    ("mySymptoms", "symptomTypes", "mndSymptomDate"): "mndSymptomsDate_af_date",
    ("mySymptoms", "symptomTypes", "mndFatigue"): "fatigue",
    ("mySymptoms", "symptomTypes", "mndPain"): "pain",
    ("mySymptoms", "symptomTypes", "mndMuscle"): "cramps",
    ("mySymptoms", "symptomTypes", "mndSaliva"): "excsaliva",
    ("mySymptoms", "symptomTypes", "mndConstipation"): "constipation",
    ("mySymptoms", "symptomTypes", "mndDisSleep"): "dSleep",
    ("mySymptoms", "symptomTypes", "mndBreath"): "sBreath",
    ("mySymptoms", "symptomTypes", "mndSpasticity"): "stiffSpas",
    ("mySymptoms", "symptomTypes", "mndChoking"): "choking",
    ("mySymptoms", "symptomTypes", "mndDepression"): "depression",
    ("mySymptoms", "symptomTypes", "mndEmotion"): "emotion",
    # My Life History
    ("myPastLH", "mndHistoryNotes", "mndLHLife"): "life_history",
    ("myPastLH", "mndHistoryNotes", "mndLHWork"): "work_history",
    ("myPastLH", "mndHistoryNotes", "mndLHFriends"): "family_friends",
    ("myPastLH", "mndHistoryNotes", "mndLHDaily"): "daily_routines",
    ("myPastLH", "mndHistoryNotes", "mndLHHobbies"): "hobbies_text",
    ("myPastLH", "mndHistoryNotes", "mndLHChat"): "enjoyable_topics",
    ("myPastLH", "mndHistoryNotes", "mndLHMusic"): "radio_music",
    ("myPastLH", "mndHistoryNotes", "mndLHTV"): "favourite_tv",
    ("myPastLH", "mndHistoryNotes", "mndLHFilms"): "favourite_films",
    ("myPastLH", "mndHistoryNotes", "mndLHBooks"): "favourite_books",
    ("myPastLH", "mndHistoryNotes", "mndLHSocialMedia"): "favourite_blogs",
    ("myPastLH", "mndHistoryNotes", "mndLHAnnoyances"): "dislikes_text",
    ("myPastLH", "mndHistoryNotes", "mndLHWorries"): "worries_text",
    ("myPastLH", "mndHistoryNotes", "mndLHRemedies"): "anxious_text",
    # My Past medical history
    ("myMedHistory", "mndMHDiagnosis", "mndConditions"): "checkbox_mappings",
    ("myMedHistory", "mndMHDiagnosis", "mndCondOther"): "mh_other",
    # My Communication
    ("myCommunication", "mndComms", "mndComDifficulty"): "commLevel",
    ("myCommunication", "mndComms", "mndComTechs"): "checkbox_mappings",
    ("myCommunication", "mndComms", "mndComChairOther"): "commMoreInfo",
    # My positioning
    ("mndPositioning", "mostComfyPos", "myMostComfy"): "comfy_pos",
    ("mndPositioning", "mostComfyPos", "mndComfyOther"): "mndPosOther",
    ("mndPositioning", "inBed", "mndLieFlat"): "lie_flat",
    ("mndPositioning", "inBed", "mndMove"): "move",
    ("mndPositioning", "inBed", "mndNeedHelp"): "checkbox_mappings",
    ("mndPositioning", "inBed", "mndNeedUse"): "checkbox_mappings",
    ("mndPositioning", "inBed", "mndNotes"): "mndPosED",
    ("mndPositioning", "mndSitting", "mndChairNeed"): "checkbox_mappings",
    ("mndPositioning", "mndSitting", "mndChairNotes"): "mndPosSD",
    ("mndPositioning", "mndSitting", "mndChairMove"): "move_chair",
    # My breathing
    ("myBreathing", "mndBreathing", "mndBreathHard"): "bre_trouble",
    ("myBreathing", "mndBreathing", "mndWhenBreathHard"): "checkbox_mappings",
    ("myBreathing", "mndBreathing", "mndBreathTracheostomy"): "tracheostomy",
    ("myBreathing", "mndBreathing", "mndNIVYN"): "niv",
    ("myBreathing", "mndBreathing", "mndBreathAssist"): "checkbox_mappings",
    ("myBreathing", "mndBreathing", "mndBAOther"): "mndBreathingOM",
    ("myBreathing", "mndBreathing", "mndNIVWhen"): "checkbox_mappings",
    ("myBreathing", "mndBreathing", "mndNIVUse"): "checkbox_mappings",
    ("myBreathing", "mndBreathing", "mndNIVdur"): "mndNIV_Hours_Day",
    # My eating and drinking needs
    ("myEatDrink", "mndEating", "mndSwallowD"): "swal",
    ("myEatDrink", "mndEating", "mndByMouth"): "eat_bm",
    ("myEatDrink", "mndEating", "mndHelpEat"): "help_ed",
    ("myEatDrink", "mndEating", "mndACC"): "adapted_cc",
    ("myEatDrink", "mndEating", "mndFluids"): "fluid_lvl",
    ("myEatDrink", "mndEating", "mndFoodCon"): "food_lvl",
    ("myEatDrink", "mndEating", "mndPEG"): "peg",
    ("myEatDrink", "mndEating", "mndTube"): "checkbox_mappings",
    ("myEatDrink", "mndEating", "mndTubeDetails"): "ft_details",
    ("myEatDrink", "mndEating", "mndAvoidFoods"): "checkbox_mappings",
    ("myEatDrink", "mndEating", "mndGluten"): "gluten_details",
    ("myEatDrink", "mndEating", "mndDairy"): "dairy_details",
    ("myEatDrink", "mndEating", "mndPeanuts"): "peanuts_details",
    ("myEatDrink", "mndEating", "mndSoy"): "soy_details",
    ("myEatDrink", "mndEating", "mndEggs"): "eggs_details",
    ("myEatDrink", "mndEating", "mndShell"): "shellfish_details",
    ("myEatDrink", "mndEating", "mndRed"): "rm_details",
    ("myEatDrink", "mndEating", "mndWhite"): "wm_details",
    ("myEatDrink", "mndEating", "mndFish"): "fish_details",
    ("myEatDrink", "mndEating", "mndFoodPrefer"): "prefer_free-text",
    ("myEatDrink", "mndEating", "mndAvoidOther"): "avoid_other",
    # ("myEatDrink", "mndEating", "mndOther"): "",
    # My physical ability
    ("myPhysical", "physicalAbility", "mndWeakness"): "checkbox_mappings",
    ("myPhysical", "physicalAbility", "mndPhyUse"): "checkbox_mappings",
    ("myPhysical", "physicalAbility", "mndWalking"): "walk?",
    ("myPhysical", "physicalAbility", "mndTransHelp"): "checkbox_mappings",
    ("myPhysical", "physicalAbility", "mndMoveAids"): "move-around_fill",
    ("myPhysical", "physicalAbility", "mndTaskAids"): "do-things_fill",
    ("myPhysical", "physicalAbility", "mndRestNeeded"): "rest_fill",
    # My personal care
    (
        "myPC",
        "personalCare",
        "mndPHygiene",
    ): "hygiene",  # button has lower case "some" option instead of "Some"
    ("myPC", "personalCare", "mndShower"): "shower",
    ("myPC", "personalCare", "mndDress"): "dress",
    ("myPC", "personalCare", "mndToil"): "toilet",
    ("myPC", "personalCare", "mndCareNeeds"): "personal-care",
    # My mouth care and saliva
    ("myMCare", "mndMouth", "mndMHelp"): "mouth_care",
    ("myMCare", "mndMouth", "mndBrush"): "brush-teeth",
    ("myMCare", "mndMouth", "mndSwabs"): "swabs",
    ("myMCare", "mndMouth", "mndXSaliva"): "saliva",
    ("myMCare", "mndMouth", "mndManageSaliva"): "checkbox_mappings",
    ("myMCare", "mndMouth", "mndSalivaOther"): "sm_other",
    # My emotions
    ("myEmotions", "mndEmotionCare", "mndEmotionNotes"): "emotions_fill",
    # My medications and allergies
    ("myMedsNAll", "myAllergies", "mndAllergies"): (
        "allergies_text",
        "MedicationAllergies",
    ),
    # First visit
    ("firstVisit", "DxDetails", "MNDDiagnosis"): "mndType",
    ("firstVisit", "mndPresentingDetails", "mndDateConfirm"): "mndDiagDate",
    ("firstVisit", "mndImported1a", "mndDateConfirm"): "mndDiagDate",
}

# key is (section_code, cde_code), value is pdf form element base (and index is appended..usually from 1 to 9)
_multi_section_field_mappings = {
    # My medications and allergies
    ("myMedsNAll", "myMedList", "mndDateStarted"): "start_date",
    ("myMedsNAll", "myMedList", "mndMedName"): "med_name",
    ("myMedsNAll", "myMedList", "mndMedDose"): "med_dose",
    ("myMedsNAll", "myMedList", "mndMedPurpose"): "med_use",
    ("myMedsNAll", "myMedList", "mndMedAdmin"): "med_taken",
    ("myMedsNAll", "myMedList", "mndMedTime"): "med_times",
    # My appointments
    ("myAppointments", "mndApptList", "mndAName"): "Name of Team memberRow",
    ("myAppointments", "mndApptList", "mndApptDate"): "Date of appointmentRow",
    ("myAppointments", "mndApptList", "mndApptTime"): "TimeRow",
    # My care team
    ("myCareTeam", "myCarerDetails", "mndCRole"): "mndCarerProfession",
    ("myCareTeam", "myCarerDetails", "mndCName"): "NameRow",
    ("myCareTeam", "myCarerDetails", "mndCPhone"): "TelephoneRow",
    ("myCareTeam", "myCarerDetails", "mndCEmail"): "EmailRow",
}

# pdf form field can be sourced from the first non-null value in a list of (section_code, cde_code)
_cascading_section_field_mappings = {
    "alsfrsScore": {
        "hierarchy": [
            ("subsequentVisit", "mndCALC", "mndALSFRS"),
            ("firstVisit", "mndCALC", "mndALSFRS"),
            ("alsfrsInstrument", "myALSFRSScoreTotal", "mndALSScore"),
        ],
        "default": ("mndCALC", "0"),
    },
}

_care_team_section = "myCarerDetails"
_care_team_primary_carer_cde = "mndPrimary"


def _interval_mapping(input_val):
    if input_val == 0 or input_val == "" or input_val is None:
        return "none"
    if input_val < 5:
        return "mild"
    if input_val < 9:
        return "moderate"
    return "severe"


def _communication_value_mapping(input_val):
    mappings = {
        "no difficulty communicating": "No difficulty",
        "some difficulty communicating": "Some Difficulty",
        "great difficulty communicating": "Great difficulty",
    }
    return mappings.get(input_val, "")


def _comfy_pos_mapping(input_val):
    mappings = {
        "In bed": "bed",
        "In my wheelchair": "wheelchair",
        "In a comfortable chair (e.g. Recliner)": "Chair",
    }
    return mappings.get(input_val, "")


def _mnd_type_mapping(input_val):
    mappings = {
        "ALS- Bulbar Onset": "ALS Bulbar Onset",
        "ALS-Cervical Onset": "ALS Cervical Onset",
        "ALS-Thoracic Diaphragmatic Onset": "ALS Diaphragmatic Onset",
        "ALS-Lumbar Onset": "ALS Lumbar Onset",
        "Flail arm": "Flail arm",
        "Flail leg": "Flail leg",
        "PLS": "PLS",
        "Undifferentiated": "Undifferentiated",
    }
    return mappings.get(input_val, "")


def _eat_drink_by_mouth_mapping(input_val):
    mappings = {"Yes": "Yes", "Some types": "Some", "No": "No"}
    return mappings.get(input_val, "")


def _help_eat_mapppings(input_val):
    mappings = {"I need to be fed": "Need", "Some help": "some", "No": "No"}
    return mappings.get(input_val, "")


def _level_mapping(input_val):
    result = re.match(r"^Level\s(\d+)(.)*", input_val)
    if result and result.groups():
        return result.groups()[0]


def _avoid_details_mapping(input_val):
    mappings = {
        "Allergy": "Allergy",
        "Intolerance": "Intolerance",
        "Lifestyle Choice": "Lifestyle_Choice",
    }
    return mappings.get(input_val, "")


def _walk_values_mapping(input_val):
    mappings = {"Yes": "Yes", "No": "No", "With Support or Aids": "need_aid"}
    return mappings.get(input_val, "")


def _brush_teeth_mapping(input_val):
    mappings = {
        "Once a day": "Once",
        "Twice daily": "Twice",
        "Three times a day": "3-times",
    }
    return mappings.get(input_val, "")


def _medication_mapping(input_val):
    product = mims_product_details(input_val)
    return product.name if product else input_val


def _date_mapping(input_val):
    if input_val:
        return datetime.datetime.strptime(input_val, "%Y-%m-%d").strftime(
            "%d/%m/%Y"
        )
    else:
        return ""


_values_mapping_cdes = {
    "mndFatigue": _interval_mapping,
    "mndPain": _interval_mapping,
    "mndMuscle": _interval_mapping,
    "mndSaliva": _interval_mapping,
    "mndConstipation": _interval_mapping,
    "mndDisSleep": _interval_mapping,
    "mndBreath": _interval_mapping,
    "mndSpasticity": _interval_mapping,
    "mndChoking": _interval_mapping,
    "mndDepression": _interval_mapping,
    "mndEmotion": _interval_mapping,
    "mndComDifficulty": _communication_value_mapping,
    "myMostComfy": _comfy_pos_mapping,
    "MNDDiagnosis": _mnd_type_mapping,
    "mndByMouth": _eat_drink_by_mouth_mapping,
    "mndHelpEat": _help_eat_mapppings,
    "mndFluids": _level_mapping,
    "mndFoodCon": _level_mapping,
    "mndGluten": _avoid_details_mapping,
    "mndDairy": _avoid_details_mapping,
    "mndPeanuts": _avoid_details_mapping,
    "mndSoy": _avoid_details_mapping,
    "mndEggs": _avoid_details_mapping,
    "mndShell": _avoid_details_mapping,
    "mndRed": _avoid_details_mapping,
    "mndWhite": _avoid_details_mapping,
    "mndFish": _avoid_details_mapping,
    "mndWalking": _walk_values_mapping,
    "mndBrush": _brush_teeth_mapping,
    "mndMedName": _medication_mapping,
    "mndDateConfirm": _date_mapping,
    "mndSymptomDate": _date_mapping,
    "mndDateStarted": _date_mapping,
}


_checkbox_mapping_cdes = {
    "mndConditions": {
        "Asthma": "mh_asthma",
        "Cancer": "mh_cancer",
        "Depression": "mh_depression",
        "Diabetes": "mh_diabetes",
        "Heart Disease": "mh_heart-disease",
        "Anxiety": "mh_anxiety",
        "High Blood Pressure": "mh_hbp",
    },
    "mndComTechs": {
        "paperPen": "commPen",
        "talkToText": "commTextApp",
        "commsBoard": "commBoard",
        "voiceAmplifier": "commVA",
        "eyeGaze": "commEyeGaze",
        "compWithSwitch": "commSwitch",
    },
    "mndLDocs": {
        "Enduring Power of Guardianship": "epg",
        "A Medical Power of Attorney": "mpa",
        "An Anticipatory Direction": "ad",
        "DNR Form": "dnr",
        "Organ and/or Tissue Donation": "otd",
    },
    "mndNeedHelp": {
        "Sit Up": "sit",
        "Turn Over": "turn_over",
        "Change Position": "change_pos",
    },
    "mndNeedUse": {
        "An adjustable bed": "adj_bed",
        "Extra pillows": "ex_pillows",
        "Pressure relieving mattress": "prm",
        "Bed cradle": "bed_cradle",
        "Neck support when sitting up": "neck_support",
    },
    "mndChairNeed": {
        "A lift or electric recliner": "lift_e-rec",
        "Pressure relief": "pressure_relief",
        "Head or neck support": "head_neck_support",
        "An electric wheelchair": "e-wheelchair",
    },
    "mndWhenBreathHard": {
        "At rest": "rest",
        "Moving around": "moving",
        "Moving a lot": "moving_lots",
    },
    "mndBreathAssist": {
        "Suctioning": "suct",
        "Assisted cough techniques": "act",
        "A fan": "fan",
        "Positioning": "bre_pos",
    },
    "mndNIVWhen": {
        "Whenever I sleep": "niv_sleep",
        "When needed": "niv_needed",
        "Most of the time": "niv_mostly",
    },
    "mndNIVUse": {
        "Independent": "niv_ind",
        "Need some assistance": "niv_some_help",
        "Need full assistance": "niv_full_assist",
    },
    "mndTube": {
        # Cannot find option in PDF for all options
        "For hydration": "hydration",
        "To top up my meals": "meals",
        "For all food and drink": "all_fd",
        "I need help with my tube feeds": "ft_help",
        "Need PEG but enjoy some food": "safbm",
    },
    "mndAvoidFoods": {
        "Gluten": "gluten",
        "Dairy": "dairy",
        "Peanuts": "peanuts",
        "Soy": "soy",
        "Eggs": "eggs",
        "Shellfish": "shellfish",
        "Red Meat": "red_meat",
        "White Meat": "white_meat",
        "Fish": "fish",
    },
    "mndWeakness": {
        "Upper Limbs": "u_limbs",
        "Lower Limbs": "l_limbs",
        "Head/Neck": "head_neck",
        "Trunk": "trunk",
    },
    "mndPhyUse": {
        "Arm/Wrist Splints": "aw_splints",
        "Leg/Foot Splints": "lf_splints",
        "Head/Neck Support": "hn_support",
    },
    "mndTransHelp": {
        "Not Needed": "not_needed",
        "Bed": "Bed",
        "A Chair": "chair",
        "Toilet": "toilettransfer",
    },
    "mndManageSaliva": {
        "Medication": "sm_meds",
        "Suction": "sm_suction",
        "Clothing Protection": "sm_clothing-p",
        "Swallowing": "sm_swallowing",
        "Clearance Techniques": "sm_clearance",
        "Wiping Mouth": "smWiping",
    },
}


def _set_data_fields(data, field, cde_code, value):
    if cde_code in _values_mapping_cdes:
        mapping_func = _values_mapping_cdes[cde_code]
        data[field] = mapping_func(value)
    elif cde_code in _checkbox_mapping_cdes:
        mappings = _checkbox_mapping_cdes[cde_code]
        if isinstance(value, list):
            checkbox_updates = {
                mappings[v]: "Yes" for v in value if v in mappings
            }
        else:
            checkbox_updates = {
                mappings[v]: "Yes" for v in [value] if v in mappings
            }
        data.update(checkbox_updates)
    else:
        data[field] = value


def _get_primary_carer_section_index(form_values):
    for section_index in range(1, 10):
        key = (_care_team_section, _care_team_primary_carer_cde, section_index)
        if key in form_values:
            value = form_values[key]
            if value and value[0] == "PrimaryContact":
                return section_index
    return 1


def generate_pdf_field_mappings(form_values):
    data = {}

    # Dynamic data tuple -> pdf field
    for (
        form_code,
        section_code,
        cde_code,
    ), field in _single_section_field_mappings.items():
        single_section_key = (form_code, section_code, cde_code, 0)
        if single_section_key in form_values:
            value = form_values[single_section_key]
            if isinstance(field, tuple):
                for f in field:
                    _set_data_fields(data, f, cde_code, value)
            else:
                _set_data_fields(data, field, cde_code, value)

    # pdf field -> list of dynamic data tuples
    for pdf_field, field_config in _cascading_section_field_mappings.items():
        data_keys = field_config["hierarchy"]
        default_code, default_value = field_config["default"]
        for key in data_keys:
            form_code, section_code, cde_code = key
            single_section_key = (*key, 0)
            if single_section_key in form_values:
                value = form_values[single_section_key]
                if value:
                    _set_data_fields(data, pdf_field, cde_code, value)

                    # Retrieve matching date value
                    if (
                        pdf_field == "alsfrsScore"
                        and form_code != "alsfrsInstrument"
                    ):
                        if date_value := form_values.get(
                            (form_code, "mndPatientInformation", "mndVDate", 0)
                        ):
                            _set_data_fields(
                                data,
                                "mndTestDate_af_date",
                                None,
                                _date_mapping(date_value),
                            )
                    break
        else:
            _set_data_fields(data, pdf_field, default_code, default_value)

    # Find primary carer's index in care team
    primary_carer_index = _get_primary_carer_section_index(form_values)
    section_indexes = range(1, 10)
    carer_indexes = list(range(1, 14))
    if primary_carer_index != 1:
        carer_indexes.remove(primary_carer_index)
        carer_indexes.insert(0, primary_carer_index)

    # Dynamic data tuple -> indexed pdf fields
    for (
        form_code,
        section_code,
        cde_code,
    ), field in _multi_section_field_mappings.items():
        indexes = (
            carer_indexes
            if section_code == _care_team_section
            else section_indexes
        )
        for idx, i in enumerate(indexes):
            indexed_field = f"{field}{idx + 1}"
            if field == "med_times":
                # special handling for medicine administration times
                suffixes = ["", "2", "3", "4", "5", "6", "6Plus"]
                keys = [
                    (form_code, section_code, cde_code + suffix, i)
                    for suffix in suffixes
                ]
                if any(k in form_values for k in keys):
                    values = [form_values[k] for k in keys if k in form_values]
                    value = ", ".join([v for v in values if v])
                    _set_data_fields(data, indexed_field, cde_code, value)
            else:
                section_key = (form_code, section_code, cde_code, i)
                if section_key in form_values:
                    value = form_values[section_key]
                    _set_data_fields(data, indexed_field, cde_code, value)
                else:
                    # Default to empty values for non existing indexed values
                    _set_data_fields(data, indexed_field, cde_code, "")

    return data
