import os, json
from django.shortcuts import render
from django.http import JsonResponse
from dateutil import parser
from datetime import datetime
from dateutil.relativedelta import relativedelta

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from django.views.decorators.http import require_http_methods
from .login import set_session
import os, uuid
from urllib.parse import urlparse

def master_tenant_request(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)
    
    type = request.GET.get("type")
    
    # print(f'Type: {type}')
    if type == 'teams':
        user = request.session.get("user")
    
        if not user:
            # return JsonResponse({"result": "Failed", "message": "로그인이 필요합니다. 로그인 부탁드립니다."})
            # return redirect("login")
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "/master/tenant_request/?type=teams"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })  

    return render(request, 'pages/master_tenant_request.html', {"type": type})

@require_http_methods(["POST"])
def master_tenant_request_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)
    # print('master_tenant_llms_save 진입')

    try:
        type = request.POST.get("type")
        bizregno = request.POST.get("bizregno")
        tenantnm = request.POST.get("tenantnm")
        billingusercnt = request.POST.get("billingusercnt")
        llmlimityn = request.POST.get("llmlimityn")
        managernm = request.POST.get("managernm")
        managerdepart = request.POST.get("managerdepart")
        managerposition = request.POST.get("managerposition")
        email = request.POST.get("email")
        telno = request.POST.get("telno")
        bizregfile = request.FILES.get("bizregile")
        iconfile = request.FILES.get("iconfile")

        encemail = encrypt_value(email)
        enctelno = encrypt_value(telno)

        user = request.session.get("user")
        if user:
            user_id = user.get("id")
        else:
            user_id = None

        # print(f'BizRegNo: {bizregno} / TenantNm: {tenantnm} / BillingUserCnt: {billingusercnt} / LLMLimitYN: {llmlimityn}')
        # print(f'ManagerNm: {managernm} / ManagerDepart: {managerdepart} / ManagerPosition: {managerposition}')
        # print(f'Email: {email} / TelNo: {telno}')

        # 설정 호출
        configs = supabase.schema("genquery").table("configs").select("*").execute().data

        if type == "tenant":
            tenant = {
                "bizregno": bizregno,
                "tenantnm": tenantnm,
                "billingusercnt": billingusercnt,
                "llmlimityn": llmlimityn,
                "managernm": managernm,
                "managerdepart": managerdepart,
                "managerposition": managerposition,
                "encemail": encemail,
                "enctelno": enctelno,
                "creator": user_id
            }
            
            supabase.schema("genquery").table("tenantreqs").insert(tenant).execute()
                
        elif type == "teams":
            user = request.session.get("user")
            user_id = user.get("id")
            email = user.get("email")

            tenant = {
                "tenantnm": tenantnm,
                "useyn": True,
                "billingusercnt": billingusercnt,
                "llmlimityn": llmlimityn,
                "creator": user_id,
                "billingmodelcd" : "Te"
            }

            ten_exi = supabase.schema("genquery").table("tenants").select("*").eq("tenantnm", tenantnm).execute().data

            if ten_exi:
                # print('이미 존재??')
                return JsonResponse({"result": "false", "message": f"이미 존재하는 {tenantnm}명입니다."})

            respon = supabase.schema("genquery").table("tenants").insert(tenant).execute().data
            new_tenantid = respon[0]['tenantid']

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

            # 1. tenantusers 에서 useruid 기준 삭제
            supabase.schema("genquery") \
                .table("tenantusers") \
                .delete() \
                .eq("useruid", user_id) \
                .execute()


            # 2. projects 에서 projectnm(email) 조회
            project_res = supabase.schema("genquery") \
                .table("projects") \
                .select("projectid") \
                .eq("projectnm", email) \
                .execute()

            project_id = None

            if project_res.data and len(project_res.data) > 0:
                project_id = project_res.data[0]["projectid"]

                # projects 삭제
                supabase.schema("genquery") \
                    .table("projects") \
                    .delete() \
                    .eq("projectid", project_id) \
                    .execute()


            # 3. projectusers 에서 projectid 기준 삭제
            if project_id:
                supabase.schema("genquery") \
                    .table("projectusers") \
                    .delete() \
                    .eq("useruid", user_id) \
                    .execute()


            # 4. tenantusers insert
            master = {
                "tenantid": new_tenantid,
                "useruid": user_id,
                "rolecd": "M",
                "useyn": True,
                "creator": user_id
            }

            supabase.schema("genquery") \
                .table("tenantusers") \
                .insert(master) \
                .execute()

            supabase.schema("genquery") \
                .table("users") \
                .update({"billingmodelcd": "Te"}) \
                .eq("useruid", user_id) \
                .execute()

            #5. 문서삭제
            # 1~4 Free로 가입 후 Teams 생성요청한거라 Free일때의 Proejct및 관련 데이터 삭제(한 사용자가 두개의 Tenants에 가입 불가능하므로) 
            # Free일때 만든 문서 및 관련 정보 삭제 필요
            if project_id:
                supabase.schema("genquery") \
                    .table("docs") \
                    .delete() \
                    .eq("projectid", project_id) \
                    .execute()
                

            now = datetime.now().isoformat()
            now_dt = datetime.now().strftime("%Y-%m-%d")
            now_1M = datetime.now() + relativedelta(months=1) - relativedelta(days=1)
            now_dt_1M = now_1M.strftime("%Y-%m-%d")

            config_price = configs[0]['priceteams']
            config_inputtokencapa = configs[0]['inputtokencapa']
            inputtokencapa = int(config_inputtokencapa) * int(billingusercnt)

            billmaster = {
                "billtargetcd": 'T',
                "tenantid": new_tenantid,
                "billingmodelcd": 'Te',
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
                "billingmodelcd": 'Te',
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

            send_user = request.session.get("user")
            set_session(request, send_user, 'tenant_setting')
        # print(tenant)

        
        
        return JsonResponse({"result": "success", "message": "성공적으로 저장되었습니다.", "type": type})

    except Exception as e:
        # print(e)
        return JsonResponse({"message": str(e)}, status=500)
    
def save_iconfile(supabase, iconfile, folder, existing_url=None):
    """
    folder: iconfiles/reqtenants | iconfiles/tenants
    """
    # 기존 파일 삭제
    if existing_url:
        try:
            parsed = urlparse(existing_url)
            storage_prefix = "/storage/v1/object/public/genquery/"
            if storage_prefix in parsed.path:
                path_to_delete = parsed.path.split(storage_prefix)[-1]
                supabase.storage.from_("genquery").remove([path_to_delete])
        except Exception as e:
            print("⚠️ 기존 파일 삭제 오류:", str(e))

    original_filename = iconfile.name
    ext = os.path.splitext(original_filename)[1]
    uuid_filename = f"{uuid.uuid4()}{ext}"
    supabase_path = f"{folder}/{uuid_filename}"

    supabase.storage.from_("genquery").upload(
        supabase_path,
        iconfile.read(),
        {"content-type": iconfile.content_type}
    )

    public_url = supabase.storage.from_("genquery") \
        .get_public_url(supabase_path) \
        .split("?")[0]

    return original_filename, public_url
