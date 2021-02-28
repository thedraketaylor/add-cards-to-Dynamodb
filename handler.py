import json
import boto3
import os
from time import sleep


def get_messages(sqs, q_url):
    visibility_timeout = int(os.environ["visibilitytimeout"])
    max_messages = int(os.environ["max_messages"])
    wait_time_secs = int(os.environ["waittimesecs"])
    response = sqs.receive_message(
        QueueUrl=q_url,
        MaxNumberOfMessages=max_messages,
        VisibilityTimeout=visibility_timeout,
        WaitTimeSeconds=wait_time_secs,
    )
    return response


def validate_card(card):
    if not isinstance(card, dict):
        return False
    ret_val = True
    if not "front" in card or not card["front"]:
        ret_val = False
    if not "back" in card or not card["back"]:
        ret_val = False
    if not "epoch" in card or not card["epoch"]:
        ret_val = False
    if not "exam" in card or not card["exam"]:
        ret_val = False
    return ret_val


def prep_card(dynamo, card):
    tmp = card["exam"].split("#")[-2:2]
    card["exam"] = tmp[0].upper() + "#" + tmp[1].lower()
    response = insert_card(dynamo, card)
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        return False
    return True


# TODO: We should probably do a batch insert here.
def insert_card(dynamo, card):
    table_name = os.environ["tablename"]
    response = dynamo.put_item(
        TableName=table_name,
        Item={
            "PK": {"S": "CARD#" + str(card["exam"])},
            "SK": {"S": "#USER#" + str(card["epoch"])},
            "front": {"S": str(card["front"])},
            "back": {"S": str(card["back"])},
        },
    )
    return response


def delete_message(sqs, q_url, message):
    sqs.delete_message(QueueUrl=q_url, ReceiptHandle=message["ReceiptHandle"])


def add_cards_to_dynamodb(event, context):
    sqs = boto3.client("sqs")
    dynamo = boto3.client("dynamodb")
    queue_name = os.environ["queuename"]
    # Get the queue url
    q_res = sqs.get_queue_url(
        QueueName=queue_name,
    )
    q_url = q_res["QueueUrl"]
    # If we get messages, loop through them and insert into dynamodb before deleting them
    response = get_messages(sqs, q_url)

    while "Messages" in response:
        for message in response["Messages"]:
            print(message)
            if isinstance(message["Body"], str):
                body = json.loads(message["Body"])

            if not validate_card(body):
                delete_message(sqs, q_url, message)
                continue

            if prep_card(dynamo, body):
                delete_message(sqs, q_url, message)

            sleep(1)
        response = get_messages(sqs, q_url)
