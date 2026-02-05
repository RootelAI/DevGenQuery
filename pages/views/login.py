import urllib.parse
import urllib.request

from django.http import JsonResponse
from django.shortcuts import render, redirect, resolve_url
from django.contrib import messages

from utilsPrj.supabase_client import get_supabase_client
import json

def is_url_valid(url):
    """Check if a given signed URL is still valid (e.g. not expired)."""
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request) as response:
            return response.status == 200
    except Exception as e:
        return False

def login_view(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        next_url = request.GET.get("next") or request.POST.get("next") or resolve_url('home')

        try:
            user_check_response =supabase.schema("genquery").table("users").select("email").eq("email", email).execute()

            if not user_check_response or not user_check_response.data:
                messages.error(request, "로그인 실패: 존재하지 않는 사용자입니다.")
                return JsonResponse({
                    'result': 'Failed',
                    'message': '로그인 실패: 존재하지 않는 사용자입니다.'
                })

            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user = auth_response.user
            session = auth_response.session

            request.session["access_token"] = session.access_token
            request.session["refresh_token"] = session.refresh_token

            user_projects = set_session(request, user, 'login')

            # ✅ Step 8. 응답 처리
            if not user_projects:
                return JsonResponse({
                    'result': 'success',
                    'message': '로그인 성공. 단, 속한 프로젝트가 없습니다. 관리자에 연락바랍니다.',
                    'next': next_url,
                })
            else:
                return JsonResponse({
                    'result': 'success',
                    'message': '로그인 성공',
                    'next': next_url,
                })

        except Exception as e:
            messages.error(request, f"로그인 실패: {str(e)}")
            return JsonResponse({'result': 'Failed', 'message': f'로그인 실패: {str(e)}'})

    next_url = request.GET.get("next", "")
    return JsonResponse({'result': 'success', 'message': '로그인 성공.'})


# 타 영역에서도 사용할 가능성이 있으므로 모듈화 처리
def set_session(request, user, type):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        user_id = user.id

        # ✅ Step 1. 사용자 roleid 조회
        user_data_response = supabase.schema("genquery").table("users") \
            .select("roleid, billingmodelcd") \
            .eq("useruid", user_id) \
            .single() \
            .execute()

        roleid = None
        billingmodelcd = None
        tenantmanager = 'N'
        projectmanager = 'N'
        editbuttonyn = 'Y'
        tenanticonurl = None

        if user_data_response.data:
            roleid = user_data_response.data.get("roleid")
            billingmodelcd = user_data_response.data.get("billingmodelcd")

        # ✅ Step 5. 프로젝트 및 테넌트 정보 조회
        user_project_response = supabase.schema("genquery").table("projectusers") \
            .select("*").eq("useruid", user_id).execute()
        user_projects = user_project_response.data

        user_tenant_response = supabase.schema("genquery").table("tenantusers") \
            .select("*").eq("useruid", user_id).execute()
        user_tenant = user_tenant_response.data

        tenants_response = supabase.schema("genquery").table("tenants") \
            .select("*").execute()
        tenants = tenants_response.data

        # tenants에 존재하는 tenantid set 생성
        valid_tenant_ids = {str(t["tenantid"]) for t in tenants}

        # user_tenant 중에서 실제 존재하는 tenant만 필터
        matched_tenants = [
            str(ut["tenantid"])
            for ut in user_tenant
            if str(ut["tenantid"]) in valid_tenant_ids
        ]

        # 최종 tenantid 1개 선택
        tenantid = matched_tenants[0] if matched_tenants else None

        if tenantid:
            matched_tenant = next(
                (t for t in tenants if str(t["tenantid"]) == str(tenantid)),
                None
            )
            if matched_tenant:
                tenanticonurl = matched_tenant.get("iconfileurl")


        # ✅ Step 6. 권한 플래그 세팅
        if user_projects and any(p.get("rolecd") == "M" for p in user_projects):
            projectmanager = 'Y'
        if user_tenant and any(t.get("rolecd") == "M" for t in user_tenant):
            tenantmanager = 'Y'
         
        # ✅ Step 7. 세션 저장
        datas = {
            "id": user_id,
            "email": user.email,
            "roleid": roleid,
            "billingmodelcd" : billingmodelcd,
            "tenantid": tenantid,
            "tenantmanager": tenantmanager,
            "tenanticonurl": tenanticonurl,   # ⭐ 추가
            "projectmanager": projectmanager,
            "editbuttonyn" : editbuttonyn,
        }

        if type == 'login':
            request.session["user"] = datas
        elif type == 'tenant_setting':
            request.session["user"].update(datas)

        return user_projects

    except Exception as e:
        messages.error(request, f"로그인 실패: {str(e)}")
        return JsonResponse({'result': 'Failed', 'message': f'로그인 실패: {str(e)}'})

def logout_view(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")


    supabase = get_supabase_client(access_token, refresh_token)

    try:
        supabase.auth.sign_out()
    except Exception as e:
         pass  # 이미 만료된 세션 등

    request.session.flush()
    return redirect("home")

def send_reset_email(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    if request.method == "POST":
        # AJAX 요청이면 request.body, 일반 form이면 request.POST
        if request.content_type == "application/json":
            import json
            data = json.loads(request.body)
            email = data.get("email", "").strip()
        else:
            email = request.POST.get("reset_email", "").strip()

        if not email:
            message = "이메일을 입력해주세요."
            if request.content_type == "application/json":
                return JsonResponse({"ok": False, "messages": message})
            else:
                messages.error(request, message)
                return redirect("login")

        try:
            redirect_url = "https://dev-smart-doc.azurewebsites.net/password-reset/"
            # redirect_url = "http://localhost:8000/password-reset/"
            supabase.auth.reset_password_email(email, {"redirect_to": redirect_url})
            message = "비밀번호 재설정 링크가 이메일로 발송되었습니다."

            if request.content_type == "application/json":
                return JsonResponse({"ok": True, "messages": message})
            else:
                messages.success(request, message)
                return redirect("login")

        except Exception as e:
            message = f"메일 발송 실패: {str(e)}"
            if request.content_type == "application/json":
                return JsonResponse({"ok": False, "messages": message})
            else:
                messages.error(request, message)
                return redirect("login")
            