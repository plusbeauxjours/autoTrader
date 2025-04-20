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

def notify(message: str):
    """
    거래 결과를 알리는 함수
    이 함수는 Slack 및 필요에 따라 다른 통지 채널을 통해 메시지를 전송합니다.
    """
    print(f"📢 {message}")
    
    # Slack으로도 알림 (중요 거래 정보이므로)
    notify_slack(f"🔔 거래 알림: {message}")
    
    # 추가 알림 채널은 여기에 구현 (이메일, 텔레그램 등)
    # 예시: send_email(message)
    # 예시: send_telegram(message)