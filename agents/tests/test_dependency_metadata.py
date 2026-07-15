from pathlib import Path
import tomllib


AGENTS_ROOT = Path(__file__).resolve().parents[1]


def _requirement_names(requirements: list[str]) -> set[str]:
    return {
        requirement.split("[", 1)[0].split(">", 1)[0].split("=", 1)[0].lower()
        for requirement in requirements
    }


def test_editable_install_declares_active_html_parser_dependency():
    metadata = tomllib.loads((AGENTS_ROOT / "pyproject.toml").read_text())

    dependency_names = _requirement_names(metadata["project"]["dependencies"])

    assert "beautifulsoup4" in dependency_names


def test_requirements_omit_dependencies_for_deleted_legacy_runtimes():
    requirements = [
        line.strip()
        for line in (AGENTS_ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    dependency_names = _requirement_names(requirements)

    assert "sentence-transformers" not in dependency_names
    assert "pygithub" not in dependency_names
