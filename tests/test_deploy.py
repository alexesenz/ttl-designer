"""La plantilla systemd y el instalador deben estar de acuerdo (§DESPLIEGUE)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
UNIT = (REPO / "deploy" / "ttl-designer.service").read_text(encoding="utf-8")
INSTALL = (REPO / "deploy" / "install.sh").read_text(encoding="utf-8")

PORT = 8040
RESERVED_PORTS = {8000, 8020}


def env(name: str) -> str:
    m = re.search(rf"^Environment={name}=(\S+)$", UNIT, re.M)
    assert m, f"la unidad no define {name}"
    return m.group(1)


def test_unit_listens_on_all_interfaces_and_fixed_port():
    assert env("TTL_HOST") == "0.0.0.0"
    assert int(env("TTL_PORT")) == PORT
    assert PORT not in RESERVED_PORTS


def test_installer_uses_same_port():
    m = re.search(r"^PORT=(\d+)$", INSTALL, re.M)
    assert m and int(m.group(1)) == PORT


def test_unit_is_production_shaped():
    exec_start = next(line for line in UNIT.splitlines() if line.startswith("ExecStart="))
    assert "--reload" not in exec_start
    assert "--host ${TTL_HOST}" in exec_start and "--port ${TTL_PORT}" in exec_start
    assert "Restart=on-failure" in UNIT
    assert "WantedBy=multi-user.target" in UNIT
    assert re.search(r"^User=__USER__$", UNIT, re.M), "nunca root: el usuario lo pone install.sh"
    assert "__REPO__" in exec_start


def test_installer_replaces_all_placeholders():
    placeholders = set(re.findall(r"__[A-Z]+__", UNIT))
    for ph in placeholders:
        assert f"s|{ph}|" in INSTALL, f"install.sh no reemplaza {ph}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="sin bash")
def test_installer_syntax():
    subprocess.run(["bash", "-n", str(REPO / "deploy" / "install.sh")], check=True)
