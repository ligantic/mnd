import datetime
import logging

from .dynamic_data_mapping import generate_pdf_field_mappings
from .form_value_resolvers import FormValueResolver

logger = logging.getLogger(__name__)


def _get_form_values(dyn_data):
    form_values = {}
    for form_dict in dyn_data["forms"]:
        form_code = form_dict["name"]
        for section_dict in form_dict["sections"]:
            section_code = section_dict["code"]
            if not section_dict["allow_multiple"]:
                for cde_dict in section_dict["cdes"]:
                    cde_code = cde_dict["code"]
                    form_values[(form_code, section_code, cde_code, 0)] = (
                        cde_dict["value"]
                    )
            else:
                items = section_dict["cdes"]
                for idx, section in enumerate(items):
                    for cde_dict in section:
                        cde_code = cde_dict["code"]
                        form_values[
                            (form_code, section_code, cde_code, idx + 1)
                        ] = cde_dict["value"]
    return form_values


def _merge_form_values(form_values, new_form_values):
    for key, value in new_form_values.items():
        current_value = form_values.get(key)
        if (
            key not in form_values
            or current_value in (None, "", 0, "0")
            or value not in (None, "", 0, "0")
        ):
            form_values[key] = value


def generate_dynamic_data_fields(registry, patient):
    form_values = {}
    max_ts = None
    for context_model in patient.context_models:
        dyn_data = patient.get_dynamic_data(
            registry, context_id=context_model.id
        )
        if not dyn_data:
            continue
        form_ts = dyn_data.get("timestamp", None)
        if form_ts:
            as_dt = datetime.datetime.strptime(form_ts[:10], "%Y-%m-%d")
            if not max_ts:
                max_ts = as_dt
            elif as_dt > max_ts:
                max_ts = as_dt
        _merge_form_values(form_values, _get_form_values(dyn_data))

    cde_codes = [code for (__, __, code, __) in form_values.keys()]
    fvr = FormValueResolver(cde_codes)

    updated_form_values = {}
    for key, value in form_values.items():
        form, section, code, section_index = key
        new_value = fvr.resolve(code, value)
        if new_value != value:
            updated_form_values[(form, section, code, section_index)] = (
                new_value
            )

    form_values.update(updated_form_values)

    data = generate_pdf_field_mappings(form_values)
    if max_ts:
        data["date_updated_af_date"] = max_ts.strftime("%d/%m/%Y")
    return data
