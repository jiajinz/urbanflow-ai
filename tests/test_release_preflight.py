"""Deterministic release-environment checks; no installation or network access."""

from importlib import metadata

import pytest

from scripts.release_preflight import validate_runtime_constraints


def test_release_pins_respect_environment_markers(tmp_path):
    path = tmp_path / 'constraints.txt'
    path.write_text('# Runtime\nexample==1.2.3\nnot-installed==9; python_version < "0"\n')

    def version(name):
        assert name == 'example'
        return '1.2.3'

    assert validate_runtime_constraints(path, version) == {'example': '1.2.3'}


def test_release_environment_rejects_mismatched_or_missing_packages(tmp_path):
    path = tmp_path / 'constraints.txt'
    path.write_text('example==1.2.3\n')
    with pytest.raises(RuntimeError, match='differs from constraints: example'):
        validate_runtime_constraints(path, lambda name: '1.2.4')

    def missing(name):
        raise metadata.PackageNotFoundError(name)

    with pytest.raises(RuntimeError, match='Missing release dependency: example'):
        validate_runtime_constraints(path, missing)
