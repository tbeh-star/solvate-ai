"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  api,
  GoldenRecordDetail,
  GoldenRecordSummary,
  MendelFact,
} from "@/lib/api";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/* ── Badge helpers (matching history/page.tsx) ─────────────── */

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

const DOC_TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  SDS: { bg: "bg-amber-50", text: "text-amber-700" },
  TDS: { bg: "bg-emerald-50", text: "text-emerald-700" },
  CoA: { bg: "bg-cyan-50", text: "text-cyan-700" },
  RPI: { bg: "bg-orange-50", text: "text-orange-700" },
  Brochure: { bg: "bg-gray-50", text: "text-gray-600" },
};

function docTypeBadge(docType: string | null) {
  if (!docType) return null;
  const c = DOC_TYPE_BADGE[docType] ?? { bg: "bg-gray-50", text: "text-gray-500" };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${c.bg} ${c.text}`}
    >
      {docType}
    </span>
  );
}

function completenessColor(v: number): string {
  if (v >= 80) return "bg-emerald-500";
  if (v >= 50) return "bg-amber-500";
  return "bg-red-400";
}

const CONFIDENCE_BADGE: Record<string, { bg: string; text: string }> = {
  high: { bg: "bg-emerald-50", text: "text-emerald-700" },
  medium: { bg: "bg-amber-50", text: "text-amber-700" },
  low: { bg: "bg-red-50", text: "text-red-700" },
};

/* ── WIAW status ──────────────────────────────────────────── */

const WIAW_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  "GREEN LIGHT": { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  ATTENTION: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  "RED FLAG": { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

/* ── Tabs ──────────────────────────────────────────────────── */

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "chemistry", label: "Chemistry" },
  { id: "physical", label: "Physical" },
  { id: "safety", label: "Safety & Compliance" },
] as const;

/* ── MendelFact row component ─────────────────────────────── */

function MendelFactRow({
  label,
  fact,
}: {
  label: string;
  fact: MendelFact | null | undefined;
}) {
  if (!fact || fact.value == null) return null;

  const conf = CONFIDENCE_BADGE[fact.confidence] ?? CONFIDENCE_BADGE.low;
  const displayValue =
    fact.unit ? `${fact.value} ${fact.unit}` : String(fact.value);

  return (
    <tr className="border-b border-gray-100/60 last:border-0">
      <td className="w-[200px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
        {label.toUpperCase()}
      </td>
      <td className="px-5 py-3">
        <span className="text-[13px] font-mono tabular-nums text-gray-700">
          {displayValue}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${conf.bg} ${conf.text}`}
        >
          {fact.confidence}
        </span>
      </td>
      <td className="px-4 py-3 text-[11px] text-gray-400">
        {fact.source_section || "—"}
      </td>
      <td className="px-4 py-3 text-[11px] text-gray-400">
        {fact.test_method || "—"}
      </td>
    </tr>
  );
}

function FactTableHeader() {
  return (
    <thead>
      <tr className="border-b border-gray-100">
        <th className="px-5 py-2.5 text-left text-[10px] font-medium tracking-wide text-gray-400">
          ATTRIBUTE
        </th>
        <th className="px-5 py-2.5 text-left text-[10px] font-medium tracking-wide text-gray-400">
          VALUE
        </th>
        <th className="px-4 py-2.5 text-left text-[10px] font-medium tracking-wide text-gray-400">
          CONFIDENCE
        </th>
        <th className="px-4 py-2.5 text-left text-[10px] font-medium tracking-wide text-gray-400">
          SOURCE
        </th>
        <th className="px-4 py-2.5 text-left text-[10px] font-medium tracking-wide text-gray-400">
          TEST METHOD
        </th>
      </tr>
    </thead>
  );
}

/* ── Simple key-value row ─────────────────────────────────── */

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <tr className="border-b border-gray-100/60 last:border-0">
      <td className="w-[200px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
        {label.toUpperCase()}
      </td>
      <td className="px-5 py-3 text-[13px] text-gray-700" colSpan={4}>
        {value}
      </td>
    </tr>
  );
}

/* ── Tag list component ───────────────────────────────────── */

function TagList({
  title,
  items,
  color = "gray",
}: {
  title: string;
  items: string[] | null | undefined;
  color?: "gray" | "blue" | "red" | "amber" | "emerald";
}) {
  if (!items || items.length === 0) return null;

  const colorMap: Record<string, string> = {
    gray: "bg-gray-100 text-gray-600",
    blue: "bg-blue-50 text-blue-700",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-50 text-amber-700",
    emerald: "bg-emerald-50 text-emerald-700",
  };

  return (
    <div>
      <p className="mb-2 text-[11px] font-medium tracking-wide text-gray-400">
        {title.toUpperCase()}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className={`rounded-full px-3 py-1 text-[12px] ${colorMap[color]}`}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function GoldenRecordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const recordId = parseInt(id, 10);

  const [record, setRecord] = useState<GoldenRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("overview");

  // Version history flyout
  const [versions, setVersions] = useState<GoldenRecordSummary[] | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [showVersions, setShowVersions] = useState(false);

  /* ── Fetch record ──────────────────────────────────────────── */

  const fetchRecord = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGoldenRecordDetail(recordId);
      setRecord(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load record");
    } finally {
      setLoading(false);
    }
  }, [recordId]);

  useEffect(() => {
    if (!isNaN(recordId)) fetchRecord();
  }, [recordId, fetchRecord]);

  /* ── Fetch versions ────────────────────────────────────────── */

  const fetchVersions = useCallback(async () => {
    if (versionsLoading) return;
    setVersionsLoading(true);
    setShowVersions(true);
    try {
      const data = await api.getRecordVersions(recordId);
      setVersions(data);
    } catch {
      setVersions(null);
    } finally {
      setVersionsLoading(false);
    }
  }, [recordId, versionsLoading]);

  /* ── Loading / Error ───────────────────────────────────────── */

  if (loading) {
    return (
      <div>
        <Link
          href="/history"
          className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
        >
          <ChevronLeftIcon />
          History
        </Link>
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[13px] text-gray-400">Loading golden record...</p>
        </div>
      </div>
    );
  }

  if (error || !record) {
    return (
      <div>
        <Link
          href="/history"
          className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
        >
          <ChevronLeftIcon />
          History
        </Link>
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-16 text-center">
          <p className="text-[14px] font-medium text-red-900">
            {error || "Record not found"}
          </p>
          <Link
            href="/history"
            className="mt-3 inline-block text-[13px] font-medium text-red-600 hover:text-red-800"
          >
            Back to History
          </Link>
        </div>
      </div>
    );
  }

  const gr = record.golden_record;

  return (
    <div className="relative">
      {/* Back link */}
      <Link
        href="/history"
        className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
      >
        <ChevronLeftIcon />
        History
      </Link>

      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
            {record.product_name}
          </h1>
          <div className="mt-2 flex items-center gap-2.5 flex-wrap">
            {record.brand && (
              <>
                <span className="text-[12px] text-gray-400">{record.brand}</span>
                <span className="text-gray-200">|</span>
              </>
            )}
            {regionBadge(record.region)}
            {docTypeBadge(record.document_type)}
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-gray-600">
              v{record.version}
            </span>
            {record.is_latest && (
              <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-medium text-emerald-600">
                LATEST
              </span>
            )}
          </div>
        </div>
        <button
          onClick={fetchVersions}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200/80 bg-white px-3 py-2 text-[12px] font-medium text-gray-600 transition-colors hover:bg-gray-50"
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
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Version History
        </button>
      </div>

      {/* KPI Cards */}
      <div className="mb-8 grid grid-cols-4 gap-4">
        {/* Completeness */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            COMPLETENESS
          </p>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-[28px] font-semibold tabular-nums leading-none text-gray-900">
              {record.completeness != null
                ? `${Math.round(record.completeness)}%`
                : "—"}
            </p>
            {record.completeness != null && (
              <div className="flex-1">
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full rounded-full ${completenessColor(record.completeness)}`}
                    style={{ width: `${record.completeness}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Version */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            VERSION
          </p>
          <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            v{record.version}
          </p>
        </div>

        {/* Region */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            REGION
          </p>
          <p className="mt-2 text-[16px] font-semibold text-gray-900">
            {record.region}
          </p>
        </div>

        {/* Document Type */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            DOCUMENT TYPE
          </p>
          <div className="mt-2">
            {record.document_type
              ? docTypeBadge(record.document_type)
              : <span className="text-[13px] text-gray-300">—</span>}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200/60">
        <nav className="-mb-px flex gap-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 px-0.5 py-2.5 text-[13px] font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-gray-900 text-gray-900"
                  : "border-transparent text-gray-400 hover:text-gray-600"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ══════════════════════════════════════════════════════════
          TAB: OVERVIEW
          ══════════════════════════════════════════════════════════ */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          {/* Document Info */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Document Information
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <tbody>
                  <InfoRow label="Document Type" value={gr.document_info?.document_type} />
                  <InfoRow label="Language" value={gr.document_info?.language} />
                  <InfoRow label="Manufacturer" value={gr.document_info?.manufacturer} />
                  <InfoRow label="Brand" value={gr.document_info?.brand} />
                  <InfoRow label="Revision Date" value={gr.document_info?.revision_date} />
                  <InfoRow
                    label="Page Count"
                    value={gr.document_info?.page_count != null ? String(gr.document_info.page_count) : null}
                  />
                </tbody>
              </table>
            </div>
          </section>

          {/* Identity */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Product Identity
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <tbody>
                  <InfoRow label="Product Name" value={gr.identity?.product_name} />
                  <InfoRow label="Product Line" value={gr.identity?.product_line} />
                  <InfoRow label="Wacker SKU" value={gr.identity?.wacker_sku} />
                  <InfoRow label="Product URL" value={gr.identity?.product_url} />
                </tbody>
              </table>
            </div>
            {gr.identity?.grade && (
              <div className="border-t border-gray-100">
                <table className="min-w-full">
                  <FactTableHeader />
                  <tbody>
                    <MendelFactRow label="Grade" fact={gr.identity.grade} />
                  </tbody>
                </table>
              </div>
            )}
            {gr.identity?.material_numbers && gr.identity.material_numbers.length > 0 && (
              <div className="border-t border-gray-100 px-5 py-4">
                <TagList
                  title="Material Numbers"
                  items={gr.identity.material_numbers}
                />
              </div>
            )}
          </section>

          {/* Application */}
          {(gr.application?.main_application ||
            (gr.application?.usage_restrictions && gr.application.usage_restrictions.length > 0) ||
            (gr.application?.packaging_options && gr.application.packaging_options.length > 0)) && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Application
                </h3>
              </div>
              <div className="px-5 py-4 space-y-4">
                {gr.application?.main_application && (
                  <div>
                    <p className="mb-1 text-[11px] font-medium tracking-wide text-gray-400">
                      MAIN APPLICATION
                    </p>
                    <p className="text-[13px] text-gray-700">
                      {gr.application.main_application}
                    </p>
                  </div>
                )}
                <TagList
                  title="Packaging Options"
                  items={gr.application?.packaging_options}
                  color="blue"
                />
                <TagList
                  title="Usage Restrictions"
                  items={gr.application?.usage_restrictions}
                  color="amber"
                />
              </div>
            </section>
          )}

          {/* Missing Attributes & Warnings */}
          {((gr.missing_attributes && gr.missing_attributes.length > 0) ||
            (gr.extraction_warnings && gr.extraction_warnings.length > 0)) && (
            <section className="rounded-xl border border-amber-200/60 bg-amber-50/30">
              <div className="border-b border-amber-100/60 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-amber-900">
                  Extraction Notes
                </h3>
              </div>
              <div className="px-5 py-4 space-y-4">
                <TagList
                  title="Missing Attributes"
                  items={gr.missing_attributes}
                  color="amber"
                />
                {gr.extraction_warnings && gr.extraction_warnings.length > 0 && (
                  <div>
                    <p className="mb-2 text-[11px] font-medium tracking-wide text-amber-600">
                      EXTRACTION WARNINGS
                    </p>
                    <ul className="space-y-1">
                      {gr.extraction_warnings.map((w, i) => (
                        <li key={i} className="text-[12px] text-amber-800">
                          {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Source Files */}
          {record.source_files && record.source_files.length > 0 && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Source Files
                </h3>
              </div>
              <div className="px-5 py-4">
                <div className="flex flex-wrap gap-1.5">
                  {record.source_files.map((f, i) => (
                    <span
                      key={i}
                      className="inline-block max-w-[300px] truncate rounded bg-gray-50 px-2.5 py-1 text-[12px] text-gray-600"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          TAB: CHEMISTRY
          ══════════════════════════════════════════════════════════ */}
      {activeTab === "chemistry" && (
        <div className="space-y-4">
          {/* Chemical Identity Facts */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Chemical Properties
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <FactTableHeader />
                <tbody>
                  <MendelFactRow label="CAS Numbers" fact={gr.chemical?.cas_numbers} />
                  <MendelFactRow label="Purity" fact={gr.chemical?.purity} />
                </tbody>
              </table>
            </div>
          </section>

          {/* Components & Synonyms */}
          {((gr.chemical?.chemical_components && gr.chemical.chemical_components.length > 0) ||
            (gr.chemical?.chemical_synonyms && gr.chemical.chemical_synonyms.length > 0)) && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Components & Synonyms
                </h3>
              </div>
              <div className="px-5 py-4 space-y-4">
                <TagList
                  title="Chemical Components"
                  items={gr.chemical?.chemical_components}
                  color="blue"
                />
                <TagList
                  title="Chemical Synonyms"
                  items={gr.chemical?.chemical_synonyms}
                />
              </div>
            </section>
          )}

          {/* No data fallback */}
          {!gr.chemical?.cas_numbers &&
            !gr.chemical?.purity &&
            (!gr.chemical?.chemical_components || gr.chemical.chemical_components.length === 0) &&
            (!gr.chemical?.chemical_synonyms || gr.chemical.chemical_synonyms.length === 0) && (
              <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
                <p className="text-[13px] text-gray-400">
                  No chemistry data extracted.
                </p>
              </div>
            )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          TAB: PHYSICAL
          ══════════════════════════════════════════════════════════ */}
      {activeTab === "physical" && (
        <div className="space-y-4">
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Physical Properties
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <FactTableHeader />
                <tbody>
                  <MendelFactRow label="Physical Form" fact={gr.physical?.physical_form} />
                  <MendelFactRow label="Density" fact={gr.physical?.density} />
                  <MendelFactRow label="Flash Point" fact={gr.physical?.flash_point} />
                  <MendelFactRow label="Temperature Range" fact={gr.physical?.temperature_range} />
                  <MendelFactRow label="Shelf Life" fact={gr.physical?.shelf_life} />
                  <MendelFactRow label="Cure System" fact={gr.physical?.cure_system} />
                </tbody>
              </table>
            </div>
          </section>

          {/* No data fallback */}
          {!gr.physical?.physical_form &&
            !gr.physical?.density &&
            !gr.physical?.flash_point &&
            !gr.physical?.temperature_range &&
            !gr.physical?.shelf_life &&
            !gr.physical?.cure_system && (
              <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
                <p className="text-[13px] text-gray-400">
                  No physical properties extracted.
                </p>
              </div>
            )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          TAB: SAFETY & COMPLIANCE
          ══════════════════════════════════════════════════════════ */}
      {activeTab === "safety" && (
        <div className="space-y-4">
          {/* WIAW Status */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                WIAW Status
              </h3>
            </div>
            <div className="px-5 py-4">
              {gr.compliance?.wiaw_status ? (
                <div className="flex items-center gap-3">
                  {(() => {
                    const w = WIAW_COLORS[gr.compliance.wiaw_status];
                    return w ? (
                      <span
                        className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-semibold ${w.bg} ${w.text}`}
                      >
                        <span className={`h-2 w-2 rounded-full ${w.dot}`} />
                        {gr.compliance.wiaw_status}
                      </span>
                    ) : (
                      <span className="text-[13px] text-gray-600">
                        {gr.compliance.wiaw_status}
                      </span>
                    );
                  })()}
                  {gr.compliance.sales_advisory && (
                    <span className="text-[13px] text-gray-500">
                      {gr.compliance.sales_advisory}
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-[13px] text-gray-400">
                  No WIAW status assigned
                </span>
              )}
            </div>
          </section>

          {/* UN Number */}
          {gr.safety?.un_number && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Hazard Data
                </h3>
              </div>
              <div className="overflow-hidden">
                <table className="min-w-full">
                  <FactTableHeader />
                  <tbody>
                    <MendelFactRow label="UN Number" fact={gr.safety.un_number} />
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* GHS Statements */}
          <TagList title="GHS Statements" items={gr.safety?.ghs_statements} color="amber" />

          {/* Certifications & Inventories */}
          {((gr.safety?.certifications && gr.safety.certifications.length > 0) ||
            (gr.safety?.global_inventories && gr.safety.global_inventories.length > 0)) && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Certifications & Inventories
                </h3>
              </div>
              <div className="px-5 py-4 space-y-4">
                <TagList
                  title="Certifications"
                  items={gr.safety?.certifications}
                  color="blue"
                />
                <TagList
                  title="Global Inventories"
                  items={gr.safety?.global_inventories}
                  color="emerald"
                />
              </div>
            </section>
          )}

          {/* Restrictions */}
          {((gr.safety?.blocked_countries && gr.safety.blocked_countries.length > 0) ||
            (gr.safety?.blocked_industries && gr.safety.blocked_industries.length > 0)) && (
            <section className="rounded-xl border border-red-200/60 bg-red-50/30">
              <div className="border-b border-red-100/60 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-red-900">
                  Restrictions & Blocks
                </h3>
              </div>
              <div className="px-5 py-4 space-y-4">
                <TagList
                  title="Blocked Countries"
                  items={gr.safety?.blocked_countries}
                  color="red"
                />
                <TagList
                  title="Blocked Industries"
                  items={gr.safety?.blocked_industries}
                  color="red"
                />
              </div>
            </section>
          )}

          {/* Sales Advisory */}
          {gr.compliance?.sales_advisory && (
            <section className="rounded-xl border border-amber-200/60 bg-amber-50/30">
              <div className="border-b border-amber-100/60 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-amber-900">
                  Sales Advisory
                </h3>
              </div>
              <div className="px-5 py-4">
                <p className="text-[13px] text-amber-800">
                  {gr.compliance.sales_advisory}
                </p>
              </div>
            </section>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          VERSION HISTORY FLYOUT
          ══════════════════════════════════════════════════════════ */}
      {showVersions && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/10"
            onClick={() => setShowVersions(false)}
          />
          <div className="fixed right-0 top-0 z-50 flex h-full w-[380px] flex-col border-l border-gray-200 bg-white shadow-lg">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <div>
                <h3 className="text-[14px] font-semibold text-gray-900">
                  Version History
                </h3>
                <p className="mt-0.5 text-[11px] text-gray-400">
                  {record.product_name} &middot; {record.region}
                </p>
              </div>
              <button
                onClick={() => setShowVersions(false)}
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
              {versionsLoading && (
                <p className="py-8 text-center text-[13px] text-gray-400">
                  Loading versions...
                </p>
              )}
              {versions && (
                <div className="space-y-3">
                  {versions.map((v) => {
                    const isCurrent = v.id === recordId;
                    return (
                      <div
                        key={v.id}
                        className={`rounded-lg border p-3.5 transition-colors ${
                          isCurrent
                            ? "border-blue-200 bg-blue-50/30"
                            : v.is_latest
                              ? "border-emerald-200 bg-emerald-50/30"
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
                            {isCurrent && (
                              <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-medium text-blue-700">
                                VIEWING
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
                            <span className="text-[11px] font-medium tabular-nums text-gray-600">
                              {v.completeness != null
                                ? `${Math.round(v.completeness)}%`
                                : "—"}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] text-gray-400">
                              Created
                            </span>
                            <span className="text-[11px] text-gray-500">
                              {formatDate(v.created_at)}
                            </span>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-3 flex items-center gap-2">
                          {!isCurrent && (
                            <Link
                              href={`/history/records/${v.id}`}
                              className="text-[11px] font-medium text-blue-600 hover:text-blue-800"
                              onClick={() => setShowVersions(false)}
                            >
                              View
                            </Link>
                          )}
                          {!isCurrent && (
                            <Link
                              href={`/history/records/${recordId}/diff/${v.id}`}
                              className="text-[11px] font-medium text-violet-600 hover:text-violet-800"
                            >
                              Compare
                            </Link>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {versions && versions.length === 0 && (
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

/* ── Icon components ──────────────────────────────────────── */

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
