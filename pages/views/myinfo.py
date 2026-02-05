from django.shortcuts import render, redirect
from utilsPrj.supabase_client import get_supabase_client
from datetime import datetime
from django.contrib import messages
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from .master_tenant_request import save_iconfile

def myinfo(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    # 세션에서 사용자 정보 가져오기
    user_session = request.session.get("user")
    user_id = user_session["id"]

    tenantusers_resp = supabase.schema("genquery").table("tenantusers").select("*").eq("useruid", user_id).execute()
    tenantusers = tenantusers_resp.data if tenantusers_resp.data else []
    tenantid = tenantusers[0]["tenantid"]

    tenants_resp = supabase.schema("genquery").table("tenants").select("*").eq("tenantid", tenantid).execute()
    tenants = tenants_resp.data if tenants_resp.data else []

    projects_resp = supabase.schema("genquery").table("projects").select("*").eq("tenantid", tenantid).execute()
    projects = projects_resp.data if projects_resp.data else []

    project_map = {p["projectid"]: p for p in projects}

    projectusers_resp = supabase.schema("genquery").table("projectusers").select("*").eq("useruid", user_id).execute()
    projectusers = projectusers_resp.data if projectusers_resp.data else []

    filtered_projectusers = []

    for pu in projectusers:
        pid = pu["projectid"]

        if pid in project_map:   # 해당 프로젝트가 존재하는 경우만
            pu["projectnm"] = project_map[pid]["projectnm"]
            filtered_projectusers.append(pu)

    projectusers = filtered_projectusers

    tenantnewusers_resp = supabase.schema("genquery").table("tenantnewusers").select("*").eq("useruid", user_id).order("createdts", desc=True).limit(1).execute()
    tenantnewusers = tenantnewusers_resp.data if tenantnewusers_resp.data else []

    if tenantnewusers:
        newtenantid = tenantnewusers[0]["tenantid"]
        # tenantid와 newtenantid가 같으면 tenantnewusers를 삭제
        if newtenantid == tenantid:
            tenantnewusers = None
            newtenants = []
        else:
            newtenants_resp = supabase.schema("genquery").table("tenants")\
                .select("tenantid, tenantnm").eq("tenantid", newtenantid).execute()
            newtenants = newtenants_resp.data if newtenants_resp.data else []
            tenantnewusers = tenantnewusers[0]
    else:
        tenantnewusers = None
        newtenants = []

    if isinstance(tenants, list) and len(tenants) > 0:
        tenants = tenants[0]
    else:
        tenants = None

    if isinstance(tenantusers, list) and len(tenantusers) > 0:
        tenantusers = tenantusers[0]
    else:
        tenantusers = None

    created = tenants.get('createdts')   # dict라서 이렇게 가져와야 함

    if isinstance(created, str):
        # T 포함 ISO 포맷이므로 fromisoformat 사용 가능
        tenants['createdts'] = datetime.fromisoformat(created)
        
    # if isinstance(tenantnewusers, list) and len(tenantnewusers) > 0:
    #     tenantnewusers = tenantnewusers[0]
    # else:
    #     tenantnewusers = None

    if isinstance(newtenants, list) and len(newtenants) > 0:
        newtenants = newtenants[0]
    else:
        newtenants = None

    user_info = supabase.schema("genquery").table("users").select("*").eq("useruid", user_id).execute().data[0]
    
    billingmodelcd = user_info["billingmodelcd"]
    tenantmanager = tenantusers["rolecd"]
    payment = None
    if billingmodelcd == "Fr":
        payment = "F"
    elif billingmodelcd == "Pr":
        payment = "Y"
    elif tenantmanager == "M":
        payment = "Y"

    billmaster = supabase.schema("genquery").table("billmasters").select("*").eq("tenantid", tenantid).execute().data

    for bill in billmaster:
        try:
            bill["decemail"] = decrypt_value(bill["encemail"]) if bill.get("encemail") else ""
            bill["dectelno"] = decrypt_value(bill["enctelno"]) if bill.get("enctelno") else ""
        except Exception:
            bill["decemail"] = ""
            bill["dectelno"] = ""
            
    billmasters = billmaster[0] if billmaster else None

    today = datetime.utcnow().date().isoformat()

    # billdts에서 현재 날짜가 기간 내에 포함된 row 조회
    billdts_res = supabase.schema("genquery").table("billdts").select("*").lte("billstartdt", today).gte("billenddt", today).eq("tenantid", tenantid).execute().data
    billdts = billdts_res[0] if billdts_res else None


    configs_res = supabase.schema("genquery").table("configs").select("*").execute().data
    configs = configs_res[0] if configs_res else None
    
    # print("user_session", user_session)
    # print("tenants", tenants)
    # print("tenantusers", tenantusers)
    # print("projectusers", projectusers)
    # print("tenantnewusers", tenantnewusers)
    # print("newtenants", newtenants)
    # print("user_info: ", user_info)
    # print("billmasters", billmasters)

    return render(request, 'pages/myinfo.html', {
        # "user_session": user_session,
        "tenants" : tenants,
        # "tenantusers" : tenantusers,
        "projectusers" : projectusers,
        "tenantnewusers" : tenantnewusers,
        "newtenants" : newtenants,
        "user_info" : user_info,
        "payment" : payment,
        "billmasters" : billmasters,
        "billdts" : billdts, 
        "configs" : configs
    })


def myinfo_update_username(request):
    if request.method == "POST":
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        # 현재 로그인한 사용자 정보 가져오기
        user_session = request.session.get("user")
        user_id = user_session["id"]

        # 폼에서 전달된 새로운 사용자명
        new_username = request.POST.get("usernm")

        if new_username:
            # Supabase users 테이블 업데이트
            update_resp = supabase.schema("genquery").table("users")\
                .update({"usernm": new_username})\
                .eq("useruid", user_id)\
                .execute()

            if not update_resp.data or len(update_resp.data) == 0:   # error가 None이면 성공
                messages.error(request, "저장에 실패했습니다. 다시 시도해주세요.")
            else:
                messages.success(request, "사용자명이 성공적으로 저장되었습니다!")

    # 수정 후 다시 MyInfo 페이지로 리다이렉트
    return redirect("myinfo")  # urls.py에서 myinfo에 해당하는 이름을 사용


def myinfo_update_contact(request):
    if request.method == "POST":
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        # 현재 로그인한 사용자 정보 가져오기
        # user_session = request.session.get("user")
        # user_id = user_session["id"]

        # 폼에서 전달된 이메일과 전화번호
        decemail = request.POST.get("decemail", "").strip()
        dectelno = request.POST.get("dectelno", "").strip()
        tenantid = request.POST.get("tenantid", "").strip()
        # 파일 업로드 처리 (추가)
        iconfile = request.FILES.get("iconfile")

        if iconfile:
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
                
        # 암호화
        encemail = encrypt_value(decemail) if decemail else None
        enctelno = encrypt_value(dectelno) if dectelno else None

        # Supabase billmasters 테이블 업데이트
        update_data = {}
        if encemail is not None:
            update_data["encemail"] = encemail
        if enctelno is not None:
            update_data["enctelno"] = enctelno

        if update_data:
            update_resp = supabase.schema("genquery").table("billmasters")\
                .update(update_data)\
                .eq("tenantid", tenantid)\
                .execute()

            if not update_resp.data or len(update_resp.data) == 0:   # error가 None이면 성공
                messages.error(request, "저장에 실패했습니다. 다시 시도해주세요.")
            else:
                messages.success(request, "정보가 성공적으로 수정되었습니다!")

    # 수정 후 다시 MyInfo 페이지로 리다이렉트
    return redirect("myinfo")  # urls.py에서 myinfo에 해당하는 이름을 사용


