import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "URBAN — Policy Digital Twin",
  description:
    "Simulate urban policy decisions in a digital twin. Every metric is tagged " +
    "Observed / Estimated / Simulated / Generated.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
