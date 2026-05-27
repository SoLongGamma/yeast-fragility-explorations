# Data infrastructure

This folder is the **intake layer** between real-world fermentation
data (from papers, lab notebooks, or user uploads) and the calibration /
recommender pipeline.

The design philosophy is one sentence: *we don't ship data, we ship a
shape that data can fit into.*

## Why this layer exists

Real yeast fermentation data comes in dozens of incompatible shapes:
- One lab reports DCW, another OD600, another wet weight.
- One paper has a step-wise feed table, another a feed-rate plot, another
  just a final yield.
- Licenses range from "do whatever" (CC0) to "do not redistribute"
  (all rights reserved).

Without a single intake format, every new dataset means rewriting the
calibration code. With this layer, every new dataset means writing one
JSON file that fits the schema.

## Folder structure

```
data/
├── README.md                  ← you are here
├── schema/
│   └── fermentation_run.schema.json   ← the universal shape
├── sources/
│   ├── sources.yaml           ← catalog of all datasets + licenses
│   ├── kccm12638_heme_pH55.json
│   └── ...                    ← one JSON per fermentation run
└── extraction/
    └── loader.py              ← load / validate / convert to ABM input
```

## Three things this layer enforces

### 1. License-aware loading

Every dataset declares its license in `source.license`. Downstream code
(calibration, recommender) reads this and gates access:

- `CC-BY*` data can be used and redistributed with attribution.
- `All rights reserved` data can be used locally for research but not
  bundled into a redistributable product.
- `User-supplied` data is private to that user — never persisted by the
  tool, never shown to anyone else.

This is enforced at the loader, not just by convention.

### 2. Provenance tracking

Every dataset records `extracted_by` and `extraction_date_iso`. If a
calibrated parameter looks weird six months from now, you can trace
which dataset contributed and how it was digitized.

### 3. ABM input conversion

`loader.to_abm_protocol(run)` produces a DataFrame the v0.1 ABM can
consume directly. The conversion logic (interpolation, unit handling,
feed-rate to glucose-availability) lives in one place so every dataset
goes through the same pipeline.

## Adding a new dataset

1. Read `schema/fermentation_run.schema.json`.
2. Build a `.json` file matching the schema for your run.
3. Add an entry to `sources/sources.yaml`.
4. Load it once with `loader.load_run()` + `loader.validate_run()` to
   confirm it passes.
5. Commit JSON and YAML in the same git commit.

## What we deliberately do NOT do

- We do not bundle copyrighted PDFs in this repository.
- We do not auto-scrape paper supplementary data without checking
  licenses.
- We do not normalize away dataset-level information that might matter
  later (we keep the original units, the original quality flags, the
  raw `notes`).

## Current contents

See `sources/sources.yaml` for the live catalog.

As of repository creation, this folder contains one example dataset
digitized from a heme-production paper (KCCM 12638 strain, three pH
conditions in progress). It is included to **demonstrate the schema**;
quantitative use requires confirming the digitization against the
original figures.
