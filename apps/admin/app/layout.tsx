import "./globals.css";

import type { ReactNode } from "react";

export const metadata = {
  title: "UnScripted Admin",
  description: "Operations, model rollout, and synthetic discourse observability"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
