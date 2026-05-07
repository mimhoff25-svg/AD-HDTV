from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_windows_bat_launcher_exists_and_targets_app():
    launcher = PROJECT_ROOT / "run_windows.bat"
    content = launcher.read_text(encoding="utf-8")

    assert launcher.exists()
    assert "app.py" in content
    assert "%*" in content


def test_windows_powershell_launcher_exists_and_targets_app():
    launcher = PROJECT_ROOT / "run_windows.ps1"
    content = launcher.read_text(encoding="utf-8")

    assert launcher.exists()
    assert "app.py" in content
    assert "$args" in content
