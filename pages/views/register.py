from django.http import JsonResponse
from django.shortcuts import render

from utilsPrj.supabase_client import get_supabase_client
# 암.복호화 관련
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def register(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)
    
    if request.method == "GET":
        return render(request, "pages/register.html")

    # POST 요청 처리
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    tenant = request.POST.get("tenant")
    billingmodelcd = request.POST.get("billingmodelcd")
    usernm = request.POST.get("usernm")
    userinfoyn = request.POST.get("userinfoyn")
    termsofuseyn = request.POST.get("termsofuseyn")
    marketingyn = request.POST.get("marketingyn")
    single = request.POST.get("single")

    if not email:
        return JsonResponse({"result": "fail", "message": "이메일은 필수입니다."}, status=400)

    if password != password_confirm:
        return JsonResponse({"result": "fail", "message": "비밀번호가 일치하지 않습니다."}, status=400)

    if len(password) < 8:
        return JsonResponse({"result": "fail", "message": "비밀번호는 최소 8자 이상이어야 합니다."}, status=400)


    # ✅ 이미 가입된 회원인지 확인
    try:
        existing_user = (
            supabase.schema("genquery")
            .table("users")
            .select("useruid")
            .eq("email", email)
            .execute()
        )
        if existing_user.data and len(existing_user.data) > 0:
            return JsonResponse(
                {"result": "fail", "message": "이미 가입된 회원입니다."},
                status=400
            )
    except Exception as e:
        return JsonResponse({"result": "fail", "message": f"중복 확인 중 오류: {str(e)}"}, status=500)

    # 이메일 존재 여부 확인
    exists_response = (
        supabase.schema("public")
        .table("users")
        .select("useruid")
        .eq("email", email)
        .execute()
    )

    if exists_response.data and len(exists_response.data) > 0:
        # 이미 존재하면 useruid 사용
        user_id = exists_response.data[0]["useruid"]
    else:
        # 없으면 신규 가입
        try:
            signup_result = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            user_id = signup_result.user.id
        except Exception as e:
            return JsonResponse({
                "result": "fail",
                "message": f"회원가입 실패: {str(e)}"
            }, status=500)

        # 1: "일반유저"
        # 5: "Power User"
        # 7: "관리자"

    # 추가 정보 없이 users 테이블에 최소한의 기본 데이터만 저장 (필요하면)
    try:
        # billingmodelcd 넣기
        if single in ("Fr", "Pr"):
            billcd = single
        else:
            billcd = (
                supabase.schema("genquery")
                .table("tenants")
                .select("*")
                .eq("tenantid", tenant)
                .execute()
                .data[0]['billingmodelcd']
            )

        supabase.schema("genquery").table("users").insert({
            "useruid": user_id,
            "email": email,
            "roleid": 1,  # 필요시 고정값 넣기
            "billingmodelcd": billcd,
            "termsofuseyn": termsofuseyn,
            "userinfoyn": userinfoyn,
            "marketingyn": marketingyn,
            "usernm": usernm,
        }).execute()

        tenantid = supabase.schema("genquery").table("tenants").select('*').eq('defaultyn', True).execute().data[0]['tenantid']
        if not tenant:
            tenant = tenantid

        # 회원가입 시 공통에는 필수로 넣기
        projectid = supabase.schema("genquery").table("projects").select('*').eq('projectnm', 'public').eq('tenantid', tenantid).execute().data[0]['projectid']
        tenantusers = {
            'tenantid': tenantid,
            'useruid': user_id,
            'rolecd': 'U',
            'useyn': True,
            'creator': user_id
        }
        supabase.schema("genquery").table("tenantusers").insert(tenantusers).execute()
        projectusers = {
            'projectid': projectid,
            'useruid': user_id,
            'rolecd': 'U',
            'useyn': True,
            'creator': user_id
        }
        supabase.schema("genquery").table("projectusers").insert(projectusers).execute()
        
        # print(f'billingmodelcd: {billingmodelcd} / BillCd: {billcd}')
        # 특정 사용 코드일 경우 해당 사용자 기준 프로젝트 생성 필요
        if billingmodelcd == 'single':
            # print('특정 사용자로 인한 프로젝트 생성')
            new_project = {
                "tenantid": tenantid,
                "projectnm": email,
                "projectdesc": "계정에 따른 자동 생성된 프로젝트 입니다.",
                "useyn": True,
                "creator": user_id
            }
            respon_project = supabase.schema("genquery").table("projects").insert(new_project).execute().data
            respon_projectid = respon_project[0]['projectid']

            new_user = {
                "projectid": respon_projectid,
                "useruid": user_id,
                "rolecd": "M",
                "useyn": True,
                "creator": user_id
            }
            supabase.schema("genquery").table("projectusers").insert(new_user).execute()

        # 특정 테넌스 선택 시 추가 작업
        if tenant != tenantid:
            # print(f'별도 테넌트 선택: {tenant}')
            tenantusers = {
                'tenantid': tenant,
                'useruid': user_id,
                'creator': user_id,
                'approvecd': 'A'
            }
            # print(f'TenantNewUsers: {tenantusers}')
            supabase.schema('genquery').table('tenantnewusers').insert(tenantusers).execute()

        # Pro 사용자의 경우 결제 관련 테이블에 정보 Insert : 추후에는 실제 결제 여부까지 따지도록 로직 보강 혹은 첫결제 이후 해당 로직 실행되도록 수정 필요
        if single == 'Pr':
            def now():
                return datetime.now().date()

            month1 = relativedelta(months=1)
            day1 = timedelta(days=1)

            billing_start = now()
            billing_end = now() + month1 - day1

            config = supabase.schema("genquery").table("configs").select('*').execute().data[0]
            inputtokencapa = config['inputtokencapa']
            serviceamt = config['pricepro']

            billmasters = {
                'billtargetcd' : "U",
                'tenantid': tenant,
                'useruid': user_id,
                'billingmodelcd' : 'Pr',
                'billingfirstdt' : billing_start.isoformat(),
                'useyn' : True,
                'creator': user_id,
            }
            # print(f'TenantNewUsers: {tenantusers}')
            supabase.schema('genquery').table('billmasters').insert(billmasters).execute()

            billdts = {
                'billtargetcd' : "U",
                'tenantid': tenant,
                'useruid': user_id,
                'billstartdt' : billing_start.isoformat(),
                'billenddt' : billing_end.isoformat(),
                'billingmodelcd' : 'Pr',
                'inputtokencapa' : inputtokencapa,
                'serviceamt' : serviceamt,
                'creator': user_id,
            }
            # print(f'TenantNewUsers: {tenantusers}')
            supabase.schema('genquery').table('billdts').insert(billdts).execute()

    except Exception as e:
        return JsonResponse({"result": "fail", "message": f"DB 저장 실패: {str(e)}"}, status=500)

    return JsonResponse({"result": "success", "message": "회원가입이 완료되었습니다.\n이메일 인증 후 로그인 가능합니다."})

def get_tenants(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        configs = supabase.schema("genquery").table("configs").select("*").execute().data

        multitenantyn = configs[0]['multitenantyn']

        if not multitenantyn:
            tenants = supabase.schema('genquery').table('tenants').select('*').neq('defaultyn', True).execute().data
        else:
            tenants = supabase.schema('genquery').table('tenants').select('*').execute().data

        # 각 테넌트 명칭 지정
        for tenant in tenants:
            if tenant.get('tenantnm') and tenant.get('defaultyn') is True:
                tenant['tenantnm'] = 'GenQuery(기본)'

        return JsonResponse({"result": "success", "tenants": tenants, "multitenantyn": multitenantyn})
    except Exception as e:
        return JsonResponse({"result": "fail", "message": f"Tenant 호출 실패: {str(e)}"}, status=500)