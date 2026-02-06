import os, json
from django.shortcuts import render
from django.http import JsonResponse
from dateutil import parser

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from django.views.decorators.http import require_http_methods

def master_tenant_llms(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)
    
    # 테넌트 정보 구하기
    tenantid = request.session.get("user", {}).get("tenantid")
    tenant = supabase.schema("genquery").table("tenants").select("*").eq("tenantid", tenantid).execute().data[0]
    
    if tenant.get('createdts'):
        try:
            dt = parser.parse(tenant['createdts']) if isinstance(tenant['createdts'], str) else tenant['createdts']
            tenant['createdts'] = dt.strftime("%y-%m-%d %H:%M")
        except Exception as e:
            tenant['createdts'] = ''
    if tenant.get('creator'):
        try:
            tenant['createuser'] = supabase.schema('public').table('users').select("*").eq("useruid", tenant['creator']).execute().data[0]['full_name']
        except Exception as e:
            tenant['createuser'] = ''
    if tenant.get('llmmodelnm'):
        try:
            llmmodel = supabase.schema('genquery').table('llmmodels').select('*').eq("llmmodelnm", tenant['llmmodelnm']).execute().data
            tenant['llmmodelnicknm'] = llmmodel[0]['llmmodelnicknm']
            tenant['llmmodelactiveyn'] = llmmodel[0]['useyn']
        except Exception as e:
            tenant['llmmodelnicknm'] = tenant['llmmodelnm']
            tenant['llmmodelactiveyn'] = False

    
    # 프로젝트 정보 구하기
    projects = supabase.schema("genquery").table("projects").select("*").eq("tenantid", tenantid).order("projectnm").execute().data
    # 날짜 포맷팅
    for project in projects:
        if project.get('createdts'):
            try:
                dt = parser.parse(project['createdts']) if isinstance(project['createdts'], str) else project['createdts']
                project['createdts'] = dt.strftime("%y-%m-%d %H:%M")
            except Exception as e:
                project['createdts'] = ''
        if project.get('creator'):
            try:
                project['createuser'] = supabase.schema('public').table('users').select("*").eq("useruid", project['creator']).execute().data[0]['full_name']
            except Exception as e:
                project['createuser'] = ''
        if project.get('llmmodelnm'):
            try:
                llmmodel = supabase.schema('genquery').table('llmmodels').select('*').eq("llmmodelnm", project['llmmodelnm']).execute().data
                project['llmmodelnicknm'] = llmmodel[0]['llmmodelnicknm']
                project['llmmodelactiveyn'] = llmmodel[0]['useyn']
            except Exception as e:
                project['llmmodelnicknm'] = project['llmmodelnm']
                project['llmmodelactiveyn'] = False
    # print(f'Projects: {projects}')

    # llm 모델 정보 획득
    # llmmodels_resp = supabase.schema("genquery").table("llmmodels").select("*").eq("useyn", True).order("llmmodelnm").execute()
    llmmodels_resp = supabase.schema("genquery").table("llmmodels").select("*").order("llmmodelnm").execute()
    llmmodels = llmmodels_resp.data if llmmodels_resp.data else []
            
    user = request.session.get("user")
    user_id = user.get("id")

    return render(request, 'pages/master_tenant_llms.html', {
        'tenant': tenant,
        'projects' : projects,
        'llmmodels': llmmodels,
    })

@require_http_methods(["POST"])
def master_tenant_llms_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)
    # print('master_tenant_llms_save 진입')

    try:
        tenantid = request.POST.get("tenantid")
        projectid = request.POST.get("projectid")
        llmmodelnm = request.POST.get("llmmodelnm")
        apikey = request.POST.get("apikey", "").strip()
        # 공백 시 기존 API Key 사용
        if apikey == "":
            # orig_apikey = supabase.schema('genquery').table('llmmodels').select("*").eq("llmmodelnm", llmmodelnm).execute().data
            if tenantid != "":
                orig_apikey = supabase.schema('genquery').table('tenants').select("*").eq("tenantid", tenantid).execute().data
            elif projectid != "":
                orig_apikey = supabase.schema('genquery').table('projects').select("*").eq("projectid", projectid).execute().data

            if orig_apikey:
                apikey = decrypt_value(orig_apikey[0]['encapikey'])

        encapikey = encrypt_value(apikey)

        user = request.session.get("user")
        user_id = user.get("id")
        # tenantid = user.get("tenantid")

        # print(f'TenanID: {tenantid} / ProjectID: {projectid}')
        # print(f'LLMMOdel: {llmmodelnm}')
        # print(f'APIKey: {apikey} / EncAPIKey: {encapikey}')

        if apikey == "":
            # print('apikey 미 존재')
            llmmodelnm = None
            encapikey = None

        data = {
            "llmmodelnm": llmmodelnm,
            "encapikey": encapikey
        }

        if tenantid != "":
            # print('TenantID 가 있다')
            data["tenantid"] = tenantid

            # print(f'Data: {data}')
            supabase.schema("genquery").table("tenants").upsert(data).execute()

        elif projectid != "":
            # print('ProjectID 가 있다')
            data ["projectid"] = projectid
            
            # print(f'Data: {data}')
            supabase.schema("genquery").table("projects").upsert(data).execute()

        
        return JsonResponse({"result": "success", "message": "성공적으로 저장되었습니다."})

    except Exception as e:
        # print(e)
        return JsonResponse({"message": str(e)}, status=500)
    
def master_tenant_llms_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)
    # print('master_tenant_llms_delete 진입')

    try:
        data = json.loads(request.body)
        tenantid = data.get("tenantid")
        projectid = data.get("projectid")

        data = {
            "llmmodelnm": "",
            "encapikey": ""
        }

        if tenantid != "":
            # print('TenantID 가 있다')
            data["tenantid"] = tenantid

            # print(f'Data: {data}')
            supabase.schema("genquery").table("tenants").upsert(data).execute()

        elif projectid != "":
            # print('ProjectID 가 있다')
            data ["projectid"] = projectid
            
            # print(f'Data: {data}')
            supabase.schema("genquery").table("projects").upsert(data).execute()

        # 삭제 수행
        # supabase.schema("genquery").table("llmconnectors").delete().eq("connectorid", connectorid).execute()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
