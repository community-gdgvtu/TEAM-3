"use client";

/**
 * Hero background art: a skyline silhouette plus an ambient canvas animation
 * of commute flows curving toward the cordon — the same origin-destination
 * idea CityStudio simulates for real, rendered here as pure atmosphere. No
 * video file, no external image: a canvas loop and one inline SVG, so there's
 * nothing to download and nothing that can fail to load.
 */

import { useEffect, useRef } from "react";

/** Deterministic skyline: [x, width, height] per building, in viewBox units. */
const BUILDINGS: Array<[number, number, number]> = [
  [0, 26, 58], [28, 18, 92], [48, 22, 40], [72, 30, 120], [104, 16, 66],
  [122, 24, 145], [148, 20, 78], [170, 34, 100], [206, 18, 54], [226, 26, 132],
  [254, 22, 70], [278, 30, 160], [310, 18, 48], [330, 24, 96], [356, 20, 118],
  [378, 32, 60], [412, 22, 140], [436, 18, 84], [456, 28, 108], [486, 24, 52],
  [512, 20, 130], [534, 30, 74], [566, 18, 100], [586, 24, 150], [612, 22, 62],
  [636, 28, 116], [666, 20, 88], [688, 30, 44], [720, 24, 128], [746, 18, 70],
  [766, 34, 96],
];

const SKYLINE_HEIGHT = 168;

function Skyline() {
  return (
    <svg
      className="hero-skyline"
      viewBox="0 0 800 168"
      preserveAspectRatio="none"
      aria-hidden
    >
      <defs>
        <linearGradient id="skylineFade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--panel-2)" stopOpacity="0" />
          <stop offset="100%" stopColor="var(--panel-2)" stopOpacity="1" />
        </linearGradient>
      </defs>
      {BUILDINGS.map(([x, w, h], i) => (
        <rect
          key={i}
          x={x}
          y={SKYLINE_HEIGHT - h}
          width={w}
          height={h}
          fill="url(#skylineFade)"
          stroke="var(--border-strong)"
          strokeWidth="1"
        />
      ))}
      {/* A few lit windows — static, not decorative-random, so SSR markup is stable. */}
      {[92, 136, 240, 292, 424, 500, 600, 700].map((x, i) => (
        <rect
          key={x}
          x={x}
          y={SKYLINE_HEIGHT - 30 - (i % 3) * 22}
          width="4"
          height="6"
          fill={i % 2 === 0 ? "var(--accent)" : "var(--stamp)"}
          opacity="0.55"
        />
      ))}
    </svg>
  );
}

interface Particle {
  x0: number;
  y0: number;
  cx: number;
  cy: number;
  t: number;
  speed: number;
  hue: "cyan" | "amber";
  size: number;
}

function FlowCanvas() {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    const container = canvas?.parentElement;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let w = 0;
    let h = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let focalX = 0;
    let focalY = 0;

    function resize() {
      if (!canvas || !container) return;
      w = container.clientWidth;
      h = container.clientHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
      focalX = w * 0.7;
      focalY = h * 0.48;
    }
    resize();
    window.addEventListener("resize", resize);

    const count = 26;
    const particles: Particle[] = Array.from({ length: count }, (_, i) => ({
      x0: -20,
      y0: Math.random() * h,
      cx: w * (0.25 + Math.random() * 0.3),
      cy: Math.random() * h,
      t: i / count,
      speed: 0.0022 + Math.random() * 0.0018,
      hue: Math.random() > 0.6 ? "amber" : "cyan",
      size: 1 + Math.random() * 1.4,
    }));

    function bezier(p0: number, p1: number, p2: number, t: number) {
      const mt = 1 - t;
      return mt * mt * p0 + 2 * mt * t * p1 + t * t * p2;
    }

    let raf = 0;

    function frame() {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.t += p.speed;
        if (p.t > 1) {
          p.t = 0;
          p.y0 = Math.random() * h;
          p.cx = w * (0.25 + Math.random() * 0.3);
          p.cy = Math.random() * h;
          p.hue = Math.random() > 0.6 ? "amber" : "cyan";
        }
        const x = bezier(p.x0, p.cx, focalX, p.t);
        const y = bezier(p.y0, p.cy, focalY, p.t);
        const fade = Math.sin(Math.PI * p.t);
        const color =
          p.hue === "amber"
            ? `rgba(226, 161, 61, ${0.5 * fade})`
            : `rgba(79, 195, 209, ${0.5 * fade})`;
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }

    if (reduceMotion) {
      // One still frame: park every particle mid-path instead of animating.
      for (const p of particles) p.t = 0.5;
      frame();
      cancelAnimationFrame(raf);
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        const x = bezier(p.x0, p.cx, focalX, p.t);
        const y = bezier(p.y0, p.cy, focalY, p.t);
        ctx.beginPath();
        ctx.fillStyle =
          p.hue === "amber" ? "rgba(226, 161, 61, 0.3)" : "rgba(79, 195, 209, 0.3)";
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas ref={ref} className="hero-flow-canvas" aria-hidden />;
}

export default function HeroVisual() {
  return (
    <div className="hero-visual" aria-hidden>
      <FlowCanvas />
      <Skyline />
    </div>
  );
}
