import os
import requests

def notify_slack(message: str):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        return
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
            print(f"❌ Slack 전송 실패: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Slack 알림 오류: {e}")