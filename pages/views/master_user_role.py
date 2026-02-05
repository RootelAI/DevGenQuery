import json
import urllib.parse
from django.http import JsonResponse
from django.shortcuts import render, redirect

from utilsPrj.supabase_client import get_service_client

def master_user_role(request):
    # access_token = request.session.get("access_token")
    # refresh_token = request.session.get("refresh_token")

    supabase = get_service_client()

    user = request.session.get("user")
    if not user:
        return redirect("login")

    user_data_response = supabase.schema("genquery").table("users") \
        .select("useruid, roleid, email") \
        .order("email") \
        .execute()

    users = user_data_response.data if user_data_response.data else []

    role_map = {
        1: "일반유저",
        5: "Power User",
        7: "관리자"
    }

    for u in users:
        u["role_name"] = role_map.get(u.get("roleid", 1), "일반유저")

    context = {
        "users": users
    }

    return render(request, 'pages/master_user_role.html', context)


def master_user_role_save(request):
    # access_token = request.session.get("access_token")
    # refresh_token = request.session.get("refresh_token")

    supabase = get_service_client()

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            useruid = data.get("useruid")
            roleid = data.get("roleid")

            response = supabase.schema("genquery").table("users") \
                .update({"roleid": roleid}).eq("useruid", useruid).execute()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=405)
