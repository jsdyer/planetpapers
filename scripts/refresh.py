"""Download the NASA Exoplanet Archive's published Planetary Systems solutions."""
from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
from html.parser import HTMLParser
from io import StringIO
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import zlib

from records import slugs

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
PARAMETERS = ("pl_masse", "pl_rade", "pl_orbper", "pl_msinie")
COLUMNS = ["pl_name", "pl_refname", "pl_pubdate", "default_flag", "rowupdate"]
for field in PARAMETERS:
    COLUMNS.extend(field + suffix for suffix in ("", "err1", "err2", "lim"))


class Reference(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.url = ""
        self.fragments = []
        self.feed(markup)
        if urlsplit(self.url).scheme not in ("http", "https") or not urlsplit(self.url).hostname:
            raise ValueError("Missing reference link")

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.url = dict(attrs).get("href", "")

    def handle_data(self, data):
        self.fragments.append(data)


def tap(query):
    url = ENDPOINT + "?" + urlencode({"query": query, "format": "csv", "maxrec": 200000})
    request = Request(url, headers={"User-Agent": "CoolCode-PlanetPapers/1.0 (+https://coolcode.ca/planetpapers/)"})
    with urlopen(request, timeout=180) as response:
        return list(csv.DictReader(StringIO(response.read().decode("utf-8-sig"))))


def measurement(row, field):
    if not row[field]:
        return None
    numbers = [float(row[field + key]) if row[field + key] else None for key in ("", "err1", "err2")]
    flag = int(row[field + "lim"]) if row[field + "lim"] else None
    if not all(math.isfinite(x) for x in numbers if x is not None) or flag not in (-1, 0, 1, None):
        raise ValueError(f"Unrecognized {field} measurement")
    return [*numbers, flag]


def relative_width(measure):
    if not measure:
        return None
    value, plus, minus, flag = measure
    if flag != 0 or value <= 0 or plus is None or minus is None or plus <= 0 or minus >= 0:
        return None
    return (plus - minus) / (2 * value)


def improvement(solutions, position):
    # Ambiguous endpoint dates (multiple values) and repeats of the same reference
    # cannot establish how much two distinct publications tightened a constraint.
    by_date = defaultdict(set)
    for ref, date, default, *fields in solutions:
        width = relative_width(fields[position])
        if width and date:
            by_date[date].add((ref, tuple(fields[position]), width))
    if len(by_date) < 2:
        return None
    first, last = by_date[min(by_date)], by_date[max(by_date)]
    if len(first) == len(last) == 1:
        initial, final = next(iter(first)), next(iter(last))
        if initial[0] != final[0] and initial[2] > final[2]:
            return initial[2] / final[2]
    return None


def compress(path, data):
    encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    path.write_bytes(gzip.compress(encoded, mtime=0))


def prepare(rows, out, previous_slugs=None):
    references, ref_ids, urls, planets = [], {}, {}, defaultdict(list)
    for row in rows:
        markup = row["pl_refname"]
        if markup not in ref_ids:
            ref = Reference(markup)
            if ref.url not in urls:
                urls[ref.url] = len(references)
                references.append(["".join(ref.fragments).strip(), ref.url])
            ref_ids[markup] = urls[ref.url]
        solution = [ref_ids[markup], row["pl_pubdate"].split(" ")[0], int(row["default_flag"]), *[measurement(row, f) for f in PARAMETERS]]
        planets[row["pl_name"]].append(solution)
    if len(planets.get("TRAPPIST-1 e", [])) < 3 or len(planets) < 5000:
        raise ValueError("Incomplete Planetary Systems table")
    multi, summaries, shards = {}, [[] for _ in PARAMETERS], defaultdict(dict)
    for name, solutions in sorted(planets.items()):
        if len({references[row[0]][1] for row in solutions}) < 2:
            continue
        shard = zlib.crc32(name.encode()) % 12
        multi[name] = shard
        ordered = sorted(solutions, key=lambda x: (x[1], x[0]))
        shards[shard][name] = ordered
        for i, ranking in enumerate(summaries):
            factor = improvement(ordered, i)
            if factor:
                ranking.append([name, round(factor, 4)])
    compress(out / "planet-slugs.json.gz", slugs(multi, previous_slugs))
    compress(out / "catalogue.json.gz", dict(names=multi, references=references, rankings=[sorted(r, key=lambda x: -x[1])[:20] for r in summaries]))
    for shard, planets_in_shard in shards.items():
        compress(out / f"solutions-{shard}.json.gz", planets_in_shard)
    info = dict(retrieved=datetime.now(timezone.utc).date().isoformat(), latest_row_update=max(r["rowupdate"] for r in rows),
                count=sum(len(planets[n]) for n in multi), planets=len(multi), source_rows=len(rows))
    (out / "index.json").write_text(json.dumps(info, indent=2) + "\n")
    print(info)


def main():
    expected = int(tap("select count(*) as n from ps")[0]["n"])
    rows = tap("select " + ",".join(COLUMNS) + " from ps")
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} PS rows, received {len(rows)}")
    destination = ROOT / "web/data"
    destination.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=destination) as temporary:
        stage = Path(temporary)
        previous = destination / "planet-slugs.json.gz"
        reserved = json.loads(gzip.decompress(previous.read_bytes())) if previous.exists() else {}
        prepare(rows, stage, reserved)
        for file in stage.iterdir():
            file.replace(destination / file.name)


if __name__ == "__main__":
    main()
