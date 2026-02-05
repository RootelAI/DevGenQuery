# utilsPrj/supabase_session_refresh.py
import time
from django.shortcuts import redirect
from django.http import JsonResponse
from gotrue.errors import AuthApiError
from utilsPrj.supabase_client import get_supabase_client

class SupabaseSessionRefreshMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        # self.last_refresh_time = 0
        # self.MIN_REFRESH_INTERVAL = 60  # 초 단위

    def __call__(self, request):

        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        user_info = request.session.get("user")

        # -------------------------------------------------------------
        # 자동 요청 제외
        # -------------------------------------------------------------
        ignored_paths = ["/favicon.ico", "/robots.txt", "/healthcheck"]
        if request.path in ignored_paths:
            return self.get_response(request)

        # -------------------------------------------------------------
        # 로그인 상태가 아닐 때 (세션 쿠키 만료 / 토큰 손실)
        # -------------------------------------------------------------
        if not access_token or not refresh_token:
            return self.get_response(request)

        # 새로운 Supabase 클라이언트 생성
        # supabase = self._get_fresh_client(access_token, refresh_token)
        supabase = self._get_fresh_client(access_token)

        try:
            if not request.session.get("user"):
                user = supabase.auth.get_user().user
                request.session["user"] = user
                request.session.modified = True

        except AuthApiError as e1:
            msg = str(e1)

            # 🔹 토큰 만료가 아니면 refresh하지 않음
            if "expired" not in msg.lower():
                return self.get_response(request)

            try:
                refreshed = supabase.auth.refresh_session(refresh_token)

                if refreshed and refreshed.session:
                    request.session["access_token"] = refreshed.session.access_token
                    request.session["refresh_token"] = refreshed.session.refresh_token
                    request.session["user"] = refreshed.session.user
                    request.session.modified = True
                else:
                    self._clear_session(request)
                    return self._handle_expired(request)

            except Exception as ex:
                self._clear_session(request)
                return self._handle_expired(request)

        except Exception as ex2:
            return self.get_response(request)

        return self.get_response(request)

    # ---------- 내부 유틸 ----------

    # def _get_fresh_client(self, access_token=None, refresh_token=None):
    #     return get_supabase_client(access_token, refresh_token)

    def _get_fresh_client(self, access_token=None):
        return get_supabase_client(access_token)

    def _clear_session(self, request):
        request.session.pop("access_token", None)
        request.session.pop("refresh_token", None)
        request.session.pop("user", None)
        request.session.modified = True

    def _handle_expired(self, request):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "result": "Failed",
                "message": "세션이 만료되었습니다. 다시 로그인해주세요."
            }, status=401)
        return redirect("home")

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
