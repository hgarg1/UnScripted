import type { ReactNode } from "react";

import styles from "./data-display.module.css";

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
}: {
  columns: Array<{
    key: string;
    header: ReactNode;
    render: (row: T) => ReactNode;
  }>;
  rows: T[];
  getRowKey: (row: T) => string;
}) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Sparkline({
  values,
  color = "var(--ui-primary)",
}: {
  values: number[];
  color?: string;
}) {
  if (!values.length) {
    return (
      <svg
        className={styles.sparkline}
        viewBox="0 0 100 40"
        aria-hidden="true"
      />
    );
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const spread = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100;
      const y = 34 - ((value - min) / spread) * 28;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      className={styles.sparkline}
      viewBox="0 0 100 40"
      aria-hidden="true"
      preserveAspectRatio="none"
    >
      <polyline
        fill="none"
        points={points}
        stroke={color}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="3"
      />
    </svg>
  );
}
