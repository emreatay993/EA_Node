# Purpose: Extract saved and current Mechanical camera snapshots without retaining native objects.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_camera_views.py

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ea_node_editor.addons.mechanical.contracts import (
    camera_view_value,
    encode_selector,
)
from ea_node_editor.runtime_contracts import TableValue
from ea_node_editor.runtime_contracts.scientific_values import snapshot_scientific_value

CAMERA_DETAILS_COLUMNS = (
    "name",
    "kind",
    "saved_index",
    "focal_x",
    "focal_y",
    "focal_z",
    "view_x",
    "view_y",
    "view_z",
    "up_x",
    "up_y",
    "up_z",
    "scene_width",
    "scene_height",
    "length_unit",
    "availability_notes",
    "run_id",
    "session_id",
    "document_id",
    "source_key",
    "system_key",
    "model_revision",
    "selector_code",
)

_IDENTITY_FIELDS = (
    "run_id",
    "session_id",
    "document_id",
    "source_key",
    "system_key",
    "model_revision",
)
_RAW_CAMERA_FIELDS = frozenset(
    {
        "kind",
        "name",
        "index",
        "focal_point",
        "view_vector",
        "up_vector",
        "scene_width",
        "scene_height",
        "length_unit",
        "availability_notes",
    }
)


# Runs inside Mechanical's scripting engine. All native state is restored and
# verified before the detached snapshots cross the server boundary.
CAMERA_SCRIPT_BODY = r'''
import json,math,xml.etree.ElementTree as ET

def _corex_note(exc):
    return type(exc).__name__+': '+str(exc)

def _corex_finite(value):
    return not math.isnan(value) and not math.isinf(value)

def _corex_vector(value):
    try:values=list(value)
    except Exception:
        values=[getattr(value,name) for name in ('X','Y','Z')]
    if len(values)!=3:raise ValueError('expected three components')
    result=[float(item) for item in values]
    if not all(_corex_finite(item) for item in result):raise ValueError('components must be finite')
    return result

def _corex_quantity(value):
    number=float(value.Value)
    if not _corex_finite(number):raise ValueError('quantity must be finite')
    unit=str(value.Unit)
    if not unit:raise ValueError('quantity unit is unavailable')
    return number,unit

def _corex_camera():
    camera=Graphics.Camera;notes={};units={}
    try:
        focal=camera.FocalPoint
        focal_point=_corex_vector(focal.Location)
        units['focal_point']=str(focal.Unit)
        if not units['focal_point']:
            focal_point=None;notes['focal_point']='focal-point unit is unavailable'
    except Exception as exc:
        focal_point=None;notes['focal_point']=_corex_note(exc)
    values={}
    for field,attribute in (('view_vector','ViewVector'),('up_vector','UpVector')):
        try:values[field]=_corex_vector(getattr(camera,attribute))
        except Exception as exc:values[field]=None;notes[field]=_corex_note(exc)
    quantities={}
    for field,attribute in (('scene_width','SceneWidth'),('scene_height','SceneHeight')):
        try:
            quantity=getattr(camera,attribute);number,unit=_corex_quantity(quantity)
            quantities[field]=(number,unit,quantity);units[field]=unit
        except Exception as exc:
            quantities[field]=(None,'',None);notes[field]=_corex_note(exc)
    available_units=[unit for unit in units.values() if unit]
    length_unit=available_units[0] if available_units else None
    if length_unit is None:notes['length_unit']='camera length unit is unavailable'
    for field in ('scene_width','scene_height'):
        number,unit,quantity=quantities[field]
        if number is not None and length_unit is not None and unit!=length_unit:
            try:number,_unit=_corex_quantity(quantity.ConvertUnit(length_unit))
            except Exception as exc:number=None;notes[field]='unit conversion failed: '+_corex_note(exc)
        values[field]=number
    return {
        'focal_point':focal_point,'view_vector':values['view_vector'],'up_vector':values['up_vector'],
        'scene_width':values['scene_width'],'scene_height':values['scene_height'],
        'length_unit':length_unit,'availability_notes':notes,
    }

def _corex_presentation_state():
    try:
        camera=Graphics.Camera
        return {
            'active_ids':[int(value.ObjectId) for value in list(Tree.ActiveObjects)],
            'camera':[str(camera.FocalPoint),str(camera.ViewVector),str(camera.UpVector),str(camera.SceneWidth),str(camera.SceneHeight)],
        }
    except Exception as exc:
        raise ValueError('mechanical.capability_unproved: exact camera restoration state is unavailable: '+_corex_note(exc))

def _corex_local_name(tag):
    return str(tag).split('}')[-1]

include=_corex_data['include'];records=[];current=_corex_camera()
if include in ('saved','saved_and_current'):
    manager=Graphics.ModelViewManager;count=int(manager.NumberOfViews)
    manager.ExportModelViews(_corex_data['export_path'])
    stream=open(_corex_data['export_path'],'rb')
    try:root=ET.fromstring(stream.read())
    finally:stream.close()
    if _corex_local_name(root.tag)!='ModelViewsManager':
        raise ValueError('mechanical.camera_schema_invalid: exported saved-view root is unsupported')
    saved=[]
    for original_index,child in enumerate(list(root)):
        if _corex_local_name(child.tag)!='ModelView':
            raise ValueError('mechanical.camera_schema_invalid: exported saved-view child is unsupported')
        if 'Name' not in child.attrib or not str(child.attrib['Name']):
            raise ValueError('mechanical.camera_schema_invalid: saved ModelView requires Name')
        saved.append({'index':original_index,'name':str(child.attrib['Name'])})
    if len(saved)!=count or [item['index'] for item in saved]!=list(range(count)):
        raise ValueError('mechanical.camera_schema_invalid: exported saved-view count/index does not match NumberOfViews')
    if saved:
        before=_corex_presentation_state();restore_name=_corex_data['restore_name']
        if restore_name in [item['name'] for item in saved]:
            raise ValueError('mechanical.camera_schema_invalid: restore view name collides with a saved view')
        created=False;operation_error=None;restore_errors=[]
        try:
            manager.CreateView(restore_name);created=True
            if int(manager.NumberOfViews)!=count+1:
                raise ValueError('restore view was not created exactly once')
            for item in saved:
                manager.ApplyModelView(item['index'])
                records.append(dict({'kind':'saved','name':item['name'],'index':item['index']},**_corex_camera()))
        except BaseException as exc:
            operation_error=exc
        finally:
            if created:
                try:manager.ApplyModelView(restore_name)
                except Exception as exc:restore_errors.append('camera apply: '+_corex_note(exc))
                try:
                    Tree.Activate([DataModel.GetObjectById(object_id) for object_id in before['active_ids']])
                except Exception as exc:restore_errors.append('active objects: '+_corex_note(exc))
                try:manager.DeleteView(restore_name)
                except Exception as exc:restore_errors.append('restore view delete: '+_corex_note(exc))
                try:
                    if int(manager.NumberOfViews)!=count:restore_errors.append('saved-view count changed')
                    if _corex_presentation_state()!=before:restore_errors.append('camera or active objects changed')
                except Exception as exc:restore_errors.append('verification: '+_corex_note(exc))
        if restore_errors:
            raise ValueError('mechanical.restore_failed: camera state restoration failed: '+'; '.join(restore_errors))
        if operation_error is not None:raise operation_error
if include in ('current','saved_and_current'):
    records.append(dict({'kind':'current','name':'Current view','index':None},**current))
_corex_receipt=json.dumps({'views':records},ensure_ascii=False,separators=(',',':'))
_corex_receipt
'''


def build_camera_views(
    payload: object,
    *,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"views"}:
        raise ValueError("Mechanical camera extraction payload is invalid")
    if set(identity) != set(_IDENTITY_FIELDS):
        raise ValueError("Mechanical camera identity is invalid")
    raw_views = payload["views"]
    if type(raw_views) is not list:
        raise TypeError("Mechanical camera views must be a list")
    views, rows = [], []
    for raw in raw_views:
        if not isinstance(raw, Mapping) or set(raw) != _RAW_CAMERA_FIELDS:
            raise ValueError("Mechanical camera record schema is invalid")
        item = {**identity, **dict(raw)}
        item["selector_code"] = encode_selector(
            "camera_view",
            document_id=str(identity["document_id"]),
            system_key=str(identity["system_key"]),
            object_path="",
            native_id=raw["index"] if raw["kind"] == "saved" else "current",
        )
        value = camera_view_value(item)
        views.append(value)
        focal = raw["focal_point"] or (None, None, None)
        view = raw["view_vector"] or (None, None, None)
        up = raw["up_vector"] or (None, None, None)
        rows.append(
            {
                "name": raw["name"],
                "kind": raw["kind"],
                "saved_index": raw["index"],
                "focal_x": focal[0],
                "focal_y": focal[1],
                "focal_z": focal[2],
                "view_x": view[0],
                "view_y": view[1],
                "view_z": view[2],
                "up_x": up[0],
                "up_y": up[1],
                "up_z": up[2],
                "scene_width": raw["scene_width"],
                "scene_height": raw["scene_height"],
                "length_unit": raw["length_unit"] or "",
                "availability_notes": json.dumps(
                    raw["availability_notes"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                **identity,
                "selector_code": item["selector_code"],
            }
        )
    import pandas as pd

    frame = pd.DataFrame(rows, columns=CAMERA_DETAILS_COLUMNS)
    frame["saved_index"] = frame["saved_index"].astype("Int64")
    frame["model_revision"] = frame["model_revision"].astype("Int64")
    for column in (
        "focal_x",
        "focal_y",
        "focal_z",
        "view_x",
        "view_y",
        "view_z",
        "up_x",
        "up_y",
        "up_z",
        "scene_width",
        "scene_height",
    ):
        frame[column] = frame[column].astype("Float64")
    details = snapshot_scientific_value(frame)
    if type(details) is not TableValue:
        raise TypeError("Mechanical camera details did not produce TableValue")
    return {
        "views": views,
        "names": [str(raw["name"]) for raw in raw_views],
        "details": details,
    }


__all__ = [
    "CAMERA_DETAILS_COLUMNS",
    "CAMERA_SCRIPT_BODY",
    "build_camera_views",
]
