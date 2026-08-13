"use client";

/**
 * Guided demo (SPEC §29). A floating launcher opens a spotlight walkthrough of the
 * real UI: each step scrolls its anchor into view, cuts a hole in a dimming
 * overlay around it, and shows a caption card with Prev / Next controls. Steps
 * that live under the analysis tab bar first ask PanelTabs to switch tabs.
 *
 * The tour is pure guidance — it never renders a metric, so it can't fabricate
 * one. It just points at what the backend produced (or its "waiting for backend"
 * state) and explains the flow.
 */

import { useCallback, useEffect, useLayoutEffect, useState } from "react";

import { TOUR_STEPS, requestDemoTab } from "../../lib/demo";

interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PAD = 8; // spotlight padding around the target, in px

export default function DemoTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [box, setBox] = useState<Box | null>(null);

  const current = TOUR_STEPS[step];

  // Position the spotlight over the current step's anchor, scrolling it into
  // view first. Re-run when the step changes; a rAF lets a just-switched tab
  // paint before we measure it.
  const place = useCallback(() => {
    const el = document.querySelector<HTMLElement>(current.selector);
    if (!el) {
      setBox(null);
      return;
    }
    const r = el.getBoundingClientRect();
    setBox({
      top: r.top - PAD,
      left: r.left - PAD,
      width: r.width + PAD * 2,
      height: r.height + PAD * 2,
    });
  }, [current.selector]);

  useLayoutEffect(() => {
    if (!open) return;
    if (current.tab) requestDemoTab(current.tab);
    const el = document.querySelector<HTMLElement>(current.selector);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    // Measure after the smooth-scroll and any tab switch have painted.
    const t = window.setTimeout(place, 260);
    return () => window.clearTimeout(t);
  }, [open, step, current.tab, current.selector, place]);

  // Keep the spotlight glued to its anchor while the user scrolls or resizes.
  useEffect(() => {
    if (!open) return;
    const onMove = () => place();
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [open, place]);

  const close = useCallback(() => setOpen(false), []);
  const next = useCallback(
    () => setStep((s) => Math.min(s + 1, TOUR_STEPS.length - 1)),
    [],
  );
  const prev = useCallback(() => setStep((s) => Math.max(s - 1, 0)), []);

  // Keyboard nav while the tour is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close, next, prev]);

  function start() {
    setStep(0);
    setOpen(true);
  }

  if (!open) {
    return (
      <button
        type="button"
        className="demo-launch"
        onClick={start}
        title="Take the 60-second guided tour"
      >
        ▶ Guided demo
      </button>
    );
  }

  const isLast = step === TOUR_STEPS.length - 1;
  // Anchor the caption card below the spotlight, or centre it if we lost the box.
  const cardStyle: React.CSSProperties = box
    ? {
        top: Math.min(box.top + box.height + 12, window.innerHeight - 220),
        left: Math.max(
          12,
          Math.min(box.left, window.innerWidth - 372),
        ),
      }
    : { top: "50%", left: "50%", transform: "translate(-50%, -50%)" };

  return (
    <div className="demo-tour" role="dialog" aria-modal="true" aria-label="Guided demo">
      {/* Dimmer with a hole punched around the target via a huge box-shadow. */}
      {box ? (
        <div
          className="demo-spotlight"
          style={{
            top: box.top,
            left: box.left,
            width: box.width,
            height: box.height,
          }}
        />
      ) : (
        <div className="demo-dimmer" onClick={close} />
      )}

      <div className="demo-card" style={cardStyle}>
        <div className="demo-card-head">
          <span className="demo-step-count">
            Step {step + 1} / {TOUR_STEPS.length}
          </span>
          <button
            type="button"
            className="demo-close"
            onClick={close}
            aria-label="Close tour"
          >
            ✕
          </button>
        </div>
        <h3 className="demo-title">{current.title}</h3>
        <p className="demo-body">{current.body}</p>
        <div className="demo-actions">
          <button
            type="button"
            className="btn"
            onClick={prev}
            disabled={step === 0}
          >
            Back
          </button>
          {isLast ? (
            <button type="button" className="btn primary" onClick={close}>
              Done
            </button>
          ) : (
            <button type="button" className="btn primary" onClick={next}>
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
