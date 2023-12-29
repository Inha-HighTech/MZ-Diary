import json
import os
import boto3
import io
import openai
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
    body = event['body']
    
    # 메시지 이벤트 처리
    if 'event' in body :
        slack_event = body['event']
        print(f"slack_event={slack_event}")
        # 채널 메시지인 경우
        if slack_event['type'] == 'message' and 'channel_type' in slack_event and 'bot_id' not in slack_event:
            user_id = slack_event['user']
            text = slack_event['text']
            keywords = [] # 일기를 적을 키워드
            
            # 일기 기록 조회
            if text == 'history':
                db_access = DatabaseAccess('mz-diary-table')
                res, cnt = db_access.get_data(user_id)
                
                i = 0
                for r in res:
                    if r['userID'] == user_id:
                        response_text = r['content']
                        post_message_to_slack(response_text, slack_event['channel'], bot_token)
                        i += 1
                    if i == 3:
                        break
                return {
                    'statusCode': 200,
                    'body': json.dumps('Event processed')
                }
            
            # 이미지 파일이 있는 경우 태깅
            diary_images = []
            if 'files' in slack_event:
                rekognition = boto3.client('rekognition')
                s3 = boto3.client('s3')
                bucket = '007-diary-image'
                
                for file in slack_event['files']:
                    file_url = file['url_private']
                    key_name = file['id']+'_'+file['name']
                    
                    # Slack에서 파일 다운로드
                    image = download_image_from_slack(file_url);
                    
                    # S3에 파일 업로드
                    s3.put_object(Body=image, Bucket=bucket, Key=key_name, ContentType=file['mimetype'])
                    diary_images.append(key_name)
                    
                    labels = process_image(file_url, rekognition)
                    keywords += labels
             
            # 사용자가 추가로 입력한 텍스트도 키워드에 추가
            keywords.append(text)
            keywords_string = ','.join(keywords)
            print(f"keywords_string={keywords_string}")
            
            # GPT에게 일기 요청    
            response_text = query_gpt(keywords_string)
            print(f"response_text={response_text}")
            post_message_to_slack(response_text, slack_event['channel'], bot_token)
            
            # DB에 저장
            db_access = DatabaseAccess('mz-diary-table')
            input_data = {
                "diaryID" : str(uuid.uuid4()), # 일기 고유 키 값
                "content" : response_text, # 일기의 내용
                "images" : diary_images, # 일기에 해당하는 이미지 목록
                "userID" : user_id, # 일기의 작성자 아이디
                "date"   : datetime.today().strftime("%Y/%m/%d %H:%M:%S") # 일기가 작성된 날짜
            }
            db_access.put_data(input_data)
                
                
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
