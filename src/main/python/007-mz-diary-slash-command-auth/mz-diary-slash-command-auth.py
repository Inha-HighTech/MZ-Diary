import json
import base64
import boto3
from urllib.parse import parse_qs

def lambda_handler(event, context):
    # base64 디코딩
    body_decoded = base64.b64decode(event['body']).decode('utf-8')
    print(f"body_decoded={body_decoded}") 
    
    body_params = parse_qs(body_decoded)
    body_json = json.dumps({k: v[0] for k, v in body_params.items()})
    print(f"body_json={body_json}")

    # command 추출
    command = body_params.get('command', [''])[0]
    print(f"command={command}")
    
    # command의 종류에 따라 다른 람다 함수 호출
    lam = boto3.client('lambda')
    payload = {}
    payload['body'] = body_json
    lam.invoke(FunctionName="007-mz-diary-"+command[1:], InvocationType='Event', Payload=json.dumps(payload))
    
    # 슬랙에 응답
    return {
        'statusCode': 200
        # 'body': json.dumps('Event processed')
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
    print(f"response_data={response_data}")
