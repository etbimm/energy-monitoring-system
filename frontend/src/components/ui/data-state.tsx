export function DataState({
  loading,
  error,
}: {
  loading: boolean;
  error: string | null;
}) {
  if (error) {
    return (
      <div
        role="alert"
        className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
      >
        {error} Pastikan backend berjalan dan NEXT_PUBLIC_API_URL sudah benar.
      </div>
    );
  }
  if (loading) {
    return (
      <p className="mb-4 rounded-lg border border-stone-200 bg-white px-4 py-3 text-sm text-stone-600">
        Memuat data dari EMS...
      </p>
    );
  }
  return null;
}
