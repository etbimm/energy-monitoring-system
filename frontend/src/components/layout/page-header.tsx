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
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-stone-900">
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