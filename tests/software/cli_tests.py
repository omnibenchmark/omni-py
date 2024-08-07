import pytest
from typer.testing import CliRunner
import shlex
import omni.cli.main

from omni.cli.main import cli

runner = CliRunner()

# largely as in https://pytest-with-eric.com/pytest-advanced/pytest-argparse-typer/
test_cases = [
    (
        "software",
        "Manage and install benchmark-specific"        
    ),
    (
        "software singularity build --easyconfig nonexistent.eb",
        "ERROR: easyconfig not found."        
    ),
    (
        "software singularity build --easyconfig zlib-1.2.10.eb",
        "Installing software for zlib-1.2.10.eb within a Singularity container"      
    ),
    (
        "software conda pin --env data/ripgrep.yml",
        "DONE: Pinned data/ripgrep.yml"
    ),
    (
        "software envmodules build -e zlib-1.2.10.eb",
        "Installing software for zlib-1.2.10.eb using easybuild. It will take some time"
    )
]

@pytest.mark.parametrize("command, expected_output", test_cases)
def test_typer(command, expected_output):
    result = runner.invoke(cli, shlex.split(command))
    assert expected_output in result.stdout
    assert result.exit_code == 0
