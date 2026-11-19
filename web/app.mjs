import {describe, formatNumber, groupSolutions, metrics, range} from "./model.mjs";

const el = id => document.getElementById(id);
function node(tag, text = "", style = "") {
  const n = document.createElement(tag);
  n.textContent = text;
  if (style) n.className = style;
  return n;
}
function link(label, url, style) {
  const a = node("a", label, style);
  a.href = url;
  return a;
}
async function get(name) {
  const res = await fetch("./data/" + name + ".json");
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}
function plotRow(item, limits) {
  const row = node("div", "", "point-row");
  const ref = node("div", "", "ref");
  ref.append(link(item.label, item.url), node("em", [item.date || "Date unavailable", item.preferred ? "archive default" : "", item.count > 1 ? item.count + " identical rows" : ""].filter(Boolean).join(" · ")));
  const glyph = node("div");
  if (item.measure && limits) {
    const [value, plus, minus, flag] = item.measure;
    const position = x => 100 * (x - limits[0]) / (limits[1] - limits[0]);
    glyph.className = "plot";
    if (!flag && (plus !== null || minus !== null)) {
      const bar = node("span", "", "bar");
      bar.style.left = position(value + (minus ?? 0)) + "%";
      bar.style.width = (position(value + (plus ?? 0)) - position(value + (minus ?? 0))) + "%";
      glyph.append(bar);
    }
    const point = link(flag === 1 ? "←" : flag === -1 ? "→" : "", item.url, flag ? "bound" : "dot");
    point.style.left = position(value) + "%";
    point.setAttribute("aria-label", item.label + ", " + describe(item.measure));
    point.title = describe(item.measure);
    glyph.append(point);
  }
  row.append(ref, glyph, node("span", describe(item.measure), "datum"));
  return row;
}
async function start() {
  const [catalogue, info] = await Promise.all([get("catalogue"), get("index")]);
  const names = Object.keys(catalogue.names), loaded = new Map();
  const planet = el("planet"), metric = el("metric"), search = el("search");
  let revision = 0;

  async function render() {
    const current = ++revision;
    const name = planet.value, field = Number(metric.value);
    el("ranking").replaceChildren(...catalogue.rankings[field].map(([target, factor]) => {
      const b = node("button", target + " · " + Number(factor.toPrecision(3)).toLocaleString("en") + "×");
      b.addEventListener("click", () => { search.value = target; populate(target); el("title").scrollIntoView({block:"nearest"}); });
      return b;
    }));
    el("plot").replaceChildren();
    el("scale").replaceChildren();
    el("archive").hidden = !name;
    if (!name) {
      el("title").textContent = "No matching planet";
      el("summary").textContent = "Try a shorter name or a different host star.";
      return;
    }
    el("title").textContent = name + " · " + metrics[field][0];
    el("summary").textContent = "Loading source measurements…";
    const shard = catalogue.names[name];
    try {
      if (!loaded.has(shard)) loaded.set(shard, get("solutions-" + shard));
      const rows = (await loaded.get(shard))[name];
      if (current !== revision) return;
      const items = groupSolutions(rows, catalogue.references, field), domain = range(items);
      const papers = new Set(items.map(it => it.url)).size;
      el("summary").textContent = rows.length + " published solutions · " + papers + " sources · " + items.filter(it => it.measure).length + " distinct source estimates in " + metrics[field][1];
      el("archive").href = "https://exoplanetarchive.ipac.caltech.edu/overview/" + encodeURIComponent(name);
      const axis = node("span", "", "scale");
      if (domain) axis.append(...domain.map(n => node("span",formatNumber(Number(n.toPrecision(5))))));
      el("scale").replaceChildren(node("span","Source"), axis, node("span", metrics[field][1]));
      el("plot").replaceChildren(...items.map(item => plotRow(item, domain)));
    } catch {
      loaded.delete(shard);
      if (current === revision) el("summary").textContent = "Could not load this group of measurements. Select the planet again to retry.";
    }
  }
  function populate(preferred) {
    const q = search.value.trim().toLowerCase();
    const matches = names.filter(n => n.toLowerCase().includes(q));
    const exact = matches.find(n => n.toLowerCase() === q);
    planet.replaceChildren(...matches.map(n => new Option(n,n)));
    if (matches.includes(preferred)) planet.value = preferred;
    else if (exact) planet.value = exact;
    el("matches").textContent = matches.length.toLocaleString("en") + " planets match";
    render();
  }
  search.addEventListener("input", () => populate(planet.value));
  planet.addEventListener("change", render);
  metric.addEventListener("change", render);
  el("stamp").textContent = "NASA Exoplanet Archive data retrieved " + info.retrieved + " · " + info.count.toLocaleString("en") + " solutions across " + info.planets.toLocaleString("en") + " planets with multiple sources.";
  const selected = new URLSearchParams(location.search).get("planet");
  populate(Object.hasOwn(catalogue.names, selected) ? selected : "TRAPPIST-1 e");
}
start().catch(() => el("summary").textContent = "The planet catalogue could not be loaded. Reload to try again.");
