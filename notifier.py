import os, requests
WEBHOOK=os.getenv('SLACK_WEBHOOK_URL')
def notify(msg):
    if WEBHOOK: requests.post(WEBHOOK, json={'text':msg})
