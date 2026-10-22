# Setup Orhun Language Action

<p align="center">
  <img src="https://raw.githubusercontent.com/orhunlang/orhun/main/assets/logo/orhun_logo_clean_white.png" width="160" alt="Orhun Logo">
</p>

<p align="center">
  <b>Official GitHub Action to set up and configure the Orhun Programming Language toolchain in your CI/CD workflows.</b>
</p>

<p align="center">
  <a href="https://github.com/orhunlang/orhun"><img src="https://img.shields.io/badge/Language-Orhun-blue?style=flat-square" alt="Language"></a>
  <a href="https://github.com/orhunlang/orhun/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/Release-v1.0.0-success?style=flat-square" alt="Latest Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-orange?style=flat-square" alt="License"></a>
  <a href="https://github.com/orhunlang/setup-orhun/actions"><img src="https://img.shields.io/github/actions/workflow/status/orhunlang/setup-orhun/test.yml?branch=main&style=flat-square" alt="Build Status"></a>
</p>

---

## Features

- ⚡ **Zero-Friction Setup:** Downloads, verifies SHA-256 checksums, and configures Orhun in seconds.
- 🌍 **Cross-Platform:** Native support for **Ubuntu Linux** (`linux-x64`), **Microsoft Windows** (`windows-x64`), and **macOS** (`macos-arm64`).
- 🔒 **Cryptographically Verified:** Validates official SHA-256 checksums on all release archives.
- 🛠️ **Full Toolchain:** Ships with the bytecode virtual machine, self-hosted compiler, and standard library.
- 📦 **Custom Version Pinning:** Pin to a specific version (`0.9.0`) or always fetch `latest`.

---

## Quickstart

Add `orhunlang/setup-orhun@v1` to your workflow:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Orhun
        uses: orhunlang/setup-orhun@v1
        with:
          orhun-version: '1.0.0'

      - name: Run tests
        run: orhun calistir main.oh
```

---

## Cross-Platform Matrix Testing

Test your Orhun programs across Linux, Windows, and macOS:

```yaml
name: Cross-Platform Tests

on: [push, pull_request]

jobs:
  matrix-test:
    name: Test on ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Orhun
        uses: orhunlang/setup-orhun@v1
        with:
          orhun-version: '1.0.0'

      - name: Check Version
        run: orhun surum

      - name: Run Script
        run: orhun test.oh
```

---

## Action Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `orhun-version` | Version of Orhun to install (`0.9.0`, `latest`) | No | `0.9.0` |
| `artifact` | Artifact flavor: `compiler` (full toolchain) or `runtime` | No | `compiler` |
| `token` | GitHub token for authenticated API requests | No | `${{ github.token }}` |

---

## Action Outputs

| Output | Description |
|---|---|
| `orhun-version` | The resolved installed Orhun version (e.g. `0.9.0`) |
| `orhun-path` | Absolute filesystem path containing the `orhun` binary |

---

## About Orhun

Orhun is a fast, Turkish-first independent programming language featuring a C++17 bytecode virtual machine, a self-hosted compiler, rich diagnostics (Compiler as a Teacher), and a modern standard library.

- **Repository:** [github.com/orhunlang/orhun](https://github.com/orhunlang/orhun)
- **Organization:** [github.com/orhunlang](https://github.com/orhunlang)

---

## License

This action is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
