"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SEED_PRODUCTS } from "@/lib/seed-products";

/* Deterministic "modified" date from product ID */
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

const TABS = [
  { id: "attributes", label: "Attributes" },
  { id: "properties", label: "Properties" },
  { id: "documents", label: "Documents" },
  { id: "skus", label: "SKUs" },
  { id: "media", label: "Media" },
] as const;

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const product = SEED_PRODUCTS.find((p) => p.id === id);
  const [activeTab, setActiveTab] = useState<string>("attributes");

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
          className="mt-4 inline-block text-[13px] font-medium text-gray-500 hover:text-gray-900 transition-colors"
        >
          Back to Products
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Back link */}
      <Link
        href="/products"
        className="mb-4 inline-flex items-center gap-1 text-[13px] text-gray-400 hover:text-gray-600 transition-colors"
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

      {/* Title area */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-gray-900">
            {product.name}
          </h1>
          <p className="mt-1 text-[13px] text-gray-400">
            {product.brand}
            <span className="mx-1.5">&middot;</span>
            {product.category}
            <span className="mx-1.5">&middot;</span>
            {product.producer}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[12px] tabular-nums text-gray-300">
            {getModifiedDate(product.id)}
          </span>
          <span className="inline-flex items-center gap-1.5 text-[12px] text-gray-500">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Published
          </span>
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

      {/* Tab content */}
      {activeTab === "attributes" ? (
        <div className="space-y-4">
          {/* Identification */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Identification
              </h3>
            </div>
            <div className="px-5 py-4">
              <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
                <Field label="Product Name" value={product.name} />
                <Field label="Brand" value={product.brand} />
                <Field label="Category" value={product.category} />
                <Field label="Producer" value={product.producer} />
                {product.cas_number && (
                  <Field label="CAS Number" value={product.cas_number} />
                )}
                {product.inci_name && (
                  <Field label="INCI Name" value={product.inci_name} />
                )}
                {product.physical_form && (
                  <Field label="Physical Form" value={product.physical_form} />
                )}
                <div className="sm:col-span-2">
                  <dt className="text-[11px] font-medium text-gray-400">
                    Description
                  </dt>
                  <dd className="mt-1 text-[13px] leading-relaxed text-gray-600">
                    {product.description}
                  </dd>
                </div>
              </dl>
            </div>
          </section>

          {/* Applications */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Applications
              </h3>
            </div>
            <div className="px-5 py-4">
              <div className="flex flex-wrap gap-1.5">
                {product.applications.map((app, i) => (
                  <span
                    key={i}
                    className="rounded-md bg-gray-100 px-2.5 py-1 text-[12px] text-gray-600"
                  >
                    {app}
                  </span>
                ))}
              </div>
            </div>
          </section>

          {/* Key Properties */}
          <section className="rounded-xl border border-gray-200/80 bg-white">
            <div className="border-b border-gray-100 px-5 py-3.5">
              <h3 className="text-[13px] font-medium text-gray-900">
                Key Properties
              </h3>
            </div>
            <div className="px-5 py-4">
              <ul className="space-y-2">
                {product.key_properties.map((prop, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 text-[13px] text-gray-600"
                  >
                    <span className="mt-1.5 inline-block h-1 w-1 flex-shrink-0 rounded-full bg-gray-300" />
                    {prop}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Benefits */}
          {product.benefits.length > 0 && (
            <section className="rounded-xl border border-gray-200/80 bg-white">
              <div className="border-b border-gray-100 px-5 py-3.5">
                <h3 className="text-[13px] font-medium text-gray-900">
                  Benefits
                </h3>
              </div>
              <div className="px-5 py-4">
                <ul className="space-y-2">
                  {product.benefits.map((benefit, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2.5 text-[13px] text-gray-600"
                    >
                      <svg
                        className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-gray-300"
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
                      {benefit}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200/80 bg-white px-6 py-16 text-center">
          <p className="text-[13px] text-gray-400">
            {TABS.find((t) => t.id === activeTab)?.label} — coming soon.
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Reusable field component ──────────────────────────────────── */

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-medium text-gray-400">{label}</dt>
      <dd className="mt-0.5 text-[13px] text-gray-700">{value}</dd>
    </div>
  );
}
