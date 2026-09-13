# Purpose: Verify the guarded native-client correction and GPU affine coordinates.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_client.py
import json
from importlib import resources

import pytest
from PyQt6.QtQml import QJSEngine

from ea_node_editor.web_host import xy_client


def test_exact_client_guard_and_float32_epoch_mapping(qapp):
    source = resources.files('xy').joinpath('static', 'index.js').read_text(encoding='utf-8')
    patched = xy_client.precise_xy_client(source)
    assert xy_client._PRECISE_MAP in patched and xy_client._PRECISE_UNIFORMS in patched
    with pytest.raises(RuntimeError, match='axis-precision adapter'):
        xy_client.precise_xy_client(patched)
    engine = QJSEngine()
    value = engine.evaluate('''(() => {
      const uniforms = {}, V = (gl, p, key) => key;
      const owner = {
        spec: {},
        _axisMode: axis => axis === 'log' ? 3 : 0,
        _axisConstant: () => 1,
        _axis: axis => axis,
        _axisCoord: (axis, value) => axis === 'log' ? Math.log10(value) : value,
        gl: {uniform2f:(key,x,y)=>uniforms[key]=[x,y], uniform1i:()=>{}, uniform1f:()=>{}},
    ''' + xy_client._PRECISE_MAP + ',' + xy_client._PRECISE_UNIFORMS + '''
      };
      const origin = 1767225600000, meta = {offset:origin+50000, scale:1};
      const map = owner._map(meta, origin+10000, origin+90000, 'time');
      owner._setAxisUniforms(null,'u_x',meta,'time');
      const affine = uniforms.u_xmeta;
      const pixels = [origin+10000, origin+50000, origin+90000].map(x => {
        const encoded = Math.fround((x-meta.offset)*meta.scale);
        const decoded = Math.fround(Math.fround(encoded/affine[1])+affine[0]);
        return Math.fround(Math.fround(decoded*Math.fround(map[0]))+Math.fround(map[1]));
      });
      owner._setAxisUniforms(null,'u_y',{offset:0,scale:2},'log');
      const logarithmic = owner._map({offset:0,scale:2},1,100,'log');
      owner.spec.coords='polar';owner._setAxisUniforms(null,'u_p',meta,'time');
      return JSON.stringify({pixels,affine,logarithmic,logMeta:uniforms.u_ymeta,polarMeta:uniforms.u_pmeta});
    })()''')
    assert not value.isError(), value.toString()
    result = json.loads(value.toString())
    assert result == {'pixels': [-1, 0, 1], 'affine': [0, 1], 'logarithmic': [1, -1],
                      'logMeta': [0, 2], 'polarMeta': [1767225650000, 1]}
    engine.deleteLater()
