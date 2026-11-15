import json
import sys
from pathlib import Path

# Add responder Lambda directory to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "src" / "responder_lambda"))

import lambda_function


def valid_sqs_event():
    incident = {
        "source": "aws.cloudwatch",
        "detail-type": "CloudWatch Alarm State Change",
        "region": "ap-southeast-2",
        "detail": {
            "alarmName": "incident-triage-lambda-error-alarm",
            "state": {"value": "ALARM"},
        },
    }

    return {
        "Records": [{"messageId": "test-message-001", "body": json.dumps(incident)}]
    }


def test_responder_processes_valid_incident():

    event = valid_sqs_event()

    result = lambda_function.lambda_handler(event, None)

    assert result == {"batchItemFailures": []}


def test_responder_reports_invalid_json():

    event = {"Records": [{"messageId": "test-message-002", "body": "invalid-json"}]}

    result = lambda_function.lambda_handler(event, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "test-message-002"}]}
