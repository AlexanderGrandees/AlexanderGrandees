import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class AdminShortcutTests(unittest.TestCase):
    def test_real_links_point_to_current_runtime_and_request_elevation(self):
        installer = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="Vexi admin links ") as tmp:
            root = Path(tmp).resolve(); target = root / "Vexi"; desktop = root / "Desktop"
            desktop.mkdir(); (target / ".venv/Scripts").mkdir(parents=True)
            (target / ".venv/Scripts/pythonw.exe").touch()
            script = root / "check.ps1"
            script.write_text('''$ErrorActionPreference='Stop'
$shell=New-Object -ComObject WScript.Shell
$old=$shell.CreateShortcut((Join-Path $env:VEXI_TEST_DESKTOP 'Vexi Dev4.lnk'))
$old.TargetPath='C:\\Windows\\notepad.exe'; $old.Save()
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $env:VEXI_TEST_INSTALLER 'shortcuts.ps1') -Target $env:VEXI_TEST_TARGET -DesktopPath $env:VEXI_TEST_DESKTOP
if ($LASTEXITCODE -ne 0) { exit 1 }
$rows=@(Get-ChildItem -LiteralPath $env:VEXI_TEST_DESKTOP -Filter *.lnk | ForEach-Object {
 $link=$shell.CreateShortcut($_.FullName)
 $bytes=[IO.File]::ReadAllBytes($_.FullName)
 [pscustomobject]@{name=$_.Name; target=$link.TargetPath; args=$link.Arguments; cwd=$link.WorkingDirectory; admin=(([BitConverter]::ToUInt32($bytes,20) -band 0x2000) -ne 0)}
})
$rows | ConvertTo-Json -Compress
''', encoding="utf-8")
            result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                env={**os.environ, "VEXI_TEST_DESKTOP": str(desktop), "VEXI_TEST_TARGET": str(target),
                     "VEXI_TEST_INSTALLER": str(installer)}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual({r["name"] for r in rows}, {"Vexi (Admin).lnk", "Vexi Dev4.lnk", "Vexi Diagnostics.lnk"})
            for row in rows:
                self.assertTrue(row["admin"])
                self.assertEqual(Path(row["target"]), target / ".venv/Scripts/pythonw.exe")
                self.assertEqual(Path(row["cwd"]), target)
                expected = "settings_ui.py" if row["name"] == "Vexi Diagnostics.lnk" else "vexi.py"
                self.assertIn(str(target / expected), row["args"])


if __name__ == "__main__": unittest.main()
