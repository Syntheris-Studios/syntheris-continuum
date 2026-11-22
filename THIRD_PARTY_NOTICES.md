# Third-party notices

The root MIT LICENSE covers Syntheris-owned code. Syntheris branding assets are excluded from it, as specified below. Third-party code, weights and installed dependencies retain their own terms.

Copyright (c) 2025 Syntheris Studios Inc.

## Practical-RIFE

Vendored from [hzwer/Practical-RIFE](https://github.com/hzwer/Practical-RIFE), Copyright (c) 2021 hzwer, MIT. The original [LICENSE](Practical-RIFE/LICENSE) and [README](Practical-RIFE/README.md) are retained unchanged. The upstream README explicitly applies MIT to its linked trained models.

**Documented known limitation awaiting owner acceptance before push:** the shipped MIT weights at `Practical-RIFE/train_log/flownet.pkl` have an undocumented exact upstream release. Size: 12,186,817 bytes. SHA-256: `fe854fc8996547c953f732aaa3b78cae76cc0a12833ae856ea0749c4c570d7d8`. Official linked v3.1, v3.8 and v4.26 downloads did not match this hash. This limitation has not been accepted on the owner's behalf. See [MODEL_PROVENANCE.md](MODEL_PROVENANCE.md) for the investigation. Application v4.26 capability labels do not establish the shipped weight version.

Syntheris modified `inference_video.py` in the earlier repair only to accept fractional `--fps` values. No application behavior changed during publication preparation. Upstream demo images and the notebook remain in the vendored distribution. The upstream FILM research citation is retained; no Google FILM backend, installer or model is shipped. Encoder tuning named `film` is unrelated.

## pytorch_msssim attribution

Two distinct implementations are relevant:

- The installed requirement `pytorch-msssim==1.0.0` is [VainF/pytorch-msssim](https://github.com/VainF/pytorch-msssim/tree/v1.0.0), **MIT**, **Copyright (c) 2019 Gongfan Fang**, verified against its [v1.0.0 LICENSE](https://github.com/VainF/pytorch-msssim/blob/v1.0.0/LICENSE). Its distribution's license notice must be retained when redistributing it.
- The vendored `Practical-RIFE/model/pytorch_msssim/__init__.py` matches the [Practical-RIFE source](https://github.com/hzwer/Practical-RIFE/blob/main/model/pytorch_msssim/__init__.py) after line-ending normalization. Its SSIM/MS-SSIM implementation follows the [Jorge Pessoa implementation](https://github.com/jorge-pessoa/pytorch-msssim), whose [LICENSE.txt](https://github.com/jorge-pessoa/pytorch-msssim/blob/master/LICENSE.txt) declares MIT. Pessoa's README credits [Po-Hsun Su's pytorch-ssim](https://github.com/Po-Hsun-Su/pytorch-ssim), whose [LICENSE.txt](https://github.com/Po-Hsun-Su/pytorch-ssim/blob/master/LICENSE.txt) also declares MIT. Credit: Jorge Pessoa, Po-Hsun Su, and Practical-RIFE contributors. This lineage attribution is based on source comparison and upstream documentation; an exact pre-vendoring revision is not recorded. Neither short upstream license file supplies a copyright year, so none is invented. The Practical-RIFE MIT notice remains intact. This vendored module is not attributed to Gongfan Fang solely because of its similar name.

## FFmpeg and imageio-ffmpeg

FFmpeg is an external executable requirement; this release does not bundle an FFmpeg executable. `imageio-ffmpeg` may install its own binary. [FFmpeg licensing guidance](https://ffmpeg.org/legal.html) describes LGPL and optional GPL components. Inspect each binary's build configuration, accompanying notices and corresponding source before redistributing an installed environment. The root MIT license does not relicense those binaries.

## PyTorch and NVIDIA CUDA

Requirements select CUDA 12.8 PyTorch/torchvision/torchaudio wheels. Their code and bundled libraries carry separate notices, including the [PyTorch license](https://github.com/pytorch/pytorch/blob/v2.7.1/LICENSE) and [NVIDIA CUDA 12.8 EULA](https://docs.nvidia.com/cuda/archive/12.8.0/eula/index.html). Consult terms shipped with the actual binaries. The downloaded runtime is not entirely MIT or entirely open. No CUDA binaries, driver or installed environment are included in this source release.

## Other installed packages and Intel components

Gradio, NumPy, SciPy, OpenCV, MoviePy, Pillow and other requirements retain their package licenses and notices. Requirements are an installation manifest, not a license grant. A complete resolved-wheel/transitive-binary license manifest has not been certified.

Redundant direct MKL and Intel OpenMP requirements were removed in the earlier repair. The tested NumPy Windows wheel uses OpenBLAS, but the PyTorch Windows CUDA wheel includes MKL/OpenMP-related components with separate terms. Preserve actual wheel notices if redistributing binaries. No installed runtime is shipped here.

## Syntheris branding assets

The following four brand assets are excluded from the root MIT LICENSE. They are owned by Syntheris Studios Inc., all rights reserved:

- `Syntheris Continuum Logo Design.png`
- `Syntheris Continuum Brand Guidelines.png`
- `Cyan _C_ Logo with Play Button.png`
- `assets/favicon_continuum.png`

The derived desktop icon, `assets/continuum.ico`, retains the source brand asset's exclusion and ownership. Inclusion in this repository does not grant an MIT license to the branding assets.
