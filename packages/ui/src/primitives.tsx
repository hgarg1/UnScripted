import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { cx } from "./utils";
import styles from "./primitives.module.css";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({
  className,
  variant = "primary",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cx(styles.button, styles[variant], className)}
      type={type}
      {...props}
    />
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx(styles.field, className)} {...props} />;
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cx(styles.field, styles.textarea, className)}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cx(styles.select, className)} {...props}>
      {children}
    </select>
  );
}

export function Toggle({
  checked,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { checked: boolean }) {
  return (
    <button
      aria-pressed={checked}
      className={cx(styles.toggle, checked && styles.toggleOn, className)}
      {...props}
    />
  );
}

export function Badge({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={cx(styles.badge, className)}>{children}</span>;
}

export function Chip({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "primary" | "success" | "warning" | "danger";
  className?: string;
}) {
  const toneClass =
    tone === "success"
      ? styles.chipSuccess
      : tone === "warning"
        ? styles.chipWarning
        : tone === "danger"
          ? styles.chipDanger
          : tone === "neutral"
            ? styles.chipNeutral
            : styles.chip;
  return (
    <span className={cx(styles.chip, toneClass, className)}>{children}</span>
  );
}

export function Tooltip({
  children,
  content,
}: {
  children: ReactNode;
  content: string;
}) {
  return (
    <span className={styles.tooltip} title={content}>
      {children}
    </span>
  );
}
