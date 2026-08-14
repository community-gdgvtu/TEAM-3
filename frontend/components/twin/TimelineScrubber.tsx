"use client";

/**
 * Time Machine scrubber (SPEC §9/§17). A draggable slider over the baseline
 * checkpoints (T0 → 10y) that drives the map time badge and the dashboard tiles.
 * Purely presentational: the parent owns the selected index.
 */

import type { Checkpoint } from "../../lib/api";

export interface TimelineScrubberProps {
  checkpoints: Checkpoint[];
  index: number;
  onChange: (index: number) => void;
  disabled?: boolean;
}

export default function TimelineScrubber({
  checkpoints,
  index,
  onChange,
  disabled = false,
}: TimelineScrubberProps) {
  const max = Math.max(0, checkpoints.length - 1);
  const current = checkpoints[index];

  return (
    <div className={`timeline${disabled ? " disabled" : ""}`}>
      <div className="timeline-head">
        <span className="timeline-title">Time machine</span>
        <span className="timeline-now">
          {current ? current.label : "—"}
          {current && current.t_months > 0 ? (
            <span className="timeline-sub">
              {" "}
              · {current.t_months < 12
                ? `${current.t_months} mo`
                : `${current.t_years} yr`}{" "}
              after implementation
            </span>
          ) : (
            <span className="timeline-sub"> · implementation</span>
          )}
        </span>
      </div>

      <input
        className="timeline-range"
        type="range"
        min={0}
        max={max}
        step={1}
        value={Math.min(index, max)}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        aria-label="Timeline checkpoint"
        list="timeline-ticks"
      />

      <div className="timeline-ticks">
        {checkpoints.map((cp, i) => (
          <button
            key={cp.label}
            type="button"
            className={`tick${i === index ? " active" : ""}`}
            onClick={() => onChange(i)}
            disabled={disabled}
          >
            {cp.label}
          </button>
        ))}
      </div>
    </div>
  );
}
