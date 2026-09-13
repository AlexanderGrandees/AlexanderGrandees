# Vexi v0.1.4 Public Preview — install / field test

## Windows + Chrome third-party bundle
The public field-test bundle contains:

```text
Vexi Core v0.1.4
+
Chrome Browser Pack v0.1.2
```

The ZIP artifact is distributed separately from the repository documentation at this stage.

## Clean-install order
1. Fully extract the bundle before running anything.
2. Run `1_INSTALL_CORE.bat` or `Core\START_HERE_INSTALL_VEXI.bat`.
3. Accept the Windows UAC prompt when shown.
4. Wait until the Core installer reports successful completion and the runtime reaches READY.
5. Confirm version:

```powershell
Get-Content C:\Vexi\version.py
```

Expected:

```text
__version__ = "0.1.4"
__channel__ = "public-preview"
__build__ = "media-context-natural-control"
```

6. Run `2_INSTALL_CHROME_PACK.bat` or `BrowserPacks\Chrome\START_HERE_CHROME_PACK.bat`.
7. Open `chrome://extensions`.
8. Enable Developer mode.
9. Choose **Load unpacked** and select:

```text
%LOCALAPPDATA%\VexiBrowserPacks\Chrome\extension
```

10. Open a normal `https://www.youtube.com/` tab and refresh it once after first extension activation.
11. Run Browser Pack diagnostics.

Expected healthy baseline:

```text
Registry: PRESENT
UTF8 BOM: False
Service: PASS v0.1.2 protocol 1
installed: true
extension_connected: true
site: youtube
page_type: HOME
snapshot_age: fresh
```

A protected internal page such as `chrome://extensions` will not produce a normal page snapshot; that is expected browser security behavior.

## Primary YouTube field matrix
Run these only after Browser Pack diagnostics are healthy:

```text
Векси, что видишь на YouTube?
Открой второе видео.
Весь экран.
Убери видео из полноэкранного режима.
Сделай видео тише.
Выключи звук на ноуте.
```

Record the exact `INTENT`, `status`, and `RESPONSE` lines for failures.

## Current known issue
`сверни это видео` / fullscreen-OFF natural language is still under Core routing hardening. A failure there does not imply that the Browser Pack or structured snapshot is broken.

## Existing Vivaldi primary machine
For the already field-tested primary setup, update only Core to v0.1.4 and keep Vivaldi Browser Pack v0.1.2 installed. Do not install Chrome Pack unless Chrome control is also required.

## Security / secrets
- Do not paste credentials or API tokens into voice/chat logs.
- Secret values belong in the dedicated security UI / OS credential store.
- Financial, irreversible and security-sensitive actions remain denied in the current public preview.

## Promotion evidence
The build is not Stable until a representative third-party PC confirms:
- clean Core install;
- runtime READY identity;
- Chrome Browser Pack registration;
- extension heartbeat;
- YouTube structured snapshot;
- visible video extraction;
- ordinal card open;
- player media controls;
- no critical installer regression.
