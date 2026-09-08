# Purpose: Build bounded IronPython-compatible Mechanical script execution payloads.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_scripts.py

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

SCRIPT_ENVIRONMENT_LIMIT = 256
SCRIPT_RECEIPT_TEXT_LIMIT = 1024
SCRIPT_FAILURE_TEXT_LIMIT = 128


SCRIPT_PREFLIGHT_BODY = r'''import json
def _corex_path(item):
    parts=[]
    seen=set()
    while item is not None and id(item) not in seen:
        seen.add(id(item))
        name=str(getattr(item,'Name','')).strip()
        if name: parts.append(name)
        item=getattr(item,'Parent',None)
    parts.reverse()
    return '/'.join(parts)
_corex_all=list(Model.Analyses)
_corex_records=[{'id':int(item.ObjectId),'name':str(item.Name),'path':_corex_path(item)} for item in _corex_all]
if len(_corex_records)>256: raise ValueError('mechanical.capacity_exceeded: Script supports at most 256 analyses')
_corex_selected=[]
for selector in _corex_data['environments']:
    if selector['kind']=='typed':
        matches=[row for row in _corex_records if row['id']==selector['object_id']]
    else:
        matches=[row for row in _corex_records if row['path']==selector['text']]
        if not matches: matches=[row for row in _corex_records if row['name']==selector['text']]
    if len(matches)!=1: raise ValueError('mechanical.selector_ambiguous: Environment is unavailable or ambiguous: '+str(selector))
    if matches[0]['id'] not in _corex_selected: _corex_selected.append(matches[0]['id'])
if not _corex_data['environments']: _corex_selected=[row['id'] for row in _corex_records]
else: _corex_selected=[row['id'] for row in _corex_records if row['id'] in _corex_selected]
_corex_receipt=json.dumps({'analyses':_corex_records,'selected_ids':_corex_selected})
_corex_receipt'''


SCRIPT_EXECUTION_BODY = r'''import json,sys,traceback
try:
    unicode
except ImportError:
    pass
except NameError:
    unicode=str
class _CorexBoundedWriter(object):
    def __init__(self,limit):
        self.limit=limit
        self.parts=[]
        self.length=0
    def write(self,value):
        if not isinstance(value,unicode): value=str(value)
        remaining=self.limit-self.length
        if remaining>0:
            value=value[:remaining]
            self.parts.append(value)
            self.length+=len(value)
    def flush(self):
        pass
    def getvalue(self):
        return u''.join(self.parts)
_corex_all=list(Model.Analyses)
_corex_by_id=dict((int(item.ObjectId),item) for item in _corex_all)
_corex_selected=[]
for object_id in _corex_data['selected_ids']:
    if object_id not in _corex_by_id: raise ValueError('mechanical.selector_missing: selected analysis changed after preflight')
    _corex_selected.append(_corex_by_id[object_id])
_corex_invocations=[None] if _corex_data['scope']=='model_once' else list(_corex_selected)
_corex_receipts=[]
_corex_failed=False
for _corex_analysis in _corex_invocations:
    _corex_scope=globals()
    _corex_names=('ExtAPI','DataModel','Model','analyses','analysis','result')
    _corex_missing=[]
    _corex_previous={}
    for _corex_name in _corex_names:
        if _corex_name in _corex_scope: _corex_previous[_corex_name]=_corex_scope[_corex_name]
        else: _corex_missing.append(_corex_name)
    _corex_stdout=_CorexBoundedWriter(1024)
    _corex_old_stdout=sys.stdout
    _corex_error=''
    _corex_result=''
    try:
        _corex_scope['ExtAPI']=ExtAPI
        _corex_scope['DataModel']=DataModel
        _corex_scope['Model']=Model
        _corex_scope['analyses']=list(_corex_selected)
        _corex_scope['analysis']=_corex_analysis
        _corex_scope.pop('result',None)
        sys.stdout=_corex_stdout
        eval(compile(_corex_data['code'],'<COREX Mechanical Script>','exec'),_corex_scope,_corex_scope)
        if 'result' in _corex_scope and _corex_scope['result'] is not None: _corex_result=str(_corex_scope['result'])
    except Exception:
        _corex_error=traceback.format_exc()
        _corex_failed=True
    finally:
        sys.stdout=_corex_old_stdout
        for _corex_name in _corex_names:
            if _corex_name in _corex_previous: _corex_scope[_corex_name]=_corex_previous[_corex_name]
            elif _corex_name in _corex_scope: del _corex_scope[_corex_name]
    _corex_receipts.append({
        'environment_id':None if _corex_analysis is None else int(_corex_analysis.ObjectId),
        'environment_name':'Model' if _corex_analysis is None else str(_corex_analysis.Name),
        'stdout':_corex_stdout.getvalue(),
        'result':_corex_result[:1024],
        'error':_corex_error[:1024],
        'status':'failed' if _corex_error else 'completed',
    })
    if _corex_error and _corex_data['stop_on_error']: break
_corex_receipt=json.dumps({'success':not _corex_failed,'receipts':_corex_receipts})
_corex_receipt'''


def validate_script_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"success", "receipts"}:
        raise RuntimeError("Mechanical script returned an invalid receipt")
    if type(value["success"]) is not bool or type(value["receipts"]) is not list:
        raise RuntimeError("Mechanical script returned invalid receipt fields")
    receipts: list[dict[str, Any]] = []
    required = {
        "environment_id",
        "environment_name",
        "stdout",
        "result",
        "error",
        "status",
    }
    for receipt in value["receipts"]:
        if not isinstance(receipt, Mapping) or set(receipt) != required:
            raise RuntimeError("Mechanical script receipt schema is invalid")
        normalized = dict(receipt)
        if (
            normalized["environment_id"] is not None
            and (type(normalized["environment_id"]) is not int or normalized["environment_id"] < 0)
        ):
            raise RuntimeError("Mechanical script environment identity is invalid")
        if normalized["status"] not in {"completed", "failed"}:
            raise RuntimeError("Mechanical script receipt status is invalid")
        for field in ("environment_name", "stdout", "result", "error"):
            if type(normalized[field]) is not str or len(normalized[field]) > SCRIPT_RECEIPT_TEXT_LIMIT:
                raise RuntimeError("Mechanical script receipt text is invalid")
        receipts.append(normalized)
    if len(receipts) > SCRIPT_ENVIRONMENT_LIMIT:
        raise RuntimeError("Mechanical script returned too many receipts")
    if value["success"] != all(row["status"] == "completed" for row in receipts):
        raise RuntimeError("Mechanical script success status does not match its receipts")
    return {"success": value["success"], "receipts": receipts}


def receipt_messages(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "status": str(receipt["status"]),
            "message": json.dumps(dict(receipt), ensure_ascii=False, separators=(",", ":")),
        }
        for receipt in receipts
    ]


def compact_failure_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_script_payload(value)
    receipts = [
        {
            **receipt,
            **{
                field: receipt[field][:SCRIPT_FAILURE_TEXT_LIMIT]
                for field in ("environment_name", "stdout", "result", "error")
            },
        }
        for receipt in checked["receipts"]
    ]
    compact = {"success": False, "receipts": receipts}
    if len(json.dumps(compact, ensure_ascii=True, separators=(",", ":")).encode()) >= 1024 * 1024:
        raise RuntimeError("Mechanical script failure diagnostics exceed the owner envelope")
    return compact


__all__ = [
    "SCRIPT_ENVIRONMENT_LIMIT",
    "SCRIPT_EXECUTION_BODY",
    "SCRIPT_FAILURE_TEXT_LIMIT",
    "SCRIPT_PREFLIGHT_BODY",
    "compact_failure_payload",
    "receipt_messages",
    "validate_script_payload",
]
