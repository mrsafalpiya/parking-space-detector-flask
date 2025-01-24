import boto3
from dotenv import load_dotenv
import uuid

load_dotenv()

dynamodb = boto3.client('dynamodb', region_name='ap-south-1')


def get_all_parking_logs():
    response = dynamodb.scan(
        TableName='parking_logs',
        FilterExpression='attribute_exists(exit_time)'
    )

    logs = []
    logs_from_db = response.get('Items', [])
    for log in logs_from_db:
        logs.append({
            'vehicle_number': log['vehicle_number']['S'],
            'arrival_time': log['arrival_time']['S'],
            'exit_time': log['exit_time']['S'],
            'day_of_week': log['day_of_week']['S']
        })
    return logs


def insert_arrival_entry(vehicle_number, day_of_week, arrival_time):
    dynamodb.put_item(
        TableName='parking_logs',
        Item={
            'id': {'S': str(uuid.uuid4())},
            'vehicle_number': {'S': vehicle_number},
            'arrival_time': {'S': str(arrival_time)},
            'day_of_week': {'S': day_of_week},
        }
    )


def insert_exit_entry(vehicle_number, day_of_week, exit_time):
    # Query the table to get the last item inserted with the given vehicle_number
    response_vehicle = dynamodb.query(
        TableName='parking_logs',
        IndexName='vehicle_number-index',  # Use the correct index name
        KeyConditionExpression='vehicle_number = :v_num',
        ExpressionAttributeValues={
            ':v_num': {'S': vehicle_number}
        },
        ScanIndexForward=False,  # Get the last inserted item
        Limit=1
    )

    # Query the table to get the last item inserted with the given day_of_week
    response_day = dynamodb.query(
        TableName='parking_logs',
        IndexName='day_of_week-index',  # Use the correct index name
        KeyConditionExpression='day_of_week = :d_week',
        ExpressionAttributeValues={
            ':d_week': {'S': day_of_week}
        },
        ScanIndexForward=False,  # Get the last inserted item
        Limit=1
    )

    items_vehicle = response_vehicle.get('Items', [])
    items_day = response_day.get('Items', [])

    # Find the common item between the two queries
    last_item = None
    for item in items_vehicle:
        if item in items_day:
            last_item = item
            break

    if last_item:
        # Update the last item with the Exit Time
        dynamodb.update_item(
            TableName='parking_logs',
            Key={
                'id': last_item['id']
            },
            UpdateExpression='SET exit_time = :exit_time',
            ExpressionAttributeValues={
                ':exit_time': {'S': str(exit_time)}
            }
        )
    else:
        # Insert a new item with Arrival Time set to 00:00
        dynamodb.put_item(
            TableName='parking_logs',
            Item={
                'id': {'S': str(uuid.uuid4())},
                'vehicle_number': {'S': vehicle_number},
                'arrival_time': {'S': '00:00'},
                'exit_time': {'S': str(exit_time)},
                'day_of_week': {'S': day_of_week}
            }
        )
