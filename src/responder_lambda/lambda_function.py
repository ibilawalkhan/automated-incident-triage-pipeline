import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_incident(record):
    """Validate and process one SQS incident message."""

    message_id = record.get("messageId", "Unknown")
    message_body = record.get("body")

    if not isinstance(message_body, str) or not message_body:
        raise ValueError("SQS message body is missing or invalid")

    try:
        incident = json.loads(message_body)
    except json.JSONDecodeError as error:
        raise ValueError("Message body contains invalid JSON") from error

    if not isinstance(incident, dict):
        raise TypeError("Event must be a JSON object")

    if incident.get("source") != "aws.cloudwatch":
        raise ValueError("Unexpected event source")

    if incident.get("detail-type") != "CloudWatch Alarm State Change":
        raise ValueError("Unexpected event type")

    detail = incident.get("detail")

    if not isinstance(detail, dict):
        raise TypeError("Event detail is missing or invalid")

    alarm_name = detail.get("alarmName")
    state = detail.get("state")
    region = incident.get("region")

    if not isinstance(alarm_name, str):
        raise TypeError("Alarm name must be a string")

    if not alarm_name:
        raise ValueError("Alarm name is missing")

    if not isinstance(state, dict):
        raise TypeError("Alarm state is missing or invalid")

    alarm_state = state.get("value")

    if not isinstance(alarm_state, str):
        raise TypeError("Alarm state value must be a string")

    if not alarm_state:
        raise ValueError("Alarm state value is missing")

    if not isinstance(region, str):
        raise TypeError("AWS region must be a string")

    if not region:
        raise ValueError("AWS region is missing")

    logger.info("Incident processed successfully.")
    logger.info("Message ID: %s", message_id)
    logger.info("Alarm name: %s", alarm_name)
    logger.info("Alarm state: %s", alarm_state)
    logger.info("Region: %s", region)


def lambda_handler(event, context):

    logger.info("Incident Triage Responder started.")

    records = event.get("Recordsss", [])

    logger.info("Number of messages received: %s", len(records))

    batch_item_failures = []

    for record in records:

        message_id = record.get("messageId")

        try:
            process_incident(record)

        except Exception:
            logger.exception("Failed to process SQS message: %s", message_id)

            if message_id:
                batch_item_failures.append({"itemIdentifier": message_id})
            else:
                raise

    logger.info("Number of failed messages: %s", len(batch_item_failures))

    return {"batchItemFailures": batch_item_failures}
