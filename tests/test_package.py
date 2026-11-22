import cardwise


def test_version_is_semver() -> None:
    parts = cardwise.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
