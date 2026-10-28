export function DemoDataNotice({ message }: { message?: string }) {
  return (
    <p
      role="status"
      className="mb-4 rounded-lg border border-green-300 bg-green-100 px-4 py-3 text-sm font-medium text-green-900"
    >
      <span className="font-semibold">Mode demo:</span>{" "}
      {message ??
        "menampilkan data simulasi realistis dari contoh power meter. Data ini bukan pembacaan meter aktual."}
    </p>
  );
}
