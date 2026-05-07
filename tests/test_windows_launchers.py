from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_bat_launcher_exists_and_forwards_args():
    launcher = PROJECT_ROOT / "run_windows.bat"
    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "app.py" in content
    assert "%*" in content


def test_ps1_launcher_exists_and_forwards_args():
    launcher = PROJECT_ROOT / "run_windows.ps1"
    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "app.py" in content
    assert "$args" in content
