# Unilog Challenge Data Profile

Profiled on 2026-08-21. Both supplied artifacts are UTF-8 CSV files, so they have no workbook sheets, merged cells, formula execution, macros, or external-link traversal.

## Official input

- File: `Unihack_ Sample Dataset - Input (1).csv`
- SHA-256: `ed41b50e26c83d0859d563028107fa81a799b5b4b9e3d5743eb846dbd3c7b862`
- Header row: 1
- Data rows: 1,000
- Columns: 6
- Headers, in order: `Mfg_Part_Num`, `Part_Desc`, `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf`
- Blank source cells: none
- Duplicate part number: `AVM6EV` occurs twice with different descriptions
- Manufacturer layout: 959 rows have an unambiguous final parenthesized token; 41 are plain manufacturer strings

Observed placeholders:

- `-- Unbranded --`: 799 E1 brand values
- `-- No Unilog Brand --`: all 1,000 Unilog brand values
- `-- No DIB Brand --`: 755 DIB brand values

The duplicate part number proves that `Mfg_Part_Num` is not globally unique. Stable input identity therefore includes dataset fingerprint, physical source row, and part number.

## Official expected output

- File: `Unihack_ Expected Output - Delivery Format.csv`
- SHA-256: `3304b26f4c3fc3cd5d51b32161cf1900c26e6a7fe238578e53f6f7132df7c580`
- Header row: 1
- Labelled rows: 2
- Columns: exactly 252
- Duplicate headers: none
- Blank columns: many fields are intentionally blank per labelled row; headers themselves are nonblank
- Labelled part numbers: `PDSH4816AF`, `WDTS7024RZ`
- Populated fields: 63 and 71 respectively
- Alignment: both labelled rows uniquely match the input by exact `Mfg_Part_Num`
- Observed classpaths: one
- Observed manufacturers: two
- Observed brands: two

The first 55 fields contain references, identifiers, raw input evidence, manufacturer/brand, classpath, descriptions, features, and common content. They are followed by exactly 50 ordered attribute label/value/UOM triples and 47 commerce, dimension, asset, document, video, origin, and status fields.

Every header is preserved exactly by the canonical code contract and validated against this file. No headers may be renamed, removed, reordered, or supplemented in a submitted delivery record.

## Missing reference data

No separate manufacturer master, LOV master, UOM workbook, Faucets/Fittings workbook, or internal-content-guideline file was supplied in the available challenge package. CatalogIQ does not fabricate these resources. Observed vocabulary from the two labelled rows is useful evidence, not a complete Unilog production taxonomy.

## Safety and parser strategy

Parsers use bounded standard-library CSV handling, UTF-8 with optional BOM, exact header validation, maximum file/row/column/cell limits, and SHA-256 fingerprints. URLs are retained only as field values and never fetched. Input/output rows remain immutable after parsing.
