import os, json
from django.shortcuts import render
from django.http import JsonResponse
from dateutil import parser
from django.views.decorators.http import require_http_methods

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from utilsPrj.llm_model import check_api_key    # jeff 20251202 0950

def master_llms(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)
    
    llmmodels_resp = supabase.schema("genquery").table("llmmodels").select("*").execute()
    llmmodels = llmmodels_resp.data if llmmodels_resp.data else []

    for llmmodel in llmmodels:
        try:
            # 복호화 처리 (값이 존재할 경우에만)
            if llmmodel.get("encapikey"):
                llmmodel["decapikey"] = decrypt_value(llmmodel["encapikey"])
            else:
                llmmodel["decapikey"] = ""
        except Exception as e:
            print('Convert Error')
            
    user = request.session.get("user")
    user_id = user.get("id")

    # tenants = supabase.schema("genquery").rpc("fn_user_tenants__r", {'p_useruid': user_id}).execute().data or []
    # 날짜 포맷팅
    for llm in llmmodels:
        if llm.get('createdts'):
            try:
                dt = parser.parse(llm['createdts']) if isinstance(llm['createdts'], str) else llm['createdts']
                llm['createdts'] = dt.strftime("%y-%m-%d %H:%M")
            except Exception as e:
                llm['createdts'] = ''
        if llm.get('creator'):
            try:
                llm['createuser'] = supabase.schema('public').table('users').select("*").eq("useruid", llm['creator']).execute().data[0]['full_name']
            except Exception as e:
                llm['createuser'] = ''

    # print(llmmodels)
    return render(request, 'pages/master_llms.html', {
        'llmmodels': llmmodels
    })

@require_http_methods(["POST"])
def master_llms_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)
    # print('llm Save 진입')

    try:
        
        llmmodelnm = request.POST.get("llmmodelnm")
        llmmodelnicknm = request.POST.get("llmmodelnicknm")
        apikey = request.POST.get("apikey", "").strip()

        # 공백 시 기존 API Key 사용
        if apikey == "":
            orig_apikey = supabase.schema('genquery').table('llmmodels').select("*").eq("llmmodelnm", llmmodelnm).execute().data
            if orig_apikey:
                apikey = decrypt_value(orig_apikey[0]['encapikey'])

        check_result_api_key = check_api_key(llmmodelnm, apikey)
        if check_result_api_key:
            useyn = request.POST.get("useyn") == "on"
            isdefault = request.POST.get("isdefault") == "on"
            encapikey = encrypt_value(apikey)
            # print(f'APIKey: {apikey} / EncAPIKey: {encapikey}')
            user = request.session.get("user")
            user_id = user.get("id")

            insert_data = {
                "llmmodelnm": llmmodelnm,
                "llmmodelnicknm": llmmodelnicknm,
                "encapikey": encapikey,
                "useyn": useyn,
                "isdefault":isdefault,
                "creator": user_id
            }
            supabase.schema("genquery").table("llmmodels").upsert(insert_data).execute()
            
            return JsonResponse({"result": "success", "message": "성공적으로 저장되었습니다."})
        else: 
            return JsonResponse({"result": "fail", "message": "API_KEY가 정확하지 않습니다. 다시 확인해 주십시요."})

    except Exception as e:
        print(e)
        return JsonResponse({"error": str(e)}, status=500)
    
def master_llms_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        data = json.loads(request.body)
        llmmodelnm = data.get("llmmodelnm")

        if not llmmodelnm:
            return JsonResponse({"error": "LLM 모델명은 필수입니다."}, status=400)

        # 삭제 수행
        supabase.schema("genquery").table("llmmodels") \
            .delete().eq("llmmodelnm", llmmodelnm).execute()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
