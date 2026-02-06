import os, json
from django.shortcuts import render
from django.http import JsonResponse
from dateutil import parser

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from django.views.decorators.http import require_http_methods

def master_llmapis(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)
    
    # 사용 하는 항목만 추출
    llmmodels_resp = supabase.schema("genquery").table("llmmodels").select("*").eq("useyn", True).order("llmvendornm").order("llmmodelnm").execute()
    llmmodels = llmmodels_resp.data if llmmodels_resp.data else []

    for llmmodel in llmmodels:
        try:
            # 날짜 포멧팅
            if llmmodel.get('createdts'):
                try:
                    dt = parser.parse(llmmodel['createdts']) if isinstance(llmmodel['createdts'], str) else llmmodel['createdts']
                    llmmodel['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    llmmodel['createdts'] = ''
            if llmmodel.get('creator'):
                try:
                    llmmodel['createuser'] = supabase.schema('public').table('users').select("*").eq("useruid", llmmodel['creator']).execute().data[0]['full_name']
                except Exception as e:
                    llmmodel['createuser'] = ''
        except Exception as e:
            print('Convert Error')

    # 사용 하는 항목들의 모델명만 추출
    llmmodel_ids = [llmmodel["llmmodelnm"] for llmmodel in llmmodels if "llmmodelnm" in llmmodel]
    
    # apis 리스트 중 사용 처리된 항목만 표시
    llmapis_resp = supabase.schema("genquery").table("llmapis").select("*").in_("llmmodelnm", llmmodel_ids).order("llmmodelnm").order("usetypecd").execute()
    llmapis = llmapis_resp.data if llmapis_resp.data else []

    for llmapi in llmapis:
        try:
            # 날짜 포멧팅
            if llmapi.get('createdts'):
                try:
                    dt = parser.parse(llmapi['createdts']) if isinstance(llmapi['createdts'], str) else llmapi['createdts']
                    llmapi['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    llmapi['createdts'] = ''
            if llmapi.get('creator'):
                try:
                    llmapi['createuser'] = supabase.schema('public').table('users').select("*").eq("useruid", llmapi['creator']).execute().data[0]['full_name']
                except Exception as e:
                    llmapi['createuser'] = ''
            if llmapi.get('usetypecd'):
                try:
                    if llmapi['usetypecd'] == 'R':
                        llmapi['usetypenm'] = 'Round'
                    elif llmapi['usetypecd'] == 'D':
                        llmapi['usetypenm'] = 'Direct'
                    elif llmapi['usetypecd'] == 'N':
                        llmapi['usetypenm'] = 'No'
                except Exception as e:
                    llmapi['usetypenm'] = ''
        except Exception as e:
            print('Convert Error')

    # 사용하는 기업 리스트 추출
    tenants_resp = supabase.schema("genquery").table("tenants").select("*").eq("useyn", True).neq("defaultyn", True).order("tenantid").execute()
    tenants = tenants_resp.data if tenants_resp.data else []
            
    user = request.session.get("user")
    user_id = user.get("id")

    # print(llmmodels)
    return render(request, 'pages/master_llmapis.html', {
        'tenants': tenants,
        'llmmodels': llmmodels,
        'llmapis': llmapis
    })

@require_http_methods(["POST"])
def master_llmapis_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)
    # print('llm Save 진입')

    try:
        llmapiuid = request.POST.get("llmapiuid")
        llmmodelnm = request.POST.get("llmmodelnm")
        apikey = request.POST.get("apikey", "").strip()
        # 공백 시 기존 API Key 사용
        if llmapiuid:
            if apikey == "":
                # print('기존 API 사용')
                orig_apikey = supabase.schema('genquery').table('llmapis').select("*").eq("llmapiuid", llmapiuid).execute().data
                if orig_apikey:
                    apikey = decrypt_value(orig_apikey[0]['encapikey'])

        usetypecd = request.POST.get('usetypecd')
        desc = request.POST.get('desc')

        encapikey = encrypt_value(apikey)
        user = request.session.get("user")
        user_id = user.get("id")


        upsert_data = {
            "llmmodelnm": llmmodelnm,
            "encapikey": encapikey,
            "usetypecd": usetypecd,
            "desc": desc,
            "creator": user_id
        }

        if llmapiuid:
            upsert_data['llmapiuid'] = llmapiuid

        # print(upsert_data)
        supabase.schema("genquery").table("llmapis").upsert(upsert_data).execute()
        
        return JsonResponse({"result": "success", "message": "성공적으로 저장되었습니다."})

    except Exception as e:
        # print(e)
        return JsonResponse({"error": str(e)}, status=500)
    
def master_llmapis_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        data = json.loads(request.body)
        llmapiuid = data.get("llmapiuid")

        if not llmapiuid:
            return JsonResponse({"error": "LLM 선택은 필수입니다."}, status=400)

        # 삭제 수행
        supabase.schema("genquery").table("llmapis").delete().eq("llmapiuid", llmapiuid).execute()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
