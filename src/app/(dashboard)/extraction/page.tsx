"use client";

import { useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  api,
  ExtractionResult,
  ExtractionResponse,
  MendelFact,
  BatchExtractionResult,
  BatchExtractionResponse,
  ConfirmExtractionResponse,
} from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────── */

type Step = "input" | "processing" | "results" | "confirmed";

/* ── Helpers ───────────────────────────────────────────────── */

function confidenceColor(v: number | null | undefined): string {
  if (v == null) return "text-gray-400";
  if (v >= 0.8) return "text-emerald-600";
  if (v >= 0.5) return "text-amber-600";
  return "text-red-500";
}

function confidenceLabel(v: number | null | undefined): string {
  if (v == null) return "";
  return `${Math.round(v * 100)}%`;
}

function formatFactValue(fact: MendelFact | null | undefined): string {
  if (!fact) return "—";
  const v = fact.value;
  if (v == null) return "—";
  const unit = fact.unit ? ` ${fact.unit}` : "";
  return `${v}${unit}`;
}

function completenessPercent(result: ExtractionResult): number {
  const missing = result.missing_attributes?.length ?? 0;
  const total = 33;
  return Math.round(((total - missing) / total) * 100);
}

function completenessColor(v: number): string {
  if (v >= 80) return "bg-emerald-500";
  if (v >= 50) return "bg-amber-500";
  return "bg-red-400";
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/* ── Document type badge colors ────────────────────────────── */

const DOC_TYPE_BADGE: Record<string, string> = {
  TDS: "bg-blue-50 text-blue-700",
  SDS: "bg-amber-50 text-amber-700",
  RPI: "bg-violet-50 text-violet-700",
  CoA: "bg-cyan-50 text-cyan-700",
  Brochure: "bg-gray-100 text-gray-600",
  unknown: "bg-gray-100 text-gray-400",
};

/* ── WIAW status badge ─────────────────────────────────────── */

const WIAW_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  "GREEN LIGHT": { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  ATTENTION: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  "RED FLAG": { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

/* ── Physical form badge ───────────────────────────────────── */

const FORM_BADGE: Record<string, string> = {
  Liquid: "bg-emerald-50 text-emerald-700",
  Powder: "bg-amber-50 text-amber-700",
  Gel: "bg-violet-50 text-violet-700",
  Paste: "bg-orange-50 text-orange-700",
  Resin: "bg-blue-50 text-blue-700",
  Granules: "bg-cyan-50 text-cyan-700",
  Pellets: "bg-teal-50 text-teal-700",
};

function formBadgeClass(form?: string | null): string {
  if (!form) return "bg-gray-50 text-gray-500";
  const firstWord = String(form).split(/[\s(]/)[0];
  return FORM_BADGE[firstWord] ?? "bg-gray-50 text-gray-500";
}

/* ── Input step (multi-file) ──────────────────────────────── */

const MAX_FILES = 20;

function InputStep({
  files,
  setFiles,
  onExtract,
  error,
}: {
  files: File[];
  setFiles: (f: File[]) => void;
  onExtract: () => void;
  error: string | null;
}) {
  const [dragOver, setDragOver] = useState(false);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const pdfs = Array.from(incoming).filter((f) =>
        f.name.toLowerCase().endsWith(".pdf"),
      );
      if (pdfs.length === 0) return;
      setFiles(
        [...files, ...pdfs]
          .slice(0, MAX_FILES) // cap at limit
          .filter(
            // dedupe by name+size
            (f, i, arr) =>
              arr.findIndex((x) => x.name === f.name && x.size === f.size) === i,
          ),
      );
    },
    [files, setFiles],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const removeFile = (idx: number) => {
    setFiles(files.filter((_, i) => i !== idx));
  };

  const totalSize = files.reduce((s, f) => s + f.size, 0);

  return (
    <div>
      <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`flex min-h-[140px] items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
            dragOver
              ? "border-gray-400 bg-gray-100/50"
              : "border-gray-200 bg-gray-50/50"
          }`}
        >
          <div className="text-center">
            {files.length > 0 ? (
              <div className="space-y-1">
                <p className="text-[13px] font-medium text-gray-700">
                  {files.length} {files.length === 1 ? "file" : "files"} selected
                  <span className="ml-2 text-[11px] font-normal text-gray-400">
                    ({formatSize(totalSize)})
                  </span>
                </p>
                <p className="text-[11px] text-gray-400">
                  Drop more PDFs to add (max {MAX_FILES})
                </p>
              </div>
            ) : (
              <>
                {/* Upload icon */}
                <svg
                  className="mx-auto mb-2 h-8 w-8 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                  />
                </svg>
                <p className="text-[13px] text-gray-400">
                  Drop PDFs here (TDS, SDS, RPI, CoA, or Brochure)
                </p>
                <label className="mt-1.5 inline-block cursor-pointer text-[13px] font-medium text-gray-900 transition-colors hover:text-gray-600">
                  Browse files
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={(e) => {
                      if (e.target.files) addFiles(e.target.files);
                      e.target.value = "";
                    }}
                    className="hidden"
                  />
                </label>
              </>
            )}
          </div>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="mt-3 max-h-[200px] space-y-1 overflow-y-auto">
            {files.map((f, i) => (
              <div
                key={`${f.name}-${f.size}`}
                className="flex items-center gap-2 rounded-lg px-3 py-1.5 hover:bg-gray-50"
              >
                <svg
                  className="h-4 w-4 shrink-0 text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
                <span className="min-w-0 flex-1 truncate text-[12px] text-gray-700">
                  {f.name}
                </span>
                <span className="shrink-0 text-[11px] text-gray-400">
                  {formatSize(f.size)}
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="shrink-0 text-[12px] text-gray-300 transition-colors hover:text-gray-600"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-3 rounded-lg border border-red-200/60 bg-red-50/50 px-4 py-2.5">
            <p className="text-[12px] text-red-600">{error}</p>
          </div>
        )}

        {/* Extract button */}
        <div className="mt-4 flex items-center justify-between">
          {files.length > 1 && (
            <button
              onClick={() => setFiles([])}
              className="text-[12px] text-gray-400 transition-colors hover:text-gray-600"
            >
              Clear all
            </button>
          )}
          <div className="ml-auto">
            <button
              disabled={files.length === 0}
              onClick={onExtract}
              className="rounded-lg bg-gray-900 px-4 py-2 text-[12px] font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-40"
            >
              Extract{files.length > 1 ? ` ${files.length} Files` : ""}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Processing step ───────────────────────────────────────── */

function ProcessingStep({
  fileCount,
  onCancel,
}: {
  fileCount: number;
  onCancel?: () => void;
}) {
  const multi = fileCount > 1;
  return (
    <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-20 text-center">
      {/* Pulsing dots */}
      <div className="mb-4 flex items-center justify-center gap-1.5">
        <span className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
        <span
          className="h-2 w-2 animate-pulse rounded-full bg-gray-300"
          style={{ animationDelay: "300ms" }}
        />
        <span
          className="h-2 w-2 animate-pulse rounded-full bg-gray-200"
          style={{ animationDelay: "600ms" }}
        />
      </div>
      <p className="text-[13px] text-gray-500">
        {multi
          ? `Extracting ${fileCount} documents...`
          : "Extracting product data..."}
      </p>
      <p className="mt-3 text-[11px] text-gray-300">
        {multi
          ? `This may take ${Math.ceil(fileCount * 0.5)}-${fileCount * 0.5 > 1 ? Math.ceil(fileCount * 0.5) : 1} minutes`
          : "This usually takes 10-30 seconds"}
      </p>
      {onCancel && (
        <button
          onClick={onCancel}
          className="mt-5 rounded-lg px-4 py-1.5 text-[12px] font-medium text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600"
        >
          Cancel
        </button>
      )}
    </div>
  );
}

/* ── Attribute row helper ──────────────────────────────────── */

function AttrRow({
  label,
  value,
  mono,
  confidence,
  source,
}: {
  label: string;
  value: string;
  mono?: boolean;
  confidence?: number | null;
  source?: string | null;
}) {
  const isEmpty = value === "—" || !value;
  return (
    <tr className="border-b border-gray-100/60 last:border-0">
      <td className="w-[180px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
        {label.toUpperCase()}
      </td>
      <td className="px-5 py-3">
        {isEmpty ? (
          <span className="text-[13px] text-gray-300">—</span>
        ) : (
          <span
            className={`text-[13px] text-gray-700 ${mono ? "font-mono tabular-nums" : ""}`}
          >
            {value}
          </span>
        )}
      </td>
      <td className="w-[60px] px-3 py-3 text-right">
        {confidence != null && !isEmpty && (
          <span className={`text-[11px] tabular-nums ${confidenceColor(confidence)}`}>
            {confidenceLabel(confidence)}
          </span>
        )}
      </td>
      <td className="w-[60px] px-3 py-3 text-right">
        {source && !isEmpty && (
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">
            {source}
          </span>
        )}
      </td>
    </tr>
  );
}

/* ── Fact row (MendelFact) ─────────────────────────────────── */

function FactRow({
  label,
  fact,
  mono,
}: {
  label: string;
  fact: MendelFact | null | undefined;
  mono?: boolean;
}) {
  return (
    <AttrRow
      label={label}
      value={formatFactValue(fact)}
      mono={mono}
      confidence={fact?.confidence === "high" ? 0.9 : fact?.confidence === "medium" ? 0.7 : fact?.confidence === "low" ? 0.3 : null}
      source={fact?.source_section || null}
    />
  );
}

/* ── List row (string[]) ───────────────────────────────────── */

function ListRow({
  label,
  items,
  pillColor,
}: {
  label: string;
  items: string[] | null | undefined;
  pillColor?: string;
}) {
  const empty = !items || items.length === 0;
  return (
    <tr className="border-b border-gray-100/60 last:border-0">
      <td className="w-[180px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400 align-top">
        {label.toUpperCase()}
      </td>
      <td className="px-5 py-3" colSpan={3}>
        {empty ? (
          <span className="text-[13px] text-gray-300">—</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {items.map((item, i) => (
              <span
                key={i}
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${pillColor || "bg-gray-100 text-gray-600"}`}
              >
                {item}
              </span>
            ))}
          </div>
        )}
      </td>
    </tr>
  );
}

/* ── Collapsible section ───────────────────────────────────── */

function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="rounded-xl border border-gray-200/80 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between border-b border-gray-100 px-5 py-3.5 text-left"
      >
        <h3 className="text-[13px] font-medium text-gray-900">{title}</h3>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {open && <div className="overflow-hidden">{children}</div>}
    </section>
  );
}

/* ── Single result detail (7 sections) ────────────────────── */

function ResultDetail({ result }: { result: ExtractionResult }) {
  const wiaw = result.compliance.wiaw_status
    ? WIAW_COLORS[result.compliance.wiaw_status]
    : null;

  return (
    <div className="space-y-4">
      {/* 1. Document Info */}
      <Section title="Document Info">
        <table className="min-w-full">
          <tbody>
            <AttrRow label="Document Type" value={result.document_info.document_type} />
            <AttrRow label="Language" value={result.document_info.language} />
            <AttrRow label="Manufacturer" value={result.document_info.manufacturer || "—"} />
            <AttrRow label="Brand" value={result.document_info.brand || "—"} />
            <AttrRow label="Revision Date" value={result.document_info.revision_date || "—"} />
            <AttrRow label="Page Count" value={String(result.document_info.page_count)} mono />
          </tbody>
        </table>
      </Section>

      {/* 2. Identity */}
      <Section title="Identity">
        <table className="min-w-full">
          <tbody>
            <AttrRow label="Product Name" value={result.identity.product_name} />
            <AttrRow label="Product Line" value={result.identity.product_line || "—"} />
            <AttrRow label="Wacker SKU" value={result.identity.wacker_sku || "—"} mono />
            <ListRow label="Material Numbers" items={result.identity.material_numbers} />
            <AttrRow label="Product URL" value={result.identity.product_url || "—"} />
            <FactRow label="Grade" fact={result.identity.grade} />
          </tbody>
        </table>
      </Section>

      {/* 3. Chemical */}
      <Section title="Chemical">
        <table className="min-w-full">
          <tbody>
            <FactRow label="CAS Numbers" fact={result.chemical.cas_numbers} mono />
            <ListRow label="Chemical Components" items={result.chemical.chemical_components} />
            <ListRow label="Chemical Synonyms" items={result.chemical.chemical_synonyms} />
            <FactRow label="Purity" fact={result.chemical.purity} mono />
          </tbody>
        </table>
      </Section>

      {/* 4. Physical */}
      <Section title="Physical Properties">
        <table className="min-w-full">
          <tbody>
            {result.physical.physical_form && (
              <tr className="border-b border-gray-100/60 last:border-0">
                <td className="w-[180px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
                  PHYSICAL FORM
                </td>
                <td className="px-5 py-3" colSpan={3}>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${formBadgeClass(formatFactValue(result.physical.physical_form))}`}>
                    {formatFactValue(result.physical.physical_form)}
                  </span>
                </td>
              </tr>
            )}
            <FactRow label="Density" fact={result.physical.density} mono />
            <FactRow label="Flash Point" fact={result.physical.flash_point} mono />
            <FactRow label="Temperature Range" fact={result.physical.temperature_range} mono />
            <FactRow label="Shelf Life" fact={result.physical.shelf_life} />
            <FactRow label="Cure System" fact={result.physical.cure_system} />
          </tbody>
        </table>
      </Section>

      {/* 5. Application */}
      <Section title="Application">
        <table className="min-w-full">
          <tbody>
            <AttrRow label="Main Application" value={result.application.main_application || "—"} />
            <ListRow label="Usage Restrictions" items={result.application.usage_restrictions} pillColor="bg-amber-50 text-amber-700" />
            <ListRow label="Packaging Options" items={result.application.packaging_options} />
          </tbody>
        </table>
      </Section>

      {/* 6. Safety */}
      <Section title="Safety">
        <table className="min-w-full">
          <tbody>
            <ListRow label="GHS Statements" items={result.safety.ghs_statements} pillColor="bg-red-50 text-red-700" />
            <FactRow label="UN Number" fact={result.safety.un_number} mono />
            <ListRow label="Certifications" items={result.safety.certifications} pillColor="bg-blue-50 text-blue-700" />
            <ListRow label="Global Inventories" items={result.safety.global_inventories} />
            <ListRow label="Blocked Countries" items={result.safety.blocked_countries} pillColor="bg-red-100 text-red-700" />
            <ListRow label="Blocked Industries" items={result.safety.blocked_industries} pillColor="bg-red-100 text-red-700" />
          </tbody>
        </table>
      </Section>

      {/* 7. Compliance */}
      <Section title="Compliance">
        <table className="min-w-full">
          <tbody>
            <tr className="border-b border-gray-100/60 last:border-0">
              <td className="w-[180px] px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
                WIAW STATUS
              </td>
              <td className="px-5 py-3" colSpan={3}>
                {wiaw ? (
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${wiaw.bg} ${wiaw.text}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${wiaw.dot}`} />
                    {result.compliance.wiaw_status}
                  </span>
                ) : (
                  <span className="text-[13px] text-gray-300">—</span>
                )}
              </td>
            </tr>
            <AttrRow label="Sales Advisory" value={result.compliance.sales_advisory || "—"} />
          </tbody>
        </table>
      </Section>

      {/* Warnings */}
      {result.extraction_warnings.length > 0 && (
        <section className="rounded-xl border border-amber-200/60 bg-amber-50/30">
          <div className="border-b border-amber-100/60 px-5 py-3.5">
            <h3 className="text-[13px] font-medium text-amber-900">
              Extraction Warnings
            </h3>
          </div>
          <div className="px-5 py-4">
            <ul className="space-y-1.5">
              {result.extraction_warnings.map((w, i) => (
                <li key={i} className="text-[12px] text-amber-800">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}

/* ── Results step — single file ───────────────────────────── */

function SingleResultsStep({
  result,
  processingTime,
  provider,
  onReset,
  onConfirm,
  isConfirming,
  confirmError,
}: {
  result: ExtractionResult;
  processingTime: number;
  provider: string | null;
  onReset: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
  confirmError: string | null;
}) {
  const completeness = completenessPercent(result);
  const docType = result.document_info.document_type;
  const docBadge = DOC_TYPE_BADGE[docType] || DOC_TYPE_BADGE.unknown;
  const wiaw = result.compliance.wiaw_status
    ? WIAW_COLORS[result.compliance.wiaw_status]
    : null;

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-[16px] font-semibold text-gray-900">
              {result.identity.product_name}
            </h2>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${docBadge}`}>
              {docType}
            </span>
            {wiaw && (
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${wiaw.bg} ${wiaw.text}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${wiaw.dot}`} />
                {result.compliance.wiaw_status}
              </span>
            )}
          </div>
          <div className="mt-1.5 flex items-center gap-2.5 text-[12px] text-gray-400">
            {result.document_info.brand && (
              <span>{result.document_info.brand}</span>
            )}
            {result.document_info.manufacturer && (
              <>
                <span className="text-gray-200">|</span>
                <span>{result.document_info.manufacturer}</span>
              </>
            )}
            <span className="text-gray-200">|</span>
            <span className="tabular-nums">{(processingTime / 1000).toFixed(1)}s</span>
            {provider && (
              <>
                <span className="text-gray-200">|</span>
                <span>{provider}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            disabled={isConfirming}
            className="rounded-lg px-3.5 py-1.5 text-[12px] font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40"
          >
            Start Over
          </button>
          <button
            onClick={onConfirm}
            disabled={isConfirming}
            className="rounded-lg bg-gray-900 px-3.5 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-60"
          >
            {isConfirming ? "Saving..." : "Confirm"}
          </button>
        </div>
      </div>

      {/* Confirm error */}
      {confirmError && (
        <div className="mb-5 rounded-lg border border-red-200/60 bg-red-50/50 px-4 py-2.5">
          <p className="text-[12px] text-red-600">{confirmError}</p>
        </div>
      )}

      {/* Completeness bar */}
      <div className="mb-5 rounded-xl border border-gray-200/80 bg-white px-5 py-4">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            COMPLETENESS
          </p>
          <p className="text-[13px] font-semibold tabular-nums text-gray-900">
            {completeness}%
          </p>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all ${completenessColor(completeness)}`}
            style={{ width: `${completeness}%` }}
          />
        </div>
        {result.missing_attributes.length > 0 && (
          <p className="mt-2 text-[11px] text-gray-400">
            {result.missing_attributes.length} missing:{" "}
            {result.missing_attributes.slice(0, 5).join(", ")}
            {result.missing_attributes.length > 5 && ` +${result.missing_attributes.length - 5} more`}
          </p>
        )}
      </div>

      <ResultDetail result={result} />
    </div>
  );
}

/* ── Results step — batch (multiple files) ────────────────── */

function BatchResultsStep({
  batchResults,
  totalTime,
  provider,
  onReset,
  onConfirm,
  isConfirming,
  confirmError,
}: {
  batchResults: BatchExtractionResult[];
  totalTime: number;
  provider: string | null;
  onReset: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
  confirmError: string | null;
}) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const successCount = batchResults.filter((r) => r.success).length;
  const failCount = batchResults.length - successCount;
  const avgCompleteness =
    successCount > 0
      ? Math.round(
          batchResults
            .filter((r) => r.success && r.result)
            .reduce((sum, r) => sum + completenessPercent(r.result!), 0) / successCount,
        )
      : 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-start justify-between">
        <div>
          <h2 className="text-[16px] font-semibold text-gray-900">
            Batch Extraction Results
          </h2>
          <div className="mt-1.5 flex items-center gap-2.5 text-[12px] text-gray-400">
            <span>
              {successCount} of {batchResults.length} extracted
            </span>
            <span className="text-gray-200">|</span>
            <span>{avgCompleteness}% avg. completeness</span>
            <span className="text-gray-200">|</span>
            <span className="tabular-nums">{(totalTime / 1000).toFixed(1)}s total</span>
            {provider && (
              <>
                <span className="text-gray-200">|</span>
                <span>{provider}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            disabled={isConfirming}
            className="rounded-lg px-3.5 py-1.5 text-[12px] font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40"
          >
            Start Over
          </button>
          <button
            onClick={onConfirm}
            disabled={isConfirming}
            className="rounded-lg bg-gray-900 px-3.5 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-60"
          >
            {isConfirming ? "Saving..." : "Confirm All"}
          </button>
        </div>
      </div>

      {/* Confirm error */}
      {confirmError && (
        <div className="mb-5 rounded-lg border border-red-200/60 bg-red-50/50 px-4 py-2.5">
          <p className="text-[12px] text-red-600">{confirmError}</p>
        </div>
      )}

      {/* Summary bar */}
      <div className="mb-5 rounded-xl border border-gray-200/80 bg-white px-5 py-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-[12px] text-gray-600">
              {successCount} successful
            </span>
          </div>
          {failCount > 0 && (
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-red-400" />
              <span className="text-[12px] text-gray-600">
                {failCount} failed
              </span>
            </div>
          )}
          <div className="ml-auto text-[11px] text-gray-400">
            avg. completeness: <span className="font-semibold text-gray-700">{avgCompleteness}%</span>
          </div>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all ${completenessColor(avgCompleteness)}`}
            style={{ width: `${avgCompleteness}%` }}
          />
        </div>
      </div>

      {/* Result cards */}
      <div className="space-y-3">
        {batchResults.map((item, idx) => {
          const isExpanded = expandedIdx === idx;
          const completeness = item.success && item.result
            ? completenessPercent(item.result)
            : 0;
          const docType = item.result?.document_info?.document_type || "unknown";
          const docBadge = DOC_TYPE_BADGE[docType] || DOC_TYPE_BADGE.unknown;
          const productName = item.result?.identity?.product_name || item.filename;

          return (
            <div key={idx} className="rounded-xl border border-gray-200/80 bg-white">
              {/* Card header — always visible */}
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                className="flex w-full items-center gap-4 px-5 py-4 text-left"
              >
                {/* Status indicator */}
                {item.success ? (
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50">
                    <svg className="h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </span>
                ) : (
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-50">
                    <svg className="h-3.5 w-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </span>
                )}

                {/* Product info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-[13px] font-medium text-gray-900">
                      {productName}
                    </span>
                    {item.success && (
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${docBadge}`}>
                        {docType}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-[11px] text-gray-400">
                    {item.filename}
                    {item.success && (
                      <span className="ml-2 tabular-nums">
                        · {completeness}% · {(item.processing_time_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                    {!item.success && (
                      <span className="ml-2 text-red-400">{item.error}</span>
                    )}
                  </p>
                </div>

                {/* Completeness mini-bar */}
                {item.success && (
                  <div className="hidden w-20 sm:block">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                      <div
                        className={`h-full rounded-full ${completenessColor(completeness)}`}
                        style={{ width: `${completeness}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Chevron */}
                {item.success && (
                  <svg
                    className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </button>

              {/* Expanded detail */}
              {isExpanded && item.success && item.result && (
                <div className="border-t border-gray-100 px-5 py-5">
                  <ResultDetail result={item.result} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Confirmed step ────────────────────────────────────────── */

function ConfirmedStep({
  count,
  onReset,
}: {
  count: number;
  onReset: () => void;
}) {
  const multi = count > 1;
  return (
    <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
      {/* Checkmark */}
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
        <svg
          className="h-6 w-6 text-emerald-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4.5 12.75l6 6 9-13.5"
          />
        </svg>
      </div>
      <h2 className="text-[14px] font-medium text-gray-900">
        {multi ? `${count} extractions confirmed` : "Extraction confirmed"}
      </h2>
      <p className="mt-1 text-[13px] text-gray-400">
        {multi
          ? `Product data from ${count} documents has been extracted successfully.`
          : "Product data has been extracted successfully."}
      </p>
      <div className="mt-6 flex items-center justify-center gap-3">
        <button
          onClick={onReset}
          className="rounded-lg px-3.5 py-1.5 text-[12px] font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700"
        >
          Extract More
        </button>
        <Link
          href="/products"
          className="rounded-lg bg-gray-900 px-3.5 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-gray-800"
        >
          Go to Products
        </Link>
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function ExtractionPage() {
  const [step, setStep] = useState<Step>("input");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Single result (1 file)
  const [singleResult, setSingleResult] = useState<ExtractionResult | null>(null);
  const [processingTime, setProcessingTime] = useState(0);
  const [provider, setProvider] = useState<string | null>(null);

  // Batch results (>1 file)
  const [batchResults, setBatchResults] = useState<BatchExtractionResult[]>([]);
  const [batchTotalTime, setBatchTotalTime] = useState(0);

  // Confirm state
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // Abort controller for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  const isBatch = files.length > 1;

  async function handleExtract() {
    if (files.length === 0) return;
    setStep("processing");
    setError(null);

    // Create abort controller for this extraction
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      if (files.length === 1) {
        // Single file → use /extract-agent
        const data: ExtractionResponse = await api.extractPdf(files[0], controller.signal);
        if (data.success && data.result) {
          setSingleResult(data.result);
          setProcessingTime(data.processing_time_ms);
          setProvider(data.provider || null);
          setStep("results");
        } else {
          setError(data.error || "Extraction failed — no result returned.");
          setStep("input");
        }
      } else {
        // Multiple files → use /extract-batch
        const data: BatchExtractionResponse = await api.extractPdfBatch(files, controller.signal);
        if (data.results && data.results.length > 0) {
          setBatchResults(data.results);
          setBatchTotalTime(data.total_processing_time_ms);
          setProvider(data.provider || null);
          setStep("results");
        } else {
          setError("Batch extraction returned no results.");
          setStep("input");
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") {
        setError("Extraction cancelled.");
      } else {
        setError(e instanceof Error ? e.message : "Extraction failed.");
      }
      setStep("input");
    } finally {
      abortControllerRef.current = null;
    }
  }

  function handleCancel() {
    abortControllerRef.current?.abort();
  }

  async function handleConfirm() {
    setIsConfirming(true);
    setConfirmError(null);

    try {
      // Build the results array for the confirm endpoint
      const resultsToConfirm: BatchExtractionResult[] = isBatch
        ? batchResults
        : singleResult
          ? [{
              filename: files[0]?.name || "document.pdf",
              success: true,
              result: singleResult,
              error: null,
              processing_time_ms: processingTime,
            }]
          : [];

      await api.confirmExtraction({
        results: resultsToConfirm,
        total_processing_time_ms: isBatch ? batchTotalTime : processingTime,
      });

      setStep("confirmed");
    } catch (e) {
      setConfirmError(
        e instanceof Error ? e.message : "Failed to save extraction results.",
      );
    } finally {
      setIsConfirming(false);
    }
  }

  function handleReset() {
    setStep("input");
    setFiles([]);
    setError(null);
    setSingleResult(null);
    setProcessingTime(0);
    setProvider(null);
    setBatchResults([]);
    setBatchTotalTime(0);
    setIsConfirming(false);
    setConfirmError(null);
  }

  const confirmedCount = isBatch
    ? batchResults.filter((r) => r.success).length
    : singleResult ? 1 : 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
          Extraction
        </h1>
        <p className="mt-1 text-[13px] text-gray-400">
          Extract product data from chemical PDFs (TDS, SDS, RPI, CoA, Brochure)
        </p>
      </div>

      {/* Steps */}
      {step === "input" && (
        <InputStep
          files={files}
          setFiles={setFiles}
          onExtract={handleExtract}
          error={error}
        />
      )}

      {step === "processing" && (
        <ProcessingStep fileCount={files.length} onCancel={handleCancel} />
      )}

      {step === "results" && !isBatch && singleResult && (
        <SingleResultsStep
          result={singleResult}
          processingTime={processingTime}
          provider={provider}
          onReset={handleReset}
          onConfirm={handleConfirm}
          isConfirming={isConfirming}
          confirmError={confirmError}
        />
      )}

      {step === "results" && isBatch && batchResults.length > 0 && (
        <BatchResultsStep
          batchResults={batchResults}
          totalTime={batchTotalTime}
          provider={provider}
          onReset={handleReset}
          onConfirm={handleConfirm}
          isConfirming={isConfirming}
          confirmError={confirmError}
        />
      )}

      {step === "confirmed" && (
        <ConfirmedStep
          count={confirmedCount}
          onReset={handleReset}
        />
      )}
    </div>
  );
}
