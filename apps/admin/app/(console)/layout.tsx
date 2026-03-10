import type { ReactNode } from "react";

import { AdminConsoleShell, AdminProvider } from "../../components/admin-shell";

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  return (
    <AdminProvider>
      <AdminConsoleShell>{children}</AdminConsoleShell>
    </AdminProvider>
  );
}
