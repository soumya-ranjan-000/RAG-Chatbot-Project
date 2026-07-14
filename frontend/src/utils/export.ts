import type { DocumentChunk } from "../types/api";

export const exportToCSV = (results: DocumentChunk[], filename = "search_results.csv") => {
  // Prepare CSV headers
  const headers = [
    "Document Name",
    "Similarity Score",
    "Chunk Content",
    "Source",
    "Document ID",
    "Chunk Index",
    "Page Label",
    "Page Range",
    "Category",
    "Tags",
    "Ingestion Date",
  ];

  // Prepare CSV rows
  const rows = results.map((chunk) => [
    `"${(chunk.metadata.source || "").replace(/"/g, '""')}"`,
    chunk.similarity.toFixed(4),
    `"${chunk.chunk_content.replace(/"/g, '""').replace(/\n/g, " ")}"`,
    `"${(chunk.metadata.source || "").replace(/"/g, '""')}"`,
    `"${(chunk.metadata.document_id || "").replace(/"/g, '""')}"`,
    chunk.metadata.chunk_index || "",
    `"${(chunk.metadata.page_label || "").replace(/"/g, '""')}"`,
    `"${(chunk.metadata.page_range || "").replace(/"/g, '""')}"`,
    `"${(chunk.metadata.category || "").replace(/"/g, '""')}"`,
    `"${(chunk.metadata.tags?.join("; ") || "").replace(/"/g, '""')}"`,
    chunk.metadata.ingestion_date || "",
  ]);

  // Create CSV content
  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.join(",")),
  ].join("\n");

  // Download file
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  downloadFile(blob, filename);
};

export const exportToJSON = (results: DocumentChunk[], filename = "search_results.json") => {
  const jsonContent = JSON.stringify(results, null, 2);
  const blob = new Blob([jsonContent], {
    type: "application/json;charset=utf-8;",
  });
  downloadFile(blob, filename);
};

const downloadFile = (blob: Blob, filename: string) => {
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
};

export const downloadChunk = (chunk: DocumentChunk, format: "csv" | "json") => {
  const timestamp = new Date().toISOString().split("T")[0];
  const filename = `chunk_${timestamp}.${format}`;

  if (format === "csv") {
    exportToCSV([chunk], filename);
  } else {
    exportToJSON([chunk], filename);
  }
};
