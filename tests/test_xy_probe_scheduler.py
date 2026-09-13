# Purpose: Prove bounded probe scheduling and stale-reply rejection without a browser.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_probe_scheduler.py
import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QJSEngine


def test_latest_only_throttle_release_errors_and_disposal():
    app = QApplication.instance() or QApplication(["probe-scheduler"])
    engine = QJSEngine()
    module = engine.importModule(str(Path(__file__).resolve().parents[1] / "ea_node_editor/web_assets/xy_host/probe_scheduler.js"))
    assert not module.isError(), module.toString()
    engine.globalObject().setProperty("create", module.property("createProbeScheduler"))
    value = engine.evaluate('''(() => {
      let clock=0, sent=[], shown=[], failures=[], tasks=new Map(), id=0;
      const q=create({send:r=>sent.push(r),pending:()=>{},result:r=>shown.push(r.position),error:e=>failures.push(e),
        now:()=>clock,setTimer:(fn,delay)=>{tasks.set(++id,{fn,due:clock+delay});return id;},clearTimer:k=>tasks.delete(k)});
      const tick=ms=>{clock+=ms;for(const [key,task] of [...tasks])if(task.due<=clock){tasks.delete(key);task.fn();}};
      q.update({position:1});
      for(let n=2;n<=100;n++)q.update({position:n});
      if(sent.length!==1)throw Error('unbounded in-flight requests');
      q.receive({revision:sent[0].revision,position:1});
      if(shown.length)throw Error('stale result painted');
      tick(99);if(sent.length!==1)throw Error('throttle bypass');
      tick(1);if(sent[1].position!==100)throw Error('latest state lost');
      q.update({position:101},true);
      q.receive({revision:sent[1].revision,position:100});
      if(sent.length!==3||sent[2].position!==101)throw Error('final release delayed');
      q.receive({revision:sent[2].revision,position:101});
      q.receive({revision:sent[2].revision,position:999});
      q.update({position:102});q.update(null);tick(1000);
      if(sent.length!==3)throw Error('cleared probe dispatched');
      q.update({position:103},true);q.receive({revision:sent[3].revision,message:'bad query'},true);
      q.update({position:104},true);q.dispose();q.receive({revision:sent[4].revision,position:104});
      q.update({position:105},true);tick(1000);
      return JSON.stringify({sent:sent.length,shown,failures,pending:tasks.size});
    })()''')
    assert not value.isError(), value.toString()
    assert json.loads(value.toString()) == {"sent": 5, "shown": [101], "failures": ["bad query"], "pending": 0}
    engine.deleteLater()
    app.processEvents()


def test_probe_coordinate_entry_is_strict_and_utc():
    app = QApplication.instance() or QApplication(["probe-coordinates"])
    engine = QJSEngine()
    module = engine.importModule(str(Path(__file__).resolve().parents[1] / "ea_node_editor/web_assets/xy_host/probe_coordinates.js"))
    assert not module.isError(), module.toString()
    engine.globalObject().setProperty("parse", module.property("parseProbePosition"))
    engine.globalObject().setProperty("format", module.property("formatProbePosition"))
    value = engine.evaluate('''(() => {
      const numeric={x_kind:'numeric',y_log:true}, time={x_kind:'datetime',y_log:false};
      if(parse('1.25e2','x',numeric)!==125)throw Error('numeric coordinate');
      for(const input of ['', 'NaN', 'Infinity', '0x20']){let ok=false;try{parse(input,'x',numeric);}catch(e){ok=true;}if(!ok)throw Error('invalid number accepted');}
      for(const input of ['0','-1']){let ok=false;try{parse(input,'y',numeric);}catch(e){ok=true;}if(!ok)throw Error('invalid log coordinate accepted');}
      const text='2026-01-01T12:00:00.123456Z', stamp=parse(text,'x',time);
      if(format(stamp,'x',time)!==text)throw Error('UTC fraction lost');
      if(format(parse('1969-12-31T23:59:59.999500Z','x',time),'x',time)!=='1969-12-31T23:59:59.999500Z')throw Error('pre-epoch precision');
      for(const input of ['2026-02-30T00:00:00Z','2026-01-01T00:00:00','2026-01-01T24:00:00Z']){let ok=false;try{parse(input,'x',time);}catch(e){ok=true;}if(!ok)throw Error('invalid UTC accepted');}
      return true;
    })()''')
    assert not value.isError(), value.toString()
    assert value.toBool()
    engine.deleteLater(); app.processEvents()
