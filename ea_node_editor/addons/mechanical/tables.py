# Purpose: Extract Mechanical model-definition fields into immutable COREX tables.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_definition_tables.py

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from ea_node_editor.addons.mechanical.contracts import DEFINITIONS_COLUMNS, definitions_table
from ea_node_editor.runtime_contracts import TableValue
from ea_node_editor.runtime_contracts.scientific_codec import check_scientific_budget
from ea_node_editor.runtime_contracts.scientific_values import (
    SCIENTIFIC_OPERATION_MAX_BYTES,
    SCIENTIFIC_VALUE_MAX_BYTES,
    snapshot_scientific_value,
)

# JSON may escape one accepted UTF-8 label byte as six ASCII bytes. Eight times
# the decoded operation ceiling also covers base64 buffers and JSON structure.
DEFINITION_ENCODED_MAX_BYTES = 8 * SCIENTIFIC_OPERATION_MAX_BYTES


# This body runs inside Mechanical. Keep it compatible with the product's scripting
# engine and detach every native object before returning across the server boundary.
DEFINITION_SCRIPT_BODY = r'''
def _corex_text(value):
    return '' if value is None else str(value)

def _corex_path(value):
    parts=[]
    seen=[]
    while value is not None and id(value) not in seen:
        seen.append(id(value))
        try:name=_corex_text(value.Name).strip()
        except:name=''
        if name:parts.append(name)
        try:value=value.Parent
        except:value=None
    parts.reverse()
    return '/'.join(parts)

def _corex_type(value):
    try:return str(value.GetType().FullName)
    except:return type(value).__name__

def _corex_property_key(prop,index):
    for name in ('APIName','Name'):
        try:value=_corex_text(getattr(prop,name))
        except:value=''
        if value and value != 'None':return value
    return 'property:'+str(index)

def _corex_quantity(value,quantity_name,source_unit):
    if value is None:return {'value':None,'unit':source_unit}
    target=value
    if _corex_data['units']=='si':
        if not quantity_name:
            raise ValueError('mechanical.table_unsupported: SI conversion requires Variable.QuantityName')
        target=value.ConvertToUnitSystem('SI',quantity_name)
    try:magnitude=float(target.Value)
    except AttributeError:
        if type(target) not in (int,float):
            raise ValueError('mechanical.table_unsupported: Field sample is not a Quantity')
        magnitude=float(target)
    unit=source_unit
    try:unit=_corex_text(target.Unit)
    except:pass
    return {'value':magnitude,'unit':unit}

def _corex_variable(variable,role):
    definition=_corex_text(variable.DefinitionType).split('.')[-1]
    formula=''
    if definition=='Formula':
        raw_formula=variable.Formula
        formula='' if raw_formula is None else str(raw_formula)
    unit=_corex_text(variable.Unit)
    quantity_name=_corex_text(variable.QuantityName)
    try:raw_values=list(variable.DiscreteValues or [])
    except TypeError:raw_values=[]
    values=[]
    converted_unit=unit
    for raw_value in raw_values:
        sample=_corex_quantity(raw_value,quantity_name,unit)
        values.append(sample['value'])
        converted_unit=sample['unit']
    if _corex_data['units']=='si' and not raw_values and unit:
        if not quantity_name:
            raise ValueError('mechanical.table_unsupported: SI conversion requires Variable.QuantityName')
        converted_unit=str(Ansys.Core.Units.UnitsManager.GetQuantityUnitForUnitSystem('SI',quantity_name))
    try:declared_count=int(variable.DiscreteValueCount)
    except:declared_count=len(values)
    if definition!='Free' and declared_count != len(values):
        raise ValueError('mechanical.table_unsupported: Variable discrete count does not match its samples')
    return {
        'name':_corex_text(variable.Name),'role':role,
        'definition_type':definition,'formula':formula,'unit':converted_unit,
        'quantity_name':quantity_name,'values':values,
    }

def _corex_fields(obj):
    result=[]
    try:properties=list(obj.VisibleProperties)
    except Exception as exc:
        raise ValueError('mechanical.table_unsupported: visible properties unavailable for '+_corex_path(obj))
    for index,prop in enumerate(properties):
        key=_corex_property_key(prop,index)
        try:internal=getattr(obj,key)
        except:continue
        if internal is None:continue
        try:
            inputs=list(internal.Inputs or [])
            output=internal.Output
        except:continue
        if output is None:continue
        try:caption=_corex_text(prop.Caption)
        except:caption=key
        try:field_name=_corex_text(internal.Name)
        except:field_name=caption
        variables=[]
        for variable in inputs:variables.append(_corex_variable(variable,'independent'))
        variables.append(_corex_variable(output,'dependent'))
        result.append({
            'kind':'field','table_key':str(int(obj.ObjectId))+':'+key+':field',
            'object_path':_corex_path(obj),'property_key':key,
            'property_caption':caption,'component':field_name or caption or key,
            'variables':variables,
        })
    return result

def _corex_step_count(obj,objects):
    cursor=obj
    while cursor is not None:
        try:return int(cursor.AnalysisSettings.NumberOfSteps)
        except:pass
        try:cursor=cursor.Parent
        except:cursor=None
    counts=[]
    for analysis in objects:
        try:count=int(analysis.AnalysisSettings.NumberOfSteps)
        except:continue
        try:active=str(Model.GetActivationStatusForAnalysis(int(obj.ObjectId),int(analysis.ObjectId))).split('.')[-1]=='ObjectActive'
        except:active=False
        if active:counts.append(count)
    if not counts or len(set(counts)) != 1:
        raise ValueError('mechanical.table_unsupported: Bolt pretension step count is unavailable or ambiguous')
    return counts[0]

def _corex_bolt_states(obj,objects):
    count=_corex_step_count(obj,objects)
    states=[]
    for step in range(1,count+1):
        states.append({'step':step,'state':str(obj.GetDefineBy(step)).split('.')[-1]})
    return {
        'kind':'bolt_states','table_key':str(int(obj.ObjectId))+':bolt_step_states',
        'object_path':_corex_path(obj),'property_key':'GetDefineBy',
        'property_caption':'Bolt pretension step states','component':'Step state',
        'states':states,
    }

objects=list(Tree.AllObjects)
objects_by_id={int(value.ObjectId):value for value in objects}
selected=[]
for source in _corex_data['sources']:
    obj=objects_by_id.get(int(source['object_id']))
    native_path='' if obj is None else _corex_path(obj)
    if obj is None or (native_path != source['object_path'] and not native_path.endswith('/'+source['object_path'])):
        raise ValueError('mechanical.selector_missing: source object is missing or changed: '+source['object_path'])
    api_type=_corex_type(obj)
    if '.Results.' in api_type or api_type.endswith('.Solution'):
        raise ValueError('mechanical.table_unsupported: result/probe sources require the T08 adapters: '+api_type)
    if api_type.endswith('Worksheet'):
        raise ValueError('mechanical.table_unsupported: worksheet sources require the T08 adapters: '+api_type)
    candidates=_corex_fields(obj)
    if source['kind']=='property':
        candidates=[value for value in candidates if value['property_key']==source['property_key']]
        if not candidates:
            raise ValueError('mechanical.table_unsupported: property has no supported Field definition: '+source['property_key'])
    elif _corex_type(obj).endswith('.BoltPretension'):
        candidates.append(_corex_bolt_states(obj,objects))
    for candidate in candidates:candidate['object_path']=source['object_path']
    table_selector=_corex_data['table_selector']
    table_text=_corex_data['table']
    if table_selector is not None:
        candidates=[value for value in candidates if value['table_key']==table_selector['native_id'] and value['object_path']==table_selector['object_path']]
    elif table_text:
        candidates=[value for value in candidates if table_text in (value['table_key'],value['property_key'],value['property_caption'],value['component'])]
    component=_corex_data['component']
    if component!='all':
        candidates=[value for value in candidates if component in (value['component'],value['property_key'],value['property_caption'])]
        if not candidates:
            raise ValueError('mechanical.selector_missing: component is unavailable: '+component)
    if not candidates:
        raise ValueError('mechanical.selector_missing: requested definition table is unavailable for '+source['object_path'])
    if len(candidates) != 1:
        names=[value['component'] for value in candidates]
        raise ValueError('mechanical.selector_ambiguous: choose Table / property or Component from '+str(names))
    selected.append(candidates[0])
_corex_json_payload=json.dumps({'schema_version':1,'records':selected},ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
with open(_corex_data['native_output_path'],'wb') as _corex_stream:
    _corex_stream.write(_corex_json_payload)
import hashlib
_corex_receipt=json.dumps({'byte_length':len(_corex_json_payload),'sha256':hashlib.sha256(_corex_json_payload).hexdigest()},separators=(',',':'))
_corex_receipt
'''


def _text(value: Any, label: str, *, empty: bool = True) -> str:
    if type(value) is not str or (not empty and not value):
        raise TypeError(f"{label} must be text")
    if len(value.encode("utf-8")) > 1024 * 1024:
        raise ValueError(f"{label} is too large")
    return value


def _sample(value: Any) -> Any:
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise TypeError("Mechanical definition samples must be finite scalar values or null")


def _heading(name: str, unit: str, *, formula_samples: bool = False) -> str:
    label = name or "Value"
    if formula_samples:
        label += " API samples"
    return f"{label} [{unit}]" if unit else label


def _definition_row(
    *,
    table_index: int,
    column_index: int,
    column_key: str,
    column_label: str,
    unit: str = "",
    quantity_name: str = "",
    definition_kind: str,
    formula: str = "",
    object_path: str,
    property_key: str,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "table_index": table_index,
        "column_index": column_index,
        "column_key": column_key,
        "column_label": column_label,
        "unit": unit,
        "quantity_name": quantity_name,
        "definition_kind": definition_kind,
        "formula": formula,
        "object_path": object_path,
        "property_key": property_key,
        "result_set": None,
        "location": "",
        "coordinate_system": "",
        "notes": notes,
    }


def _variable(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "name", "role", "definition_type", "formula", "unit", "quantity_name", "values"
    }:
        raise TypeError("Mechanical Variable payload schema is invalid")
    result = {key: _text(value[key], f"Variable {key}") for key in (
        "name", "role", "definition_type", "formula", "unit", "quantity_name"
    )}
    if result["role"] not in {"independent", "dependent"}:
        raise ValueError("Mechanical Variable role is invalid")
    if result["definition_type"] not in {"Discrete", "Formula", "Free"}:
        raise ValueError("Mechanical Variable definition type is unsupported")
    if type(value["values"]) is not list:
        raise TypeError("Mechanical Variable values must be a list")
    result["values"] = [_sample(item) for item in value["values"]]
    return result


def _frame_value(frame: Any, *, table_key: str) -> TableValue:
    from ea_node_editor.runtime_contracts import scientific_values

    size = scientific_values._native_scientific_size(frame)
    if size is None:
        raise TypeError("Mechanical definition table must be a pandas DataFrame")
    if size > SCIENTIFIC_VALUE_MAX_BYTES:
        raise ValueError(
            f"mechanical.capacity_exceeded: table {table_key!r} is {size} decoded bytes; "
            "narrow Source, Table / property, or Component"
        )
    value = snapshot_scientific_value(frame)
    if type(value) is not TableValue:
        raise TypeError("Mechanical definition extraction did not produce a TableValue")
    return value


def build_definition_tables(payload: Any) -> dict[str, Any]:
    """Validate detached native records and create full-fidelity immutable values."""
    if not isinstance(payload, Mapping) or set(payload) != {"schema_version", "records"}:
        raise TypeError("Mechanical definition result schema is invalid")
    if payload["schema_version"] != 1 or type(payload["records"]) is not list:
        raise ValueError("Unsupported Mechanical definition result schema")
    import pandas as pd

    tables: list[TableValue] = []
    definitions: list[dict[str, Any]] = []
    for table_index, raw in enumerate(payload["records"]):
        if not isinstance(raw, Mapping):
            raise TypeError("Mechanical definition record must be a mapping")
        kind = raw.get("kind")
        common = {"kind", "table_key", "object_path", "property_key", "property_caption", "component"}
        expected = common | ({"variables"} if kind == "field" else {"states"} if kind == "bolt_states" else set())
        if not expected or set(raw) != expected:
            raise TypeError("Mechanical definition record schema is invalid")
        table_key, object_path, property_key = (
            _text(raw[name], f"definition {name}", empty=False)
            for name in ("table_key", "object_path", "property_key")
        )
        _text(raw["property_caption"], "definition property_caption")
        _text(raw["component"], "definition component", empty=False)
        columns: list[tuple[str, list[Any]]] = []
        if kind == "field":
            if type(raw["variables"]) is not list or not raw["variables"]:
                raise ValueError("Mechanical Field has no variables")
            variables = [_variable(item) for item in raw["variables"]]
            visible = [item for item in variables if item["role"] == "dependent" or item["values"]]
            populated_lengths = {len(item["values"]) for item in visible if item["values"]}
            if len(populated_lengths) > 1:
                raise ValueError(
                    f"mechanical.table_unsupported: table {table_key!r} has inconsistent "
                    f"populated column lengths {sorted(populated_lengths)}; no rows were padded"
                )
            row_count = next(iter(populated_lengths), 1)
            for column_index, variable in enumerate(visible):
                samples = list(variable["values"])
                definition_type = variable["definition_type"]
                if not samples:
                    if definition_type not in {"Free", "Formula"}:
                        raise ValueError(
                            f"mechanical.table_unsupported: table {table_key!r} has an empty "
                            f"{definition_type} dependent column"
                        )
                    samples = [None] * row_count
                definition_kind = (
                    "free" if definition_type == "Free" else
                    "formula" if definition_type == "Formula" else
                    "tabular" if len(variable["values"]) > 1 else "constant"
                )
                formula_samples = definition_type == "Formula" and bool(variable["values"])
                label = _heading(variable["name"], variable["unit"], formula_samples=formula_samples)
                columns.append((label, samples))
                notes = "independent variable" if variable["role"] == "independent" else ""
                if formula_samples:
                    notes = "; ".join(filter(None, (notes, "API samples; formula retained separately")))
                definitions.append(_definition_row(
                    table_index=table_index, column_index=column_index,
                    column_key=variable["name"], column_label=label,
                    unit=variable["unit"], quantity_name=variable["quantity_name"],
                    definition_kind=definition_kind, formula=variable["formula"],
                    object_path=object_path, property_key=property_key, notes=notes,
                ))
        else:
            if type(raw["states"]) is not list or not raw["states"]:
                raise ValueError("Bolt pretension has no step states")
            steps, states = [], []
            for item in raw["states"]:
                if not isinstance(item, Mapping) or set(item) != {"step", "state"}:
                    raise TypeError("Bolt pretension state schema is invalid")
                if type(item["step"]) is not int or item["step"] <= 0:
                    raise ValueError("Bolt pretension step must be a positive integer")
                steps.append(item["step"])
                states.append(_text(item["state"], "Bolt pretension state", empty=False))
            columns = [("Step", steps), ("State", states)]
            definitions.extend((
                _definition_row(
                    table_index=table_index, column_index=0, column_key="step",
                    column_label="Step", definition_kind="step_index",
                    object_path=object_path, property_key=property_key,
                ),
                _definition_row(
                    table_index=table_index, column_index=1, column_key="state",
                    column_label="State", definition_kind="bolt_pretension_state",
                    object_path=object_path, property_key=property_key,
                ),
            ))
        frame = pd.DataFrame({index: values for index, (_label, values) in enumerate(columns)})
        frame.columns = [label for label, _values in columns]
        tables.append(_frame_value(frame, table_key=table_key))
    definitions_frame = pd.DataFrame(definitions, columns=DEFINITIONS_COLUMNS)
    for column in ("table_index", "column_index", "result_set"):
        definitions_frame[column] = definitions_frame[column].astype("Int64")
    from ea_node_editor.runtime_contracts import scientific_values

    definitions_size = scientific_values._native_scientific_size(definitions_frame)
    if definitions_size is None:
        raise TypeError("Mechanical Definitions must be a pandas DataFrame")
    if definitions_size > SCIENTIFIC_VALUE_MAX_BYTES:
        raise ValueError(
            f"mechanical.capacity_exceeded: table 'Definitions' is {definitions_size} decoded bytes; "
            "narrow Source, Table / property, or Component"
        )
    definitions_value = definitions_table(definitions)
    total = sum(value.nbytes for value in (*tables, definitions_value))
    if total > SCIENTIFIC_OPERATION_MAX_BYTES:
        raise ValueError(
            f"mechanical.capacity_exceeded: definition output is {total} decoded bytes; "
            "narrow Source, Table / property, or Component"
        )
    result = {"tables": tables, "definitions": definitions_value}
    check_scientific_budget(result)
    return result


__all__ = [
    "DEFINITION_ENCODED_MAX_BYTES",
    "DEFINITION_SCRIPT_BODY",
    "build_definition_tables",
]
