# views.py
import json
from dateutil import parser
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from urllib.parse import urlparse
from datetime import datetime

from django.views.decorators.http import require_http_methods
import logging

from utilsPrj.supabase_client import get_supabase_client
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# logger = logging.getLogger(__name__)

def master_tenant_users(request):
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
        page = "master_tenantusers"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")
    roleid = user.get("roleid")

    tenantid = request.GET.get('tenantid')

    if tenantid is None:
        tenantid = user.get('tenantid')

    if not tenantid:
        users = supabase.schema("genquery").table("tenantusers") \
            .select("tenantid").eq("useruid", user_id).eq("useyn", True).eq("rolecd", "M").execute()

        if users.data and len(users.data) > 0:
            tenantid = users.data[0]['tenantid']
        else:
            # print(f"⚠️ user_id={user_id} 의 tenant 정보가 없습니다.")
            tenantid = None  # 또는 0 으로 기본값 지정 가능

    tenantnm = supabase.schema('genquery').table('tenants').select('*').eq('tenantid', tenantid).execute().data[0]['tenantnm']

    try:# tenantusers 테이블에서 데이터 조회
        response = supabase.schema('genquery').table('tenantusers').select('*').eq('tenantid', tenantid).order('useruid', desc=True).execute()
        
        tenantusers = response.data if response.data else []
        
        for i in tenantusers:
            if i.get('tenantid'):
                try:
                    i['sep'] = 'users'
                except Exception as e:
                    print(e)
                    i['sep'] = ''

        tenantnewusers = supabase.schema('genquery').table('tenantnewusers').select('*').eq('tenantid', tenantid).eq('approvecd', 'A').execute().data or []

        for i in tenantnewusers:
            if i.get('tenantid'):
                try:
                    i['sep'] = 'newusers'
                    i['rolecd'] = 'U'  # ✅ rolecd 필드 추가
                except Exception as e:
                    print(e)
                    i['sep'] = ''

        # print(tenantnewusers)

        tenantallusers = tenantusers + tenantnewusers
        
        for i in tenantallusers:
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

        users = supabase.schema('public').table('users').select('*').execute()

        # print(tenantallusers)
        context = {
            'tenantid': tenantid,
            'tenantnm': tenantnm,
            'tenantusers': tenantallusers,
            # 'total_count': len(tenantallusers),
            # 'active_count': len([g for g in tenantallusers if g.get('is_active', False)]),
            'roleid' : roleid,
        }
        
        return render(request, 'pages/master_tenant_users.html', context)
        
    except Exception as e:
        # logger.error(f"기업 조회 중 오류 발생: {e}")
        return render(request, 'pages/master_tenant_users.html', {
            'tenantusers': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_tenant_users_save(request):
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
            page = "master_tenantusers"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 기업 정보 추출
        sep = request.POST.get('sep')
        tenantnewuid = request.POST.get('tenantnewuid')
        tenantid = request.POST.get('tenantid')
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
    
        # genquery 테넌트의 tenantid 가져오기
        other_tenant = supabase.schema('genquery').table('tenants')\
            .select('tenantid')\
            .eq('defaultyn', True)\
            .execute()

        # tenantid 추출
        other_tenantid = other_tenant.data[0]["tenantid"]
        
        useruid = user[0]['useruid']

        # 기존 존재 여부 파악
        existing = None
        if tenantid:
            resp = supabase.schema("genquery").table("tenantusers").select("*").eq("tenantid", tenantid).eq('useruid', useruid).execute()
            existing = resp.data[0] if resp.data else None

        #tenantusermonths
        # 오늘 날짜 (DATE 기반 비교)
        today = datetime.utcnow().date().isoformat()

        # billdts에서 현재 날짜가 기간 내에 포함된 row 조회
        billdts_res = (
            supabase.schema("genquery")
            .table("billdts")
            .select("*")
            .lte("billstartdt", today)
            .gte("billenddt", today)
            .eq("tenantid", tenantid)
            .execute()
        )

        other_tenantid = int(other_tenantid)
        tenantid = int(tenantid)

        if not billdts_res.data:
            if other_tenantid != tenantid:
                return JsonResponse({
                    "result": "Failed",
                    "message": "현재 사용 가능한 결제 기간이 존재하지 않습니다."
                })
            else:
                billstartdt = None  # 또는 적절한 기본값 처리
        else:
            billstartdt = billdts_res.data[0]["billstartdt"]
     
        # 기존 사용자 정보에서 useyn
        useyn_old = existing["useyn"] if existing else None

        # 새로 변경되었거나 활성화된 경우
        if (not existing or (useyn_old == False and useyn == True)) and other_tenantid != tenantid:

            # tenantusermonths에서 현재 billingstartdt 기준 사용자 수 조회
            tum_res = (
                supabase.schema("genquery")
                .table("tenantusermonths")
                .select("*")
                .eq("tenantid", tenantid)
                .eq("billstartdt", billstartdt)
                .execute()
            )
            current_user_count = len(tum_res.data)

            # tenants 테이블의 최대 허용 사용자 수 조회
            tenant_row = (
                supabase.schema("genquery")
                .table("tenants")
                .select("*")
                .eq("tenantid", tenantid)
                .execute()
                .data[0]
            )
            billingusercnt = tenant_row["billingusercnt"]

            # 제한 초과인 경우
            if billingusercnt <= current_user_count:
                return JsonResponse({
                    'result': 'Failed',
                    'message': '해당 요금제의 사용 가능 인원이 모두 찼습니다.'
                })

            # 가능하면 tenantusermonths에 INSERT
            new_record = {
                "billstartdt": billstartdt,
                "tenantid": tenantid,
                "useruid": useruid,
                "recordtypecd": "N",
                "creator": useruid
            }

            supabase.schema("genquery").table("tenantusermonths").insert(new_record).execute()
            
        data = {
            "tenantid": tenantid,
            "useruid": useruid,
            "useyn": useyn,
            "rolecd": rolecd
        }
        # print(f'Data: {data}')
        if existing:
            response = supabase.schema('genquery').table('tenantusers').update(data).eq('tenantid', tenantid).eq('useruid', useruid).execute()

            if sep == 'newusers':
                data = {
                    "tenantnewuid": tenantnewuid,
                    "approvecd": 'S',
                    'approveuseruid': user_id,
                    'approvedts': datetime.now().isoformat()
                }
                # print(data)
                respons = supabase.schema('genquery').table('tenantnewusers').upsert(data).execute()
        else:
            other_tenant_user = supabase.schema('genquery').table('tenantusers')\
                .select('*')\
                .neq('tenantid', other_tenantid)\
                .eq('useruid', useruid)\
                .execute()

            # genquery 외 다른 테넌트에도 존재함
            if other_tenant_user.data:
                return JsonResponse({
                    'result': 'Failed',
                    'message': '해당 사용자는 다른 기업에 이미 소속되어 있습니다.'
                })
            
            data["creator"] = user_id
            
            if useruid is not None:
                tenantnewusers_res  = supabase.schema('genquery').table('tenantnewusers').select('tenantnewuid').eq('useruid', useruid).eq('tenantid', tenantid).eq('approvecd', 'A').execute()
                if tenantnewusers_res.data:
                    tenantnewuid = tenantnewusers_res.data[0]['tenantnewuid']
                    sep = 'newusers'
                else:
                    tenantnewuid = None
                    sep = None

            response = supabase.schema('genquery').table('tenantusers').insert(data).execute()

            billingmodelcd_res  = supabase.schema('genquery').table('tenants').select('billingmodelcd').eq('tenantid', tenantid).execute()
            if billingmodelcd_res.data:
                billingmodelcd = billingmodelcd_res.data[0]['billingmodelcd']
            else:
                billingmodelcd = None

            supabase.schema("genquery") \
                .table("users") \
                .update({"billingmodelcd": billingmodelcd}) \
                .eq("useruid", useruid) \
                .execute()   

            projectid = supabase.schema('genquery').table('projects').select('projectid').eq('tenantid', tenantid).eq('projectnm', 'public').execute().data[0]['projectid']
            data = {
                "projectid": projectid,
                "useruid": useruid,
                "rolecd": rolecd,
                "useyn": useyn,
                "creator": user_id
            }
            response = supabase.schema('genquery').table('projectusers').insert(data).execute()

            if sep == 'newusers':
                data = {
                    "tenantnewuid": tenantnewuid,
                    "approvecd": 'S',
                    'approveuseruid': user_id,
                    'approvedts': datetime.now().isoformat()
                }

                # print(data)
                respons = supabase.schema('genquery').table('tenantnewusers').upsert(data).execute()

            # 공용 테넌트 id 조회
            if other_tenantid != tenantid:
                public_tenantid = supabase.schema('genquery').table('tenants').select('*').eq('defaultyn', True).execute().data[0]['tenantid']
                # 공용 테넌트 및 public id 조회
                public_projectid = supabase.schema('genquery').table('projects').select('projectid').eq('tenantid', public_tenantid).eq('projectnm', 'public').execute().data[0]['projectid']

                email_projectid = supabase.schema('genquery').table('projects').select('projectid').eq('tenantid', public_tenantid).eq('projectnm', email).execute().data[0]['projectid']

                if public_projectid:
                    supabase.schema("genquery") \
                        .table("docs") \
                        .delete() \
                        .eq("projectid", email_projectid) \
                        .execute()
                
                    
        if response.data:
            return JsonResponse({
                'result': 'success',
                'group': response.data[0],
                'message': '사용자가 성공적으로 저장되었습니다.'
            })
        else:
            return JsonResponse({
                'result': 'Failed',
                'message': '사용자 저장에 실패했습니다.'
            })
            
    except Exception as e:
        # logger.error(f"사용자 저장 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'사용자 저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_tenant_users_delete(request):
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
            page = "master_tenantusers"
            return render(request, "pages/home.html", {
            "code": code,
            "text": text,
            "page": page,
            "request": request
        })
        user_id = user.get("id")
        
        # POST 데이터에서 기업 정보 추출
        data = json.loads(request.body)
        sep = data.get('sep')
        tenantnewuid = data.get('tenantnewuid')
        tenantid = data.get('tenantid')
        useruid = data.get('useruid')
        approvenote = data.get("approvenote")  # 신규 사용자 삭제 사유

        # ✅ 1단계: tenantusers에서 삭제
        supabase.schema('genquery').table('tenantusers') \
            .delete().eq('tenantid', tenantid).eq('useruid', useruid).execute()

        # ✅ 2단계: 해당 tenant의 모든 projects 조회
        projects_resp = supabase.schema('genquery').table('projects') \
            .select('projectid').eq('tenantid', tenantid).execute()
        project_list = projects_resp.data or []

        # ✅ 3단계: 각 project에 대해 projectusers에서 동일 useruid 삭제
        for p in project_list:
            projectid = p.get('projectid')
            if projectid:
                supabase.schema('genquery').table('projectusers') \
                    .delete().eq('projectid', projectid).eq('useruid', useruid).execute()
                
        # 4단계: tenantnewusers 에서 삭제
        if tenantnewuid:
            data = {
                "tenantnewuid": tenantnewuid,
                "approvecd": 'D',
                "approvenote" : approvenote,
                'approveuseruid': user_id,
                'approvedts': datetime.now().isoformat()
            }
            # print(data)
            respons = supabase.schema('genquery').table('tenantnewusers').upsert(data).execute()

        return JsonResponse({
            'result': 'success',
            'message': '사용자 및 관련 프로젝트 사용자 정보가 모두 삭제되었습니다.'
        })
            
    except Exception as e:
        logger.error(f"사용자 삭제 중 오류 발생: {e}")
        return JsonResponse({
            'result': 'Failed',
            'message': f'사용자 삭제 중 오류가 발생했습니다: {str(e)}'
        })