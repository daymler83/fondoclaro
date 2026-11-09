from pathlib import Path
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_env_is_ignored_but_example_is_trackable():
    result=subprocess.run(["git","-C",str(ROOT),"check-ignore","--no-index",".env",".env.local",".env.example"],text=True,capture_output=True,check=False)
    assert result.stdout.splitlines()==[".env",".env.local"]
    assert ".env" in (ROOT/".gitignore").read_text().splitlines()


def test_env_example_has_only_empty_configuration():
    pairs=dict(line.split("=",1) for line in (ROOT/".env.example").read_text().splitlines() if line.strip())
    assert set(pairs)=={"TELEGRAM_BOT_TOKEN","TELEGRAM_CHANNEL","WHATSAPP_TOKEN","WHATSAPP_PHONE_NUMBER_ID","WHATSAPP_VERIFY_TOKEN","WHATSAPP_APP_SECRET","OWNER_PHONE"}
    assert all(value=="" for value in pairs.values())


def test_defusedxml_is_a_pinned_direct_dependency():
    config=tomllib.loads((ROOT/"pyproject.toml").read_text())
    assert "defusedxml==0.7.1" in config["project"]["dependencies"]
