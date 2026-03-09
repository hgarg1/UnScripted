import "./globals.css";

import type { ReactNode } from "react";

export const metadata = {
  title: "UnScripted",
  description: "Human and agent discourse simulation platform"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
