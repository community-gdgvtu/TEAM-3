/**
 * WebGL capability probe.
 *
 * The 3D twin (deck.gl) needs a working WebGL context. On machines with
 * hardware acceleration disabled, old browsers, or headless/preview panes, that
 * context never comes up and deck.gl renders nothing — a black box. We detect
 * that here so the studio can fall back to a flat, top-down plan of the same
 * city instead of showing an empty frame.
 */
export function hasWebGL(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl =
      canvas.getContext("webgl2") ||
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl");
    if (!gl) return false;
    // Some environments hand back a context that immediately reports lost.
    const lose = (gl as WebGLRenderingContext).getExtension?.(
      "WEBGL_lose_context",
    );
    void lose;
    return true;
  } catch {
    return false;
  }
}
