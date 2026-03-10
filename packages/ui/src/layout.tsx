import type { ReactNode } from "react";

import { cx } from "./utils";
import styles from "./layout.module.css";

export function AppShell({
  sidebar,
  topbar,
  insight,
  mobileNav,
  children,
  className,
}: {
  sidebar?: ReactNode;
  topbar?: ReactNode;
  insight?: ReactNode;
  mobileNav?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx(styles.shell, className)}>
      <div className={styles.inner}>
        {sidebar ? <aside className={styles.sidebar}>{sidebar}</aside> : null}
        <main className={styles.main}>
          {topbar ? <div>{topbar}</div> : null}
          {children}
          {mobileNav ? (
            <div className={styles.mobileNav}>{mobileNav}</div>
          ) : null}
        </main>
        {insight ? <aside className={styles.insight}>{insight}</aside> : null}
      </div>
    </div>
  );
}

export function Sidebar({
  brand,
  nav,
  footer,
}: {
  brand: ReactNode;
  nav: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <>
      <div className={styles.topbar}>
        <div className={styles.brand}>
          <div className={styles.brandMark} />
          <div>{brand}</div>
        </div>
      </div>
      <div className={styles.topbar}>
        <nav className={styles.nav}>{nav}</nav>
      </div>
      {footer ? (
        <div className={styles.topbar}>
          <div className={styles.sidebarFooter}>{footer}</div>
        </div>
      ) : null}
    </>
  );
}

export function NavLink({
  children,
  active = false,
  trailing,
}: {
  children: ReactNode;
  active?: boolean;
  trailing?: ReactNode;
}) {
  return (
    <span className={cx(styles.navLink, active && styles.navLinkActive)}>
      <span>{children}</span>
      {trailing ? <span>{trailing}</span> : null}
    </span>
  );
}

export function Topbar({
  left,
  right,
}: {
  left: ReactNode;
  right?: ReactNode;
}) {
  return (
    <header className={styles.topbar}>
      <div>{left}</div>
      {right ? <div>{right}</div> : null}
    </header>
  );
}
