import pytest
import os
import shutil
from core.data_logger import DataLogger

@pytest.fixture
def logger():
    test_dir = "test_logs"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    dl = DataLogger(log_dir=test_dir)
    yield dl
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def test_start_stop_logging(logger):
    logger.start_logging()
    assert logger.current_log_file is not None
    assert os.path.exists(logger.current_log_file)
    logger.stop_logging()
    assert logger.file_handle is None

def test_log_string(logger):
    logger.start_logging()
    logger.log("test data")
    logger.stop_logging()
    
    with open(logger.current_log_file, "r") as f:
        content = f.read()
        assert "test data" in content

def test_log_dict_missing_fields(logger):
    # This is what Task 2 is about
    logger.start_logging()
    # Test logging a dict with some missing expected fields
    data = {"time": 100, "alt": 20.0} # missing 'pitch', 'roll', etc.
    try:
        logger.log(data)
    except Exception as e:
        pytest.fail(f"Logger crashed with dict: {e}")
    logger.stop_logging()

def test_log_none_or_empty(logger):
    logger.start_logging()
    logger.log(None)
    logger.log("")
    logger.stop_logging()
