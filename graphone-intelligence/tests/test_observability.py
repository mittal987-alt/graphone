import json
import logging

from src.utils.observability import (
    JsonFormatter,
    clear_observability_context,
    metrics,
    new_run_id,
    set_task_id,
)


def test_run_and_task_ids_are_set():
    run_id = new_run_id()
    task_id = set_task_id()
    assert run_id
    assert task_id
    clear_observability_context()


def test_json_formatter_outputs_valid_json():
    record = logging.LogRecord(
        "graphone",
        logging.WARNING,
        __file__,
        1,
        "fixture warning",
        (),
        None,
    )
    record.event = "provider_error"
    record.provider = "gemini"
    record.retryCount = 2
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "provider_error"
    assert payload["provider"] == "gemini"
    assert payload["retryCount"] == 2


def test_metrics_snapshot_and_reset():
    metrics.reset()
    metrics.increment("fixture_requests", 3)
    snapshot = metrics.snapshot()
    assert snapshot["fixture_requests"] == 3
    metrics.reset()
