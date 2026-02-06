# master_object.py
import json
from dateutil import parser
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from urllib.parse import urlparse

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value

def master_tenant_request_list(request):
    # 세션 토큰
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        code = 'login'
        text = '로그인이 필요합니다.'
        page = "master_object"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    # user_id = user.get("id")
    
    tenantreqs = supabase.schema("genquery").table("tenantreqs").select("*").execute().data
    for i in tenantreqs:
        # 복호화
        if i.get('encemail'):
            try:
                i['email'] = decrypt_value(i['encemail'])
            except Exception as e:
                # print(e)
                i['email'] = ''
        if i.get('enctelno'):
            try:
                i['telno'] = decrypt_value(i['enctelno'])
            except Exception as e:
                i['telno'] = ''
        # 시간 포맷 정리
        if i.get('createdts'):
            try:
                dt = parser.parse(i['createdts']) if isinstance(i['createdts'], str) else i['createdts']
                i['createdts'] = dt.strftime("%y-%m-%d %H:%M")
            except Exception as e:
                i['createdts'] = ''
    
    return render(request, 'pages/master_tenant_request_list.html', {
        'user' : user,
        'tenantreqs': tenantreqs,
    })

def master_tenant_request_list_save (request):
    # print('master_object_save_object 진입')
    # 세션 토큰
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return render(request, 'pages/home.html')
    
    if not user:
        # return JsonResponse({"result": "Failed", "message": "로그인이 필요합니다. 로그인 부탁드립니다."})
        # return redirect("login")
        code = 'login'
        text = '로그인이 필요합니다.'
        page = "master_chapter_template"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")
    
    if request.method == "POST":
        body = json.loads(request.body)
        chapteruid = body.get("chapteruid")
        

    return JsonResponse({"result": "error", "message": "잘못된 요청"}, status=400)