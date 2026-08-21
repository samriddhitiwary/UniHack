# Unilog Manufacturer and Brand Resolution

```text
Part_Manuf + E1/Unilog/DIB Brand + Part_Desc + MPN
                         ↓
              Placeholder cleansing
                         ↓
               Organization parsing
                         ↓
             Supplier-likeness analysis
                         ↓
       Brand and manufacturer candidate extraction
                         ↓
   Repeated description / MPN / relationship evidence
                         ↓
               Deterministic conflicts
                         ↓
  Manufacturer result + Brand result + Supplier organization
                         ↓
             Delivery fields + review metrics
```

The build command creates a versioned, hashed JSON artifact. Runtime loads it once into maps keyed by
normalized organization, brand, leading phrase, and MPN prefix. Resolution performs bounded indexed
lookups and no startup rebuild, full scan, network request, crawler, or model call.

Manufacturer and brand are independent. Supplier-brand relations cannot establish ownership,
manufacturer-brand relations are supporting rather than forcing evidence, and `TRADE_NAME` remains
blank unless future supplied evidence explicitly defines its semantics.
