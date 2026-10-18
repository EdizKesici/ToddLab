# ToddLab

**The hard indicators of societies.** Comparing nations by what can't lie.

ToddLab collects and normalizes hard social indicators (mortality, health,
fertility, education, crime, demography...) so countries can be compared
on measured outcomes rather than on GDP, opinion surveys or declared
figures. It follows the method of the historian-demographer Emmanuel Todd,
who foresaw the collapse of the USSR in 1976 from a single indicator:
rising infant mortality.

Live: <https://toddlab.vercel.app>

The repository holds two parts:

- **Backend** (Python, repo root): fetches public sources, normalizes them
  and publishes a static data payload in `data/dist/`.
- **Frontend** (Next.js, `frontend/`): a web app that reads that payload.

## Principles

- **Measured, not declared.** Outcome indicators (deaths, measurements,
  test results) over survey data.
- **Canonical vs. witness.** Each indicator has one as-reported canonical
  source; other sources are kept beside it as witnesses, never merged.
- **No invented values.** No interpolation: gaps are displayed, not
  filled. Nothing is derived inside the indicator layer.
- **Everything is traceable.** Every point carries its provider, source
  reference and citation.

## Data

`data/dist/` is committed so the project stays usable offline:

| File | Content |
|------|---------|
| `catalog.json` | the indicators: unit, direction, reliability, sources |
| `entities.json` | countries and territories |
| `indicators/<id>.json` | canonical series and witness series |
| `todd_corpus.json` | the indicators Todd cites across his books |
| `extra_corpus.json` | the metrics outside Todd's books |
| `score/` | the derived score layer |

Sources: Eurostat, OECD, Our World in Data, WHO GHO, WHO/Europe Data
Warehouse, UNESCO Institute for Statistics, World Bank, UN Demographic
Yearbook, ILOSTAT, plus small curated tables kept in `catalog/curated/`
(dated laws, each row cited: Inter-Parliamentary Union, Wikipedia). All are
free and open; credits and licenses are in `docs/licenses.md`.

Each indicator is labelled **official** (figures published by state statistical
services, no model behind them) or **estimate** (anything an international
institution recalculates or models). The flag is `canonical_nature` in the
catalog.

Todd's own metrics are listed in `todd_core.csv`; `extra_core.csv` lists the
relevant metrics outside his books.

### Score layer

On top of the indicators, two composite scores per country-year are
derived and always labelled as derived: **official** (canonical sources
only) and **modelled** (widest-coverage single source per component).
They use a frozen absolute scale and show their coverage with every value.
They are never merged. Each is stored for two metric sets: **Todd only** and
**Todd + extra** (the extra metrics weigh 1 each); the web app has a toggle.
Adding the extra set lowers coverage for countries outside Europe, so fewer
countries are scored. Contract: `docs/score-contract.md`.

## Backend quick start

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python -m src.cli check-config   # validate the configs
python -m src.cli fetch          # download sources -> data/raw (network)
python -m src.cli rebuild        # data/raw -> data/dist (no network)
python -m src.cli all            # fetch, then rebuild
python -m src.cli stats          # counts of the built payload
python scripts/normalize_extra_refs.py   # extra_core.csv -> config/extra_refs.yaml

pytest
```

`data/raw/` and `data/processed/` are regenerable and not committed.

## Frontend quick start

Requires Node.js and npm.

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
npm run build && npm start       # production build
```

The frontend has no copy of the data: it reads `data/dist/` in place, and
picks up a rebuilt payload on the next request without a restart. Set
`TODDLAB_DIST_DIR` to read it from another location.

## Deploy (Vercel, free Hobby plan)

1. Import the GitHub repository in Vercel.
2. Set **Root Directory** to `frontend` and keep "Include source files outside
   of the Root Directory" enabled (the app reads `data/dist/` at the repo root).
3. Keep the default build command (`npm run build`). Nothing else to configure:
   `next.config.ts` detects Vercel and bundles `data/dist/` with the functions.
   Set `NEXT_PUBLIC_SITE_URL` only if you add a custom domain.

The Hobby plan is for non-commercial use. To update the data, push a new
`data/dist/` to `main`: Vercel redeploys.

## Repository layout

```
src/            pipeline, connectors, schema, score layer, CLI
config/         indicators, sources, entities, score definition
catalog/        curated tables
data/dist/      published payload (committed)
docs/           architecture, methodology, ADRs, score contract, Todd's predictions
scripts/        score-bounds freezer, CSV normalizers, fixture builders
tests/          pytest suite
frontend/       Next.js web app
todd_core.csv   Todd's indicators as cited in his books
extra_core.csv  metrics outside Todd's books
```

Further reading: `docs/methodology.md`, `docs/architecture.md`,
`docs/the-measurement-problem.md`, `docs/adr/`.

Todd's predictions: `docs/todd_predictions.md` lists, book by book, what Todd
announced, with his own words checked against the books, what happened since,
and a draft verdict. The website shows a short version at `/predictions`.

## License

MIT, see `LICENSE`. Data remains under each provider's license. ToddLab is
non-commercial, which some sources require (WHO/Europe data: CC BY-NC-SA;
UNESCO UIS: CC BY-SA, ShareAlike applies to the files that carry it).
