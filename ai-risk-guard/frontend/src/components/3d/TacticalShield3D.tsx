import React, { useEffect, useRef } from 'react';
import { ShieldCADState } from '../../types';

interface TacticalShield3DProps {
  scrollProgress: number;
  cadState: ShieldCADState;
  onCADChange?: (updates: Partial<ShieldCADState>) => void;
  className?: string;
  convergingThreads?: Array<{ x: number; y: number; progress: number; color: string }>;
}

export const TacticalShield3D: React.FC<TacticalShield3DProps> = ({
  scrollProgress,
  cadState,
  onCADChange,
  className = ''
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const threeStateRef = useRef<{
    renderer?: any;
    scene?: any;
    camera?: any;
    controls?: any;
    shieldGroup?: any;
    mainMesh?: any;
    edgeMesh?: any;
    circuitMesh?: any;
    particleSystem?: any;
    coreMesh?: any;
    coreGlowSprite?: any;
    pointLight?: any;
    animId?: number;
    clock?: any;
  }>({});

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const THREE = (window as any).THREE;
    if (!THREE) {
      console.warn('Three.js not found on window.');
      return;
    }

    const width = container.clientWidth || 540;
    const height = container.clientHeight || 540;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, width / height, 0.01, 200);

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.75;
    container.appendChild(renderer.domElement);

    // 3. OrbitControls
    let controls: any = null;
    if (THREE.OrbitControls) {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
      controls.enableZoom = false;
      controls.autoRotate = cadState.autoRotate;
      controls.autoRotateSpeed = 1.3;
      controls.minPolarAngle = Math.PI / 2;
      controls.maxPolarAngle = Math.PI / 2;
    }

    // 4. Lighting Rig (80% Navy Blue, 10% Red, 10% Silver)
    scene.add(new THREE.AmbientLight(0x071B3E, 3.8));

    const keyLight = new THREE.DirectionalLight(0xE2E8F0, 4.2);
    keyLight.position.set(4, 4, 5);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x0E2F68, 4.5);
    fillLight.position.set(-4, -2, 4);
    scene.add(fillLight);

    const backLight = new THREE.DirectionalLight(0xCBD5E1, 3.5);
    backLight.position.set(0, 0, -5);
    scene.add(backLight);

    const pointLight = new THREE.PointLight(0xFF2A4B, 6.0, 14);
    pointLight.position.set(0, 0, 2.2);
    scene.add(pointLight);

    // 5. Build Original Procedural Industrial Cryo-Shield
    const shieldMasterGroup = new THREE.Group();
    scene.add(shieldMasterGroup);

    function createShieldPathPoints(scale = 1.0) {
      const pts = [];
      pts.push(new THREE.Vector2(0.0 * scale, 1.25 * scale));
      pts.push(new THREE.Vector2(0.48 * scale, 1.06 * scale));
      pts.push(new THREE.Vector2(0.88 * scale, 0.88 * scale));
      pts.push(new THREE.Vector2(0.96 * scale, 0.42 * scale));
      pts.push(new THREE.Vector2(0.94 * scale, -0.05 * scale));
      pts.push(new THREE.Vector2(0.78 * scale, -0.52 * scale));
      pts.push(new THREE.Vector2(0.50 * scale, -0.92 * scale));
      pts.push(new THREE.Vector2(0.24 * scale, -1.25 * scale));
      pts.push(new THREE.Vector2(0.0 * scale, -1.48 * scale));
      pts.push(new THREE.Vector2(-0.24 * scale, -1.25 * scale));
      pts.push(new THREE.Vector2(-0.50 * scale, -0.92 * scale));
      pts.push(new THREE.Vector2(-0.78 * scale, -0.52 * scale));
      pts.push(new THREE.Vector2(-0.94 * scale, -0.05 * scale));
      pts.push(new THREE.Vector2(-0.96 * scale, 0.42 * scale));
      pts.push(new THREE.Vector2(-0.88 * scale, 0.88 * scale));
      pts.push(new THREE.Vector2(-0.48 * scale, 1.06 * scale));
      return pts;
    }

    function createFacetedShieldGeometry() {
      const geom = new THREE.BufferGeometry();
      const vertices: number[] = [];
      const indices: number[] = [];

      const outerPts = createShieldPathPoints(1.0);
      const midPts = createShieldPathPoints(0.74);
      const innerPts = createShieldPathPoints(0.48);
      const N = outerPts.length;

      const Z_FRONT_CENTER = 0.26;
      const Z_FRONT_INNER = 0.20;
      const Z_FRONT_MID = 0.14;
      const Z_FRONT_OUTER = 0.08;
      const Z_SIDE_RIM = 0.00;
      const Z_BACK_OUTER = -0.08;
      const Z_BACK_MID = -0.14;
      const Z_BACK_CENTER = -0.22;

      vertices.push(0, 0.05, Z_FRONT_CENTER);
      innerPts.forEach((p: any) => vertices.push(p.x, p.y + 0.05, Z_FRONT_INNER));
      midPts.forEach((p: any) => vertices.push(p.x, p.y + 0.05, Z_FRONT_MID));
      outerPts.forEach((p: any) => vertices.push(p.x, p.y, Z_FRONT_OUTER));
      outerPts.forEach((p: any) => vertices.push(p.x * 1.03, p.y * 1.03, Z_SIDE_RIM));
      outerPts.forEach((p: any) => vertices.push(p.x, p.y, Z_BACK_OUTER));
      midPts.forEach((p: any) => vertices.push(p.x, p.y + 0.05, Z_BACK_MID));
      const backCenterIdx = 6 * N + 1;
      vertices.push(0, 0.05, Z_BACK_CENTER);

      for (let i = 0; i < N; i++) {
        const next = (i + 1) % N;
        indices.push(0, 1 + i, 1 + next);
        indices.push(1 + i, N + 1 + i, N + 1 + next);
        indices.push(1 + i, N + 1 + next, 1 + next);
        indices.push(N + 1 + i, 2 * N + 1 + i, 2 * N + 1 + next);
        indices.push(N + 1 + i, 2 * N + 1 + next, N + 1 + next);
        indices.push(2 * N + 1 + i, 3 * N + 1 + i, 3 * N + 1 + next);
        indices.push(2 * N + 1 + i, 3 * N + 1 + next, 2 * N + 1 + next);
        indices.push(3 * N + 1 + i, 4 * N + 1 + i, 4 * N + 1 + next);
        indices.push(3 * N + 1 + i, 4 * N + 1 + next, 3 * N + 1 + next);
        indices.push(4 * N + 1 + i, 5 * N + 1 + i, 5 * N + 1 + next);
        indices.push(4 * N + 1 + i, 4 * N + 1 + next, 5 * N + 1 + next);
        indices.push(backCenterIdx, 5 * N + 1 + next, 5 * N + 1 + i);
      }

      geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      geom.setIndex(indices);
      geom.center();
      geom.computeVertexNormals();
      return geom;
    }

    const scaleGroup = new THREE.Group();
    scaleGroup.scale.set(1.85, 1.85, 1.85);

    // 1. Navy Blue 80% Convex Armor Shell Material
    const shieldGeom = createFacetedShieldGeometry();
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x071D45,
      emissive: 0x030F28,
      emissiveIntensity: 0.95,
      metalness: 0.55,
      roughness: 0.15,
      transmission: 0.68,
      thickness: 1.8,
      ior: 1.55,
      transparent: true,
      opacity: 0.96,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      side: THREE.DoubleSide
    });
    const mainMesh = new THREE.Mesh(shieldGeom, glassMat);
    scaleGroup.add(mainMesh);

    // 2. Beveled Titanium Silver Edges (10% Silver)
    const edgeGeom = new THREE.EdgesGeometry(shieldGeom, 14);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0xCBD5E1, transparent: true, opacity: 0.95 });
    const edgeMesh = new THREE.LineSegments(edgeGeom, edgeMat);
    scaleGroup.add(edgeMesh);

    // 3. Tactical Circuits (10% Threat Red & Silver)
    const circuitPositions: number[] = [];
    const angles = [0, Math.PI / 4, Math.PI / 2, (3 * Math.PI) / 4, Math.PI, (5 * Math.PI) / 4, (3 * Math.PI) / 2, (7 * Math.PI) / 4];
    angles.forEach((ang) => {
      const x1 = Math.cos(ang) * 0.12, y1 = Math.sin(ang) * 0.12 + 0.05;
      const x2 = Math.cos(ang) * 0.45, y2 = Math.sin(ang) * 0.45 + 0.05;
      circuitPositions.push(x1, y1, 0.25, x2, y2, 0.20);
      const x3 = x2 + (Math.cos(ang) > 0 ? 0.12 : -0.12), y3 = y2 + 0.08;
      circuitPositions.push(x2, y2, 0.20, x3, y3, 0.17);
    });
    [-0.35, -0.2, 0.2, 0.35].forEach((x) => {
      circuitPositions.push(x, 0.75, 0.15, x, -0.45, 0.16);
      circuitPositions.push(x, -0.45, 0.16, x * 0.5, -0.85, 0.18);
    });
    const circuitGeo = new THREE.BufferGeometry();
    circuitGeo.setAttribute('position', new THREE.Float32BufferAttribute(circuitPositions, 3));
    const circuitMesh = new THREE.LineSegments(
      circuitGeo,
      new THREE.LineBasicMaterial({ color: 0xFF2A4B, transparent: true, opacity: 0.85 })
    );
    scaleGroup.add(circuitMesh);

    // 4. Orbit Particle Nodes (10% Silver Metallic Dust)
    const nodePos: number[] = [];
    for (let i = 0; i < 180; i++) {
      const ang = (i / 180) * Math.PI * 2 * 3.5;
      const rad = 0.15 + (i / 180) * 0.75;
      nodePos.push(
        Math.cos(ang) * rad,
        Math.sin(ang) * rad * 1.25 + 0.05,
        (i % 2 === 0 ? 0.18 : -0.18) + (Math.random() - 0.5) * 0.05
      );
    }
    const nodeGeo = new THREE.BufferGeometry();
    nodeGeo.setAttribute('position', new THREE.Float32BufferAttribute(nodePos, 3));
    const particleSystem = new THREE.Points(
      nodeGeo,
      new THREE.PointsMaterial({
        color: 0xE2E8F0,
        size: 0.024,
        transparent: true,
        opacity: 0.95,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    scaleGroup.add(particleSystem);

    // 5. Central Ruby Iris Core (10% Threat Red)
    const coreGeo = new THREE.SphereGeometry(0.08, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xFF2A4B });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.set(0, 0.05, 0.25);
    scaleGroup.add(coreMesh);

    // 6. Threat Red Glow Sprite
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 128;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
      grad.addColorStop(0, 'rgba(255, 42, 75, 1.0)');
      grad.addColorStop(0.35, 'rgba(220, 38, 38, 0.7)');
      grad.addColorStop(1, 'rgba(11, 37, 86, 0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 128, 128);
    }
    const glowTex = new THREE.CanvasTexture(canvas);
    const coreGlowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: glowTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    coreGlowSprite.scale.set(1.3, 1.3, 1);
    coreGlowSprite.position.set(0, 0.05, 0.26);
    scaleGroup.add(coreGlowSprite);

    shieldMasterGroup.add(scaleGroup);

    // Fit camera to shield
    const box = new THREE.Box3().setFromObject(shieldMasterGroup);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    shieldMasterGroup.position.x = -center.x;
    shieldMasterGroup.position.y = -center.y;
    shieldMasterGroup.position.z = -center.z;

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    const cameraDist = ((maxDim / 2) / Math.tan(fov / 2)) * 0.95;

    camera.position.set(0, 0, cameraDist);
    camera.near = 0.01;
    camera.far = 150;
    camera.updateProjectionMatrix();

    if (controls) {
      controls.target.set(0, 0, 0);
      controls.update();
    }

    const clock = new THREE.Clock();

    // Render loop
    const animate = () => {
      const animId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      if (controls) controls.update();
      if (shieldMasterGroup) shieldMasterGroup.position.y = Math.sin(t * 1.8) * 0.04;
      if (coreMesh) coreMesh.scale.setScalar(1 + Math.sin(t * 2.8) * 0.12);
      if (coreGlowSprite) coreGlowSprite.scale.setScalar(1.3 + Math.sin(t * 2.8) * 0.15);
      if (particleSystem) particleSystem.rotation.z = t * 0.02;
      if (pointLight) pointLight.intensity = 5.2 + Math.sin(t * 3.0) * 0.5;

      renderer.render(scene, camera);
      threeStateRef.current.animId = animId;
    };
    animate();

    // Handle Resize
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    threeStateRef.current = {
      renderer,
      scene,
      camera,
      controls,
      shieldGroup: shieldMasterGroup,
      mainMesh,
      edgeMesh,
      circuitMesh,
      particleSystem,
      coreMesh,
      coreGlowSprite,
      pointLight,
      clock
    };

    return () => {
      if (threeStateRef.current.animId) {
        cancelAnimationFrame(threeStateRef.current.animId);
      }
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    };
  }, []);

  // Update CAD View Angle, Wireframe, and AutoRotate
  useEffect(() => {
    const { controls, mainMesh, camera } = threeStateRef.current;
    if (!controls) return;

    controls.autoRotate = cadState.autoRotate;

    if (mainMesh) {
      mainMesh.visible = !cadState.wireframe;
    }

    if (camera) {
      const dist = camera.position.length() || 6;
      switch (cadState.viewAngle) {
        case 'FRONT':
          camera.position.set(0, 0, dist);
          break;
        case 'TOP':
          camera.position.set(0, dist, 0.01);
          break;
        case 'RIGHT':
          camera.position.set(dist, 0, 0);
          break;
        case 'SECTION':
          camera.position.set(dist * 0.7, dist * 0.4, dist * 0.6);
          break;
        case 'EXPLODED':
          camera.position.set(dist * 0.5, dist * 0.3, dist * 0.8);
          break;
        case 'ISOMETRIC':
        default:
          camera.position.set(dist * 0.6, dist * 0.4, dist * 0.7);
          break;
      }
      camera.lookAt(0, 0, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    }
  }, [cadState]);

  return (
    <div className={`relative w-full h-full min-h-[560px] sm:min-h-[640px] lg:min-h-[700px] flex items-center justify-center ${className}`}>
      <div 
        ref={containerRef} 
        className="w-full h-full min-h-[560px] sm:min-h-[640px] lg:min-h-[700px] relative cursor-grab active:cursor-grabbing" 
      />
    </div>
  );
};
