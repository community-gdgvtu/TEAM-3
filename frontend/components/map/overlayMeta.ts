/**
 * Pure overlay metadata (no deck.gl imports) so the panel can render captions,
 * legends and provenance chips during SSR without pulling the WebGL stack in.
 * The heavy layer builders live in `overlays.ts` and are imported only by the
 * SSR-disabled map component.
 */

export type OverlayMode = "none" | "traffic" | "transit" | "support";

export type Provenance = "Synthetic" | "Simulated" | "Placeholder";

export interface OverlayMeta {
  mode: OverlayMode;
  label: string;
  provenance: Provenance;
  /** What the overlay shows + the honesty caveat (SPEC §34). */
  caption: string;
  legend: Array<{ color: string; label: string }>;
  /** Hide the base choropleth so the overlay is legible. */
  hideBaseZones: boolean;
}

export const OVERLAY_META: Record<OverlayMode, OverlayMeta> = {
  none: {
    mode: "none",
    label: "Zones",
    provenance: "Synthetic",
    caption: "",
    legend: [],
    hideBaseZones: false,
  },
  traffic: {
    mode: "traffic",
    label: "Traffic flow",
    provenance: "Placeholder",
    caption:
      "Illustrative corridor-load index from link capacity — not simulated flow. Real per-link volumes arrive with /simulate.",
    legend: [
      { color: "rgb(80,200,90)", label: "Lower load" },
      { color: "rgb(246,190,90)", label: "Mid" },
      { color: "rgb(246,60,60)", label: "Higher load" },
    ],
    hideBaseZones: false,
  },
  transit: {
    mode: "transit",
    label: "Transit demand",
    provenance: "Synthetic",
    caption:
      "Daily trip attraction per zone from the synthetic OD matrix (world input). Policy-shifted demand comes from /simulate.",
    legend: [
      { color: "rgb(60,90,180)", label: "Lower demand" },
      { color: "rgb(246,190,96)", label: "Higher demand" },
    ],
    hideBaseZones: true,
  },
  support: {
    mode: "support",
    label: "Support / opposition",
    provenance: "Placeholder",
    caption:
      "Illustrative support gradient (placeholder). Real cohort support comes from /simulate + the public-reaction model.",
    legend: [
      { color: "rgb(220,84,84)", label: "Oppose" },
      { color: "rgb(120,130,150)", label: "Split" },
      { color: "rgb(80,200,120)", label: "Support" },
    ],
    hideBaseZones: true,
  },
};
