from src.receipt_scanner_model import analyze


def test_main():
    assert isinstance(analyze.main("file_path_test"), str)
