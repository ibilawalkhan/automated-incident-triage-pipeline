import json
import importlib.util
from pathlib import Path

module_path = (
    Path(__file__).resolve().parents[1] / "src" / "chaos_lambda" / "lambda_function.py"
)

spec = importlib.util.spec_from_file_location("chaos_lambda_under_test", module_path)

lambda_function = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_function)


def test_chaos_lambda_returns_success():
    response = lambda_function.lambda_handler({}, None)

    assert response["statusCode"] == 200


def test_chaos_lambda_returns_valid_json():
    response = lambda_function.lambda_handler({}, None)

    body = json.loads(response["body"])

    assert isinstance(body, dict)


def test_chaos_lambda_returns_expected_message():
    response = lambda_function.lambda_handler({}, None)

    body = json.loads(response["body"])

    assert body["message"] == "Chaos Lambda executed successfully!!!"


def test_chaos_lambda_returns_expected_project():
    response = lambda_function.lambda_handler({}, None)

    body = json.loads(response["body"])

    assert body["project"] == "automated-incident-triage-pipeline"
