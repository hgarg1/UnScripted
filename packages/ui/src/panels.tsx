import type { ReactNode } from "react";

import { cx } from "./utils";
import styles from "./panels.module.css";

type SurfaceProps = {
  eyebrow?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  className?: string;
};

export function Card({
  eyebrow,
  title,
  description,
  children,
  className,
}: SurfaceProps) {
  return (
    <section className={cx(styles.card, className)}>
      {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
      {title ? <h2 className={styles.title}>{title}</h2> : null}
      {description ? <p className={styles.description}>{description}</p> : null}
      {children ? <div className={styles.content}>{children}</div> : null}
    </section>
  );
}

export function Panel({
  eyebrow,
  title,
  description,
  children,
  className,
}: SurfaceProps) {
  return (
    <section className={cx(styles.panel, className)}>
      {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
      {title ? <h3 className={styles.title}>{title}</h3> : null}
      {description ? <p className={styles.description}>{description}</p> : null}
      {children ? <div className={styles.content}>{children}</div> : null}
    </section>
  );
}

export function MetricCard({
  eyebrow,
  value,
  label,
  children,
  className,
}: {
  eyebrow?: ReactNode;
  value: ReactNode;
  label: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx(styles.metricCard, className)}>
      {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
      <p className={styles.metricValue}>{value}</p>
      <p className={styles.metricLabel}>{label}</p>
      {children ? <div className={styles.content}>{children}</div> : null}
    </section>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header>
      {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
      <div
        style={{
          display: "flex",
          gap: "16px",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 className={cx(styles.title, styles.displayTitle)}>{title}</h1>
          {description ? (
            <p className={styles.description}>{description}</p>
          ) : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
    </header>
  );
}

export function Tabs<T extends string>({
  items,
  value,
  onChange,
}: {
  items: Array<{ value: T; label: ReactNode }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className={styles.tabs} role="tablist">
      {items.map((item) => (
        <button
          key={item.value}
          className={cx(styles.tab, item.value === value && styles.tabActive)}
          role="tab"
          aria-selected={item.value === value}
          onClick={() => onChange(item.value)}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: ReactNode;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) {
    return null;
  }

  return (
    <>
      <button
        aria-label="Close drawer"
        className={styles.drawerBackdrop}
        onClick={onClose}
        type="button"
      />
      <aside className={styles.drawer}>
        <Panel eyebrow="Detail" title={title} className={styles.panelDense}>
          {children}
        </Panel>
      </aside>
    </>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: ReactNode;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) {
    return null;
  }

  return (
    <>
      <button
        aria-label="Close modal"
        className={styles.modalBackdrop}
        onClick={onClose}
        type="button"
      />
      <section className={styles.modal}>
        <Panel eyebrow="Dialog" title={title} className={styles.panelDense}>
          {children}
        </Panel>
      </section>
    </>
  );
}

export function StatusCard({
  eyebrow,
  title,
  description,
  children,
}: SurfaceProps) {
  return (
    <Panel eyebrow={eyebrow} title={title} description={description}>
      {children}
    </Panel>
  );
}
