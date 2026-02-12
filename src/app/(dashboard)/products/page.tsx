"use client";

import { useState } from "react";
import Link from "next/link";
import { SEED_PRODUCTS, BRANDS } from "@/lib/seed-products";

/* ── KPI helpers ───────────────────────────────────────────── */

const uniqueBrands = new Set(SEED_PRODUCTS.map((p) => p.brand)).size;
const uniqueCategories = new Set(SEED_PRODUCTS.map((p) => p.category)).size;
const avgCompleteness = Math.round(
  SEED_PRODUCTS.reduce((sum, p) => sum + p.completeness, 0) /
    SEED_PRODUCTS.length
);

const STATS = [
  { label: "PRODUCTS", value: String(SEED_PRODUCTS.length), sub: null },
  { label: "BRANDS", value: String(uniqueBrands), sub: null },
  { label: "CATEGORIES", value: String(uniqueCategories), sub: null },
  {
    label: "AVG. COMPLETENESS",
    value: `${avgCompleteness}%`,
    sub: null,
  },
];

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
  // Match on first word for compound forms like "Liquid (colorless, clear...)"
  const firstWord = form.split(/[\s(]/)[0];
  return FORM_BADGE[firstWord] ?? "bg-gray-50 text-gray-500";
}

function formBadgeLabel(form?: string): string {
  if (!form) return "—";
  // Shorten long descriptors for table display
  const firstWord = form.split(/[\s(]/)[0];
  return firstWord;
}

/* ── WIAW status colors ────────────────────────────────────── */

const WIAW_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  GREEN: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
  },
  ATTENTION: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    dot: "bg-amber-500",
  },
  RED: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

/* ── Extraction status ─────────────────────────────────────── */

const EXTRACTION_COLORS: Record<
  string,
  { bg: string; text: string }
> = {
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

/* ── Page ──────────────────────────────────────────────────── */

export default function ProductsPage() {
  const [brandFilter, setBrandFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filtered = SEED_PRODUCTS.filter((p) => {
    const matchesBrand = brandFilter === "All" || p.brand === brandFilter;
    const matchesSearch =
      searchQuery === "" ||
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.cas_numbers ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.category ?? "").toLowerCase().includes(searchQuery.toLowerCase());
    return matchesBrand && matchesSearch;
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
          Products
        </h1>
        <p className="mt-1 text-[13px] text-gray-400">
          Wacker Chemie AG — Full product catalog
        </p>
      </div>

      {/* KPI Cards */}
      <div className="mb-8 grid grid-cols-4 gap-4">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-gray-200/80 bg-white px-5 py-4"
          >
            <p className="text-[11px] font-medium tracking-wide text-gray-400">
              {stat.label}
            </p>
            <p className="mt-1 text-[28px] font-semibold tabular-nums leading-none text-gray-900">
              {stat.value}
            </p>
            {stat.sub && (
              <p className="mt-0.5 text-[12px] text-gray-400">{stat.sub}</p>
            )}
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="mb-5 flex items-center gap-4">
        <select
          value={brandFilter}
          onChange={(e) => setBrandFilter(e.target.value)}
          className="rounded-lg border-0 bg-transparent py-1.5 pr-8 pl-2 text-[13px] font-medium text-gray-400 focus:outline-none focus:ring-0"
        >
          <option value="All">All Brands</option>
          {BRANDS.map((brand) => (
            <option key={brand} value={brand}>
              {brand}
            </option>
          ))}
        </select>

        <div className="relative max-w-xs flex-1">
          <svg
            className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, CAS, category..."
            className="w-full rounded-lg border border-gray-200/80 bg-white py-1.5 pl-9 pr-3 text-[13px] text-gray-700 placeholder:text-gray-300 focus:border-gray-300 focus:outline-none focus:ring-0"
          />
        </div>

        <span className="ml-auto text-[12px] tabular-nums text-gray-400">
          {filtered.length} of {SEED_PRODUCTS.length}
        </span>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
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
                  FORM
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                  WIAW
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                  COMPLETENESS
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                  EXTRACTION
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-medium tracking-wide text-gray-400">
                  DOCS
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((product, i) => {
                const wiaw = product.wiaw_status
                  ? WIAW_COLORS[product.wiaw_status]
                  : null;
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
                  <tr
                    key={product.id}
                    className={`transition-colors hover:bg-gray-50/50 ${
                      i !== filtered.length - 1
                        ? "border-b border-gray-100/60"
                        : ""
                    }`}
                  >
                    {/* Product name + category */}
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/products/${product.id}`}
                        className="text-[13px] font-medium text-gray-900 transition-colors hover:text-gray-600"
                      >
                        {product.name}
                      </Link>
                      <p className="mt-0.5 text-[11px] text-gray-400 truncate max-w-[220px]">
                        {product.category}
                      </p>
                    </td>

                    {/* Brand */}
                    <td className="whitespace-nowrap px-4 py-3.5 text-[12px] text-gray-400">
                      {product.brand}
                    </td>

                    {/* Physical Form Badge */}
                    <td className="whitespace-nowrap px-4 py-3.5">
                      {product.physical_form ? (
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${formBadgeClass(product.physical_form)}`}
                        >
                          {formBadgeLabel(product.physical_form)}
                        </span>
                      ) : (
                        <span className="text-[12px] text-gray-300">—</span>
                      )}
                    </td>

                    {/* WIAW Status */}
                    <td className="whitespace-nowrap px-4 py-3.5">
                      {wiaw ? (
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${wiaw.bg} ${wiaw.text}`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${wiaw.dot}`}
                          />
                          {product.wiaw_status}
                        </span>
                      ) : (
                        <span className="text-[12px] text-gray-300">—</span>
                      )}
                    </td>

                    {/* Completeness */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                          <div
                            className={`h-full rounded-full ${completenessColor(product.completeness)}`}
                            style={{
                              width: `${product.completeness}%`,
                            }}
                          />
                        </div>
                        <span className="text-[11px] tabular-nums text-gray-400">
                          {product.completeness}%
                        </span>
                      </div>
                    </td>

                    {/* Extraction Status */}
                    <td className="whitespace-nowrap px-4 py-3.5">
                      {extraction ? (
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${extraction.bg} ${extraction.text}`}
                        >
                          {extractionLabel(product.extraction_status)}
                        </span>
                      ) : (
                        <span className="text-[12px] text-gray-300">—</span>
                      )}
                    </td>

                    {/* Docs count */}
                    <td className="whitespace-nowrap px-4 py-3.5">
                      <span
                        className={`text-[12px] tabular-nums ${docCount > 0 ? "text-gray-600" : "text-gray-300"}`}
                      >
                        {docCount}/4
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[14px] font-medium text-gray-900">
            No products found
          </p>
          <p className="mt-1 text-[13px] text-gray-400">
            Try adjusting your search or filter.
          </p>
        </div>
      )}
    </div>
  );
}
