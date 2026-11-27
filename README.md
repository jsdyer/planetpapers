# Planet Papers

[Compare published exoplanet measurements](https://coolcode.ca/planetpapers/)

<!-- coolcode:guide -->
Select TRAPPIST-1 e and compare the mass estimates from Gillon (2017), Grimm (2018) and Agol (2021). The plot and table preserve each paper’s uncertainties, while the other solutions remain visible when that paper has no mass estimate.
The permanent measurement records compare exoplanets with at least three dated references reporting the same parameter and at least two distinct central estimates. Browse mass, radius, orbital period or minimum mass. Each profile links directly to the individual references and opens the matching planet and parameter in the chart. Other planets are linked when their records cite the same paper.
<!-- /coolcode:guide -->

[Browse published measurements by planet](https://coolcode.ca/planetpapers/records/).

## Coverage and sources

The NASA Exoplanet Archive's [Planetary Systems table (PS)](https://exoplanetarchive.ipac.caltech.edu/docs/API_TD_columns.html) retains separate literature solutions for each planet. This tool downloads the public [TAP table](https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+count%28%2A%29+as+n+from+ps&format=json) and indexes planets with two or more distinct reference URLs. Every included solution remains accessible. Some sources are archive catalogues or follow-up records. Links follow the Archive’s original references.

Choose planet mass, radius, orbital period, or minimum mass. Minimum mass uses the separate M sin i column. A paper’s failure to report a field appears as a missing value. Upper and lower limits keep their direction, and a missing error bar remains unknown. A reference can supply multiple solutions. The table combines identical values and error bounds from that same reference, and shows how many source rows they represent. Different values from the same source remain visible. Published values can depend on different models, observations or assumptions.

The precision list uses the earliest and latest distinct publication dates with positive values and a reported two-sided, nonzero uncertainty for the same field. Relative half-width is (upper error + absolute lower error) / (2 × value). The factor divides the earlier relative half-width by the later one. Tied endpoint dates with conflicting estimates are excluded. The list shows the 20 largest decreases per parameter. A narrower reported uncertainty does not establish greater accuracy. Papers can use different confidence conventions.

This research uses the NASA Exoplanet Archive, operated by the California Institute of Technology under contract with NASA under the Exoplanet Exploration Program. Cite [the Archive](https://doi.org/10.26133/NEA12) and the linked source papers. Search, selection and plotting run on the device. Source links open the cited provider.

## Build and refresh

Python 3.12 and Node build and test the app without application dependencies. `python3 scripts/refresh.py` retrieves the full PS row count and the measurement columns, verifies completeness and prepares a compressed source snapshot. The refresh is scheduled for 08:37 UTC on the fifth day of each month and also supports manual runs. Each successful build regenerates the permanent profiles, paginated directories and sitemap from the same snapshot. The offline build `python3 scripts/build.py` expands the checked-in snapshot into static, on-demand planet groups. Retrieval dates record a successful source fetch. Publication dates come from the individual PS solution. Failed scheduled fetches leave the previous deployment available.

Run `node --test tests/*.test.mjs`, `python3 -m unittest discover -s tests -v`, and `python3 scripts/build.py`. Run `python3 tests/browser_smoke.py` with Playwright Chromium installed, or set `CHROMIUM_PATH` to a compatible Chromium binary.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
