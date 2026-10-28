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
        className="mb-4 rounded-lg border border-red-300 bg-red-100 px-4 py-3 text-sm font-medium text-red-900"
      >
        {error} Data simulasi digunakan sebagai pengganti. Pastikan backend berjalan
        dan NEXT_PUBLIC_API_URL sudah benar untuk melihat data aktual.
      </div>
    );
  }
  if (loading) {
    return (
      <p className="mb-4 rounded-lg border border-yellow-300 bg-yellow-100 px-4 py-3 text-sm font-medium text-yellow-900">
        Memuat data dari EMS...
      </p>
    );
  }
  return null;
}
