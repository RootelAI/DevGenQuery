# utils/sms_sender.py
import time
import hmac
import hashlib
import base64
import requests
import json
from django.conf import settings

class NaverSMSSender:
    def __init__(self):
        self.access_key = settings.NAVER_CLOUD_SMS['ACCESS_KEY_ID']
        self.secret_key = settings.NAVER_CLOUD_SMS['SECRET_KEY']
        self.service_id = settings.NAVER_CLOUD_SMS['SERVICE_ID']
        self.from_number = settings.NAVER_CLOUD_SMS['FROM_NUMBER']
        self.base_url = f"https://sens.apigw.ntruss.com/sms/v2/services/{self.service_id}"
        
        # 디버깅: 설정값 확인
        # print(f"=== SMS 설정 디버깅 ===")
        # print(f"ACCESS_KEY: {self.access_key[:10]}..." if self.access_key else "ACCESS_KEY: None")
        # print(f"SERVICE_ID: {self.service_id}")
        # print(f"FROM_NUMBER: {self.from_number}")
        # print(f"=====================")
        
        # 필수값 검증
        if not all([self.access_key, self.secret_key, self.service_id, self.from_number]):
            raise ValueError("네이버 클라우드 SMS 설정이 완전하지 않습니다. 환경변수를 확인해주세요.")
        
        # URL 구성
        self.base_url = f"https://sens.apigw.ntruss.com/sms/v2/services/{self.service_id}"
        # print(f"API URL: {self.base_url}")
    
    def _make_signature(self, method, uri, timestamp):
        """네이버 클라우드 API 서명 생성"""
        message = f"{method} {uri}\n{timestamp}\n{self.access_key}"
        message = bytes(message, 'UTF-8')
        secret_key = bytes(self.secret_key, 'UTF-8')
        
        signature = base64.b64encode(
            hmac.new(secret_key, message, digestmod=hashlib.sha256).digest()
        )
        return signature.decode('utf-8')
    
    def send_sms(self, to_number, content):
        """SMS 발송"""
        timestamp = str(int(time.time() * 1000))
        uri = f"/sms/v2/services/{self.service_id}/messages"
        
        # 헤더 생성
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'x-ncp-apigw-timestamp': timestamp,
            'x-ncp-iam-access-key': self.access_key,
            'x-ncp-apigw-signature-v2': self._make_signature('POST', uri, timestamp)
        }
        
        # 요청 데이터
        data = {
            'type': 'SMS',
            'from': self.from_number,
            'content': content,
            'messages': [
                {
                    'to': to_number
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                data=json.dumps(data)
            )
            
            if response.status_code == 202:
                return {'success': True, 'message': 'SMS 발송 성공'}
            else:
                return {
                    'success': False, 
                    'message': f'SMS 발송 실패: {response.status_code}',
                    'error': response.text
                }
                
        except Exception as e:
            return {'success': False, 'message': f'SMS 발송 중 오류: {str(e)}'}