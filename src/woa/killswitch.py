"""Cost kill switch.

AWS Budgets publishes to an SNS topic when WOA's monthly cost passes the stop
threshold. This function then sets the reserved concurrency of the WOA functions
to 0, so nothing can invoke them any more (Alexa, the setup page, or an attacker).

To turn WOA back on after checking the bill:
  aws lambda delete-function-concurrency --function-name <stack>-skill
  aws lambda delete-function-concurrency --function-name <stack>-web
"""

import logging
import os

log = logging.getLogger()
log.setLevel(logging.INFO)


def stop_functions(client, names):
    stopped = []
    for name in names:
        client.put_function_concurrency(FunctionName=name, ReservedConcurrentExecutions=0)
        stopped.append(name)
        log.warning("cost kill switch: %s stopped (reserved concurrency 0)", name)
    return stopped


def lambda_handler(event, context, client=None):
    names = [n.strip() for n in os.environ.get("TARGET_FUNCTIONS", "").split(",") if n.strip()]
    if client is None:
        import boto3
        client = boto3.client("lambda")
    return {"stopped": stop_functions(client, names)}
