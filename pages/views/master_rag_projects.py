# views.py
import json
from dateutil import parser
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
import os
import re
from azure.storage.blob import BlobServiceClient
from utilsPrj.vectordb_builder_all import rebuild_vectordb

def master_rag_projects(request):
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
        page = "master_rag_projects"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")

    try:# projects 테이블에서 데이터 조회
        project_response = supabase.schema('rag').table('projects').select('*').order('createdts', desc=True).execute()
        projects = project_response.data if project_response.data else []

        # for proj in projects:
        #     proj["apikey"] = decrypt_value(proj["encapikey"])
            
        # for i in projects:
        #     if i.get('createdts'):
        #         try:
        #             dt = parser.parse(i['createdts']) if isinstance(i['createdts'], str) else i['createdts']
        #             i['createdts'] = dt.strftime("%y-%m-%d %H:%M")
        #         except Exception as e:
        #             i['createdts'] = ''
        #     if i.get('creator'):
        #         try:
        #             creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
        #             i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
        #         except Exception as e:
        #             i['creatornm'] = ''

        context = {
            'projects': projects,
        }
        
        return render(request, 'pages/master_rag_projects.html', context)
        
    except Exception as e:
        return render(request, 'pages/master_rag_projects.html', {
            'projects': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_rag_projects_save(request):
    """새 프로젝트 생성 (필요시 사용)"""
    try:
        # 세션 토큰
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)
        
        user = request.session.get("user")
        if not user:
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "master_rag_projects"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 프로젝트 정보 추출
        projectid = request.POST.get('projectid')
        projectnm = request.POST.get('projectnm')
        projectdesc = request.POST.get('projectdesc')
        useyn = request.POST.get('useyn')
        llmmodelnm  = request.POST.get('llmmodelnm')
        apikey  = request.POST.get('apikey')
        dirpath  = request.POST.get('dirpath')

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
            resp = supabase.schema("rag").table("projects").select("*").eq("projectid", projectid).execute()
            existing = resp.data[0] if resp.data else None
        
        data = {
            "projectnm": projectnm,
            "projectdesc": projectdesc,
            "useyn": useyn,
            "llmmodelnm" : llmmodelnm,
            "dirpath" : dirpath 
        }

        # ✅ apikey가 입력된 경우에만 업데이트
        if apikey:
            data["encapikey"] = encrypt_value(apikey)
            
        if existing:
            response = supabase.schema('rag').table('projects').update(data).eq('projectid', projectid).execute()
        else:
            # 새 프로젝트라면 Azure Blob 컨테이너 생성
            AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            
            # 컨테이너 이름은 소문자 + 공백을 '-'로, 특수문자 제거
            container_name = re.sub(r'[^a-z0-9-]', '', dirpath.lower().replace(" ", "-"))
            
            # 컨테이너 생성 (이미 존재하면 예외 발생 가능)
            blob_service_client.create_container(container_name)

            data["creator"] = user_id
            response = supabase.schema('rag').table('projects').insert(data).execute()

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
        return JsonResponse({
            'result': 'Failed',
            'error': f'프로젝트 저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_rag_projects_delete(request):
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
            page = "master_rag_projects"
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
        
        if not projectid:
            return JsonResponse({
                'result': 'Failed',
                'message': 'projectid가 없습니다.'
            })

        # 프로젝트 조회 (dirpath 확보)
        resp = supabase.schema('rag').table('projects') \
            .select('dirpath') \
            .eq('projectid', projectid) \
            .execute()

        if not resp.data:
            return JsonResponse({
                'result': 'Failed',
                'message': '프로젝트를 찾을 수 없습니다.'
            })

        dirpath = resp.data[0]['dirpath']
        
        # 프로젝트 상태 업데이트
        supabase.schema('rag').table('projects').delete().eq('projectid', projectid).execute()

        AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        # 생성할 때와 동일한 규칙으로 컨테이너 이름 계산
        container_name = re.sub(
            r'[^a-z0-9-]',
            '',
            dirpath.lower().replace(" ", "-")
        )

        blob_service_client.delete_container(container_name)

        return JsonResponse({'result': 'success', 'message': '프로젝트가 성공적으로 삭제되었습니다.'})
            
    except Exception as e:
        return JsonResponse({
            'result': 'Failed',
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_rag_vectordb_all(request):
    """프로젝트 단위로 vectordb 재적재"""
    try:
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        user = request.session.get("user")
        if not user:
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "master_rag_projects"
            return render(request, "pages/home.html", {
                "code": code,
                "text": text,
                "page": page,
                "request": request
            })
        user_id = user.get("id")

        # POST 데이터에서 projectid 추출
        data = json.loads(request.body)
        projectid = data.get('projectid')
        if not projectid:
            return JsonResponse({'result': 'Failed', 'message': 'projectid가 없습니다.'})

        # 프로젝트 조회 (dirpath 확보)
        project_resp = supabase.schema('rag').table('projects') \
            .select('dirpath') \
            .eq('projectid', projectid) \
            .execute()

        if not project_resp.data:
            return JsonResponse({'result': 'Failed', 'message': '프로젝트를 찾을 수 없습니다.'})

        dirpath = project_resp.data[0]['dirpath']
        # print("dirpath", dirpath)

        # =========================
        # 🔥 핵심: vectordb 재적재 호출
        # =========================
        rebuild_vectordb(dirpath)

        return JsonResponse({'result': 'success', 'message': f'{dirpath} vectordb 재적재 완료'})

    except Exception as e:
        return JsonResponse({'result': 'Failed', 'message': f'적재 중 오류가 발생했습니다: {str(e)}'})
