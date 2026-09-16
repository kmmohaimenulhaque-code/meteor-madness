import { useEffect, useRef } from "react";

/**
 * Lightweight interactive 3D-style solar system (canvas projection).
 * Planets + NEO markers from NeoWs list. Drag to rotate, scroll to zoom.
 */
const PLANETS = [
  { name: "Mercury", a: 0.39, r: 2.2, color: "#b1b1b1" },
  { name: "Venus", a: 0.72, r: 3.4, color: "#e8cda0" },
  { name: "Earth", a: 1.0, r: 3.6, color: "#4f8ef7" },
  { name: "Mars", a: 1.52, r: 2.8, color: "#d16b4a" },
  { name: "Jupiter", a: 2.8, r: 8.5, color: "#d4a574" },
  { name: "Saturn", a: 3.6, r: 7.2, color: "#e6d5a8" },
];

export default function SolarSystemScene({ asteroids = [], selectedId }) {
  const canvasRef = useRef(null);
  const stateRef = useRef({
    rotY: 0.4,
    rotX: 0.35,
    zoom: 1,
    dragging: false,
    lastX: 0,
    lastY: 0,
    t: 0,
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let frame;
    let running = true;

    function resize() {
      const parent = canvas.parentElement;
      const w = parent?.clientWidth || 800;
      const h = parent?.clientHeight || 420;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    resize();
    window.addEventListener("resize", resize);

    function project(x, y, z, w, h, zoom) {
      const s = stateRef.current;
      // rotate around Y then X
      const cosY = Math.cos(s.rotY);
      const sinY = Math.sin(s.rotY);
      const cosX = Math.cos(s.rotX);
      const sinX = Math.sin(s.rotX);
      let x1 = x * cosY - z * sinY;
      let z1 = x * sinY + z * cosY;
      let y1 = y * cosX - z1 * sinX;
      z1 = y * sinX + z1 * cosX;
      const scale = (140 * zoom) / (3.2 + z1 * 0.15);
      return {
        sx: w / 2 + x1 * scale,
        sy: h / 2 + y1 * scale,
        scale,
        depth: z1,
      };
    }

    function draw() {
      if (!running) return;
      const s = stateRef.current;
      s.t += 0.008;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      // stars
      ctx.fillStyle = "#050814";
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 80; i++) {
        const sx = (i * 97) % w;
        const sy = (i * 53) % h;
        ctx.fillStyle = `rgba(255,255,255,${0.2 + (i % 5) * 0.1})`;
        ctx.fillRect(sx, sy, 1.2, 1.2);
      }

      // orbital rings + planets
      const bodies = [];

      // Sun
      bodies.push({
        name: "Sun",
        x: 0,
        y: 0,
        z: 0,
        r: 14,
        color: "#ffcc66",
        kind: "sun",
      });

      PLANETS.forEach((p, idx) => {
        const angle = s.t * (0.25 / Math.sqrt(p.a)) + idx;
        const x = Math.cos(angle) * p.a * 1.15;
        const z = Math.sin(angle) * p.a * 1.15;
        bodies.push({
          name: p.name,
          x,
          y: 0,
          z,
          r: p.r,
          color: p.color,
          kind: "planet",
          a: p.a,
        });
      });

      // NEOs as small rocks near Earth orbit
      const neoList = (asteroids || []).slice(0, 24);
      neoList.forEach((a, i) => {
        const ang = s.t * 0.5 + i * 0.35;
        const rad = 1.05 + (i % 5) * 0.08;
        const selected = String(a.id) === String(selectedId);
        bodies.push({
          name: a.name || a.id,
          x: Math.cos(ang) * rad,
          y: Math.sin(ang * 0.7) * 0.12,
          z: Math.sin(ang) * rad,
          r: selected ? 3.2 : 1.6,
          color: selected ? "#ff8a3d" : "#c9d1d9",
          kind: "neo",
          selected,
        });
      });

      // orbits
      PLANETS.forEach((p) => {
        ctx.beginPath();
        ctx.strokeStyle = "rgba(120,160,220,0.18)";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 64; i++) {
          const ang = (i / 64) * Math.PI * 2;
          const x = Math.cos(ang) * p.a * 1.15;
          const z = Math.sin(ang) * p.a * 1.15;
          const pr = project(x, 0, z, w, h, s.zoom);
          if (i === 0) ctx.moveTo(pr.sx, pr.sy);
          else ctx.lineTo(pr.sx, pr.sy);
        }
        ctx.stroke();
      });

      bodies
        .map((b) => ({ ...b, p: project(b.x, b.y, b.z, w, h, s.zoom) }))
        .sort((a, b) => a.p.depth - b.p.depth)
        .forEach((b) => {
          const { sx, sy, scale } = b.p;
          const radius = Math.max(1.2, b.r * (scale / 40));
          ctx.beginPath();
          ctx.fillStyle = b.color;
          ctx.arc(sx, sy, radius, 0, Math.PI * 2);
          ctx.fill();
          if (b.kind === "sun") {
            ctx.beginPath();
            ctx.fillStyle = "rgba(255,200,80,0.25)";
            ctx.arc(sx, sy, radius * 2.2, 0, Math.PI * 2);
            ctx.fill();
          }
          if (b.selected || b.kind === "planet" || b.kind === "sun") {
            ctx.fillStyle = "rgba(230,240,255,0.85)";
            ctx.font = "11px system-ui, sans-serif";
            ctx.fillText(b.name, sx + radius + 4, sy + 3);
          }
        });

      ctx.fillStyle = "rgba(180,200,230,0.55)";
      ctx.font = "11px system-ui, sans-serif";
      ctx.fillText("Drag to rotate · scroll to zoom · orange = selected NEO", 12, h - 12);

      frame = requestAnimationFrame(draw);
    }

    draw();

    function onDown(e) {
      stateRef.current.dragging = true;
      stateRef.current.lastX = e.clientX;
      stateRef.current.lastY = e.clientY;
    }
    function onMove(e) {
      if (!stateRef.current.dragging) return;
      const dx = e.clientX - stateRef.current.lastX;
      const dy = e.clientY - stateRef.current.lastY;
      stateRef.current.rotY += dx * 0.008;
      stateRef.current.rotX += dy * 0.006;
      stateRef.current.lastX = e.clientX;
      stateRef.current.lastY = e.clientY;
    }
    function onUp() {
      stateRef.current.dragging = false;
    }
    function onWheel(e) {
      e.preventDefault();
      stateRef.current.zoom = Math.min(
        2.4,
        Math.max(0.55, stateRef.current.zoom * (e.deltaY > 0 ? 0.92 : 1.08))
      );
    }

    canvas.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      running = false;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [asteroids, selectedId]);

  return <canvas ref={canvasRef} className="story-solar-canvas" />;
}
