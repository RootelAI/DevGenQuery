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

def master_projects(request):
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
        page = "master_projects"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")


    tenantid = request.GET.get('tenantid')

    if not tenantid:
        users = supabase.schema("genquery").table("tenantusers") \
            .select("tenantid").eq("useruid", user_id).eq("useyn", True).execute()

        if users.data and len(users.data) > 0:
            tenantid = users.data[0]['tenantid']
        else:
            tenantid = None  # 또는 0 으로 기본값 지정 가능

    try:# projects 테이블에서 데이터 조회
        response = supabase.schema('genquery').table('projects').select('*').eq('tenantid', tenantid).order('createdts', desc=True).execute()
        projects = response.data if response.data else []
         
        tenantnm = supabase.schema('genquery').table('tenants').select('*').eq('tenantid', tenantid).execute().data[0]['tenantnm']
        
        for i in projects:
            if i.get('createdts'):
                try:
                    dt = parser.parse(i['createdts']) if isinstance(i['createdts'], str) else i['createdts']
                    i['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    i['createdts'] = ''
            if i.get('creator'):
                try:
                    creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
                    i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                except Exception as e:
                    i['creatornm'] = ''

        azure_key_vault_response = supabase.schema('genquery').table('azure_key_vault').select('*').eq('tenantid', tenantid).order('createdts', desc=True).execute()
        azure_key_vault = azure_key_vault_response.data if azure_key_vault_response.data else []

        context = {
            'projects': projects,
            'tenantnm': tenantnm,
            'total_count': len(projects),
            'active_count': len([g for g in projects if g.get('is_active', False)]),
            'azure_key_vault' : azure_key_vault,
        }
        
        return render(request, 'pages/master_projects.html', context)
        
    except Exception as e:
        logger.error(f"프로젝트 조회 중 오류 발생: {e}")
        return render(request, 'pages/master_projects.html', {
            'projects': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_projects_save(request):
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
            page = "master_projects"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        
        # POST 데이터에서 프로젝트 정보 추출
        tenantid = request.POST.get('tenantid')
        projectid = request.POST.get('projectid')
        projectnm = request.POST.get('projectnm')
        useyn = request.POST.get('useyn')
        projectdesc = request.POST.get('projectdesc')
        access_key_uid  = request.POST.get('access_key_uid')
              
        if not tenantid:
            users = supabase.schema("genquery").table("tenantusers") \
                .select("tenantid").eq("useruid", user_id).eq("useyn", True).execute()

            if users.data and len(users.data) > 0:
                tenantid = users.data[0]['tenantid']
            else:
                tenantid = None  # 또는 0 으로 기본값 지정 가능

        if useyn == 'on':
            useyn = True
        else:
            useyn = False
            
        if not projectnm:
            return JsonResponse({
                'success': False,
                'error': '프로젝트명은 필수입니다.'
            })
        
        # 기존 존재 여부 파악
        existing = None
        if projectid:
            resp = supabase.schema("genquery").table("projects").select("*").eq("projectid", projectid).execute()
            existing = resp.data[0] if resp.data else None
        
        data = {
            "projectnm": projectnm,
            "useyn": useyn,
            "tenantid": tenantid,
            "projectdesc": projectdesc,
            "creator": user_id,
            "access_key_uid" : access_key_uid 
        }

        if existing:
            response = supabase.schema('genquery').table('projects').update(data).eq('projectid', projectid).execute()
        else:
            data["creator"] = user_id
            response = supabase.schema('genquery').table('projects').insert(data).execute()
        
        if response.data:
            return JsonResponse({
                'result': 'success',
                'group': response.data[0],
                'message': '프로젝트가 성공적으로 저장되었습니다.'
            })
        else:
            return JsonResponse({
                'result': 'Failed',
                'error': '프로젝트 저장에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"프로젝트 저장 중 오류 발생: {e}")
        print(e)
        return JsonResponse({
            'result': 'Failed',
            'error': f'프로젝트 저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_projects_delete(request):
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
            page = "master_projects"
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
        
        # 프로젝트 상태 업데이트
        supabase.schema('genquery').table('projects').delete().eq('projectid', projectid).execute()
        
        return JsonResponse({'result': 'success', 'message': '프로젝트가 성공적으로 삭제되었습니다.'})
            
    except Exception as e:
        logger.error(f"프로젝트 삭제 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })