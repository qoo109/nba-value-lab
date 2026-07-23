# Historical Gold 5,826 Freeze Manifest Design Rationale v1

The binary `.sqlite.gz` SHA-256 is preserved as execution evidence, while the semantic corpus digest is designed to remain stable across scientifically equivalent rebuilds that differ only in explicitly volatile generation timestamps or metadata.

The design deliberately separates:

```text
binary identity      -> exact downloaded file evidence
semantic identity    -> stable scientific feature corpus
execution receipt    -> workflow, job, Artifact and digest evidence
```

This separation prevents a harmless generation timestamp from changing the scientific identity while still ensuring that any stable feature, schema, metadata, row count, season, completeness, or point-in-time change produces a different corpus digest or fails closed.
