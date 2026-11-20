import json
import importlib.util
from pathlib import Path

module_path = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "responder_lambda"
    / "lambda_function.py"
)

spec = importlib.util.spec_from_file_location(
    "responder_lambda_under_test", module_path
)

lambda_function = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_function)


def create_valid_record(message_id="test-message-001"):
    incident = {
        "source": "aws.cloudwatch",
        "detail-type": "CloudWatch Alarm State Change",
        "region": "ap-southeast-2",
        "detail": {
            "alarmName": "IncidentTriage-TestAlarm",
            "state": {"value": "ALARM"},
        },
    }

    return {"messageId": message_id, "body": json.dumps(incident)}


def test_process_valid_incident():
    record = create_valid_record()

    # Should process successfully without raising an exception.
    lambda_function.process_incident(record)


def test_process_incident_rejects_missing_body():
    record = {"messageId": "test-001"}

    try:
        lambda_function.process_incident(record)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "body is missing or invalid" in str(error)


def test_process_incident_rejects_invalid_json():
    record = {"messageId": "test-002", "body": "{invalid-json}"}

    try:
        lambda_function.process_incident(record)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "invalid JSON" in str(error)


def test_process_incident_rejects_unexpected_source():
    incident = json.loads(create_valid_record()["body"])
    incident["source"] = "unexpected.source"

    record = {"messageId": "test-003", "body": json.dumps(incident)}

    try:
        lambda_function.process_incident(record)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unexpected event source" in str(error)


def test_process_incident_rejects_unexpected_event_type():
    incident = json.loads(create_valid_record()["body"])
    incident["detail-type"] = "Unexpected Event"

    record = {"messageId": "test-004", "body": json.dumps(incident)}

    try:
        lambda_function.process_incident(record)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unexpected event type" in str(error)


def test_process_incident_rejects_missing_alarm_name():
    incident = json.loads(create_valid_record()["body"])
    incident["detail"]["alarmName"] = ""

    record = {"messageId": "test-005", "body": json.dumps(incident)}

    try:
        lambda_function.process_incident(record)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Alarm name is missing" in str(error)


def test_lambda_handler_processes_valid_sqs_message():
    event = {"Records": [create_valid_record()]}

    response = lambda_function.lambda_handler(event, None)

    assert response == {"batchItemFailures": []}


def test_lambda_handler_reports_invalid_message():
    event = {"Records": [{"messageId": "bad-message-001", "body": "{invalid-json}"}]}

    response = lambda_function.lambda_handler(event, None)

    assert response == {"batchItemFailures": [{"itemIdentifier": "bad-message-001"}]}


def test_lambda_handler_processes_valid_and_invalid_messages():
    event = {
        "Records": [
            create_valid_record("valid-message"),
            {"messageId": "invalid-message", "body": "{invalid-json}"},
        ]
    }

    response = lambda_function.lambda_handler(event, None)

    assert response == {"batchItemFailures": [{"itemIdentifier": "invalid-message"}]}


def test_lambda_handler_handles_empty_batch():
    response = lambda_function.lambda_handler({"Records": []}, None)

    assert response == {"batchItemFailures": []}


def test_lambda_handler_rejects_failed_message_without_id():
    event = {"Records": [{"body": "{invalid-json}"}]}

    try:
        lambda_function.lambda_handler(event, None)
        assert False, "Expected ValueError"
    except ValueError:
        pass
