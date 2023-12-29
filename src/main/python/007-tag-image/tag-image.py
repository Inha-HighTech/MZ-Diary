import json
import os
import boto3
import io
import openai
from urllib import request, parse

def lambda_handler(event, context):
    # 환경 변수에서 Slack 토큰 읽기
    bot_token = os.environ.get('BOT_TOKEN')
    
    # Slack 이벤트 데이터 파싱
    body = json.loads(event['body'])
    print(f"body={body}")
    
    # 메시지 이벤트 처리``
    if 'event' in body :
        slack_event = body['event']
        print(f"slack_event={slack_event}")
        # 채널 메시지인 경우
        if slack_event['type'] == 'message' and 'channel_type' in slack_event and 'bot_id' not in slack_event:
            user_id = slack_event['user']
            text = slack_event['text']
            
            if text == "help" or text == "h":
                post_message_to_slack( "사진과 키워드를 입력하면 일기를 자동으로 생성해줄게요!", slack_event['channel'], bot_token)
            else :
                # tagImageWorker 람다 호출
                lam = boto3.client('lambda')
                payload = {}
                payload['body'] = body
                lam.invoke(FunctionName="tagImageWorker", InvocationType='Event', Payload=json.dumps(payload))
            
    # 슬랙에 응답
    return {
        'statusCode': 200,
        'body': json.dumps('Event processed')
    }


def query_gpt(keywords_string):
    content = f"{keywords_string}으로 3줄짜리 일기 써줘. 한국어로."
    messages = [{"role":"user", "content":content}]
    
    client = openai.OpenAI(
        api_key = os.environ['GPT_API_KEY']
    )
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    res = completion.choices[0].message.content
    return res

def process_image(url, rekognition):
    image = download_image_from_slack(url)
    labels = get_labels_from_image(image, rekognition)
    return labels
    
def get_labels_from_image(image, rekognition):
    res = rekognition.detect_labels(
        Image={'Bytes': image},
        MaxLabels=1,
        MinConfidence=80
    )
    labels = sorted([label['Name'] for label in res['Labels']])
    return labels
    
def download_image_from_slack(file_url):
    bot_token = os.environ.get('BOT_TOKEN')
    req = request.Request(file_url, headers={'Authorization': f"Bearer {bot_token}"})
    res = request.urlopen(req).read()
    return res
 
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