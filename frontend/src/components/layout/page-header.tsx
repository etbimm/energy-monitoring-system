export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex min-h-24 flex-wrap items-center justify-between gap-4 rounded-2xl bg-white px-6 py-5 sm:px-8">
      <div>
        <h1 className="text-4xl font-extrabold uppercase tracking-tight text-[#8d1c1c]">
          {title}
        </h1>
        {description ? (
          <p className="mt-1 text-sm text-stone-500">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}