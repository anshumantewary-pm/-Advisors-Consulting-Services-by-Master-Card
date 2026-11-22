import cardwise.credit as credit


def test_public_api_is_exported() -> None:
    for name in credit.__all__:
        assert hasattr(credit, name), name
    assert callable(credit.decide)
    assert callable(credit.monitor)
