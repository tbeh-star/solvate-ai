"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, VersionDiffResponse, DiffEntry } from "@/lib/api";

/* ── Helpers ──────────────────────────────────────────────── */

const REGION_BADGE: Record<string, { bg: string; text: string }> = {
  EU: { bg: "bg-blue-50", text: "text-blue-700" },
  US: { bg: "bg-indigo-50", text: "text-indigo-700" },
  JP: { bg: "bg-violet-50", text: "text-violet-700" },
  CN: { bg: "bg-rose-50", text: "text-rose-700" },
  KR: { bg: "bg-pink-50", text: "text-pink-700" },
  GLOBAL: { bg: "bg-gray-50", text: "text-gray-500" },
};

function regionBadge(region: string) {
  const c = REGION_BADGE[region] ?? REGION_BADGE.GLOBAL;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${c.bg} ${c.text}`}
    >
      {region}
    </span>
  );
}

function formatLabel(field: string): string {
  return field
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatSectionName(section: string): string {
  const map: Record<string, string> = {
    document_info: "Document Information",
    identity: "Product Identity",
    chemical: "Chemical Properties",
    physical: "Physical Properties",
    application: "Application",
    safety: "Safety",
    compliance: "Compliance",
  };
  return map[section] ?? formatLabel(section);
}

function displayValue(val: string | number | string[] | Record<string, unknown> | null): string {
  if (val == null) return "—";
  if (Array.isArray(val)) return val.join("; ");
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

/* ── Change type styles ───────────────────────────────────── */

const CHANGE_STYLES: Record<
  string,
  { border: string; bg: string; label: string; labelBg: string; labelText: string }
> = {
  added: {
    border: "border-emerald-200",
    bg: "bg-emerald-50/40",
    label: "Added",
    labelBg: "bg-emerald-100",
    labelText: "text-emerald-700",
  },
  removed: {
    border: "border-red-200",
    bg: "bg-red-50/40",
    label: "Removed",
    labelBg: "bg-red-100",
    labelText: "text-red-700",
  },
  changed: {
    border: "border-amber-200",
    bg: "bg-amber-50/40",
    label: "Changed",
    labelBg: "bg-amber-100",
    labelText: "text-amber-700",
  },
};

/* ── Diff Entry Row ───────────────────────────────────────── */

function DiffEntryRow({ entry }: { entry: DiffEntry }) {
  const style = CHANGE_STYLES[entry.change_type] ?? CHANGE_STYLES.changed;

  return (
    <div className={`rounded-lg border ${style.border} ${style.bg} p-3.5`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] font-medium text-gray-800">
          {formatLabel(entry.field)}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${style.labelBg} ${style.labelText}`}
        >
          {style.label}
        </span>
      </div>

      {entry.change_type === "changed" && (
        <div className="space-y-1.5">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-red-100">
              <span className="text-[9px] font-bold text-red-600">-</span>
            </span>
            <div className="min-w-0 flex-1">
              <span className="text-[12px] text-red-700 line-through">
                {displayValue(entry.old_value)}
              </span>
              {entry.old_unit && (
                <span className="ml-1 text-[11px] text-red-500">
                  {entry.old_unit}
                </span>
              )}
              {entry.old_confidence && (
                <span className="ml-1.5 text-[10px] text-red-400">
                  ({entry.old_confidence})
                </span>
              )}
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-100">
              <span className="text-[9px] font-bold text-emerald-600">+</span>
            </span>
            <div className="min-w-0 flex-1">
              <span className="text-[12px] font-medium text-emerald-700">
                {displayValue(entry.new_value)}
              </span>
              {entry.new_unit && (
                <span className="ml-1 text-[11px] text-emerald-500">
                  {entry.new_unit}
                </span>
              )}
              {entry.new_confidence && (
                <span className="ml-1.5 text-[10px] text-emerald-400">
                  ({entry.new_confidence})
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {entry.change_type === "added" && (
        <div className="flex items-start gap-2">
          <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-100">
            <span className="text-[9px] font-bold text-emerald-600">+</span>
          </span>
          <div className="min-w-0 flex-1">
            <span className="text-[12px] font-medium text-emerald-700">
              {displayValue(entry.new_value)}
            </span>
            {entry.new_unit && (
              <span className="ml-1 text-[11px] text-emerald-500">
                {entry.new_unit}
              </span>
            )}
          </div>
        </div>
      )}

      {entry.change_type === "removed" && (
        <div className="flex items-start gap-2">
          <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-red-100">
            <span className="text-[9px] font-bold text-red-600">-</span>
          </span>
          <div className="min-w-0 flex-1">
            <span className="text-[12px] text-red-700 line-through">
              {displayValue(entry.old_value)}
            </span>
            {entry.old_unit && (
              <span className="ml-1 text-[11px] text-red-500">
                {entry.old_unit}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function VersionDiffPage() {
  const params = useParams<{ id: string; compareId: string }>();
  const id1 = parseInt(params.id, 10);
  const id2 = parseInt(params.compareId, 10);

  const [diff, setDiff] = useState<VersionDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiff = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getVersionDiff(id1, id2);
      setDiff(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load diff");
    } finally {
      setLoading(false);
    }
  }, [id1, id2]);

  useEffect(() => {
    if (!isNaN(id1) && !isNaN(id2)) fetchDiff();
  }, [id1, id2, fetchDiff]);

  /* ── Loading / Error ───────────────────────────────────────── */

  if (loading) {
    return (
      <div>
        <Link
          href={`/history/records/${id1}`}
          className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
        >
          <ChevronLeftIcon />
          Back to Record
        </Link>
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[13px] text-gray-400">Computing diff...</p>
        </div>
      </div>
    );
  }

  if (error || !diff) {
    return (
      <div>
        <Link
          href={`/history/records/${id1}`}
          className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
        >
          <ChevronLeftIcon />
          Back to Record
        </Link>
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-16 text-center">
          <p className="text-[14px] font-medium text-red-900">
            {error || "Diff not available"}
          </p>
        </div>
      </div>
    );
  }

  // Count changes by type
  const addedCount = diff.sections.reduce(
    (sum, s) => sum + s.changes.filter((c) => c.change_type === "added").length,
    0
  );
  const removedCount = diff.sections.reduce(
    (sum, s) => sum + s.changes.filter((c) => c.change_type === "removed").length,
    0
  );
  const changedCount = diff.sections.reduce(
    (sum, s) => sum + s.changes.filter((c) => c.change_type === "changed").length,
    0
  );

  return (
    <div>
      {/* Back link */}
      <Link
        href={`/history/records/${id1}`}
        className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
      >
        <ChevronLeftIcon />
        Back to Record
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
          Version Diff
        </h1>
        <div className="mt-2 flex items-center gap-2.5 flex-wrap">
          <span className="text-[13px] text-gray-600">
            {diff.record_a.product_name}
          </span>
          {regionBadge(diff.record_a.region)}
          <span className="text-gray-300">|</span>
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-gray-600">
            v{diff.record_a.version}
          </span>
          <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-gray-600">
            v{diff.record_b.version}
          </span>
        </div>
      </div>

      {/* Summary bar */}
      <div className="mb-8 flex items-center gap-6 rounded-xl border border-gray-200/80 bg-white px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            {diff.total_changes}
          </span>
          <span className="text-[12px] text-gray-400">
            total changes
          </span>
        </div>
        <div className="h-8 w-px bg-gray-200" />
        {changedCount > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span className="text-[12px] font-medium tabular-nums text-amber-700">
              {changedCount} changed
            </span>
          </div>
        )}
        {addedCount > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-[12px] font-medium tabular-nums text-emerald-700">
              {addedCount} added
            </span>
          </div>
        )}
        {removedCount > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            <span className="text-[12px] font-medium tabular-nums text-red-700">
              {removedCount} removed
            </span>
          </div>
        )}
        {diff.total_changes === 0 && (
          <span className="text-[12px] text-gray-400">
            No differences found between these versions.
          </span>
        )}
      </div>

      {/* Summary text */}
      {diff.summary && (
        <p className="mb-6 text-[13px] text-gray-500">
          {diff.summary}
        </p>
      )}

      {/* Sections with changes */}
      <div className="space-y-6">
        {diff.sections.map((section) => (
          <section
            key={section.section}
            className="rounded-xl border border-gray-200/80 bg-white"
          >
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                {formatSectionName(section.section)}
              </h3>
              <span className="text-[11px] tabular-nums text-gray-400">
                {section.changes.length} change{section.changes.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="space-y-2 p-4">
              {section.changes.map((change, i) => (
                <DiffEntryRow key={`${section.section}-${change.field}-${i}`} entry={change} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* No changes */}
      {diff.sections.length === 0 && (
        <div className="rounded-xl border border-emerald-200/60 bg-emerald-50/30 px-6 py-16 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <p className="text-[14px] font-medium text-emerald-900">
              Identical
            </p>
          </div>
          <p className="text-[13px] text-emerald-700">
            These two versions have no differences in their extraction data.
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Icon ──────────────────────────────────────────────────── */

function ChevronLeftIcon() {
  return (
    <svg
      className="h-3.5 w-3.5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 19l-7-7 7-7"
      />
    </svg>
  );
}
