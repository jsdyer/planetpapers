"""Publish source-backed comparisons from the same Planetary Systems rows as the chart."""
from bisect import bisect_left
from collections import defaultdict
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, urlencode, urlsplit
from xml.etree import ElementTree as ET

BASE = 'https://coolcode.ca/planetpapers/'
METRICS = (
    ('mass', 'Mass', 'Earth masses'),
    ('radius', 'Radius', 'Earth radii'),
    ('orbital-period', 'Orbital period', 'days'),
    ('minimum-mass', 'Minimum mass (M sin i)', 'Earth masses'),
)
GUIDES = (
    'Compare published estimates of planetary mass in Earth masses.',
    'Compare published measurements of planetary radius in Earth radii.',
    'Compare reported orbital periods in days, the time a planet takes to orbit its host.',
    'Compare the reported product of planetary mass and the sine of orbital inclination. The true mass can be larger.',
)
SOURCE = 'https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html'
PAGE_SIZE = 80
MAX_DISPLAY = 40


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def slugs(names, previous=None):
    """Reserve existing URLs even when names disappear or future names collide."""
    result = dict(previous or {})
    occupied = set(result.values())
    if len(occupied) != len(result) or any(not re.fullmatch(r'[a-z0-9]+(?:-{1,2}[a-z0-9]+)*', slug) for slug in occupied):
        raise ValueError('Invalid reserved planet slug')
    for name in sorted(set(names) - result.keys()):
        plain = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
        base = re.sub('[^a-z0-9]+', '-', plain).strip('-') or 'planet'
        slug = base
        if base in occupied:
            # The double hyphen cannot occur in a base generated above.
            slug = base+'--'+sha256(name.encode()).hexdigest()[:12]
        if slug in occupied:
            raise ValueError('Planet slug collision')
        occupied.add(slug)
        result[name] = slug
    return result


def number(n):
    if n == int(n):
        return str(int(n))
    return str(n).replace('e-0', 'e−').replace('e-', 'e−')


def uncertainty(measure):
    _, plus, minus, _ = measure
    if plus is None and minus is None:
        return 'Unreported'
    if plus is not None and minus is not None and plus == -minus:
        return '± ' + number(plus)
    return '+' + (number(plus) if plus is not None else '?') + ' / −' + (number(abs(minus)) if minus is not None else '?')


def value(measure):
    v, _, _, flag = measure
    return {1: '< ', -1: '> '}.get(flag, '') + number(v)


def kind(flag):
    return {1: 'Upper limit', -1: 'Lower limit', 0: 'Estimate', None: 'Limit flag unavailable'}[flag]


def grouped(rows, refs, field):
    result = {}
    for ref, date, default, *measures in rows:
        measure = measures[field]
        if measure is None:
            continue
        # Match the interactive chart's grouping by source URL and full quoted measurement.
        k = (refs[ref][1], tuple(measure))
        if k not in result:
            result[k] = [ref, date, bool(default), measure]
        else:
            result[k][2] |= bool(default)
    return sorted(result.values(), key=lambda r: (r[1] or 'z', refs[r[0]][0], refs[r[0]][1], value(r[3])))


def comparable(items, refs):
    dated = [r for r in items if r[1] and r[3][3] == 0]
    if len({refs[r[0]][1] for r in dated}) < 3 or len({r[3][0] for r in dated}) < 2:
        return None
    # A repeated value in a later paper is still useful in the table. The lead
    # shows two different published central values from different references.
    for latest in reversed(dated):
        for previous in dated:
            if refs[previous[0]][1] != refs[latest[0]][1] and previous[3][0] != latest[3][0]:
                return sorted((previous, latest), key=lambda r: r[1])
    return None


def explorer(name, field):
    return '?' + urlencode({'planet': name, 'metric': METRICS[field][0]})


def related_planets(name, ref_ids, by_ref, refs):
    found = {}
    for ref in sorted(ref_ids, key=lambda ref: (len(by_ref.get(ref, ())), refs[ref][1])):
        candidates = by_ref.get(ref, [])
        if len(candidates) < 2:
            continue
        position = bisect_left(candidates, name)
        # A Kepler survey can contain thousands of planets. A small window
        # gives deterministic neighbours without producing all possible pairs.
        adjacent = range(max(0, position - 4), min(len(candidates), position + 5))
        for index in sorted(adjacent, key=lambda i: (abs(i - position), candidates[i])):
            other = candidates[index]
            if other != name and other not in found:
                found[other] = ref
            if len(found) == 3:
                return found
    return found


def html_page(path, title, description, heading, body):
    prefix = '../' * len(path.rstrip('/').split('/'))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} · Planet Papers</title><meta name="description" content="{escape(description, quote=True)}">'
            f'<link rel="canonical" href="{BASE}{path}"><link rel="stylesheet" href="{prefix}style.css">'
            f'<script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script></head><body data-tool="planetpapers" class="record">'
            f'<a class="skip" href="#content">Skip to content</a><header><nav>{link(prefix, "Planet Papers")} {link(prefix+"records/", "Browse measurements")}</nav>'
            f'<div class="hero"><h1>{escape(heading)}</h1><p>{escape(description)}</p></div></header>'
            f'<main id="content">{body}<footer>{link(SOURCE, "NASA Planetary Systems column definitions")} · '
            f'{link("https://doi.org/10.26133/NEA12", "Archive citation")} · {link("https://coolcode.ca/skyarchive/", "Sky Archive Explorer")}</footer></main></body></html>')


def profile(name, slug_map, record, refs, by_ref, retrieved):
    fields, pairs, ref_ids = record
    primary = next(iter(pairs))
    metric, label, unit = METRICS[primary]
    left, right = pairs[primary]
    caption = (f'{name} has published {label.lower()} estimates of {value(left[3])} and '
               f'{value(right[3])} {unit}. Compare the dated sources and their quoted uncertainties.')
    body = f'<p class="actions">{link("../../../"+explorer(name, primary), "Open the interactive chart for "+name)}</p>'
    body += '<p class="record-topic">' + ' · '.join(link('#'+METRICS[f][0], METRICS[f][1]) for f in pairs) + '</p>'
    for field, pair in pairs.items():
        token, label, unit = METRICS[field]
        items = fields[field]
        first, later = pair
        def cited(row):
            ref, date, _, m = row
            suffix = uncertainty(m)
            text = escape(value(m)) + (' ' + escape(suffix) if suffix != 'Unreported' else '') + ' ' + escape(unit)
            return f'<strong>{text}</strong> in {link(refs[ref][1], refs[ref][0])} ({escape(date)})'
        total = len({refs[r[0]][1] for r in items})
        body += (f'<section id="{token}"><h2>{escape(label)} in {escape(unit)}</h2>'
                 f'<p>Reported values include {cited(first)} and {cited(later)}.</p>'
                 f'<p class="chart-note">{total} cited sources. Authors can use different observations, models and uncertainty conventions.</p>')
        # Always retain earliest and latest context if an exceptionally long record outgrows this table.
        shown = items if len(items) <= MAX_DISPLAY else items[:MAX_DISPLAY // 2] + items[-MAX_DISPLAY // 2:]
        body += (f'<table><caption>Published {escape(label.lower())} measurements</caption><thead><tr>'
                 f'<th scope="col">Source and publication date</th><th scope="col">Value ({escape(unit)})</th>'
                 '<th scope="col">Quoted uncertainty</th></tr></thead><tbody>')
        for ref, date, default, measure in shown:
            note = kind(measure[3])
            label_text, url = refs[ref]
            body += (f'<tr><th scope="row">{link(url, label_text)}<small>{escape(date or "Date unavailable")}'
                     f'{" · archive default" if default else ""}</small></th><td>{escape(value(measure))}'
                     f'{"<small>"+note+"</small>" if note != "Estimate" else ""}</td><td>{escape(uncertainty(measure))}</td></tr>')
        body += '</tbody></table>'
        if len(shown) < len(items):
            body += f'<p>Showing {len(shown)} of {len(items)} distinct source estimates.</p>'
        body += '<p>'+link('../../../'+explorer(name, field), 'View the '+label.lower()+' chart')+' · '+link('../../measurements/'+token+'/', 'Browse other planets by '+label.lower())+'</p></section>'
    related = related_planets(name, ref_ids, by_ref, refs)
    if related:
        body += '<section><h2>Other planets in the same papers</h2><ul>'
        for other, ref in related.items():
            body += '<li>'+link('../'+slug_map[other]+'/', other)+' · '+link(refs[ref][1], refs[ref][0])+'</li>'
        body += '</ul></section>'
    body += (f'<p class="source-note">NASA Exoplanet Archive snapshot retrieved {escape(retrieved)}. Dates in the tables refer to publications or catalogue releases. '
             f'{link("https://exoplanetarchive.ipac.caltech.edu/overview/"+quote(name, safe=""), "Open the archive entry for "+name)}.</p>')
    path = 'records/planets/'+slug_map[name]+'/'
    return path, html_page(path, name+' published exoplanet measurements', caption, name+' measurements', body)


def publish(stage):
    stage = Path(stage)
    data = stage / 'data'
    catalogue = json.loads((data / 'catalogue.json').read_text())
    info = json.loads((data / 'index.json').read_text())
    names, refs = catalogue['names'], catalogue['references']
    if len(names) != info['planets']:
        raise ValueError('Catalogue coverage does not match the source stamp')
    for label, url in refs:
        if not label or urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname:
            raise ValueError('Invalid source reference')
    reservations = data / "planet-slugs.json"
    slug_map = json.loads(reservations.read_text())
    if set(names) - slug_map.keys() or slugs(names, slug_map) != slug_map:
        raise ValueError("Missing or invalid stable planet slugs")
    reservations.unlink()
    records, by_ref = {}, defaultdict(list)
    for shard in sorted(set(names.values())):
        planets = json.loads((data / f'solutions-{shard}.json').read_text())
        if set(planets) != {name for name in names if names[name] == shard}:
            raise ValueError('Planet-to-shard index differs from the measurements')
        for name, rows in planets.items():
            fields = [grouped(rows, refs, field) for field in range(len(METRICS))]
            pairs = {f: pair for f, items in enumerate(fields) if (pair := comparable(items, refs))}
            if not pairs:
                continue
            ref_ids = {r[0] for f in pairs for r in fields[f] if r[1] and
                       urlsplit(refs[r[0]][1]).hostname in ('ui.adsabs.harvard.edu', 'adsabs.harvard.edu', 'doi.org', 'dx.doi.org')}
            records[name] = (fields, pairs, ref_ids)
            for ref in ref_ids:
                by_ref[ref].append(name)
    if 'TRAPPIST-1 e' not in records:
        raise ValueError('Named example is missing from the comparison records')
    for group in by_ref.values():
        group.sort()
    # The explorer reads this generated lookup from its already requested catalogue.
    catalogue['profiles'] = {name:slug_map[name] for name in sorted(records)}
    (data / 'catalogue.json').write_text(json.dumps(catalogue, ensure_ascii=False, separators=(',', ':')))
    paths = []
    def write(path, content):
        target = stage / path / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        paths.append(path)
    ordered = sorted(records, key=lambda name: (name.casefold(), name))
    for name in ordered:
        write(*profile(name, slug_map, records[name], refs, by_ref, info['retrieved']))
    topics = []
    for field, (token, title, unit) in enumerate(METRICS):
        matches = [name for name in ordered if field in records[name][1]]
        if not matches:
            continue
        topics.append((token, title, len(matches)))
        chunks = [matches[i:i+PAGE_SIZE] for i in range(0, len(matches), PAGE_SIZE)]
        topic_path = 'records/measurements/'+token+'/'
        for i, group in enumerate(chunks):
            path = topic_path if i == 0 else topic_path+f'page-{i+1}/'
            pre = '' if i == 0 else '../'
            pages = [(pre+('./' if j==0 else f'page-{j+1}/'), f'{j+1}') for j in range(len(chunks))]
            body = ('<p>'+link(('../../' if i==0 else '../../../'), 'All measurement types')+'</p>'
                    f'<h2>{escape(group[0])} through {escape(group[-1])}</h2><ul class="planet-list">')
            for name in group:
                body += '<li>'+link(pre+'../../planets/'+slug_map[name]+'/#'+token, name)+'</li>'
            body += '</ul>'
            if len(pages) > 1:
                body += '<nav class="pagination" aria-label="Result pages"><span>Pages</span>'+''.join(
                    f'<strong aria-current="page">{n}</strong>' if j == i else link(url,n) for j,(url,n) in enumerate(pages))+'</nav>'
            desc = f'{GUIDES[field]} {len(matches):,} planets have at least three dated sources and differing estimates.'
            if len(chunks)>1:
                desc += f' Page {i+1} of {len(chunks)}.'
            write(path, html_page(path, title+' comparisons'+(f' · page {i+1}' if i else ''), desc, title+' comparisons', body))
    body = '<h2>Choose a measurement</h2><ul class="topic-list">'
    for token, label, count in topics:
        body += '<li>'+link('measurements/'+token+'/', label)+f'<span>{count:,} planets</span></li>'
    body += '</ul><h2>Start with a planet</h2><ul>'
    for name in ['TRAPPIST-1 e','51 Peg b','55 Cnc e','HD 209458 b']:
        if name in records:
            body += '<li>'+link('planets/'+slug_map[name]+'/', name)+'</li>'
    body += (f'</ul><p>Each profile compares at least three dated sources reporting the same measurement, including two different central values. '
             f'One-sided bounds appear separately. The {link("../", "interactive explorer")} includes all {len(names):,} multi-source planets.</p>'
             f'<p>NASA Exoplanet Archive snapshot retrieved {escape(info["retrieved"])}.</p>')
    path = 'records/'
    write(path, html_page(path, 'Published exoplanet measurements by planet', f'Compare measurements for {len(records):,} exoplanets. See the values, uncertainties and papers behind each comparison.', 'Published exoplanet measurements', body))
    if len(paths) > 50000:
        raise ValueError('Child sitemap exceeds its URL limit')
    xml = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in sorted(paths):
        ET.SubElement(ET.SubElement(xml, 'url'), 'loc').text = BASE+path
    ET.ElementTree(xml).write(stage / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    return len(records), len(paths)
