# Purpose: Stage XY's client with precise affine mapping for large-offset axes.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_client.py, tests/test_xy_probe_qml.py
from __future__ import annotations


# XY 0.0.6 ships offset-encoded float32 geometry but its named-axis path adds
# the absolute offset back in GLSL. Epoch milliseconds then lose minute-scale
# precision before the viewport subtraction. Keep cartesian affine axes in
# encoded coordinates; nonlinear and polar mappings retain the native path.
# Match complete, known methods so an upstream change requires explicit review
# instead of silently applying an unverified rewrite. The installed package is
# never modified; only our session's local asset receives this correction.
_NATIVE_MAP = '_map(e,t,n,r=null){if(!r)return[2/((n-t)*e.scale),(e.offset-t)/(n-t)*2-1];let i=this._axis(r),a=this._axisCoord(i,t),o=this._axisCoord(i,n);if(![a,o].every(Number.isFinite)||o===a)return[0,-2];let s=2/(o-a);return[s,-1-a*s]}'
_NATIVE_UNIFORMS = '_setAxisUniforms(e,t,n,r){let i=this.gl,a=t=>V(i,e,t);i.uniform2f(a(`${t}meta`),n&&Number.isFinite(n.offset)?n.offset:0,n&&n.scale?n.scale:1),i.uniform1i(a(`${t}mode`),this._axisMode(r)),i.uniform1f(a(`${t}constant`),this._axisConstant(r))}'

_PRECISE_MAP = '''_map(meta, lo, hi, axisId=null) {
  if (!axisId || (this.spec?.coords !== `polar` && this._axisMode(axisId) === 0)) {
    return [2 / ((hi - lo) * meta.scale), (meta.offset - lo) / (hi - lo) * 2 - 1];
  }
  const axis = this._axis(axisId), first = this._axisCoord(axis, lo), last = this._axisCoord(axis, hi);
  if (![first, last].every(Number.isFinite) || first === last) return [0, -2];
  const factor = 2 / (last - first);
  return [factor, -1 - first * factor];
}'''
_PRECISE_UNIFORMS = '''_setAxisUniforms(program, prefix, meta, axisId) {
  const gl = this.gl, uniform = name => V(gl, program, name);
  const mode = this._axisMode(axisId);
  const relative = this.spec?.coords !== `polar` && mode === 0;
  gl.uniform2f(uniform(`${prefix}meta`), relative ? 0 : (meta && Number.isFinite(meta.offset) ? meta.offset : 0),
    relative ? 1 : (meta && meta.scale ? meta.scale : 1));
  gl.uniform1i(uniform(`${prefix}mode`), mode);
  gl.uniform1f(uniform(`${prefix}constant`), this._axisConstant(axisId));
}'''


def precise_xy_client(source: str) -> str:
    for native, replacement in ((_NATIVE_MAP, _PRECISE_MAP), (_NATIVE_UNIFORMS, _PRECISE_UNIFORMS)):
        if source.count(native) != 1:
            raise RuntimeError("The installed XY client changed. Review the fullscreen axis-precision adapter before using it.")
        source = source.replace(native, replacement)
    return source
