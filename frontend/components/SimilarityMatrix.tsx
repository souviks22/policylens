"use client";

import { useMemo, useState } from "react";

interface Props {
  matrix: number[][];
  rowLabels: string[];
  colLabels: string[];
  maxRows?: number;
  maxCols?: number;
}

function scoreToColor(score: number): string {
  if (score >= 0.95) return "#22c55e";
  if (score >= 0.80) return "#86efac";
  if (score >= 0.65) return "#fbbf24";
  if (score >= 0.45) return "#f59e0b";
  if (score >= 0.20) return "#7a7464";
  return "#2a2825";
}

function truncLabel(s: string, n = 16) {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

const CELL = 40;
const LABEL_W = 150;
const HEADER_H = 130;
const LEGEND_H = 32;
const PAD = 16;

export default function SimilarityMatrix({
  matrix,
  rowLabels,
  colLabels,
  maxRows = 12,
  maxCols = 12,
}: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  const rows = useMemo(() => matrix.slice(0, maxRows), [matrix, maxRows]);
  const rLabels = useMemo(() => rowLabels.slice(0, maxRows), [rowLabels, maxRows]);
  const cLabels = useMemo(() => colLabels.slice(0, maxCols), [colLabels, maxCols]);

  if (!rows.length || !cLabels.length) {
    return (
      <div className="text-center py-8 text-ink-600 text-sm italic">
        Not enough sections detected to render the similarity matrix.
      </div>
    );
  }

  const svgW = LABEL_W + cLabels.length * CELL + PAD;
  const svgH = HEADER_H + rows.length * CELL + LEGEND_H + PAD;

  return (
    <div className="overflow-x-auto relative">
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width={svgW}
        height={svgH}
        style={{ fontFamily: "'JetBrains Mono', 'Courier New', monospace", display: "block" }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* ── Column labels (rotated -45°) ─────────────────────────────────── */}
        {cLabels.map((label, j) => {
          const cx = LABEL_W + j * CELL + CELL / 2;
          return (
            <text
              key={`col-${j}`}
              x={LABEL_W + j * CELL + CELL / 2}
              y={HEADER_H - 8}
              textAnchor="start"
              transform={`rotate(-45, ${LABEL_W + j * CELL + CELL / 2}, ${HEADER_H - 8})`}
              fontSize={9}
              fill="#7a7464"
            >
              {truncLabel(label)}
            </text>
          );
        })}

        {/* ── Row labels + cells ───────────────────────────────────────────── */}
        {rows.map((row, i) => {
          const rowCols = row.slice(0, maxCols);
          return (
            <g key={`row-${i}`}>
              {/* Row label */}
              <text
                x={LABEL_W - 8}
                y={HEADER_H + i * CELL + CELL / 2 + 4}
                textAnchor="end"
                fontSize={9}
                fill="#99937e"
              >
                {truncLabel(rLabels[i] ?? `Row ${i + 1}`)}
              </text>

              {/* Cells */}
              {rowCols.map((score, j) => {
                const cx = LABEL_W + j * CELL;
                const cy = HEADER_H + i * CELL;
                const fill = scoreToColor(score);
                const textFill = score > 0.65 ? "#1a1815" : "#e8e6de";
                const r = rLabels[i] ?? `Row ${i + 1}`;
                const c = cLabels[j] ?? `Col ${j + 1}`;
                return (
                  <g
                    key={`cell-${i}-${j}`}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() =>
                      setTooltip({
                        x: cx + CELL / 2,
                        y: cy,
                        text: `${truncLabel(r, 24)} ↔ ${truncLabel(c, 24)}: ${score.toFixed(3)}`,
                      })
                    }
                  >
                    <rect
                      x={cx + 1}
                      y={cy + 1}
                      width={CELL - 2}
                      height={CELL - 2}
                      rx={3}
                      fill={fill}
                      opacity={0.9}
                    />
                    <text
                      x={cx + CELL / 2}
                      y={cy + CELL / 2 + 4}
                      textAnchor="middle"
                      fontSize={8}
                      fill={textFill}
                      fontWeight="500"
                    >
                      {score >= 0.05 ? score.toFixed(2) : ""}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* ── Legend ───────────────────────────────────────────────────────── */}
        {(() => {
          const legendY = HEADER_H + rows.length * CELL + 12;
          const stops = [0, 0.25, 0.50, 0.75, 1.0];
          return (
            <g>
              <text x={LABEL_W} y={legendY - 1} fontSize={7} fill="#625d51">
                Cosine similarity →
              </text>
              {stops.map((v, k) => (
                <g key={`leg-${k}`}>
                  <rect
                    x={LABEL_W + k * 42}
                    y={legendY + 4}
                    width={38}
                    height={10}
                    rx={2}
                    fill={scoreToColor(v)}
                    opacity={0.9}
                  />
                  <text
                    x={LABEL_W + k * 42}
                    y={legendY + 24}
                    fontSize={7}
                    fill="#7a7464"
                  >
                    {v.toFixed(2)}
                  </text>
                </g>
              ))}
            </g>
          );
        })()}

        {/* ── Tooltip ──────────────────────────────────────────────────────── */}
        {tooltip && (
          <g>
            <rect
              x={Math.min(tooltip.x - 4, svgW - 260)}
              y={tooltip.y - 22}
              width={Math.min(tooltip.text.length * 6 + 12, 280)}
              height={18}
              rx={4}
              fill="#2a2825"
              stroke="#4e4a42"
              strokeWidth={0.5}
            />
            <text
              x={Math.min(tooltip.x + 2, svgW - 254)}
              y={tooltip.y - 9}
              fontSize={8}
              fill="#e8e6de"
            >
              {tooltip.text}
            </text>
          </g>
        )}
      </svg>

      {(rowLabels.length > maxRows || colLabels.length > maxCols) && (
        <p className="text-xs text-ink-700 mt-2 italic">
          Showing {Math.min(rowLabels.length, maxRows)} × {Math.min(colLabels.length, maxCols)} of{" "}
          {rowLabels.length} × {colLabels.length} sections
        </p>
      )}
    </div>
  );
}
