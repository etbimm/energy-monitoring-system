"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/form";

export type PageSize = 20 | 50;

export function PaginationControls({
  page,
  pageSize,
  itemCount,
  hasNextPage,
  totalItems,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: PageSize;
  itemCount: number;
  hasNextPage: boolean;
  totalItems?: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: PageSize) => void;
}) {
  const firstItem = itemCount === 0 ? 0 : page * pageSize + 1;
  const lastItem = page * pageSize + itemCount;
  const pageCount =
    totalItems === undefined
      ? undefined
      : Math.max(1, Math.ceil(totalItems / pageSize));

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-stone-100 pt-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-stone-500" aria-live="polite">
        {totalItems === undefined
          ? itemCount === 0
            ? "Tidak ada baris"
            : `Menampilkan ${firstItem}-${lastItem}`
          : `Menampilkan ${firstItem}-${lastItem} dari ${totalItems}`}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
        <label className="flex items-center gap-2 text-xs text-stone-600">
          <span>Baris per halaman</span>
          <select
            aria-label="Jumlah baris per halaman"
            value={pageSize}
            onChange={(event) => {
              const nextSize = Number(event.target.value);
              if (nextSize === 20 || nextSize === 50) {
                onPageSizeChange(nextSize);
              }
            }}
            className="rounded-md border border-stone-300 bg-white px-2 py-1.5 text-xs text-stone-700 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </label>
        <Button
          variant="secondary"
          aria-label="Halaman sebelumnya"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-1.5"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden />
          <span className="sr-only">Sebelumnya</span>
        </Button>
        <span className="min-w-16 text-center text-xs text-stone-600">
          Halaman {page + 1}
          {pageCount === undefined ? "" : ` / ${pageCount}`}
        </span>
        <Button
          variant="secondary"
          aria-label="Halaman berikutnya"
          disabled={!hasNextPage}
          onClick={() => onPageChange(page + 1)}
          className="px-2 py-1.5"
        >
          <span className="sr-only">Berikutnya</span>
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
