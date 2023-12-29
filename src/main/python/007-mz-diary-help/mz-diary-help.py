import json
import base64
import boto3
import os
from urllib import request, parse

def lambda_handler(event, context):
    # 환경 변수에서 Slack 토큰 읽기
    bot_token = os.environ.get('BOT_TOKEN')
    
    # Slack 이벤트 데이터 파싱
    body = json.loads(event['body'])

    post_message_to_slack(
        """사진과 키워드를 적으면, 지피티가 일기를 자동으로 생성해줄게요!
사진이 없으면, 키워드만 적어주세요!
        
슬랙 커맨드가 총 2개 있어요!
/help : MZ일기의 사용법을 알려줘요
/history : 내가 쓴 일기 기록을 보여줘요""",
        body['channel_id'],
        bot_token
        )

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
    print(f"response_data={response_data}")