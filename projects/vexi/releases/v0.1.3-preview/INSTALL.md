# Vexi v0.1.3 Public Preview - installation

This preview is intended for Windows field testing on additional PCs.

## Clean install / update

1. Download `Vexi_v0.1.3_Public_Preview.zip` from this folder.
2. Extract the ZIP completely. Do not run the installer from inside the archive.
3. Open `Vexi_v0.1.3_Public_Preview/Core`.
4. Run `INSTALL_VEXI.bat`.
5. Accept the Windows UAC prompt.
6. Continue in the separate Administrator PowerShell window until it reports:

```text
VEXI v0.1.3 PUBLIC PREVIEW INSTALL COMPLETE
Core runtime: READY
```

The bootstrap supports both a clean PC and an existing `C:\Vexi` installation.

## What the bootstrap may install

When missing, the installer can use Windows Package Manager (`winget`) to install:

- Python 3.11 (`Python.Python.3.11`)
- Ollama (`Ollama.Ollama`)

It then:

- creates `C:\Vexi\.venv`;
- installs Vexi Python dependencies;
- pulls the configured local Ollama model if absent;
- prewarms faster-whisper `small` and Silero `v5_ru`;
- creates Startup/Desktop/Settings shortcuts;
- launches Vexi hidden;
- requires a `Vexi v0.1.3 ready` log marker before reporting success.

Internet access is required for a first clean install. Model/dependency downloads can make the first installation substantially longer than an update.

Installer log:

```text
%TEMP%\Vexi_v0.1.3_public_install.log
```

## Browser Pack

After Core is ready, install only the Browser Pack(s) matching the browser(s) used on that PC.

Available packs:

- Vivaldi
- Chrome
- Edge
- Brave
- Opera
- Firefox

Each pack is stored independently from Core and survives Core upgrades.

For Chromium-family browsers, run `INSTALL_BROWSER_PACK.bat`, then use the browser's extensions page and **Load unpacked** with the extension folder shown by the installer.

## Current safety profile

- API keys/tokens are entered only through `Vexi Settings -> Security`.
- Secrets are stored with Windows Credential Manager and are not accepted through normal voice/chat input.
- Financial, legal-external, security-sensitive, destructive, and other high-responsibility external side effects are denied in this preview.
- Reversible account mutations require an explicit approval contract before support is enabled.

## Preview status

Core v0.1.3 has reached `READY` on the primary Windows laptop. The clean-install bootstrap and independent Browser Packs remain preview/test until they pass on additional Windows machines.
