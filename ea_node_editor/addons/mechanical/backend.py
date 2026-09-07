# Purpose: Open native Mechanical models and execute allowlisted owner operations.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_owner_protocol.py

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.addons.mechanical.inspection import collect_catalogue_rows

LIFECYCLE_OPERATIONS = frozenset({"health", "open", "close"})


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
        return self.open(args)

    def open(self, args: Mapping[str, Any]) -> dict[str, Any]:
        required = {"source_path", "work_path", "mode", "release_code", "system", "catalogue_identity", "view_export_path", "timeout_sec"}
        if set(args) != required:
            raise ValueError("Mechanical open arguments are invalid")
        source = Path(str(args["source_path"])).resolve(strict=True)
        work = Path(str(args["work_path"])).resolve()
        if work.exists():
            raise ValueError("Mechanical working destination already exists")
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
            "rows": collect_catalogue_rows(tree=tree, graphics=graphics, identity=identity, systems=systems),
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
            return [], _RemoteTree(self.mechanical), _RemoteGraphics(self.mechanical), "standalone"
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
        return [], values["Tree"], values["Graphics"], "standalone"

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
        return public_choices, _RemoteTree(self.mechanical), _RemoteGraphics(self.mechanical), public_match["key"]

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
        self.__dict__.update(values)
    def GetType(self):
        return _Proxy(FullName=self.api_type)


class _RemoteTree:
    def __init__(self, client: Any) -> None:
        self.client = client
        self.metadata_errors: list[str] = []
    @property
    def AllObjects(self):
        script = """import json
def g(o,n,d=None):
 try:return getattr(o,n)
 except:return d
rows=[]
for o in list(Tree.AllObjects):
 p=g(o,'Parent'); props=[];props_error=''
 try:
  for q in list(o.VisibleProperties):
   try:v=str(q.StringValue);e=''
   except Exception as x:v='';e=type(x).__name__
   iv=g(q,'InternalValue'); field_inputs=None
   if iv is not None and hasattr(iv,'Inputs') and hasattr(iv,'Output'):
    try:field_inputs=len(list(iv.Inputs))
    except:field_inputs=0
   props.append({'APIName':str(g(q,'APIName','')),'Caption':str(g(q,'Caption','')),'StringValue':v,'error':e,'field_inputs':field_inputs})
 except Exception as x:props_error=type(x).__name__
 table=g(o,'TabularData'); table_keys=None
 if table is not None:
  try:table_keys=[str(k) for k in table.Keys]
  except Exception as x:table_keys=[]
 cs=g(o,'CoordinateSystem'); coordinate=None if cs is None else {'ObjectId':g(cs,'ObjectId'),'Name':str(g(cs,'Name',''))}
 scopes={}
 for attr in ('Location','SourceLocation','TargetLocation'):
  if hasattr(o,attr):
   try:
    s=getattr(o,attr);ids=g(s,'Ids',[]) or [];count=int(ids.Count) if hasattr(ids,'Count') else len(ids);scopes[attr]={'ObjectId':g(s,'ObjectId'),'Name':str(g(s,'Name','')),'ScopeCount':count}
   except Exception as x:scopes[attr]={'error':type(x).__name__}
 rows.append({'ObjectId':int(g(o,'ObjectId',-1)),'Name':str(g(o,'Name','')),'api_type':str(o.GetType().FullName),'parent_id':int(g(p,'ObjectId')) if p is not None and g(p,'ObjectId') is not None else None,'props':props,'props_error':props_error,'table_keys':table_keys,'has_hidden':hasattr(o,'Hidden'),'Hidden':g(o,'Hidden'),'has_source':hasattr(o,'ImportableObjectSourceId'),'ImportableObjectSourceId':str(g(o,'ImportableObjectSourceId','')),'coordinate':coordinate,'scopes':scopes})
json.dumps(rows)"""
        rows = json.loads(self.client.run_python_script(script))
        objects = {}
        for r in rows:
            values = dict(ObjectId=r["ObjectId"], Name=r["Name"], api_type=r["api_type"], Parent=None, VisibleProperties=[_RemoteProperty(**p) for p in r["props"]])
            if r["table_keys"] is not None: values["TabularData"] = _Proxy(Keys=r["table_keys"])
            if r["has_hidden"]: values["Hidden"] = r["Hidden"]
            if r["has_source"]: values["ImportableObjectSourceId"] = r["ImportableObjectSourceId"]
            if r["coordinate"] is not None: values["CoordinateSystem"] = _Proxy(**r["coordinate"])
            for name, scope in r["scopes"].items():
                if "error" in scope: self.metadata_errors.append(f"{r['Name']}: {name}: {scope['error']}")
                else: values[name] = _Proxy(**scope)
            if r["props_error"]: self.metadata_errors.append(f"{r['Name']}: VisibleProperties: {r['props_error']}")
            objects[r["ObjectId"]] = _Proxy(**values)
        for row in rows:
            if row["parent_id"] in objects: objects[row["ObjectId"]].Parent = objects[row["parent_id"]]
        return list(objects.values())


class _RemoteProperty(_Proxy):
    def __init__(self, **values: Any) -> None:
        field_inputs = values.pop("field_inputs", None)
        super().__init__(**values)
        self.InternalValue = None if field_inputs is None else _Proxy(Inputs=[None] * field_inputs, Output=True)
    @property
    def StringValue(self):
        if self.error: raise ValueError(self.error)
        return self.__dict__["StringValue"]


class _RemoteViewManager:
    def __init__(self, client: Any) -> None: self.client = client
    @property
    def NumberOfViews(self): return int(self.client.run_python_script("str(Graphics.ModelViewManager.NumberOfViews)"))
    def ExportModelViews(self, path: str) -> None:
        self.client.run_python_script(_data_script({"path": path}, "Graphics.ModelViewManager.ExportModelViews(_corex_data['path'])\nstr(True)"))


class _RemoteGraphics:
    def __init__(self, client: Any) -> None: self.ModelViewManager = _RemoteViewManager(client)


__all__ = ["LIFECYCLE_OPERATIONS", "MechanicalOwnerBackend"]
