import os
import requests
import logging
from datetime import datetime

def notify_slack(message: str):
    """
    Slack으로 메시지를 전송합니다.
    오류 발생 시 로깅만 하고 예외를 발생시키지 않습니다.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logging.warning("❌ SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        print("❌ SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        return
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    payload = {"text": formatted_message}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code != 200:
            error_msg = f"❌ Slack 전송 실패: {response.status_code} - {response.text}"
            logging.error(error_msg)
            print(error_msg)
    except Exception as e:
        error_msg = f"❌ Slack 알림 오류: {str(e)}"
        logging.error(error_msg)
        print(error_msg)

def notify(message: str):
    """
    거래 결과를 알리는 함수
    이 함수는 Slack 및 필요에 따라 다른 통지 채널을 통해 메시지를 전송합니다.
    """
    logging.info(f"📢 {message}")
    print(f"📢 {message}")
    
    # Slack으로도 알림 (중요 거래 정보이므로)
    notify_slack(f"🔔 거래 알림: {message}")
    
    # 추가 알림 채널은 여기에 구현 (이메일, 텔레그램 등)
    # 예시: send_email(message)
    # 예시: send_telegram(message)