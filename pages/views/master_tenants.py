# views.py
import json
from dateutil import parser
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from urllib.parse import urlparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_http_methods
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
import logging
from .master_tenant_request import save_iconfile
from utilsPrj.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

def master_tenants(request):
    """기업 관리 메인 페이지"""
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
        page = "master_tenants"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")

    try:# tenants 테이블에서 데이터 조회
        response = supabase.schema('genquery').table('tenants').select('*').order('createdts', desc=True).execute()       
        tenants = response.data if response.data else []
        
        billmasters_response = supabase.schema('genquery').table('billmasters').select('*').execute()       
        billmasters = billmasters_response.data if billmasters_response.data else []

        bill_map = {}
        for bill in billmasters:
            tenantid = bill.get("tenantid")
            if tenantid:
                bill_map[tenantid] = bill

        for tenant in tenants:

            # 생성일시 포맷
            if tenant.get('createdts'):
                try:
                    dt = parser.parse(tenant['createdts']) if isinstance(tenant['createdts'], str) else tenant['createdts']
                    tenant['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception:
                    tenant['createdts'] = ''

            # 생성자 이름
            if tenant.get('creator'):
                try:
                    creatornm = (
                        supabase.schema('public')
                        .table('users')
                        .select('full_name')
                        .eq('useruid', tenant['creator'])
                        .execute()
                        .data
                    )
                    tenant['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                except Exception:
                    tenant['creatornm'] = ''

            # 5️⃣ billmasters 정보 붙이기
            bill = bill_map.get(tenant.get("tenantid"))

            if bill:
                tenant["encemail"] = bill.get("encemail")
                tenant["enctelno"] = bill.get("enctelno")

                # ✅ 복호화
                tenant["decemail"] = decrypt_value(bill["encemail"]) if bill.get("encemail") else ""
                tenant["dectelno"] = decrypt_value(bill["enctelno"]) if bill.get("enctelno") else ""
            else:
                tenant["encemail"] = ""
                tenant["enctelno"] = ""
                tenant["decemail"] = ""
                tenant["dectelno"] = ""

        context = {
            'tenants': tenants,
            # 'total_count': len(tenants),
            # 'active_count': len([g for g in tenants if g.get('is_active', False)]),
        }
        # print("tenants", tenants)
        return render(request, 'pages/master_tenants.html', context)
        
    except Exception as e:
        logger.error(f"기업 조회 중 오류 발생: {e}")
        return render(request, 'pages/master_tenants.html', {
            'tenants': [],
            'message': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_tenants_save(request):
    """새 기업 생성 (필요시 사용)"""
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
            page = "master_tenants"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")

        # POST 데이터에서 기업 정보 추출
        tenantid = request.POST.get('tenantid')
        tenantnm = request.POST.get('tenantnm')
        billingmodelcd = request.POST.get("billingmodelcd")
        billingusercnt = request.POST.get("billingusercnt")
        email = request.POST.get("email")
        telno = request.POST.get("telno")
        encemail = encrypt_value(email)
        enctelno = encrypt_value(telno)
        # 파일 업로드 처리 (추가)
        iconfile = request.FILES.get("iconfile")

        useyn = request.POST.get('useyn')
        if useyn == 'on':
            useyn = True
        else:
            useyn = False
            
        llmlimityn = request.POST.get('llmlimityn')
        if llmlimityn == 'on':
            llmlimityn = True
        else:
            llmlimityn = False

        if not tenantnm:
            return JsonResponse({
                'result': 'Failed',
                'message': '기업명은 필수입니다.'
            })
              
        # 기존 존재 여부 파악
        existing = None
        if tenantid:
            resp = supabase.schema("genquery").table("tenants").select("*").eq("tenantid", tenantid).execute()
            existing = resp.data[0] if resp.data else None

        # 설정 호출
        configs = supabase.schema("genquery").table("configs").select("*").execute().data

        data = {
            "tenantnm": tenantnm,
            "useyn": useyn,
            "billingusercnt": billingusercnt,
            "llmlimityn": llmlimityn,
            "billingmodelcd" : billingmodelcd,
            "creator":user_id,
            "llmmodeluseyn":False,
        }

        if existing:
            response = supabase.schema('genquery').table('tenants').update(data).eq('tenantid', tenantid).execute()

            # 기존 iconfileurl 가져오기
            iconfileurl_response = supabase.schema("genquery").table("tenants").select("iconfileurl").eq("tenantid", tenantid).execute()
            iconfileurl = iconfileurl_response.data[0]["iconfileurl"] if iconfileurl_response.data else None

            # =============================
            # 기업 아이콘 파일 업로드 처리
            # =============================
            if iconfile:
                file_nm, file_url = save_iconfile(
                    supabase,
                    iconfile,
                    folder="iconfiles/tenants",
                    existing_url=iconfileurl,
                )

                supabase.schema("genquery") \
                    .table("tenants") \
                    .update({
                        "iconfilenm": file_nm,
                        "iconfileurl": file_url
                    }) \
                    .eq("tenantid", tenantid) \
                    .execute()
            
        else:
            existingnm = None
            resp = supabase.schema("genquery").table("tenants").select("*").eq("tenantnm", tenantnm).execute()
            existingnm = resp.data[0] if resp.data else None

            if existingnm:
                return JsonResponse({
                    'result': 'Failed',
                    'message': '이미 존재하고 있는 기업명입니다.'
                })
            
            response = supabase.schema('genquery').table('tenants').insert(data).execute().data
            new_tenantid = response[0]['tenantid']

            # =============================
            # 기업 아이콘 파일 업로드 처리
            # =============================
            if iconfile:
                file_nm, file_url = save_iconfile(
                    supabase,
                    iconfile,
                    folder="iconfiles/tenants"
                )

                supabase.schema("genquery") \
                    .table("tenants") \
                    .update({
                        "iconfilenm": file_nm,
                        "iconfileurl": file_url
                    }) \
                    .eq("tenantid", new_tenantid) \
                    .execute()


            # print(response)
            data = {
                "tenantid": new_tenantid,
                "projectnm": 'public',
                "projectdesc": '공용',
                "useyn": True,
                "creator": user_id
            }
            # print(data)
            response = supabase.schema('genquery').table('projects').insert(data).execute()

            now_dt = datetime.now().strftime("%Y-%m-%d")
            now_1M = datetime.now() + relativedelta(months=1) - relativedelta(days=1)
            now_dt_1M = now_1M.strftime("%Y-%m-%d")

            config_price = configs[0]['priceenterprise']
            config_inputtokencapa = configs[0]['inputtokencapa']
            inputtokencapa = int(config_inputtokencapa) * int(billingusercnt)

            billmaster = {
                "billtargetcd": 'T',
                "tenantid": new_tenantid,
                "billingmodelcd": 'En',
                "billingfirstdt": now_dt,
                "useyn": True,
                "encemail": encemail,
                "enctelno": enctelno,
                "creator": user_id
            }

            supabase.schema("genquery").table("billmasters").insert(billmaster).execute()

            billdts = {
                "billtargetcd": 'T',
                "tenantid": new_tenantid,
                "billstartdt": now_dt,
                "billenddt": now_dt_1M,
                "billingmodelcd": 'En',
                "inputtokencapa": inputtokencapa,
                "inputtoken": 0,
                "overtokenm": 0,
                "serviceamt": config_price,
                "addamt": 0,
                "creator": user_id
            }

            supabase.schema("genquery").table("billdts").insert(billdts).execute()

            tokentenants = {
                "tenantid": new_tenantid,
                "billstartdt": now_dt,
                "runcnt": 0,
                "inputtoken": 0,
                "inputtokencapa": inputtokencapa,
            }

            supabase.schema("genquery").table("tokentenants").insert(tokentenants).execute()

            tenantusermonths = {
                "billstartdt": now_dt,
                "tenantid": new_tenantid,
                "useruid": user_id,
                "recordtypecd": 'N',
                "creator": user_id
            }

            supabase.schema('genquery').table('tenantusermonths').insert(tenantusermonths).execute()

        if response.data:
            return JsonResponse({
                'result': 'success',
                'tenant': response.data[0],
                'message': '기업이 성공적으로 저장되었습니다.'
            })
        else:
            return JsonResponse({
                'result': 'Failed',
                'message': '기업 저장에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"기업 저장 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'기업 저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_tenants_delete(request):
    """기업 활성/비활성 상태 변경 (필요시 사용)"""
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
            page = "master_tenants"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 기업 정보 추출
        data = json.loads(request.body)
        tenantid = data.get('tenantid')
                
        # =============================
        # 기업 아이콘 파일 삭제
        # =============================
        tenant_resp = supabase.schema("genquery").table("tenants") \
            .select("iconfileurl") \
            .eq("tenantid", tenantid) \
            .single() \
            .execute()

        iconfileurl = tenant_resp.data.get("iconfileurl") if tenant_resp.data else None

        # 기존 파일 삭제
        if iconfileurl:
            try:
                parsed = urlparse(iconfileurl)
                storage_prefix = "/storage/v1/object/public/genquery/"
                if storage_prefix in parsed.path:
                    path_to_delete = parsed.path.split(storage_prefix)[-1]
                    supabase.storage.from_("genquery").remove([path_to_delete])
            except Exception as e:
                print("⚠️ 기존 파일 삭제 오류:", str(e))


        # 1️⃣ 해당 tenant의 모든 projects 조회
        projects_resp = supabase.schema('genquery').table('projects').select('projectid').eq('tenantid', tenantid).execute()
        projects = projects_resp.data or []

        # 2️⃣ 각 project에 대해 projectusers 삭제
        for p in projects:
            projectid = p.get('projectid')
            if projectid:
                supabase.schema('genquery').table('projectusers').delete().eq('projectid', projectid).execute()

        # 3️⃣ projects 전체 삭제
        supabase.schema('genquery').table('projects').delete().eq('tenantid', tenantid).execute()

        # 4️⃣ tenant 삭제
        supabase.schema('genquery').table('tenants').delete().eq('tenantid', tenantid).execute()
        
        return JsonResponse({'result': 'success', 'message': '기업 및 관련 데이터가 모두 삭제되었습니다.'})

            
    except Exception as e:
        logger.error(f"기업 삭제 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })