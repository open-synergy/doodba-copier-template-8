import os
from pathlib import Path

import pytest
from copier.main import copy
from plumbum import FG
from plumbum.cmd import invoke

try:
    from plumbum.cmd import docker
except ImportError:
    docker = None


@pytest.mark.skipif(docker is None, reason="Need docker CLI to test doodba-qa")
@pytest.mark.skipif(
    os.environ.get("DOCKER_TEST") != "1", reason="Missing DOCKER_TEST=1 env variable"
)
def test_doodba_qa(tmp_path: Path, supported_odoo_version: float):
    """Test Doodba QA works fine with a scaffolding copy."""
    copy(
        ".",
        tmp_path,
        data={"odoo_version": supported_odoo_version},
        force=True,
        vcs_ref="HEAD",
    )
    qa_run = docker[
        "container",
        "run",
        "--rm",
        "--privileged",
        f"-v{tmp_path}:{tmp_path}:z",
        "-v/var/run/docker.sock:/var/run/docker.sock:z",
        f"-w{tmp_path}",
        "-eADDON_CATEGORIES=-p",
        "-eCOMPOSE_FILE=test.yaml",
        f"-eODOO_MAJOR={int(supported_odoo_version)}",
        f"-eODOO_MINOR={supported_odoo_version:.1f}",
        "tecnativa/doodba-qa",
    ]
    try:
        qa_run["secrets-setup"] & FG
        qa_run["networks-autocreate"] & FG
        qa_run["build"] & FG
        qa_run["closed-prs"] & FG
        qa_run["flake8"] & FG
        qa_run["pylint"] & FG
        qa_run["addons-install"] & FG
        qa_run["coverage"] & FG
    finally:
        qa_run["shutdown"] & FG
        invoke["-r", tmp_path, "stop", "--purge"] & FG