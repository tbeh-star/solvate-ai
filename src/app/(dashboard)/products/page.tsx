"use client";

import { useState } from "react";
import Link from "next/link";
import { SEED_PRODUCTS, BRANDS } from "@/lib/seed-products";

/* Deterministic "modified" date from product ID (avoids hydration mismatch) */
function getModifiedDate(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash << 5) - hash + id.charCodeAt(i);
    hash |= 0;
  }
  const daysAgo = Math.abs(hash % 90);
  const date = new Date(2024, 0, 15);
  date.setDate(date.getDate() + daysAgo);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ProductsPage() {
  const [brandFilter, setBrandFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filtered = SEED_PRODUCTS.filter((p) => {
    const matchesBrand = brandFilter === "All" || p.brand === brandFilter;
    const matchesSearch =
      searchQuery === "" ||
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase());
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
          {filtered.length} of {SEED_PRODUCTS.length} products
        </p>
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
            placeholder="Search..."
            className="w-full rounded-lg border border-gray-200/80 bg-white py-1.5 pl-9 pr-3 text-[13px] text-gray-700 placeholder:text-gray-300 focus:border-gray-300 focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="overflow-hidden rounded-xl border border-gray-200/80 bg-white">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-5 py-3 text-left text-[11px] font-medium text-gray-400">
                  Name
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-medium text-gray-400">
                  Brand
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-medium text-gray-400">
                  Description
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-medium text-gray-400">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-medium text-gray-400">
                  Modified
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((product, i) => (
                <tr
                  key={product.id}
                  className={`transition-colors hover:bg-gray-50/50 ${
                    i !== filtered.length - 1 ? "border-b border-gray-100/60" : ""
                  }`}
                >
                  <td className="whitespace-nowrap px-5 py-3">
                    <Link
                      href={`/products/${product.id}`}
                      className="text-[13px] font-medium text-gray-900 hover:text-gray-600 transition-colors"
                    >
                      {product.name}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-[12px] text-gray-400">
                    {product.brand}
                  </td>
                  <td className="max-w-xs px-5 py-3 text-[12px] text-gray-400">
                    {product.description.length > 70
                      ? product.description.slice(0, 70) + "..."
                      : product.description}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3">
                    <span className="inline-flex items-center gap-1.5 text-[12px] text-gray-500">
                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Active
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-[12px] tabular-nums text-gray-400">
                    {getModifiedDate(product.id)}
                  </td>
                </tr>
              ))}
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
