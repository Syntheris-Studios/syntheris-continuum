# Shipped model

- Path: `Practical-RIFE/train_log/flownet.pkl`
- Size: 12,186,817 bytes
- SHA-256: `fe854fc8996547c953f732aaa3b78cae76cc0a12833ae856ea0749c4c570d7d8`
- Origin: the existing Practical-RIFE distribution used by the backend. The owner recalls downloading it from the official [Practical-RIFE repository](https://github.com/hzwer/Practical-RIFE).
- License evidence: retained Practical-RIFE MIT LICENSE and the upstream README's explicit MIT statement for linked trained models.
- Status: **documented known limitation, exact upstream release undocumented; owner acceptance required before push and not yet given.**

## Upstream investigation — November 22, 2026

The official [GitHub releases page](https://github.com/hzwer/Practical-RIFE/releases) listed no releases. The [README model table](https://github.com/hzwer/Practical-RIFE#trained-model) links model archives instead. Downloaded the following official Google Drive links into a disposable validation directory and hashed their `train_log/flownet.pkl` ZIP entries without loading or executing their model code:

| Upstream label | Official linked download | Weight bytes | Weight SHA-256 |
|---|---|---:|---|
| v3.8 — 2021.6.17 | [Google Drive](https://drive.google.com/file/d/1O5KfS3KzZCY3imeCr2LCsntLhutKuAqj/view) | 12,186,817 | `d01ec40c0df8005e468cad013e15a6a0ea29d965d1a3a7cd05facb5d9cdb0f48` |
| v3.1 — 2021.5.17 | [Google Drive](https://drive.google.com/file/d/1xn4R3TQyFhtMXN2pa3lRB8cd4E1zckQe/view) | 18,214,714 | `edb1b900827db54c34b56eaa0e8989e8ff2cb4c33564f81bf954afc96fe990ac` |
| 4.26 — 2024.09.21 | [Google Drive](https://drive.google.com/file/d/1gViYvvQrtETBgU1w8axZSsr7YUuw31uy/view) | 24,636,301 | `45c7f74156704769dc9f85cfcaf8552e1e926f9399dcfa3a553dee88fac6f53f` |

None matches. Matching v3.8 file size and local 2021-era HDv3 filenames are insufficient evidence for an exact release. The application's v4.26 detection is also not provenance evidence. This was a targeted investigation, not an exhaustive comparison of every historical mirror. No replacement weight was installed; the shipped hash remains unchanged.

The nested second model set and AppleDouble metadata are excluded from this release.
