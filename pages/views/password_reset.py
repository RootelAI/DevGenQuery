from django.shortcuts import render, redirect
from django.contrib import messages

from utilsPrj.supabase_client import SUPABASE_URL, SUPABASE_KEY
import requests


def password_reset(request):
    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")
        access_token = request.GET.get("access_token")
        type_ = request.GET.get("type")

        if password != confirm:
            messages.error(request, "비밀번호가 일치하지 않습니다.")
            return render(request, "pages/password_reset.html")

        if not access_token or type_ != "recovery":
            messages.error(request, "유효하지 않은 접근입니다.")
            return render(request, "pages/password_reset.html")

        # ✅ supabase_client에서 불러온 값 사용
        url = f"{SUPABASE_URL}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        }

        try:
            resp = requests.put(url, json={"password": password}, headers=headers)
            if resp.ok:
                return render(request, "pages/password_reset.html", {"reset_success": True})
            else:
                messages.error(request, f"비밀번호 변경 실패: {resp.text}")
        except Exception as e:
            messages.error(request, f"비밀번호 변경 실패: {str(e)}")

    return render(request, "pages/password_reset.html")