# balanced40 package

Generated on HPC by `exp-8/pack_balanced40_from_hpc.sh`.

Files:

- `balanced40_data_20260611_110242.tar.gz`: full archive (may exceed GitHub per-file limit)
- `balanced40_data_20260611_110242.tar.gz.sha256`: checksum for full archive
- `balanced40_data_20260611_110242.tar.gz.parts.sha256`: checksums for split parts
- `balanced40_data_20260611_110242.tar.gz.part-000...`: 90MB split parts for git push

Recommended git payload:

```bash
git add exp-8/balanced40_package/README.md \
        exp-8/balanced40_package/balanced40_data_20260611_110242.tar.gz.part-* \
        exp-8/balanced40_package/balanced40_data_20260611_110242.tar.gz.parts.sha256
git commit -m "Add balanced40 data package chunks"
git push
```

On local after pull:

```bash
bash exp-8/unpack_balanced40_local.sh
```
