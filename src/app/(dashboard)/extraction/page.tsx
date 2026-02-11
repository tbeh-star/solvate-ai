"use client";

import { useState } from "react";

export default function ExtractionPage() {
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Extract Price Data</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Text input */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-medium">From Text</h2>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste chemical price information here..."
            className="h-48 w-full rounded-md border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            disabled={!input.trim()}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Extract from Text
          </button>
        </div>

        {/* File upload */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-medium">From File</h2>
          <div className="flex h-48 items-center justify-center rounded-md border-2 border-dashed border-gray-300 bg-gray-50">
            <div className="text-center">
              <p className="text-sm text-gray-500">
                {file ? file.name : "Drop a PDF or image here"}
              </p>
              <label className="mt-2 cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                Browse files
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
            </div>
          </div>
          <button
            disabled={!file}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Extract from File
          </button>
        </div>
      </div>

      {/* Extraction results will go here in Phase 2 */}
      <div className="mt-8 rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-lg font-medium">Extracted Data</h2>
        <p className="text-sm text-gray-500">
          Extraction results will appear here. This will be connected to the AI
          pipeline in Phase 2.
        </p>
      </div>
    </div>
  );
}
