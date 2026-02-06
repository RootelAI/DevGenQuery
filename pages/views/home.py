from django.shortcuts import render
from datetime import datetime, timedelta
from utilsPrj.supabase_client import get_supabase_client
import uuid
from django.http import JsonResponse
import json

def home(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user_id = request.session.get("user", {}).get("id")

    return render(request, 'pages/home.html', {
            "user_id" : user_id
    })

def hide_popup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({"status": "fail", "error": "Invalid JSON"}, status=400)

        popupid = data.get("popupid")
        days = data.get("days", 1)

        try:
            days = int(days)
        except Exception as e:
            days = 1

        user_uid = request.session.get("user", {}).get("id")

        if not user_uid:
            return JsonResponse({"status": "fail", "error": "User not logged in"}, status=403)
        if not popupid:
            return JsonResponse({"status": "fail", "error": "No popupid provided"}, status=400)

        # Supabase 처리
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        enddt = (datetime.utcnow() + timedelta(days=days)).isoformat()

        existing = supabase.schema("genquery").table("popupdeactivates")\
            .select("*")\
            .eq("popupid", popupid)\
            .eq("useruid", user_uid)\
            .execute()

        if existing.data:
            supabase.schema("genquery").table("popupdeactivates")\
                .update({"enddt": enddt})\
                .eq("popupid", popupid)\
                .eq("useruid", user_uid)\
                .execute()
        else:
            supabase.schema("genquery").table("popupdeactivates")\
                .insert({
                    "popupid": popupid,
                    "useruid": user_uid,
                    "enddt": enddt,
                    "creator": user_uid
                }).execute()

        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "fail"}, status=400)

def search_help(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({"status": "fail", "error": "Invalid JSON"}, status=400)

        url = data.get("url")

        response = supabase.schema("genquery").table("helps").select("*").eq("url", url).execute().data or []

        # JsonResponse로 반환
        return JsonResponse({
            "status": "success",
            "data": response
        })
    else:
        return JsonResponse({"status": "fail", "error": "POST 요청만 허용됩니다."}, status=400)