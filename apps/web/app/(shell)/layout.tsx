import type { ReactNode } from "react";

import { WebAppProvider, WebProductShell } from "../../components/app-shell";

export default function ProductShellLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <WebAppProvider>
      <WebProductShell>{children}</WebProductShell>
    </WebAppProvider>
  );
}
