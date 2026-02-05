# views.py
import json
from dateutil import parser
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from urllib.parse import urlparse

from django.views.decorators.http import require_http_methods
import logging

from utilsPrj.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

def master_project_users(request):
    """프로젝트 관리 메인 페이지"""
    # 세션 토큰
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")

    if not user:
        # return JsonResponse({"result": "Failed", "message": "로그인이 필요합니다. 로그인 부탁드립니다."})
        # return redirect("login")
        code = 'login'
        text = '로그인이 필요합니다.'
        page = "master_projectusers"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")
    
    tenantmanager = request.session.get("user", {}).get("tenantmanager")

    if tenantmanager == "Y":
        projects = supabase.schema('genquery').rpc("fn_allproject_filtered__r_user_manager", {'p_useruid': user_id}).execute().data
    else:
        # 사용자가 속한 전체 프로젝트 조회
        projects = supabase.schema('genquery').rpc("fn_project_filtered__r_user_manager", {'p_useruid': user_id}).execute().data

    # 없을 수 있음
    projectid = request.GET.get('projects')

    # 프로젝트가 1개만 존재하면 자동 선택
    if not projectid and projects and len(projects) == 1:
        projectid = projects[0]['projectid']

    try:# projectusers 테이블에서 데이터 조회
        if projectid:
            projectnm = supabase.schema('genquery').table('projects').select('*').eq('projectid', projectid).execute().data[0]['projectnm']

            response = supabase.schema('genquery').table('projectusers').select('*').eq('projectid', projectid).order('useruid', desc=True).execute()

            projectusers = response.data if response.data else []
            
            for i in projectusers:
                if i.get('createdts'):
                    try:
                        dt = parser.parse(i['createdts']) if isinstance(i['createdts'], str) else i['createdts']
                        i['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                    except Exception as e:
                        i['createdts'] = ''
                if i.get('useruid'):
                    try:
                        user = supabase.schema('public').table('users').select('*').eq('useruid', i['useruid']).execute().data
                        i['usernm'] = user[0]['full_name']
                        i['email'] = user[0]['email']
                    except Exception as e:
                        i['usernm'] = ''
                if i.get('creator'):
                    try:
                        creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
                        i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                    except Exception as e:
                        i['creatornm'] = ''

            tenantusers = supabase.schema('genquery').rpc("fn_tenantusers_notin_projectusers__r", {'p_projectid': projectid}).execute().data

            for i in tenantusers:
                if i.get('useruid'):
                    try:
                        user = supabase.schema('public').table('users').select('*').eq('useruid', i['useruid']).execute().data
                        i['usernm'] = user[0]['full_name']
                        i['email'] = user[0]['email']
                    except Exception as e:
                        i['usernm'] = ''
        else:
            projectnm = None
            projectusers = []
            tenantusers = []

        context = {
            'projects': projects,
            'projectid': projectid,
            'projectnm': projectnm,
            'projectusers': projectusers,
            'tenantusers': tenantusers,
        }
        

        return render(request, 'pages/master_project_users.html', context)
        
    except Exception as e:
        logger.error(f"프로젝트 조회 중 오류 발생: {e}")
        return render(request, 'pages/master_project_users.html', {
            'projectusers': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_project_users_save(request):
    """새 프로젝트 생성 (필요시 사용)"""
    try:
        # 세션 토큰
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        user = request.session.get("user")
        if not user:
            # return JsonResponse({"result": "Failed", "message": "로그인이 필요합니다. 로그인 부탁드립니다."})
            # return redirect("login")
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "master_projectusers"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 프로젝트 정보 추출
        projectid = request.POST.get('projectid')
        usernm = request.POST.get('usernm')
        email = request.POST.get('email')
        useyn = request.POST.get('useyn')
        rolecd = request.POST.get("rolecd")

        if useyn == 'on':
            useyn = True
        else:
            useyn = False
            
        if not email:
            return JsonResponse({
                'success': False,
                'message': '이메일은 필수입니다.'
            })
        
        user = supabase.schema('public').table('users').select('*').eq('email', email).execute().data
        # 존재 여부 체크
        if not user:
            return JsonResponse({
                'result': 'Failed',
                'message': '존재하지 않는 이메일입니다.'
            })
        
        useruid = user[0]['useruid']
        
        # 기존 존재 여부 파악
        existing = None
        if projectid:
            resp = supabase.schema("genquery").table("projectusers").select("*").eq("projectid", projectid).eq('useruid', useruid).execute()
            existing = resp.data[0] if resp.data else None
        
        data = {
            "projectid": projectid,
            "useruid": useruid,
            "useyn": useyn,
            "rolecd":rolecd
        }

        if existing:
            response = supabase.schema('genquery').table('projectusers').update(data).eq('projectid', projectid).eq('useruid', useruid).execute()
        else:
            data["creator"] = user_id
            response = supabase.schema('genquery').table('projectusers').insert(data).execute()
        
        if response.data:
            return JsonResponse({
                'result': 'success',
                'project': response.data[0],
                'message': '사용자가 성공적으로 저장되었습니다.'
            })
        else:
            return JsonResponse({
                'result': 'Failed',
                'message': '사용자 저장에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"사용자 저장 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'사용자 저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_project_users_delete(request):
    """프로젝트 활성/비활성 상태 변경 (필요시 사용)"""
    try:
        # 세션 토큰
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        user = request.session.get("user")
        if not user:
            # return JsonResponse({"result": "Failed", "message": "로그인이 필요합니다. 로그인 부탁드립니다."})
            # return redirect("login")
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "master_projectusers"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 프로젝트 정보 추출
        data = json.loads(request.body)
        projectid = data.get('projectid')
        useruid = data.get('useruid')
        
        # 프로젝트 상태 업데이트
        supabase.schema('genquery').table('projectusers').delete().eq('projectid', projectid).eq('useruid', useruid).execute()
        
        return JsonResponse({'result': 'success', 'message': '사용자가 성공적으로 삭제되었습니다.'})
            
    except Exception as e:
        logger.error(f"사용자 삭제 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'사용자 삭제 중 오류가 발생했습니다: {str(e)}'
        })