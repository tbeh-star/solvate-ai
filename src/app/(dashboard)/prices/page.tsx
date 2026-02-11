"use client";

import { useEffect, useState } from "react";
import { useUser } from "@auth0/nextjs-auth0";
import { api, InternalPrice, PaginatedResponse } from "@/lib/api";

export default function PricesPage() {
  const { user } = useUser();
  const [prices, setPrices] = useState<PaginatedResponse<InternalPrice> | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPrices() {
      if (!user) return;
      try {
        setLoading(true);
        // In production, get the token from the Auth0 session
        const res = await fetch("/api/auth/token");
        const { accessToken } = await res.json();
        const data = await api.listPrices(accessToken);
        setPrices(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load prices");
      } finally {
        setLoading(false);
      }
    }
    fetchPrices();
  }, [user]);

  if (loading) {
    return <div className="text-gray-500">Loading prices...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Prices</h1>
        <span className="text-sm text-gray-500">
          {prices?.total ?? 0} total records
        </span>
      </div>

      {prices && prices.items.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Product
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Specs
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Delivery
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Location
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {prices.items.map((price) => (
                <tr key={price.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {price.product_raw}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {price.price_currency === "USD" ? "$" : price.price_currency}
                    {price.price_value.toFixed(2)}/{price.price_unit}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {price.specs || "-"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {price.delivery_term || "-"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {price.location || "-"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {price.source_format}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {new Date(price.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-lg border bg-white p-12 text-center">
          <h3 className="text-lg font-medium text-gray-900">No prices yet</h3>
          <p className="mt-2 text-sm text-gray-500">
            Go to the Extract tab to start extracting price data from text,
            PDFs, or images.
          </p>
        </div>
      )}
    </div>
  );
}
