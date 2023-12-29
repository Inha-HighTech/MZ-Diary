import json
import os
import boto3
import io
from datetime import datetime
import uuid
from urllib import request, parse

class DatabaseAccess():
    def __init__(self, TABLE_NAME):
        # DynamoDB 세팅
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(TABLE_NAME)
    
    def get_data(self, user_id):
        res = self.table.scan()
        items = res['Items'] # 모든 item
        count = res['Count'] # item 개수
        return items, count
    
    def put_data(self, input_data):
        self.table.put_item(
            Item =  input_data
        )
        print("Putting data is completed!")


def lambda_handler(event, context):
    # 환경 변수에서 Slack 토큰 읽기
    bot_token = os.environ.get('BOT_TOKEN')
    
    # Slack 이벤트 데이터 파싱
    body = json.loads(event['body'])
    
    # 메시지 이벤트 처리
    if 'command' in body :
        user_id = body['user_id']
        command = body['command']
        
        # 일기 기록 조회
        if command == '/history':
            db_access = DatabaseAccess('mz-diary-table')
            res, cnt = db_access.get_data(user_id)
            
            i = 0
            for r in res:
                if r['userID'] == user_id:
                    response_text = f"[{r['date']}]\n" + r['content']
                    post_message_to_slack(response_text, body['channel_id'], bot_token)
                    i += 1
                if i == 5:
                    break
            return {
                'statusCode': 200,
                'body': json.dumps('Event processed')
            }
    return {
        'statusCode': 200,
        'body': json.dumps('Event processed')
    }
    
def post_message_to_slack(response_text, channel_id, bot_token):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        'Authorization': f"Bearer {bot_token}",
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        'channel': channel_id,
        'text': response_text
    }).encode('utf-8')
    
    req = request.Request(url, data=payload, headers=headers)
    response = request.urlopen(req)
    response_data = response.read()
