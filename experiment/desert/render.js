// Desert world — image pipeline for the photoreal pass.
// The site's grid is drawn with custom shaders that expect no tone mapping, so the desert's post-processing (ambient
// occlusion, bloom) only runs once the grid has handed over completely (landed). While building in, the world renders
// directly with per-material ACES tone mapping, which matches what the composer's output pass does, so nothing jumps.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { N8AOPass } from '../vendor/n8ao/N8AO.js';
import { Sky } from 'three/addons/objects/Sky.js';

export const EXPOSURE = 1.0;

export function setupRenderer(renderer) {
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = EXPOSURE;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
}

// Image-based light and reflections: a physically based golden-hour sky over warm sand, with a low ring of ranges
// on the horizon, so car paint and glass reflect a believable world.
export function skyEnvironment(renderer, sunDir, { sand = 0x9a6a42, ranges = 0x6e4b46 } = {}) {
  const sc = new THREE.Scene(), sky = new Sky(); sky.scale.setScalar(4000);
  const u = sky.material.uniforms; u.turbidity.value = 6; u.rayleigh.value = 1.6; u.mieCoefficient.value = 0.006; u.mieDirectionalG.value = 0.86; u.sunPosition.value.copy(sunDir);
  sc.add(sky);
  const gnd = new THREE.Mesh(new THREE.CircleGeometry(3000, 48).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: sand })); gnd.position.y = -1; sc.add(gnd);
  const ring = new THREE.Mesh(new THREE.CylinderGeometry(2500, 2500, 90, 64, 1, true), new THREE.MeshBasicMaterial({ color: ranges, side: THREE.BackSide })); ring.position.y = 30; sc.add(ring);
  const pm = new THREE.PMREMGenerator(renderer), tm = renderer.toneMapping; renderer.toneMapping = THREE.NoToneMapping;
  const env = pm.fromScene(sc, 0.02).texture; renderer.toneMapping = tm; pm.dispose();
  return env;
}

// grain + a whisper of vignette, done in the composer so it sits on the world and not on the slide's HTML
const FinishShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: 0.035 }, uVig: { value: 0.18 }, uK: { value: 1 } },
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime, uGrain, uVig, uK; varying vec2 vUv;
    float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + uTime * 37.0) * 43758.5453); }
    void main() {
      vec4 c = texture2D(tDiffuse, vUv); vec3 o = c.rgb;
      float l = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
      // golden-hour print grade: a little contrast and colour, warm highlights, faintly cool shadows
      vec3 g = (c.rgb - 0.5) * 1.07 + 0.5;
      g = mix(vec3(l), g, 1.14);
      g += vec3(0.022, 0.004, -0.028) * smoothstep(0.35, 1.0, l) + vec3(-0.014, 0.0, 0.016) * (1.0 - smoothstep(0.0, 0.35, l));
      c.rgb = mix(o, g, uK);
      c.rgb += (h(gl_FragCoord.xy) - 0.5) * uGrain * uK * (0.35 + 0.65 * (1.0 - abs(l - 0.45) * 1.6));   // luminance-weighted grain
      vec2 d = vUv - 0.5; c.rgb *= 1.0 - uVig * uK * dot(d, d) * 2.2;
      gl_FragColor = c;
    }`,
};

export function makeComposer(renderer, scene, camera) {
  const size = new THREE.Vector2(); renderer.getSize(size);
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, rt);
  composer.setPixelRatio(Math.min(renderer.getPixelRatio(), 1.5));
  composer.addPass(new RenderPass(scene, camera));
  const ao = new N8AOPass(scene, camera, size.x, size.y);
  Object.assign(ao.configuration, { aoRadius: 2.2 * 108, distanceFalloff: 0.6 * 108, intensity: 2.2, color: new THREE.Color(0x1a0f08), halfRes: true, depthAwareUpsampling: true, gammaCorrection: false, aoSamples: 12, denoiseSamples: 6, denoiseRadius: 10 });
  if (!window.__noAO) composer.addPass(ao);
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.22, 0.55, 0.92);
  if (!window.__noBloom) composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const finish = new ShaderPass(FinishShader); composer.addPass(finish);
  const resize = () => { renderer.getSize(size); composer.setSize(size.x, size.y); ao.setSize(size.x, size.y); };
  addEventListener('resize', resize);
  let t = 0;
  return {
    render(dt, k = 1) { t += dt; finish.uniforms.uTime.value = t % 100; finish.uniforms.uK.value = k; ao.configuration.intensity = 2.2 * k; bloom.strength = 0.22 * k; composer.render(dt); },
  };
}
