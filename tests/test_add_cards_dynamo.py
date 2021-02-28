import sys
import boto3
import json
import botocore
import pytest
import copy
from time import sleep
from moto import mock_sqs, mock_dynamodb2

sys.path.append("../")
import handler

card = {"front": "front", "back": "back", "epoch": "epoch", "exam": "AWS#dva"}


@mock_sqs
def test_get_messages_empty(monkeypatch):
    monkeypatch.setenv("queue_name", "queue_test")
    monkeypatch.setenv("visibilitytimeout", "30")
    monkeypatch.setenv("max_messages", "3")
    monkeypatch.setenv("waittimesecs", "3")
    sqs = boto3.client("sqs")
    l = sqs.create_queue(QueueName="test")
    response = handler.get_messages(sqs, l["QueueUrl"])
    assert "Messages" not in response


@mock_sqs
def test_get_messages(monkeypatch):
    monkeypatch.setenv("queue_name", "queue_test")
    monkeypatch.setenv("visibilitytimeout", "30")
    monkeypatch.setenv("max_messages", "3")
    monkeypatch.setenv("waittimesecs", "3")
    sqs = boto3.client("sqs")
    l = sqs.create_queue(QueueName="test")
    sqs.send_message(
        QueueUrl=l["QueueUrl"], MessageBody="This is a test", DelaySeconds=0
    )
    response = handler.get_messages(sqs, l["QueueUrl"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Messages"]) > 0


@mock_sqs
def test_delete_messages(monkeypatch):
    monkeypatch.setenv("queue_name", "queue_test")
    monkeypatch.setenv("visibilitytimeout", "10")
    monkeypatch.setenv("max_messages", "3")
    monkeypatch.setenv("waittimesecs", "3")
    sqs = boto3.client("sqs")
    l = sqs.create_queue(QueueName="test")
    sqs.send_message(
        QueueUrl=l["QueueUrl"], MessageBody="This is a test", DelaySeconds=0
    )
    response = handler.get_messages(sqs, l["QueueUrl"])
    message = response["Messages"][0]
    handler.delete_message(sqs, l["QueueUrl"], message)
    sleep(10)
    new_response = handler.get_messages(sqs, l["QueueUrl"])
    assert "Messages" not in new_response


def test_validate():
    test_card = copy.deepcopy(card)
    response = handler.validate_card(test_card)
    assert response == True
    response = handler.validate_card("card")
    assert response == False
    del test_card["front"]
    response = handler.validate_card(test_card)
    assert response == False
    test_card["front"] = "front"
    del test_card["back"]
    response = handler.validate_card(test_card)
    assert response == False
    test_card["back"] = "back"
    del test_card["epoch"]
    response = handler.validate_card(test_card)
    assert response == False
    del test_card["exam"]
    response = handler.validate_card(test_card)
    assert response == False


def test_prep_card_pass(monkeypatch):
    def insert_card_test(dynamo, card):
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    monkeypatch.setattr(handler, "insert_card", insert_card_test)
    dynamo = "test"
    response = handler.prep_card(dynamo, card)
    assert response == True


def test_prep_card_fail(monkeypatch):
    def insert_card_test(dynamo, card):
        return {"ResponseMetadata": {"HTTPStatusCode": 400}}

    monkeypatch.setattr(handler, "insert_card", insert_card_test)
    dynamo = "test"
    response = handler.prep_card(dynamo, card)
    assert response == False


@mock_dynamodb2
def test_insert_card_pass(monkeypatch):
    monkeypatch.setenv("tablename", "testtable")
    table = "testtable"
    dynamo = boto3.client("dynamodb")
    dynamo.create_table(
        TableName=table,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
    )
    response = handler.insert_card(dynamo, card)
    assert (
        "ResponseMetadata" in response
        and "HTTPStatusCode" in response["ResponseMetadata"]
    )


@mock_sqs
def test_add_card_to_dynamodb(monkeypatch):
    def mock_valid_card(body):
        return True

    def mock_valid_card_fail(body):
        return False

    def mock_prep_card(dynamo, card):
        return True

    monkeypatch.setenv("visibilitytimeout", "10")
    monkeypatch.setenv("max_messages", "3")
    monkeypatch.setenv("waittimesecs", "3")
    test_queue = "test_queue"
    monkeypatch.setenv("queuename", test_queue)
    monkeypatch.setenv("tablename", "testtable")
    monkeypatch.setattr(handler, "validate_card", mock_valid_card)
    monkeypatch.setattr(handler, "prep_card", mock_prep_card)

    sqs = boto3.client("sqs")
    queue = sqs.create_queue(QueueName=test_queue)
    sqs.send_message(
        QueueUrl=queue["QueueUrl"], MessageBody=json.dumps(card), DelaySeconds=0
    )
    handler.add_cards_to_dynamodb("event", "context")

    monkeypatch.setattr(handler, "validate_card", mock_valid_card_fail)
    handler.add_cards_to_dynamodb("event", "context")