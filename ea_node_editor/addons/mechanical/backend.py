# Purpose: Open native Mechanical models and execute allowlisted Open/Search/table operations.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_owner_protocol.py, tests/mechanical_catalogue/test_search_tree.py

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.addons.mechanical.inspection import collect_catalogue_rows, search_tree
from ea_node_editor.addons.mechanical.tables import (
    DEFINITION_ENCODED_MAX_BYTES,
    DEFINITION_SCRIPT_BODY,
    build_definition_tables,
)

LIFECYCLE_OPERATIONS = frozenset(
    {"health", "open", "search", "definition_tables", "close"}
)


def _data_script(data: Mapping[str, Any], body: str) -> str:
    encoded = base64.b64encode(json.dumps(dict(data)).encode()).decode("ascii")
    return (
        "import base64,json\n_corex_data=json.loads(base64.b64decode("
        + repr(encoded)
        + ").decode('utf-8'))\n"
        + body
    )


class MechanicalOwnerBackend:
    def __init__(self) -> None:
        self.app = self.mechanical = self.workbench = None
        self.tree = self.model = self.data_model = None
        self.work_root: Path | None = None
        self.system_name = ""
        self.interactive_model = False
        self.native_identities: list[dict[str, int]] = []

    def _launch_workbench(self, *, release: int, mode: str, workdir: Path, timeout_sec: float) -> Any:
        from ea_node_editor.addons.mechanical.workbench import launch_workbench_owner
        client = launch_workbench_owner(
            release_code=release,
            show_gui=mode == "interactive",
            client_workdir=str(workdir),
            server_workdir=str(workdir),
            timeout_sec=timeout_sec,
        )
        self.native_identities.append(dict(client.identity))
        return client

    @staticmethod
    def _require_receipt(value: Any, operation: str) -> None:
        if value is not True:
            raise RuntimeError(f"Workbench {operation} failed; inspect its native diagnostic log")

    def execute(self, operation: str, args: Mapping[str, Any]) -> dict[str, Any]:
        if operation not in LIFECYCLE_OPERATIONS:
            raise ValueError(f"Unsupported Mechanical owner operation: {operation!r}")
        if operation in {"health", "close"}:
            if args:
                raise ValueError(f"Mechanical owner operation {operation!r} does not accept arguments")
            if operation == "close":
                self.close()
            return {"status": "ready" if operation == "health" else "closed"}
        if operation == "open":
            return self.open(args)
        if operation == "search":
            return self.search(args)
        return self.definition_tables(args)

    def definition_tables(self, args: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "sources", "family", "table", "table_selector", "component", "units",
            "native_output_path",
        }
        if set(args) != required or (self.app is None and self.mechanical is None):
            raise ValueError("Mechanical definition-table arguments or session state are invalid")
        if self.work_root is None:
            raise ValueError("Mechanical definition-table working root is unavailable")
        output = Path(str(args["native_output_path"]))
        if (
            output.parent.resolve() != self.work_root
            or not output.name.startswith("native-definitions-")
            or output.suffix != ".json"
            or output.exists()
        ):
            raise ValueError("Mechanical definition-table output path is not run-owned")
        script = _data_script(args, DEFINITION_SCRIPT_BODY)
        try:
            raw_receipt = (
                self.app.execute_script(script)
                if self.app is not None
                else self.mechanical.run_python_script(script)
            )
            receipt = json.loads(raw_receipt) if type(raw_receipt) is str else None
            if (
                not isinstance(receipt, dict)
                or set(receipt) != {"byte_length", "sha256"}
                or type(receipt["byte_length"]) is not int
                or not 0 <= receipt["byte_length"] <= DEFINITION_ENCODED_MAX_BYTES
                or type(receipt["sha256"]) is not str
                or len(receipt["sha256"]) != 64
                or not output.is_file()
                or output.is_symlink()
            ):
                raise RuntimeError("Mechanical definition extraction returned an invalid receipt")
            stat = output.lstat()
            if (
                bool(getattr(stat, "st_file_attributes", 0) & 0x400)
                or stat.st_size != receipt["byte_length"]
            ):
                raise RuntimeError("Mechanical definition extraction file is invalid")
            data = output.read_bytes()
            if hashlib.sha256(data).hexdigest() != receipt["sha256"]:
                raise RuntimeError("Mechanical definition extraction file hash is invalid")
            return {
                "status": "extracted",
                "definition_tables": build_definition_tables(json.loads(data)),
            }
        finally:
            output.unlink(missing_ok=True)

    def search(self, args: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "filter", "query", "match", "case_sensitive", "include_hidden_properties",
            "invert", "identity", "typed_selector",
        }
        if set(args) != required or self.tree is None or self.model is None:
            raise ValueError("Mechanical search arguments or session state are invalid")
        tree = (
            _RemoteTree(self.mechanical, include_hidden_properties=bool(args["include_hidden_properties"]))
            if isinstance(self.tree, _RemoteTree)
            else self.tree
        )
        return {
            "status": "searched",
            "search": search_tree(
                tree=tree,
                model=self.model,
                data_model=self.data_model,
                identity=dict(args["identity"]),
                filter_code=str(args["filter"]),
                query=str(args["query"]),
                match_mode=str(args["match"]),
                case_sensitive=bool(args["case_sensitive"]),
                include_hidden_properties=bool(args["include_hidden_properties"]),
                invert=bool(args["invert"]),
                typed_selector=args["typed_selector"],
            ),
        }

    def open(self, args: Mapping[str, Any]) -> dict[str, Any]:
        required = {"source_path", "work_path", "mode", "release_code", "system", "catalogue_identity", "view_export_path", "timeout_sec"}
        if set(args) != required:
            raise ValueError("Mechanical open arguments are invalid")
        source = Path(str(args["source_path"])).resolve(strict=True)
        work = Path(str(args["work_path"])).resolve()
        if work.exists():
            raise ValueError("Mechanical working destination already exists")
        self.work_root = work.parent.resolve(strict=True)
        suffix = source.suffix.casefold()
        if suffix in {".wbpj", ".wbpz"}:
            systems, tree, graphics, selected = self._open_workbench(
                source, work, int(args["release_code"]), str(args["mode"]), str(args["system"]), float(args["timeout_sec"])
            )
        elif suffix in {".mechdb", ".mechdat", ".mechpz"}:
            systems, tree, graphics, selected = self._open_standalone(
                source, work, int(args["release_code"]), str(args["mode"])
            )
        else:
            raise ValueError("Unsupported Mechanical source extension")
        identity = dict(args["catalogue_identity"])
        identity["system_key"] = selected
        identity["view_export_path"] = str(args["view_export_path"])
        if suffix in {".wbpj", ".wbpz"} and not selected:
            rows = collect_catalogue_rows(
                tree=None, graphics=None, identity=identity, systems=systems,
                status="system_required", message="Select a Mechanical Model/system before opening.",
            )
            self.close()
            return {"status": "system_required", "rows": rows, "systems": systems}
        return {
            "status": "opened",
            "rows": collect_catalogue_rows(
                tree=tree, graphics=graphics, identity=identity, systems=systems,
                model=self.model, data_model=self.data_model,
            ),
            "systems": systems,
            "system_key": selected,
        }

    def _open_standalone(self, source: Path, work: Path, release: int, mode: str):
        if mode == "interactive":
            from ansys.mechanical.core import launch_mechanical
            self.mechanical = launch_mechanical(version=release, batch=False, cleanup_on_exit=True)
            if release > 261:
                capability = json.loads(
                    self.mechanical.run_python_script(
                        "import json\np=DataModel.Project\n"
                        "json.dumps(bool(Tree is not None and Graphics is not None and "
                        "all(callable(getattr(p,n,None)) for n in ('Open','SaveAs','Unarchive'))))"
                    )
                )
                if capability is not True:
                    raise RuntimeError(
                        "mechanical.capability_unproved: later interactive standalone release lacks Project/Tree/Graphics operations"
                    )
            self.mechanical.run_python_script(_data_script(
                {"source": str(source), "work": str(work), "archive": source.suffix.casefold() == ".mechpz"},
                "p=_corex_data\nDataModel.Project.Unarchive(p['source'],p['work'],False) if p['archive'] else (DataModel.Project.Open(p['source']),DataModel.Project.SaveAs(p['work'],False))\nstr(True)",
            ))
            self.tree = _RemoteTree(self.mechanical)
            self.model = _RemoteModel(self.mechanical)
            return [], self.tree, _RemoteGraphics(self.mechanical), "standalone"
        from ansys.mechanical.core import App, global_variables
        self.app = App(version=release)
        values = global_variables(self.app)
        if release > 261:
            project = values.get("DataModel").Project if values.get("DataModel") is not None else None
            if (
                project is None
                or not callable(getattr(self.app, "open", None))
                or not callable(getattr(self.app, "save_as", None))
                or not callable(getattr(project, "Unarchive", None))
                or values.get("Tree") is None
                or values.get("Graphics") is None
            ):
                raise RuntimeError(
                    "mechanical.capability_unproved: later embedded standalone release lacks App Open/SaveAs, Project.Unarchive, Tree, or Graphics"
                )
        if source.suffix.casefold() == ".mechpz":
            values["DataModel"].Project.Unarchive(str(source), str(work), False)
        else:
            self.app.open(str(source))
            self.app.save_as(str(work), overwrite=False)
        self.tree, self.model, self.data_model = values["Tree"], values["Model"], values["DataModel"]
        return [], self.tree, values["Graphics"], "standalone"

    def _open_workbench(self, source: Path, work: Path, release: int, mode: str, requested: str, timeout_sec: float):
        self.workbench = self._launch_workbench(
            release=release,
            mode="background",
            workdir=work.parent,
            timeout_sec=timeout_sec,
        )
        if release > 261:
            capability = self.workbench.run_script_string(
                "import json\nwb_script_result=json.dumps(all(name in globals() and callable(globals()[name]) for name in ('Open','Save','Archive','Unarchive','GetAllSystems','GetSystem')))"
            )
            if capability is not True or not all(
                callable(getattr(self.workbench, name, None))
                for name in ("start_mechanical_server", "stop_mechanical_server")
            ):
                raise RuntimeError(
                    "mechanical.capability_unproved: later Workbench release lacks required project/server operations"
                )
        source_choices = None
        if source.suffix.casefold() == ".wbpz":
            body = "Unarchive(ArchivePath=_corex_data['source'],ProjectPath=_corex_data['work'],Overwrite=False)\nSave()\n"
        else:
            archive = work.with_suffix(".wbpz")
            self._require_receipt(self.workbench.run_script_string(_data_script(
                {"source": str(source)},
                "Open(FilePath=_corex_data['source'])\nwb_script_result=json.dumps(True)",
            )), "Open")
            staged = work.with_name(work.stem + "-staged.wbpj")
            self._require_receipt(self.workbench.run_script_string(_data_script(
                {"staged": str(staged)},
                "Save(FilePath=_corex_data['staged'],Overwrite=False)\nwb_script_result=json.dumps(True)",
            )), "working-copy Save")
            self._require_receipt(self.workbench.run_script_string(_data_script(
                {"archive": str(archive)},
                "Archive(FilePath=_corex_data['archive'],IncludeSkippedFiles=True,IncludeUserFiles=True,IncludeExternalImportedFiles=True,FailIfMissingFiles=True)\nwb_script_result=json.dumps(True)",
            )), "Archive")
            source_choices = self._workbench_systems()
            self.workbench.exit()
            self.workbench = None
            if not archive.is_file():
                raise RuntimeError("Workbench did not publish the native working archive")
            self.workbench = self._launch_workbench(
                release=release, mode="background", workdir=work.parent, timeout_sec=timeout_sec
            )
            body = "Unarchive(ArchivePath=_corex_data['archive'],ProjectPath=_corex_data['work'],Overwrite=False)\nSave()\n"
        self._require_receipt(self.workbench.run_script_string(_data_script(
            {"source": str(source), "work": str(work), "archive": str(work.with_suffix('.wbpz')), "archive_name": "corex_working.wbpz"},
            body + "wb_script_result=json.dumps(True)",
        )), "Unarchive")
        target_choices = self._workbench_systems()
        public_choices = source_choices or target_choices
        selected = requested.strip()
        public_match = select_model_system(public_choices, selected)
        if public_match is None:
            return public_choices, None, None, ""
        target_match = select_model_system(target_choices, public_match["key"])
        if target_match is None:
            raise RuntimeError("Unarchived Workbench Model identity does not match its source")
        self.system_name = target_match["system_keys"][0]
        if mode == "interactive":
            capability = self.workbench.run_script_string(
                _data_script(
                    {"system": self.system_name},
                    "c=GetSystem(Name=_corex_data['system']).GetContainer(ComponentName='Model')\n"
                    "wb_script_result=json.dumps(bool(callable(getattr(c,'Edit',None)) and callable(getattr(c,'Exit',None))))",
                )
            )
            if capability is not True:
                raise RuntimeError(
                    "mechanical.capability_unproved: selected Workbench Model lacks Edit/Exit"
                )
            self._require_receipt(
                self.workbench.run_script_string(
                    _data_script(
                        {"system": self.system_name},
                        "s=GetSystem(Name=_corex_data['system'])\n"
                        "c=s.GetContainer(ComponentName='Model')\n"
                        "c.Edit(Hidden=False,Interactive=True)\n"
                        "wb_script_result=json.dumps(True)",
                    )
                ),
                "Model.Edit",
            )
            self.interactive_model = True
        from ansys.mechanical.core import connect_to_mechanical
        port = self.workbench.start_mechanical_server(system_name=self.system_name)
        self.mechanical = connect_to_mechanical(ip="127.0.0.1", port=port)
        self.tree = _RemoteTree(self.mechanical)
        self.model = _RemoteModel(self.mechanical)
        return public_choices, self.tree, _RemoteGraphics(self.mechanical), public_match["key"]

    def _workbench_systems(self) -> list[dict[str, Any]]:
        raw = self.workbench.run_script_string(
            "import json\nwb_script_result=json.dumps([{'key':str(s.Name),'label':str(s.DisplayText),'model_key':str(s.GetContainer(ComponentName='Model').Name)} for s in GetAllSystems() if s.GetContainer(ComponentName='Model') is not None])"
        )
        systems = json.loads(raw) if isinstance(raw, str) else raw
        return deduplicate_model_systems(systems)

    def close(self) -> None:
        errors: list[Exception] = []
        if self.app is not None:
            try:
                self.app.close()
                self.app = None
            except Exception as exc:
                errors.append(exc)
        if self.workbench is not None:
            if self.system_name:
                try:
                    self.workbench.stop_mechanical_server(system_name=self.system_name)
                except Exception as exc:
                    errors.append(exc)
            if self.interactive_model:
                try:
                    self._require_receipt(
                        self.workbench.run_script_string(
                            _data_script(
                                {"system": self.system_name},
                                "s=GetSystem(Name=_corex_data['system'])\n"
                                "s.GetContainer(ComponentName='Model').Exit(SaveDatabase=False)\n"
                                "wb_script_result=json.dumps(True)",
                            )
                        ),
                        "Model.Exit",
                    )
                    self.interactive_model = False
                except Exception as exc:
                    errors.append(exc)
            try:
                self.workbench.exit()
                self.workbench = self.mechanical = None
            except Exception as exc:
                errors.append(exc)
        if errors:
            # Failed clients remain referenced so the child's final cleanup retries once.
            raise RuntimeError("Mechanical native cleanup failed: " + "; ".join(str(exc) for exc in errors))
        self.work_root = None


def deduplicate_model_systems(systems: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for item in systems:
        model_key = str(item["model_key"])
        record = unique.setdefault(
            model_key,
            {"key": str(item["key"]), "label": str(item["label"]), "model_key": model_key, "system_keys": []},
        )
        record["system_keys"].append(str(item["key"]))
    return list(unique.values())


def select_model_system(choices: list[dict[str, Any]], selected: str) -> dict[str, Any] | None:
    if not selected and len(choices) == 1:
        return choices[0]
    if not selected:
        return None
    matches = [item for item in choices if selected in {item["key"], item["model_key"], *item["system_keys"]}]
    if len(matches) != 1:
        raise ValueError(f"Mechanical system selection {selected!r} is unavailable or ambiguous")
    return matches[0]


class _Proxy:
    def __init__(self, **values: Any) -> None:
        self._errors = dict(values.pop("_errors", {}))
        self.__dict__.update(values)
    def __getattr__(self, name: str):
        if name in self._errors:
            raise RuntimeError(self._errors[name])
        raise AttributeError(name)
    def GetType(self):
        if "GetType" in self._errors:
            raise RuntimeError(self._errors["GetType"])
        return _Proxy(FullName=self.api_type)


class _RemoteTree:
    def __init__(self, client: Any, *, include_hidden_properties: bool = False) -> None:
        self.client = client
        self.include_hidden_properties = include_hidden_properties
        self.metadata_errors: list[str] = []
    @property
    def AllObjects(self):
        script = _data_script({"include_hidden": self.include_hidden_properties}, """import json
def field(o,n,text=False):
 try:v=getattr(o,n)
 except AttributeError:return {'present':False,'error':'','value':None}
 except Exception as x:return {'present':True,'error':type(x).__name__,'value':None}
 try:return {'present':True,'error':'','value':str(v) if text else v}
 except Exception as x:return {'present':True,'error':type(x).__name__,'value':None}
rows=[]
tags={};tags_available=True
try:
 for t in list(DataModel.ObjectTags):
  for tagged in list(t.Objects):tags.setdefault(int(tagged.ObjectId),[]).append(str(t.Name))
except:tags_available=False
for o in list(Tree.AllObjects):
 oid=int(o.ObjectId);name=field(o,'Name',True);category=field(o,'DataModelObjectCategory',True)
 try:api_type={'present':True,'error':'','value':str(o.GetType().FullName)}
 except Exception as x:api_type={'present':True,'error':type(x).__name__,'value':None}
 parent=field(o,'Parent');parent_value=parent['value']
 try:parent_id=int(parent_value.ObjectId) if parent_value is not None else None
 except:parent_id=None
 props=[];props_error=''
 try:
   for q in list(o.Properties if _corex_data['include_hidden'] else o.VisibleProperties):
    api_name=field(q,'APIName',True);prop_name=field(q,'Name',True);caption=field(q,'Caption',True);string_value=field(q,'StringValue',True)
    internal=field(q,'InternalValue');internal_error=internal['error'];iv=internal['value'];field_inputs=None;internal_fields=None;is_field=False;output_error=''
    output=None
    if iv is not None:
     inputs_record=field(iv,'Inputs');output_record=field(iv,'Output')
     if inputs_record['present'] or output_record['present']:
      is_field=True;output_error=output_record['error']
      if inputs_record['present'] and not inputs_record['error']:
       try:field_inputs=len(list(inputs_record['value']))
       except:field_inputs=None
      if output_record['present'] and not output_record['error']:
       out=output_record['value'];output={n:field(out,n,n!='DiscreteValueCount') for n in ('DefinitionType','DiscreteValueCount','Formula','Unit','QuantityName')}
     else:
      internal_fields={n:field(iv,n,n in ('Unit','QuantityName')) for n in ('Value','Unit','QuantityName')}
      scalar=internal_fields['Value']
      if scalar['present'] and not scalar['error'] and type(scalar['value']) not in (int,float):scalar['present']=False;scalar['value']=None
    props.append({'APIName':api_name,'Name':prop_name,'Caption':caption,'StringValue':string_value,'internal_error':internal_error,'is_field':is_field,'output_error':output_error,'field_inputs':field_inputs,'output':output,'internal':internal_fields})
 except Exception as x:props_error=type(x).__name__
 table_field=field(o,'TabularData');table=table_field['value'];table_keys=None
 if table_field['present'] and not table_field['error'] and table is not None:
  try:table_keys=[str(k) for k in table.Keys]
  except:table_keys=[]
 bindings={}
 for attr in ('CoordinateSystem','Orientation'):
   binding=field(o,attr)
   if binding['present']:
    if binding['error']:bindings[attr]={'error':binding['error']}
    else:
     cs=binding['value'];bindings[attr]=None if cs is None else {'ObjectId':field(cs,'ObjectId')['value'],'Name':field(cs,'Name',True)['value']}
 scopes={}
 for attr in ('Location','SourceLocation','TargetLocation'):
   scope=field(o,attr)
   if scope['present']:
    if scope['error']:scopes[attr]={'error':scope['error']}
    elif scope['value'] is None:scopes[attr]=None
    else:
     s=scope['value'];scopes[attr]={n:field(s,n,n in ('Name','SelectionType','DataModelObjectCategory')) for n in ('ObjectId','Name','SelectionType','DataModelObjectCategory','TotalSelection')}
     ids=field(s,'Ids')
     if ids['present'] and not ids['error']:
      try:ids['value']=list(ids['value'] or ())
      except Exception as x:ids={'present':True,'error':type(x).__name__,'value':None}
     scopes[attr]['Ids']=ids
 rows.append({'ObjectId':oid,'Name':name,'api_type':api_type,'category':category,'parent_id':parent_id,'props':props,'props_error':props_error,'table_keys':table_keys,'hidden':field(o,'Hidden'),'source':field(o,'ImportableObjectSourceId',True),'state':field(o,'ObjectState',True),'suppressed':field(o,'Suppressed'),'bindings':bindings,'scopes':scopes,'direct_tags':tags.get(oid,[]),'tags_available':tags_available})
json.dumps(rows)""")
        rows = json.loads(self.client.run_python_script(script))
        objects = {}
        for r in rows:
            properties = [_RemoteProperty(**p) for p in r["props"]]
            values = dict(ObjectId=r["ObjectId"], Parent=None, _corex_direct_tags=r["direct_tags"], _corex_tags_available=r["tags_available"])
            errors = {}
            for key, field_name in (("Name", "Name"), ("api_type", "GetType"), ("category", "DataModelObjectCategory")):
                item = r[key]
                if item["error"]: errors[field_name] = item["error"]
                elif item["present"]: values[field_name if field_name != "GetType" else "api_type"] = item["value"]
            property_field = "Properties" if self.include_hidden_properties else "VisibleProperties"
            if r["props_error"]: errors[property_field] = r["props_error"]
            else: values[property_field] = properties
            if not self.include_hidden_properties and not r["props_error"]: values["VisibleProperties"] = properties
            if r["table_keys"] is not None: values["TabularData"] = _Proxy(Keys=r["table_keys"])
            for key, field_name in (("hidden", "Hidden"), ("source", "ImportableObjectSourceId"), ("state", "ObjectState"), ("suppressed", "Suppressed")):
                item = r[key]
                if item["error"]: errors[field_name] = item["error"]
                elif item["present"]: values[field_name] = item["value"]
            for name, binding in r["bindings"].items():
                if isinstance(binding, dict) and "error" in binding:
                    errors[name] = binding["error"]
                    self.metadata_errors.append(f"{r['Name']}: {name}: {binding['error']}")
                else: values[name] = None if binding is None else _Proxy(**binding)
            for name, scope in r["scopes"].items():
                if scope is None:
                    values[name] = None
                elif "error" in scope:
                    errors[name] = scope["error"]
                    self.metadata_errors.append(f"{r['Name']}: {name}: {scope['error']}")
                else:
                    scope_values, scope_errors = {}, {}
                    for field_name, item in scope.items():
                        if item["error"]: scope_errors[field_name] = item["error"]
                        elif item["present"]: scope_values[field_name] = item["value"]
                    if "Ids" in scope_values: scope_values["Ids"] = list(scope_values["Ids"] or ())
                    values[name] = _Proxy(_errors=scope_errors, **scope_values)
            objects[r["ObjectId"]] = _Proxy(_errors=errors, **values)
        for row in rows:
            if row["parent_id"] in objects: objects[row["ObjectId"]].Parent = objects[row["parent_id"]]
        return list(objects.values())


class _RemoteProperty(_Proxy):
    def __init__(self, **values: Any) -> None:
        internal_error = values.pop("internal_error", "")
        is_field = values.pop("is_field", False)
        output_error = values.pop("output_error", "")
        field_inputs = values.pop("field_inputs", None)
        output_fields = values.pop("output", None)
        internal_fields = values.pop("internal", None)
        property_values, property_errors = {}, {}
        for name, item in values.items():
            if item["error"]: property_errors[name] = item["error"]
            elif item["present"]: property_values[name] = item["value"]
        if internal_error:
            property_errors["InternalValue"] = internal_error
        elif is_field:
            internal_errors = {}
            internal_values = {}
            if field_inputs is None:
                internal_errors["Inputs"] = "unavailable"
            else:
                internal_values["Inputs"] = [None] * field_inputs
            if output_error:
                internal_errors["Output"] = output_error
            else:
                output_values, output_errors = {}, {}
                for name, item in (output_fields or {}).items():
                    if item["error"]: output_errors[name] = item["error"]
                    elif item["present"]: output_values[name] = item["value"]
                internal_values["Output"] = _Proxy(
                    _errors=output_errors, **output_values
                )
            property_values["InternalValue"] = _Proxy(
                _errors=internal_errors, **internal_values
            )
        elif field_inputs is None:
            if internal_fields is None:
                property_values["InternalValue"] = None
            else:
                internal_values, internal_errors = {}, {}
                for name, item in internal_fields.items():
                    if item["error"]: internal_errors[name] = item["error"]
                    elif item["present"]: internal_values[name] = item["value"]
                property_values["InternalValue"] = _Proxy(
                    _errors=internal_errors, **internal_values
                )
        super().__init__(_errors=property_errors, **property_values)


class _RemoteModel:
    def __init__(self, client: Any) -> None:
        self.client = client
    def GetActivationStatusForAnalysis(self, object_id: int, analysis_id: int):
        return self.client.run_python_script(_data_script(
            {"object_id": object_id, "analysis_id": analysis_id},
            "str(Model.GetActivationStatusForAnalysis(_corex_data['object_id'],_corex_data['analysis_id']))",
        ))


class _RemoteViewManager:
    def __init__(self, client: Any) -> None: self.client = client
    @property
    def NumberOfViews(self): return int(self.client.run_python_script("str(Graphics.ModelViewManager.NumberOfViews)"))
    def ExportModelViews(self, path: str) -> None:
        self.client.run_python_script(_data_script({"path": path}, "Graphics.ModelViewManager.ExportModelViews(_corex_data['path'])\nstr(True)"))


class _RemoteGraphics:
    def __init__(self, client: Any) -> None: self.ModelViewManager = _RemoteViewManager(client)


__all__ = ["LIFECYCLE_OPERATIONS", "MechanicalOwnerBackend"]
