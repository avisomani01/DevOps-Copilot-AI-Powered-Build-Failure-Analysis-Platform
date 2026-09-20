type Props = { value: string };
export function StatusBadge({ value }: Props) {
  const style = value === "COMPLETED" || value === "ANALYZED" ? "bg-emerald-100 text-emerald-700" : value === "PENDING" || value === "UPLOADED" || value === "ANALYZING" ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${style}`}>{value.replaceAll("_", " ")}</span>;
}
