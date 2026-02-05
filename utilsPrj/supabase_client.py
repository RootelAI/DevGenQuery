import os
from supabase import create_client
from dotenv import load_dotenv
from gotrue.errors import AuthApiError

import threading
import socket
import httpx
import time    # jeff 20251121 1030 추가

# .env 파일 로드
load_dotenv()

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

SUPABASE_URL = os.environ.get('SUPABASE_URL') or os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY') or os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')


# jeff 20260106 1015 추가
from threading import Lock

_http_lock = Lock()

class LockedClient(httpx.Client):
    def request(self, *args, **kwargs):
        with _http_lock:
            return super().request(*args, **kwargs)
#####

# jeff 20251121 1345 추가 
# DNS 캐싱
_dns_cache = {}
_dns_lock = threading.Lock()

def resolve_dns(url):
    """DNS를 미리 조회하고 캐싱"""
    with _dns_lock:
        if url not in _dns_cache:
            try:
                host = url.replace("https://", "").replace("http://", "").split("/")[0]
                ip = socket.gethostbyname(host)
                _dns_cache[url] = ip
                # print(f"[DNS] {host} resolved to {ip}")
            except Exception as e:
                # print(f"[DNS Error] {e}")
                _dns_cache[url] = None
        return _dns_cache[url]

# 앱 시작 시 DNS 미리 조회
SUPABASE_IP = resolve_dns(SUPABASE_URL)

# 스레드 로컬 저장소
_thread_local = threading.local()

def get_thread_supabase(access_token=None, refresh_token=None):
    """
    스레드별 Supabase 클라이언트 (연결 풀 재사용)
    """
    if not hasattr(_thread_local, 'client') or not hasattr(_thread_local, 'http_client'):
        # HTTP Client 생성 (연결 풀 관리)
        # _thread_local.http_client = httpx.Client(
        _thread_local.http_client = LockedClient(    # jeff 20260106 1015
            limits=httpx.Limits(
                max_connections=10,      # 스레드당 최대 10개 연결
                max_keepalive_connections=5,  # Keep-alive 5개
                keepalive_expiry=30.0    # 30초 후 연결 재사용
            ),
            timeout=httpx.Timeout(
                connect=10.0,    # 연결 타임아웃 10초
                read=30.0,       # 읽기 타임아웃 30초
                write=30.0,
                pool=5.0
            ),
            transport=httpx.HTTPTransport(
                retries=2,       # 실패 시 2회 재시도
            )
        )
        
        # Supabase 클라이언트 생성
        _thread_local.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # HTTP 클라이언트 교체
        _thread_local.client.postgrest.session = _thread_local.http_client

    # 세션 설정
    if access_token and refresh_token:
        try:
            _thread_local.client.auth.set_session(access_token, refresh_token)
        except Exception as e:
            pass#print(f"[Warning] Session 설정 실패: {e}")

    return _thread_local.client


def cleanup_thread_client():
    """스레드 종료 시 연결 정리"""
    if hasattr(_thread_local, 'http_client'):
        try:
            _thread_local.http_client.close()
        except:
            pass
        delattr(_thread_local, 'http_client')
    
    if hasattr(_thread_local, 'client'):
        delattr(_thread_local, 'client')
##########



# 클라이언트 생성
def get_supabase_client(access_token=None, refresh_token=None):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if access_token:
        # refresh 없이 access_token만 세팅
        client.auth._access_token = access_token

    return client


# import threading

# # 스레드별 클라이언트 저장소
# _thread_local = threading.local()

# def get_supabase_client(access_token=None, refresh_token=None):
#     """
#     스레드별로 독립적인 Supabase 클라이언트 반환.
#     """
#     # 현재 스레드에 클라이언트가 없으면 생성
#     if not hasattr(_thread_local, 'client'):
#         _thread_local.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
#     # 세션 설정
#     if access_token and refresh_token:
#         try:
#             _thread_local.client.auth.set_session(access_token, refresh_token)
#         except Exception as e:
#             print(f"[Warning] Session 설정 실패: {e}")
    
#     return _thread_local.client

def get_service_client():
    """
    서비스 역할 키를 사용하는 클라이언트 (관리용)
    """
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_supabase(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    if supabase is None:
        # 세션 초기화 후 로그인 페이지로 redirect 처리 가능
        request.session.flush()  # Django 세션 삭제
        return None  # 호출하는 곳에서 체크 후 redirect
    
    return supabase
