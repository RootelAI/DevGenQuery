import os
from supabase import create_client
# from dotenv import load_dotenv
from utilsPrj.secrets_manager import secrets_manager

# .env 파일 로드
# load_dotenv()

SUPABASE_URL = secrets_manager.get_secret("AI-SUPABASE-URL")
SUPABASE_KEY = secrets_manager.get_secret("AI-SUPABASE-KEY")
SUPABASE_SERVICE_ROLE_KEY = secrets_manager.get_secret("AI-SUPABASE-SERVICE-ROLE-KEY")

# 클라이언트 생성
def get_supabase_client(access_token=None, refresh_token=None):
    """
    Supabase 클라이언트 생성 및 세션 설정 함수.
    access_token이 있으면 auth 세션을 설정.
    """
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    if access_token and refresh_token:
        client.auth.set_session(access_token, refresh_token)
    return client

def get_service_client():
    """
    서비스 역할 키를 사용하는 클라이언트 (관리용)
    """
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)