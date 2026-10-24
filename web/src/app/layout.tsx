import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HeistBox — Ocean's 11 × PAIR Vault",
  description: "Three judges, one vault. Watch an LLM-as-judge get robbed, a firewall freeze an honest customer, and HeistBox × PAIR bust the heist in 1.8ms.",
};

export const viewport: Viewport = {
  themeColor: "#07040d",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
