"use client";

import { useEffect, useState, useCallback } from "react";
import {
  api,
  ExtractionRunSummary,
  ExtractionRunDetail,
  GoldenRecordSummary,
  PaginatedResponse,
} from "@/lib/api";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function durationLabel(start: string, end: string | null): string {
  if (!end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function completenessColor(v: number): string {
  if (v >= 80) return "bg-emerald-500";
  if (v >= 50) return "bg-amber-500";
  return "bg-red-400";
}

const STATUS_BADGE: Record<string, { bg: string; text: string; dot: string }> =
  {
    completed: {
      bg: "bg-emerald-50",
      text: "text-emerald-700",
      dot: "bg-emerald-500",
    },
    running: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
    failed: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
  };

function statusBadge(status: string) {
  const colors = STATUS_BADGE[status] ?? {
    bg: "bg-gray-50",
    text: "text-gray-600",
    dot: "bg-gray-400",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${colors.bg} ${colors.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/* ── Region badge colors ─────────────────────────────────── */

const REGION_BADGE: Record<string, { bg: string; text: string }> = {
  EU: { bg: "bg-blue-50", text: "text-blue-700" },
  US: { bg: "bg-indigo-50", text: "text-indigo-700" },
  JP: { bg: "bg-violet-50", text: "text-violet-700" },
  CN: { bg: "bg-rose-50", text: "text-rose-700" },
  KR: { bg: "bg-pink-50", text: "text-pink-700" },
  GLOBAL: { bg: "bg-gray-50", text: "text-gray-500" },
};

function regionBadge(region: string) {
  const colors = REGION_BADGE[region] ?? REGION_BADGE.GLOBAL;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${colors.bg} ${colors.text}`}
    >
      {region}
    </span>
  );
}

/* ── Doc type badge ──────────────────────────────────────── */

const DOC_TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  SDS: { bg: "bg-amber-50", text: "text-amber-700" },
  TDS: { bg: "bg-emerald-50", text: "text-emerald-700" },
  CoA: { bg: "bg-cyan-50", text: "text-cyan-700" },
  RPI: { bg: "bg-orange-50", text: "text-orange-700" },
  Brochure: { bg: "bg-gray-50", text: "text-gray-600" },
};

function docTypeBadge(docType: string | null) {
  if (!docType) return <span className="text-[12px] text-gray-300">—</span>;
  const colors = DOC_TYPE_BADGE[docType] ?? {
    bg: "bg-gray-50",
    text: "text-gray-500",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${colors.bg} ${colors.text}`}
    >
      {docType}
    </span>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function HistoryPage() {
  // View state
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // Runs list state
  const [runs, setRuns] = useState<ExtractionRunSummary[]>([]);
  const [runsTotal, setRunsTotal] = useState(0);
  const [runsPage, setRunsPage] = useState(1);
  const [runsPages, setRunsPages] = useState(0);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState<string | null>(null);

  // Run detail state
  const [runDetail, setRunDetail] = useState<ExtractionRunDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Version history flyout
  const [versionHistory, setVersionHistory] = useState<
    GoldenRecordSummary[] | null
  >(null);
  const [versionLoading, setVersionLoading] = useState(false);
  const [versionForRecord, setVersionForRecord] = useState<number | null>(null);

  /* ── Fetch runs list ─────────────────────────────────────── */

  const fetchRuns = useCallback(async (page: number) => {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const data: PaginatedResponse<ExtractionRunSummary> =
        await api.listRuns(page);
      setRuns(data.items);
      setRunsTotal(data.total);
      setRunsPages(data.pages);
    } catch (err) {
      setRunsError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRunId === null) {
      fetchRuns(runsPage);
    }
  }, [selectedRunId, runsPage, fetchRuns]);

  /* ── Fetch run detail ────────────────────────────────────── */

  const fetchDetail = useCallback(async (runId: number) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const data = await api.getRunDetail(runId);
      setRunDetail(data);
    } catch (err) {
      setDetailError(
        err instanceof Error ? err.message : "Failed to load run detail"
      );
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRunId !== null) {
      fetchDetail(selectedRunId);
    }
  }, [selectedRunId, fetchDetail]);

  /* ── Fetch version history ─────────────────────────────── */

  const fetchVersions = useCallback(async (recordId: number) => {
    setVersionLoading(true);
    setVersionForRecord(recordId);
    try {
      const versions = await api.getRecordVersions(recordId);
      setVersionHistory(versions);
    } catch {
      setVersionHistory(null);
    } finally {
      setVersionLoading(false);
    }
  }, []);

  const closeVersionFlyout = () => {
    setVersionHistory(null);
    setVersionForRecord(null);
  };

  /* ── KPI aggregates (from loaded runs) ───────────────────── */

  const totalRecords = runs.reduce(
    (sum, r) => sum + (r.golden_records_count ?? 0),
    0
  );
  const totalPdfs = runs.reduce((sum, r) => sum + (r.pdf_count ?? 0), 0);

  /* ── Render: Run Detail View ─────────────────────────────── */

  if (selectedRunId !== null) {
    return (
      <div className="relative">
        {/* Back button + header */}
        <div className="mb-8">
          <button
            onClick={() => {
              setSelectedRunId(null);
              setRunDetail(null);
              closeVersionFlyout();
            }}
            className="mb-3 flex items-center gap-1.5 text-[13px] font-medium text-gray-400 transition-colors hover:text-gray-600"
          >
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
            Back to Runs
          </button>
          <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
            Run #{selectedRunId}
          </h1>
          {runDetail && (
            <p className="mt-1 text-[13px] text-gray-400">
              {formatDate(runDetail.started_at)} &middot;{" "}
              {formatTime(runDetail.started_at)}
            </p>
          )}
        </div>

        {/* Loading / Error */}
        {detailLoading && (
          <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
            <p className="text-[13px] text-gray-400">Loading run details...</p>
          </div>
        )}

        {detailError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-4 text-center">
            <p className="text-[13px] text-red-600">{detailError}</p>
          </div>
        )}

        {runDetail && !detailLoading && (
          <>
            {/* Run info cards */}
            <div className="mb-8 grid grid-cols-4 gap-4">
              <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
                <p className="text-[11px] font-medium tracking-wide text-gray-400">
                  PDFS PROCESSED
                </p>
                <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
                  {runDetail.pdf_count ?? 0}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
                <p className="text-[11px] font-medium tracking-wide text-gray-400">
                  GOLDEN RECORDS
                </p>
                <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
                  {runDetail.golden_records_count ?? 0}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
                <p className="text-[11px] font-medium tracking-wide text-gray-400">
                  DURATION
                </p>
                <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
                  {durationLabel(runDetail.started_at, runDetail.finished_at)}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
                <p className="text-[11px] font-medium tracking-wide text-gray-400">
                  STATUS
                </p>
                <div className="mt-2">{statusBadge(runDetail.status)}</div>
              </div>
            </div>

            {/* Golden Records table */}
            {runDetail.golden_records.length > 0 ? (
              <div className="overflow-hidden rounded-xl border border-gray-200/80 bg-white">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="px-5 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        PRODUCT
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        BRAND
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        REGION
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        DOC
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        VERSION
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        COMPLETENESS
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                        MISSING
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {runDetail.golden_records.map((gr, i) => (
                      <tr
                        key={gr.id}
                        className={`transition-colors hover:bg-gray-50/50 ${
                          i !== runDetail.golden_records.length - 1
                            ? "border-b border-gray-100/60"
                            : ""
                        }`}
                      >
                        {/* Product name + source files */}
                        <td className="px-5 py-3.5">
                          <span className="text-[13px] font-medium text-gray-900">
                            {gr.product_name}
                          </span>
                          {gr.source_files.length > 0 && (
                            <p className="mt-0.5 max-w-[200px] truncate text-[10px] text-gray-400">
                              {gr.source_files[0]}
                            </p>
                          )}
                        </td>

                        {/* Brand */}
                        <td className="whitespace-nowrap px-4 py-3.5 text-[12px] text-gray-400">
                          {gr.brand ?? "—"}
                        </td>

                        {/* Region */}
                        <td className="whitespace-nowrap px-4 py-3.5">
                          {regionBadge(gr.region)}
                        </td>

                        {/* Doc type */}
                        <td className="whitespace-nowrap px-4 py-3.5">
                          {docTypeBadge(gr.document_type)}
                        </td>

                        {/* Version — clickable to open history flyout */}
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <button
                            onClick={() => fetchVersions(gr.id)}
                            className="inline-flex items-center gap-1 transition-colors hover:opacity-70"
                            title="View version history"
                          >
                            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-gray-600">
                              v{gr.version}
                            </span>
                            {gr.is_latest && (
                              <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-medium text-emerald-600">
                                LATEST
                              </span>
                            )}
                          </button>
                        </td>

                        {/* Completeness */}
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                              <div
                                className={`h-full rounded-full ${completenessColor(gr.completeness ?? 0)}`}
                                style={{
                                  width: `${gr.completeness ?? 0}%`,
                                }}
                              />
                            </div>
                            <span className="text-[11px] tabular-nums text-gray-400">
                              {gr.completeness != null
                                ? `${Math.round(gr.completeness)}%`
                                : "—"}
                            </span>
                          </div>
                        </td>

                        {/* Missing */}
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <span
                            className={`text-[12px] tabular-nums ${
                              (gr.missing_count ?? 0) > 0
                                ? "text-amber-600"
                                : "text-gray-300"
                            }`}
                          >
                            {gr.missing_count ?? 0} attrs
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
                <p className="text-[14px] font-medium text-gray-900">
                  No golden records
                </p>
                <p className="mt-1 text-[13px] text-gray-400">
                  This run didn&apos;t produce any golden records.
                </p>
              </div>
            )}
          </>
        )}

        {/* ── Version History Flyout ────────────────────────── */}
        {(versionHistory || versionLoading) && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40 bg-black/10"
              onClick={closeVersionFlyout}
            />
            {/* Panel */}
            <div className="fixed right-0 top-0 z-50 flex h-full w-[380px] flex-col border-l border-gray-200 bg-white shadow-lg">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
                <div>
                  <h3 className="text-[14px] font-semibold text-gray-900">
                    Version History
                  </h3>
                  {versionHistory && versionHistory.length > 0 && (
                    <p className="mt-0.5 text-[11px] text-gray-400">
                      {versionHistory[0].product_name} &middot;{" "}
                      {versionHistory[0].region}
                    </p>
                  )}
                </div>
                <button
                  onClick={closeVersionFlyout}
                  className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto px-5 py-4">
                {versionLoading && (
                  <p className="py-8 text-center text-[13px] text-gray-400">
                    Loading versions...
                  </p>
                )}
                {versionHistory && (
                  <div className="space-y-3">
                    {versionHistory.map((v) => {
                      const isCurrent = v.id === versionForRecord;
                      return (
                        <div
                          key={v.id}
                          className={`rounded-lg border p-3.5 transition-colors ${
                            v.is_latest
                              ? "border-emerald-200 bg-emerald-50/30"
                              : isCurrent
                                ? "border-blue-200 bg-blue-50/30"
                                : "border-gray-100 bg-white"
                          }`}
                        >
                          {/* Version header */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-gray-700">
                                v{v.version}
                              </span>
                              {v.is_latest && (
                                <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700">
                                  LATEST
                                </span>
                              )}
                              {isCurrent && !v.is_latest && (
                                <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-medium text-blue-700">
                                  CURRENT
                                </span>
                              )}
                            </div>
                            {docTypeBadge(v.document_type)}
                          </div>

                          {/* Details */}
                          <div className="mt-2.5 space-y-1.5">
                            {v.revision_date && (
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] text-gray-400">
                                  Revision Date
                                </span>
                                <span className="text-[11px] font-medium text-gray-600">
                                  {v.revision_date}
                                </span>
                              </div>
                            )}
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] text-gray-400">
                                Completeness
                              </span>
                              <div className="flex items-center gap-1.5">
                                <div className="h-1 w-10 overflow-hidden rounded-full bg-gray-100">
                                  <div
                                    className={`h-full rounded-full ${completenessColor(v.completeness ?? 0)}`}
                                    style={{
                                      width: `${v.completeness ?? 0}%`,
                                    }}
                                  />
                                </div>
                                <span className="text-[11px] tabular-nums font-medium text-gray-600">
                                  {v.completeness != null
                                    ? `${Math.round(v.completeness)}%`
                                    : "—"}
                                </span>
                              </div>
                            </div>
                            {v.doc_language && (
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] text-gray-400">
                                  Language
                                </span>
                                <span className="text-[11px] font-medium text-gray-600">
                                  {v.doc_language.toUpperCase()}
                                </span>
                              </div>
                            )}
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] text-gray-400">
                                Created
                              </span>
                              <span className="text-[11px] text-gray-500">
                                {formatDate(v.created_at)}
                              </span>
                            </div>
                            {v.source_files.length > 0 && (
                              <div className="mt-1">
                                <span className="text-[11px] text-gray-400">
                                  Source
                                </span>
                                <div className="mt-0.5 flex flex-wrap gap-1">
                                  {v.source_files.map((f, fi) => (
                                    <span
                                      key={fi}
                                      className="inline-block max-w-[200px] truncate rounded bg-gray-50 px-1.5 py-0.5 text-[10px] text-gray-500"
                                    >
                                      {f}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                {versionHistory && versionHistory.length === 0 && (
                  <p className="py-8 text-center text-[13px] text-gray-400">
                    No version history found.
                  </p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  /* ── Render: Runs List View (default) ────────────────────── */

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
          History
        </h1>
        <p className="mt-1 text-[13px] text-gray-400">
          Past extraction runs &amp; golden records
        </p>
      </div>

      {/* KPI Cards */}
      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            TOTAL RUNS
          </p>
          <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            {runsTotal}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            TOTAL RECORDS
          </p>
          <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            {totalRecords}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            PDFS PROCESSED
          </p>
          <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            {totalPdfs}
          </p>
        </div>
      </div>

      {/* Loading */}
      {runsLoading && (
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[13px] text-gray-400">Loading extraction runs...</p>
        </div>
      )}

      {/* Error */}
      {runsError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-4 text-center">
          <p className="text-[13px] text-red-600">{runsError}</p>
        </div>
      )}

      {/* Runs Table */}
      {!runsLoading && !runsError && runs.length > 0 && (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200/80 bg-white">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-5 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    RUN
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    DATE
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    PDFS
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    RECORDS
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    DURATION
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                    STATUS
                  </th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, i) => (
                  <tr
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    className={`cursor-pointer transition-colors hover:bg-gray-50/50 ${
                      i !== runs.length - 1
                        ? "border-b border-gray-100/60"
                        : ""
                    }`}
                  >
                    <td className="px-5 py-3.5">
                      <span className="text-[13px] font-medium text-gray-900">
                        #{run.id}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5">
                      <span className="text-[12px] text-gray-600">
                        {formatDate(run.started_at)}
                      </span>
                      <span className="ml-1.5 text-[11px] text-gray-300">
                        {formatTime(run.started_at)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-[12px] tabular-nums text-gray-600">
                      {run.pdf_count ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-[12px] tabular-nums text-gray-600">
                      {run.golden_records_count ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-[12px] tabular-nums text-gray-400">
                      {durationLabel(run.started_at, run.finished_at)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5">
                      {statusBadge(run.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {runsPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                onClick={() => setRunsPage((p) => Math.max(1, p - 1))}
                disabled={runsPage <= 1}
                className="rounded-lg border border-gray-200/80 bg-white px-3 py-1.5 text-[12px] font-medium text-gray-500 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                &larr; Prev
              </button>
              <span className="text-[12px] tabular-nums text-gray-400">
                Page {runsPage} of {runsPages}
              </span>
              <button
                onClick={() =>
                  setRunsPage((p) => Math.min(runsPages, p + 1))
                }
                disabled={runsPage >= runsPages}
                className="rounded-lg border border-gray-200/80 bg-white px-3 py-1.5 text-[12px] font-medium text-gray-500 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next &rarr;
              </button>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!runsLoading && !runsError && runs.length === 0 && (
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[14px] font-medium text-gray-900">
            No extraction runs yet
          </p>
          <p className="mt-1 text-[13px] text-gray-400">
            Upload PDFs on the Extraction page to create your first run.
          </p>
        </div>
      )}
    </div>
  );
}
