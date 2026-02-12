"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SEED_PRODUCTS } from "@/lib/seed-products";

/* ── Physical form badge colors ────────────────────────────── */

const FORM_BADGE: Record<string, string> = {
  Liquid: "bg-emerald-50 text-emerald-700",
  Powder: "bg-amber-50 text-amber-700",
  Gel: "bg-violet-50 text-violet-700",
  Paste: "bg-orange-50 text-orange-700",
  Resin: "bg-blue-50 text-blue-700",
  Granules: "bg-cyan-50 text-cyan-700",
  Pellets: "bg-teal-50 text-teal-700",
};

function formBadgeClass(form?: string): string {
  if (!form) return "bg-gray-50 text-gray-500";
  const firstWord = form.split(/[\s(]/)[0];
  return FORM_BADGE[firstWord] ?? "bg-gray-50 text-gray-500";
}

/* ── WIAW status colors ────────────────────────────────────── */

const WIAW_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  GREEN: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  ATTENTION: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  RED: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

/* ── Extraction status ─────────────────────────────────────── */

const EXTRACTION_COLORS: Record<string, { bg: string; text: string }> = {
  complete: { bg: "bg-emerald-50", text: "text-emerald-700" },
  partial: { bg: "bg-amber-50", text: "text-amber-700" },
  in_progress: { bg: "bg-blue-50", text: "text-blue-700" },
};

function extractionLabel(status?: string): string {
  if (!status) return "—";
  if (status === "in_progress") return "In Progress";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

/* ── Completeness bar ──────────────────────────────────────── */

function completenessColor(v: number): string {
  if (v >= 80) return "bg-emerald-500";
  if (v >= 50) return "bg-amber-500";
  return "bg-red-400";
}

/* ── Tabs ──────────────────────────────────────────────────── */

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "chemistry", label: "Chemistry" },
  { id: "compliance", label: "Compliance" },
  { id: "documents", label: "Documents" },
] as const;

/* ── Page ──────────────────────────────────────────────────── */

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const product = SEED_PRODUCTS.find((p) => p.id === id);
  const [activeTab, setActiveTab] = useState<string>("overview");

  if (!product) {
    return (
      <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
        <p className="text-[14px] font-medium text-gray-900">
          Product not found
        </p>
        <p className="mt-1 text-[13px] text-gray-400">
          The product you are looking for does not exist.
        </p>
        <Link
          href="/products"
          className="mt-4 inline-block text-[13px] font-medium text-gray-500 transition-colors hover:text-gray-900"
        >
          Back to Products
        </Link>
      </div>
    );
  }

  const wiaw = product.wiaw_status ? WIAW_COLORS[product.wiaw_status] : null;
  const extraction = product.extraction_status
    ? EXTRACTION_COLORS[product.extraction_status]
    : null;
  const docCount = [
    product.tds_available,
    product.sds_available,
    product.rpi_available,
    product.coa_available,
  ].filter(Boolean).length;

  return (
    <div>
      {/* Back link */}
      <Link
        href="/products"
        className="mb-6 inline-flex items-center gap-1 text-[13px] text-gray-400 transition-colors hover:text-gray-600"
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
        Products
      </Link>

      {/* Title + meta row */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
            {product.name}
          </h1>
          <div className="mt-2 flex items-center gap-2.5 flex-wrap">
            <span className="text-[12px] text-gray-400">{product.brand}</span>
            <span className="text-gray-200">|</span>
            <span className="text-[12px] text-gray-400">
              {product.producer}
            </span>
            {product.cas_numbers && (
              <>
                <span className="text-gray-200">|</span>
                <span className="font-mono text-[12px] tabular-nums text-gray-400">
                  CAS {product.cas_numbers}
                </span>
              </>
            )}
            {product.product_line && (
              <>
                <span className="text-gray-200">|</span>
                <span className="text-[12px] text-gray-400">
                  {product.product_line}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {wiaw && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${wiaw.bg} ${wiaw.text}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${wiaw.dot}`} />
              {product.wiaw_status}
            </span>
          )}
          {extraction && (
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${extraction.bg} ${extraction.text}`}
            >
              {extractionLabel(product.extraction_status)}
            </span>
          )}
        </div>
      </div>

      {/* Quick info cards */}
      <div className="mb-8 grid grid-cols-4 gap-4">
        {/* Completeness */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            COMPLETENESS
          </p>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-[28px] font-semibold tabular-nums leading-none text-gray-900">
              {product.completeness}%
            </p>
            <div className="flex-1">
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                <div
                  className={`h-full rounded-full ${completenessColor(product.completeness)}`}
                  style={{ width: `${product.completeness}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Physical Form */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            PHYSICAL FORM
          </p>
          <div className="mt-2">
            {product.physical_form ? (
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${formBadgeClass(product.physical_form)}`}
              >
                {product.physical_form}
              </span>
            ) : (
              <span className="text-[13px] text-gray-300">—</span>
            )}
          </div>
        </div>

        {/* Category */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            CATEGORY
          </p>
          <p className="mt-2 text-[13px] font-medium text-gray-900">
            {product.category}
          </p>
        </div>

        {/* Documents */}
        <div className="rounded-xl border border-gray-200/80 bg-white px-5 py-4">
          <p className="text-[11px] font-medium tracking-wide text-gray-400">
            DOCUMENTS
          </p>
          <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
            {docCount}
            <span className="text-[14px] font-normal text-gray-400">/4</span>
          </p>
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

      {/* ════════════════════════════════════════════════════════════
          TAB: OVERVIEW
          ════════════════════════════════════════════════════════════ */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          {/* Description */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Description
              </h3>
            </div>
            <div className="px-5 py-4">
              <p className="text-[13px] leading-relaxed text-gray-600">
                {product.description}
              </p>
            </div>
          </section>

          {/* Identification */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Identification
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <tbody>
                  <IdRow label="Product Name" value={product.name} />
                  <IdRow label="Brand" value={product.brand} />
                  <IdRow label="Product Line" value={product.product_line} />
                  <IdRow label="Category" value={product.category} />
                  <IdRow label="Producer" value={product.producer} />
                  {product.cas_numbers && (
                    <IdRow label="CAS Numbers" value={product.cas_numbers} mono />
                  )}
                  {product.wacker_sku && (
                    <IdRow label="Wacker SKU" value={product.wacker_sku} mono />
                  )}
                  {product.inci_name && (
                    <IdRow label="INCI Name" value={product.inci_name} />
                  )}
                  {product.grade && (
                    <IdRow label="Grade" value={product.grade} />
                  )}
                  {product.main_application && (
                    <IdRow
                      label="Main Application"
                      value={product.main_application}
                    />
                  )}
                  {product.product_url && (
                    <tr className="border-b border-gray-100/60 last:border-0">
                      <td className="px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400">
                        PRODUCT URL
                      </td>
                      <td className="px-5 py-3">
                        <a
                          href={product.product_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[13px] text-blue-600 hover:text-blue-800 underline"
                        >
                          wacker.com →
                        </a>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Physical Properties */}
          {(product.density ||
            product.flash_point ||
            product.temperature_range ||
            product.shelf_life ||
            product.purity ||
            product.cure_system) && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Physical Properties
                </h3>
              </div>
              <div className="overflow-hidden">
                <table className="min-w-full">
                  <tbody>
                    {product.physical_form && (
                      <IdRow
                        label="Physical Form"
                        value={product.physical_form}
                        badge
                      />
                    )}
                    {product.density && (
                      <IdRow label="Density" value={product.density} mono />
                    )}
                    {product.flash_point && (
                      <IdRow
                        label="Flash Point"
                        value={product.flash_point}
                        mono
                      />
                    )}
                    {product.temperature_range && (
                      <IdRow
                        label="Temperature Range"
                        value={product.temperature_range}
                        mono
                      />
                    )}
                    {product.purity && (
                      <IdRow label="Purity" value={product.purity} mono />
                    )}
                    {product.shelf_life && (
                      <IdRow label="Shelf Life" value={product.shelf_life} />
                    )}
                    {product.cure_system && (
                      <IdRow label="Cure System" value={product.cure_system} />
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Packaging & Logistics */}
          {(product.packaging_options ||
            product.material_numbers ||
            product.un_number) && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Packaging & Logistics
                </h3>
              </div>
              <div className="overflow-hidden">
                <table className="min-w-full">
                  <tbody>
                    {product.packaging_options && (
                      <IdRow
                        label="Packaging"
                        value={product.packaging_options}
                      />
                    )}
                    {product.material_numbers && (
                      <IdRow
                        label="Material Numbers"
                        value={product.material_numbers}
                        mono
                      />
                    )}
                    {product.un_number && (
                      <IdRow label="UN Number" value={product.un_number} mono />
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: CHEMISTRY
          ════════════════════════════════════════════════════════════ */}
      {activeTab === "chemistry" && (
        <div className="space-y-4">
          {/* Chemical Identity */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Chemical Identity
              </h3>
            </div>
            <div className="overflow-hidden">
              <table className="min-w-full">
                <tbody>
                  {product.cas_numbers && (
                    <IdRow label="CAS Numbers" value={product.cas_numbers} mono />
                  )}
                  {product.chemical_components && (
                    <IdRow
                      label="Chemical Components"
                      value={product.chemical_components}
                    />
                  )}
                  {product.chemical_synonyms && (
                    <IdRow
                      label="Chemical Synonyms"
                      value={product.chemical_synonyms}
                    />
                  )}
                  {product.inci_name && (
                    <IdRow label="INCI Name" value={product.inci_name} />
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* GHS & Hazard */}
          {product.ghs_statements && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  GHS & Hazard Information
                </h3>
              </div>
              <div className="px-5 py-4">
                <p className="text-[13px] leading-relaxed text-gray-600">
                  {product.ghs_statements}
                </p>
              </div>
            </section>
          )}

          {/* Global Inventories */}
          {product.global_inventories && product.global_inventories.length > 0 && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Global Chemical Inventories
                </h3>
              </div>
              <div className="px-5 py-4">
                <div className="flex flex-wrap gap-1.5">
                  {product.global_inventories.map((inv, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-gray-100 px-3 py-1 text-[12px] text-gray-600"
                    >
                      {inv}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Certifications */}
          {product.certifications && product.certifications.length > 0 && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Certifications
                </h3>
              </div>
              <div className="px-5 py-4">
                <div className="flex flex-wrap gap-1.5">
                  {product.certifications.map((cert, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-blue-50 px-3 py-1 text-[12px] text-blue-700"
                    >
                      {cert}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* No data fallback */}
          {!product.cas_numbers &&
            !product.chemical_components &&
            !product.chemical_synonyms &&
            !product.inci_name &&
            !product.ghs_statements && (
              <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
                <p className="text-[13px] text-gray-400">
                  No chemistry data extracted yet.
                </p>
              </div>
            )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: COMPLIANCE
          ════════════════════════════════════════════════════════════ */}
      {activeTab === "compliance" && (
        <div className="space-y-4">
          {/* WIAW Status Card */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                WIAW Status
              </h3>
            </div>
            <div className="px-5 py-4">
              {wiaw ? (
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-semibold ${wiaw.bg} ${wiaw.text}`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${wiaw.dot}`}
                    />
                    {product.wiaw_status}
                  </span>
                  {product.sales_advisory && (
                    <span className="text-[13px] text-gray-500">
                      {product.sales_advisory}
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

          {/* Restrictions */}
          {(product.blocked_countries && product.blocked_countries.length > 0) ||
          (product.blocked_industries &&
            product.blocked_industries.length > 0) ||
          product.usage_restrictions ? (
            <section className="rounded-xl border border-red-200/60 bg-red-50/30">
              <div className="border-b border-red-100/60 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-red-900">
                  Restrictions & Blocks
                </h3>
              </div>
              <div className="space-y-4 px-5 py-4">
                {product.blocked_countries &&
                  product.blocked_countries.length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium tracking-wide text-red-400 mb-2">
                        BLOCKED COUNTRIES
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {product.blocked_countries.map((country, i) => (
                          <span
                            key={i}
                            className="rounded-full bg-red-100 px-3 py-1 text-[12px] font-medium text-red-700"
                          >
                            {country}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                {product.blocked_industries &&
                  product.blocked_industries.length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium tracking-wide text-red-400 mb-2">
                        BLOCKED INDUSTRIES
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {product.blocked_industries.map((ind, i) => (
                          <span
                            key={i}
                            className="rounded-full bg-red-100 px-3 py-1 text-[12px] font-medium text-red-700"
                          >
                            {ind}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                {product.usage_restrictions && (
                  <div>
                    <p className="text-[11px] font-medium tracking-wide text-red-400 mb-2">
                      USAGE RESTRICTIONS
                    </p>
                    <p className="text-[13px] text-red-800">
                      {product.usage_restrictions}
                    </p>
                  </div>
                )}
              </div>
            </section>
          ) : (
            <section className="rounded-xl border border-emerald-200/60 bg-emerald-50/30">
              <div className="px-5 py-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-[13px] font-medium text-emerald-800">
                    No restrictions or blocks
                  </span>
                </div>
              </div>
            </section>
          )}

          {/* Extraction Status */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Extraction Status
              </h3>
            </div>
            <div className="px-5 py-4">
              {extraction ? (
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-[12px] font-medium ${extraction.bg} ${extraction.text}`}
                >
                  {extractionLabel(product.extraction_status)}
                </span>
              ) : (
                <span className="text-[13px] text-gray-400">
                  Not started
                </span>
              )}
            </div>
          </section>

          {/* Sales Advisory */}
          {product.sales_advisory && (
            <section className="rounded-xl border border-amber-200/60 bg-amber-50/30">
              <div className="border-b border-amber-100/60 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-amber-900">
                  Sales Advisory
                </h3>
              </div>
              <div className="px-5 py-4">
                <p className="text-[13px] text-amber-800">
                  {product.sales_advisory}
                </p>
              </div>
            </section>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: DOCUMENTS
          ════════════════════════════════════════════════════════════ */}
      {activeTab === "documents" && (
        <div className="space-y-4">
          {/* Document availability grid */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Document Availability
              </h3>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-2 gap-3">
                <DocCard
                  label="Technical Data Sheet"
                  abbr="TDS"
                  available={product.tds_available}
                />
                <DocCard
                  label="Safety Data Sheet"
                  abbr="SDS"
                  available={product.sds_available}
                />
                <DocCard
                  label="Regulatory Product Information"
                  abbr="RPI"
                  available={product.rpi_available}
                />
                <DocCard
                  label="Certificate of Analysis"
                  abbr="CoA"
                  available={product.coa_available}
                />
              </div>
            </div>
          </section>

          {/* Wacker Product URL */}
          {product.product_url && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  External Source
                </h3>
              </div>
              <div className="px-5 py-4">
                <a
                  href={product.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-200/80 px-4 py-2.5 text-[13px] font-medium text-gray-700 transition-colors hover:bg-gray-50"
                >
                  <svg
                    className="h-4 w-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                  View on Wacker.com
                </a>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Helper components ──────────────────────────────────────── */

function IdRow({
  label,
  value,
  mono,
  badge,
}: {
  label: string;
  value: string;
  mono?: boolean;
  badge?: boolean;
}) {
  return (
    <tr className="border-b border-gray-100/60 last:border-0">
      <td className="px-5 py-3 text-[11px] font-medium tracking-wide text-gray-400 w-[180px]">
        {label.toUpperCase()}
      </td>
      <td className="px-5 py-3">
        {badge ? (
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${formBadgeClass(value)}`}
          >
            {value}
          </span>
        ) : (
          <span
            className={`text-[13px] text-gray-700 ${mono ? "font-mono tabular-nums" : ""}`}
          >
            {value}
          </span>
        )}
      </td>
    </tr>
  );
}

function DocCard({
  label,
  abbr,
  available,
}: {
  label: string;
  abbr: string;
  available: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
        available
          ? "border-emerald-200/60 bg-emerald-50/30"
          : "border-gray-200/60 bg-gray-50/30"
      }`}
    >
      <div>
        <p
          className={`text-[13px] font-medium ${available ? "text-emerald-900" : "text-gray-400"}`}
        >
          {abbr}
        </p>
        <p
          className={`text-[11px] ${available ? "text-emerald-600" : "text-gray-300"}`}
        >
          {label}
        </p>
      </div>
      {available ? (
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
          <svg
            className="h-3.5 w-3.5 text-emerald-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2.5}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </span>
      ) : (
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
          <svg
            className="h-3.5 w-3.5 text-gray-300"
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
        </span>
      )}
    </div>
  );
}
