"use client";

import { useState } from "react";
import Link from "next/link";
import {
  SEED_ACTIONS,
  ACTION_TYPE_CONFIG,
  sortActions,
  getActionCounts,
  timeAgo,
  type ActionType,
  type ActionItem,
  type ActionPriority,
} from "@/lib/seed-actions";

/* ── Minimal priority label ────────────────────────────────────── */

const PRIORITY_LABEL: Record<ActionPriority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const PRIORITY_DOT: Record<ActionPriority, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  medium: "bg-yellow-400",
  low: "bg-gray-300",
};

const FILTER_TABS: (ActionType | "all")[] = [
  "all",
  "compliance",
  "onboarding",
  "quote",
  "query",
  "insight",
];

/* ── Confidence indicator ──────────────────────────────────────── */

function Confidence({ value }: { value: number }) {
  const color =
    value >= 80
      ? "text-emerald-600"
      : value >= 50
        ? "text-amber-600"
        : "text-red-500";

  return (
    <span className={`text-xs tabular-nums ${color}`}>
      {value}%
    </span>
  );
}

/* ── Action card ───────────────────────────────────────────────── */

function ActionCard({
  action,
  isExpanded,
  isResolved,
  onToggle,
  onResolve,
}: {
  action: ActionItem;
  isExpanded: boolean;
  isResolved: boolean;
  onToggle: () => void;
  onResolve: () => void;
}) {
  const config = ACTION_TYPE_CONFIG[action.type];

  if (isResolved) return null;

  return (
    <div
      className={`group rounded-xl border border-gray-200/80 border-l-[3px] ${config.border} bg-white transition-all hover:shadow-[0_1px_3px_rgba(0,0,0,0.04)]`}
    >
      {/* Main row */}
      <div className="px-5 py-4">
        {/* Top meta line */}
        <div className="mb-2 flex items-center gap-3">
          <span
            className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ${config.badge}`}
          >
            {config.label}
          </span>
          <div className="flex items-center gap-1.5">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${PRIORITY_DOT[action.priority]}`}
            />
            <span className="text-[11px] text-gray-400">
              {PRIORITY_LABEL[action.priority]}
            </span>
          </div>
          <span className="text-[11px] text-gray-300">&middot;</span>
          <span className="text-[11px] text-gray-400">
            {timeAgo(action.createdAt)}
          </span>
          <span className="text-[11px] text-gray-300">&middot;</span>
          <span className="text-[11px] text-gray-400">{action.source}</span>

          {/* Confidence — right-aligned */}
          <div className="ml-auto flex items-center gap-1.5">
            <Confidence value={action.confidence} />
          </div>
        </div>

        {/* Title + Summary */}
        <h3 className="text-[14px] font-semibold leading-snug text-gray-900">
          {action.title}
        </h3>
        <p className="mt-1 text-[13px] leading-relaxed text-gray-500">
          {action.summary}
        </p>

        {/* Actions row */}
        <div className="mt-3.5 flex items-center justify-between">
          {/* Buttons */}
          <div className="flex items-center gap-2">
            {action.buttons.map((btn, i) => {
              let cls: string;
              if (btn.variant === "primary") {
                cls =
                  "rounded-lg bg-gray-900 px-3.5 py-1.5 text-[12px] font-medium text-white hover:bg-gray-800 transition-colors";
              } else if (btn.variant === "danger") {
                cls =
                  "rounded-lg px-3.5 py-1.5 text-[12px] font-medium text-red-600 hover:bg-red-50 transition-colors";
              } else {
                cls =
                  "rounded-lg px-3.5 py-1.5 text-[12px] font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors";
              }

              return (
                <button
                  key={i}
                  className={cls}
                  onClick={() => {
                    if (btn.variant === "primary" || btn.label === "Bestätigen") {
                      onResolve();
                    } else if (
                      btn.variant === "danger" ||
                      btn.label === "Zurückstellen" ||
                      btn.label === "Ignorieren"
                    ) {
                      onResolve();
                    }
                  }}
                >
                  {btn.label}
                </button>
              );
            })}
          </div>

          {/* Expand toggle */}
          <button
            onClick={onToggle}
            className="flex items-center gap-1 text-[12px] text-gray-400 hover:text-gray-600 transition-colors"
          >
            {isExpanded ? "Weniger" : "Details"}
            <svg
              className={`h-3.5 w-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Expanded detail panel */}
      {isExpanded && (
        <div className="border-t border-gray-100 px-5 py-4">
          <p className="text-[13px] leading-relaxed text-gray-600">
            {action.detail}
          </p>
          {action.relatedProductId && (
            <Link
              href={`/products/${action.relatedProductId}`}
              className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              Produkt anzeigen
              <svg
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────── */

export default function QueuePage() {
  const [filter, setFilter] = useState<ActionType | "all">("all");
  const [sortBy, setSortBy] = useState<"priority" | "date">("priority");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());

  const pendingActions = SEED_ACTIONS.filter((a) => !resolvedIds.has(a.id));
  const counts = getActionCounts(pendingActions);

  const filtered =
    filter === "all"
      ? pendingActions
      : pendingActions.filter((a) => a.type === filter);

  const sorted = sortActions(filtered, sortBy);

  function handleResolve(id: string) {
    setResolvedIds((prev) => new Set(prev).add(id));
    if (expandedId === id) setExpandedId(null);
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
          Action Queue
        </h1>
        <p className="mt-1 text-[13px] text-gray-400">
          {pendingActions.length === 0
            ? "All clear — no pending actions."
            : `${pendingActions.length} ${pendingActions.length === 1 ? "item needs" : "items need"} your attention`}
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-1">
          {FILTER_TABS.map((tab) => {
            const isActive = filter === tab;
            const count = counts[tab] || 0;
            const label =
              tab === "all"
                ? "All"
                : ACTION_TYPE_CONFIG[tab as ActionType].label;

            return (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                  isActive
                    ? "bg-gray-900 text-white"
                    : "text-gray-400 hover:text-gray-700 hover:bg-gray-100/60"
                }`}
              >
                {label}
                <span
                  className={`tabular-nums text-[11px] ${
                    isActive ? "text-white/50" : "text-gray-300"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "priority" | "date")}
          className="rounded-lg border-0 bg-transparent py-1.5 pr-8 pl-2 text-[13px] font-medium text-gray-400 focus:outline-none focus:ring-0"
        >
          <option value="priority">Priority</option>
          <option value="date">Newest</option>
        </select>
      </div>

      {/* Cards */}
      {sorted.length > 0 ? (
        <div className="space-y-2.5">
          {sorted.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              isExpanded={expandedId === action.id}
              isResolved={resolvedIds.has(action.id)}
              onToggle={() =>
                setExpandedId(expandedId === action.id ? null : action.id)
              }
              onResolve={() => handleResolve(action.id)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50">
            <svg
              className="h-5 w-5 text-emerald-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <p className="text-[14px] font-medium text-gray-900">
            {filter === "all"
              ? "All clear"
              : `No ${ACTION_TYPE_CONFIG[filter as ActionType].label} actions`}
          </p>
          <p className="mt-1 text-[13px] text-gray-400">
            {filter === "all"
              ? "Agents are working in the background."
              : "Nothing pending in this category."}
          </p>
        </div>
      )}
    </div>
  );
}
