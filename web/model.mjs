export const metrics = [
  ["Mass", "Earth masses"], ["Radius", "Earth radii"], ["Orbital period", "days"], ["Minimum mass (M sin i)", "Earth masses"]
];

export function groupSolutions(rows, references, metric) {
  const grouped = new Map();
  for (const [ref, date, preferred, ...fields] of rows) {
    const [label, url] = references[ref];
    const measure = fields[metric];
    const key = JSON.stringify([url, measure]);
    if (!grouped.has(key)) grouped.set(key, {label, url, date, preferred: false, measure, count: 0});
    const item = grouped.get(key);
    item.count++;
    item.preferred ||= Boolean(preferred);
  }
  return [...grouped.values()].sort((a,b) => (a.date || "z").localeCompare(b.date || "z") || a.label.localeCompare(b.label));
}

export function formatNumber(n) {
  return n === 0 ? "0" : Math.abs(n) < 0.00001 ? n.toExponential().replace("e-","e−") : String(n);
}

export function describe(m) {
  if (!m) return "Not reported";
  const [value, plus, minus, flag] = m;
  const prefix = flag === 1 ? "< " : flag === -1 ? "> " : "";
  const suffix = flag === 1 ? " (upper limit)" : flag === -1 ? " (lower limit)" : "";
  const v = prefix + formatNumber(value);
  if (plus === null && minus === null) return v + (suffix || " (uncertainty unreported)");
  if (plus !== null && minus !== null && plus === -minus) return v + " ± " + formatNumber(plus) + suffix;
  return v + " +" + (plus === null ? "?" : formatNumber(plus)) + " / −" + (minus === null ? "?" : formatNumber(Math.abs(minus))) + suffix;
}

export function range(items) {
  const edges = [];
  for (const {measure} of items) {
    if (!measure) continue;
    const [value, plus, minus, flag] = measure;
    edges.push(value);
    if (!flag) edges.push(value + (plus ?? 0), value + (minus ?? 0));
  }
  if (!edges.length) return null;
  const lower = Math.min(...edges), upper = Math.max(...edges);
  const pad = (upper - lower || Math.abs(upper) || 1) * 0.08;
  return [lower - pad, upper + pad];
}
