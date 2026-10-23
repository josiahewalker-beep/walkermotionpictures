// Shared shader chunks for the slide worlds (desert, drive-in): the build-in from the grid and the height haze.
// Every world material carries the DESERT_REV define and its own world's uniforms (REV below), so two worlds can share
// one chunk text: nothing world-specific is baked into the GLSL.
import * as THREE from 'three';
let installed = false, commonOrig = null;
export const REV_UNIFORMS = () => ({ uRev: { value: 1 }, uMode: { value: 0 }, uOrigin: { value: new THREE.Vector3() }, uCam: { value: new THREE.Vector3() },
  uR: { value: 1e7 }, uVoid: { value: new THREE.Color(0xf6f7f9) }, uFloor: { value: 0 },
  uHzY0: { value: 0 }, uHzH: { value: 3000 }, uHzSun: { value: new THREE.Vector3(0, 1, 0) }, uHzSunC: { value: new THREE.Color(1, 1, 1) } });
export function installWorldChunks() {
  if (installed) return; installed = true;
  const S = THREE.ShaderChunk; if (commonOrig === null) commonOrig = S.common;
    S.common = commonOrig + `
#ifdef DESERT_REV
 uniform float uRev; uniform int uMode; uniform vec3 uOrigin; uniform vec3 uCam; uniform float uR; uniform vec3 uVoid; uniform float uFloor;
 uniform float uHzY0; uniform float uHzH; uniform vec3 uHzSun; uniform vec3 uHzSunC;
 varying float vDK; varying float vG;
#endif`;
    // the world is built outward from the billboard's foot through the grid's own cells (160 units, aligned with the lattice).
    // vDK: 0 at the front, 1 settled. Props use their own origin so they arrive whole; ground, road and ranges (DESERT_GROUND) per point.
    S.project_vertex = `#ifdef DESERT_REV
 vec4 dwp = vec4( transformed, 1.0 );
 #ifdef USE_INSTANCING
  dwp = instanceMatrix * dwp;
 #endif
 dwp = modelMatrix * dwp;
 #ifdef DESERT_GROUND
  vec3 dOrg = dwp.xyz;
 #else
  #ifdef USE_INSTANCING
   vec3 dOrg = ( modelMatrix * instanceMatrix * vec4( 0.0, 0.0, 0.0, 1.0 ) ).xyz;
  #else
   vec3 dOrg = ( modelMatrix * vec4( 0.0, 0.0, 0.0, 1.0 ) ).xyz;
  #endif
 #endif
 vDK = uRev >= 0.9999 ? 1.0 : clamp( ( uR - length( dOrg.xz - uOrigin.xz ) ) / ( 0.25 * uR + 300.0 ), 0.0, 1.0 );
 vG = 1.0;
 if ( uRev < 0.9999 ) {
  #ifndef DESERT_GROUND
   #ifdef REV_BLOOM
    // trees bloom: each grows from its own base while the build front travels from it to 9x its distance (eased), so they swell into
    // the world with the grid's cells instead of popping in whole; the un-build runs the same curve backwards
    float bk = clamp( log( uR / ( length( dOrg.xz - uOrigin.xz ) + 200.0 ) ) / log( 9.0 ), 0.0, 1.0 );   // the front grows exponentially: measure in log so each tree takes ~40% of the build to grow
    float bt = fract( sin( dot( floor( dOrg.xz / 40.0 ), vec2( 12.9898, 78.233 ) ) ) * 43758.5453 ) * 0.3;
    vG = smoothstep( bt, bt + 0.7, bk ); vG = 1.0 - ( 1.0 - vG ) * ( 1.0 - vG ) * ( 1.0 - vG );
    dwp.xyz = mix( vec3( dOrg.x, uFloor, dOrg.z ), dwp.xyz, vG );
   #else
   if ( uMode == 0 ) vG = smoothstep( 0.0, 1.0, vDK );
   else if ( uMode == 2 ) { float ct = fract( sin( dot( floor( dOrg.xz / 160.0 ), vec2( 12.9898, 78.233 ) ) ) * 43758.5453 ) * 0.35; vG = smoothstep( ct, ct + 0.45, vDK ); }
   dwp.y = mix( uFloor, dwp.y, vG );                      // props rise up out of the grid's floor
   #endif
  #else
   if ( uMode == 0 ) dwp.y = mix( uFloor, dwp.y, smoothstep( 0.0, 1.0, vDK ) );   // ground and ranges lift out of the fabric
  #endif
 }
 vec4 mvPosition = viewMatrix * dwp;
 gl_Position = projectionMatrix * mvPosition;
#else
 vec4 mvPosition = vec4( transformed, 1.0 );
 #ifdef USE_BATCHING
  mvPosition = batchingMatrix * mvPosition;
 #endif
 #ifdef USE_INSTANCING
  mvPosition = instanceMatrix * mvPosition;
 #endif
 mvPosition = modelViewMatrix * mvPosition;
 gl_Position = projectionMatrix * mvPosition;
#endif`;
    S.fog_pars_vertex = '#ifdef USE_FOG\n varying float vFogDepth;\n #ifdef FOG_EXP2\n  varying vec3 vFogWP;\n #endif\n#endif';
    S.fog_vertex = `#ifdef USE_FOG
 vFogDepth = - mvPosition.z;
 #ifdef FOG_EXP2
  #ifdef DESERT_REV
   vFogWP = dwp.xyz;
  #else
   vec4 fogWP = vec4( transformed, 1.0 );
   #ifdef USE_INSTANCING
    fogWP = instanceMatrix * fogWP;
   #endif
   vFogWP = ( modelMatrix * fogWP ).xyz;
  #endif
 #endif
#endif`;
    S.fog_pars_fragment = '#ifdef USE_FOG\n uniform vec3 fogColor;\n varying float vFogDepth;\n #ifdef FOG_EXP2\n  uniform float fogDensity;\n  varying vec3 vFogWP;\n #else\n  uniform float fogNear;\n  uniform float fogFar;\n #endif\n#endif';
    S.fog_fragment = `#ifdef USE_FOG
 #ifdef FOG_EXP2
  #ifdef DESERT_REV
   float fogH = exp( - max( vFogWP.y - uHzY0, 0.0 ) / uHzH );
   float fogSun = pow( max( dot( normalize( vFogWP - cameraPosition ), uHzSun ), 0.0 ), 4.0 );
   vec3 fogSunC = uHzSunC;
  #else
   float fogH = 1.0, fogSun = 0.0; vec3 fogSunC = fogColor;
  #endif
  float fogFactor = 1.0 - exp( - fogDensity * vFogDepth * ( 0.45 + 0.55 * fogH ) );
  vec3 fogC = mix( fogColor, fogSunC, fogSun * 0.5 );
  #ifdef DESERT_REV
  if ( uRev < 0.9999 ) {
   float fk = vDK;
   #ifdef DESERT_GROUND
    fk = clamp( ( uR - length( vFogWP.xz - uOrigin.xz ) ) / ( 0.25 * uR + 300.0 ), 0.0, 1.0 );
   #endif
   vec3 gp = vFogWP / 160.0 + vec3( 0.0, 0.5, 0.0 ), gw = abs( fract( gp - 0.5 ) - 0.5 ) / max( fwidth( gp ), vec3( 1e-4 ) );   // horizontal lines sit half a cell off the floor, so surfaces lying on it don't all light up
   float lnFar = 1.0 - smoothstep( 0.12, 0.35, max( max( fwidth( gp.x ), fwidth( gp.y ) ), fwidth( gp.z ) ) );   // dense lines far away fade instead of blurring solid
   float ln = ( 1.0 - clamp( min( min( gw.x, gw.y ), gw.z ) - 0.6, 0.0, 1.0 ) ) * lnFar;
   vec2 cf = abs( fract( gp.xz - 0.5 ) - 0.5 ) / max( fwidth( gp.xz ), vec2( 1e-4 ) );
   float edge = ( 1.0 - clamp( min( cf.x, cf.y ) - 0.8, 0.0, 1.0 ) ) * lnFar;
   vec3 lineC = vec3( 0.24, 0.40, 0.96 ), paleC = uVoid * 0.94;
   if ( uMode == 0 ) {            // rise: surfaces come up out of the fabric as pale grid-lined sheets, then take their colour
    if ( fk <= 0.0 ) discard;
    gl_FragColor.rgb = mix( mix( paleC, lineC, ln * 0.9 ), gl_FragColor.rgb, smoothstep( 0.12, 0.75, fk ) );
   } else if ( uMode == 1 ) {     // drape: the grid's lines settle onto every surface first, then the fill comes in behind them
    if ( fk <= 0.0 ) discard;
    if ( fk < 0.3 ) { if ( ln < 0.5 ) discard; gl_FragColor.rgb = lineC; }
    else { float s2 = smoothstep( 0.3, 1.0, fk ); gl_FragColor.rgb = mix( mix( paleC, gl_FragColor.rgb, s2 ), lineC, ln * ( 1.0 - s2 ) * 0.85 ); }
   } else {                       // cells: each grid cell switches on with its outline lit, props grow up inside their cell
    float g = vG;
    #ifdef DESERT_GROUND
     float ct = fract( sin( dot( floor( gp.xz ), vec2( 12.9898, 78.233 ) ) ) * 43758.5453 ) * 0.35;
     g = smoothstep( ct, ct + 0.45, fk );
    #endif
    if ( g <= 0.002 ) discard;
    gl_FragColor.rgb = mix( mix( paleC, lineC, max( edge, ln * 0.6 ) ), gl_FragColor.rgb, smoothstep( 0.05, 0.85, g ) );
   }
   fogC = mix( uVoid, fogC, smoothstep( 0.6, 1.0, uRev ) );
  }
  #endif
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogC, fogFactor );
 #else
  float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
 #endif
#endif`;
}
