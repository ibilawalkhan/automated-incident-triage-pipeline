import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info("Incident Triage Pipeline")
    logger.info("Chaos Lambda executed successfully!!!")
    logger.info("Generating test activity for CloudWatch...")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Chaos Lambda executed successfully!!!",
                "project": "automated-incident-triage-pipeline",
            }
        ),
    }
