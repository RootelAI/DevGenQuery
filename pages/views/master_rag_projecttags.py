# views.py
import json
from dateutil import parser
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value

def master_rag_projecttags(request):
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
        page = "master_rag_projecttags"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")

    try:# projects 테이블에서 데이터 조회
        project_response = supabase.schema('rag').table('projects').select('*').order('projectid', desc=False).execute()
        projects = project_response.data if project_response.data else []
        project_map = {p["projectid"]: p["projectnm"] for p in projects}
        
        projecttags_response = supabase.schema('rag').table('projecttags').select('*').order('projectid', desc=False).execute()
        projecttags = projecttags_response.data if projecttags_response.data else []

        # 각 테이블에 projectnm 추가
        for projecttag in projecttags:
            projecttag["projectnm"] = project_map.get(projecttag["projectid"], "-")

        projecttagvalues_response = supabase.schema('rag').table('projecttagvalues').select('*').order('projectid', desc=False).execute()
        projecttagvalues = projecttagvalues_response.data if projecttagvalues_response.data else []

        context = {
            'projects': projects,
            'projecttags' : projecttags,
            'projecttagvalues' : projecttagvalues
        }
        
        return render(request, 'pages/master_rag_projecttags.html', context)
        
    except Exception as e:
        return render(request, 'pages/master_rag_projecttags.html', {
            'projects': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })
    
@require_http_methods(["POST"])
def master_rag_projecttags_save(request):
    """프로젝트 Tag + Tag Values 저장 (값은 전체 삭제 후 insert)"""
    try:
        # 세션 토큰
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        supabase = get_supabase_client(access_token, refresh_token)

        user = request.session.get("user")
        if not user:
            code = 'login'
            text = '로그인이 필요합니다.'
            page = "master_rag_projecttags"
            return render(request, "pages/home.html", {
                "code": code,
                "text": text,
                "page": page,
                "request": request
            })
        user_id = user.get("id")
        
        # POST 데이터에서 프로젝트 Tag 정보 추출
        projectid = request.POST.get('projectid')
        tagcd = request.POST.get('tagcd')
        tagnm = request.POST.get('tagnm')
        uicomponent = request.POST.get('uicomponent')
        useyn = request.POST.get('useyn')
        orderno = request.POST.get('orderno')

        useyn = True if useyn == "True" else False
        orderno = int(orderno) if orderno else None

        # 기존 존재 여부 파악 (projecttags)
        resp = supabase.schema("rag").table("projecttags") \
            .select("*").eq("projectid", projectid).eq("tagcd", tagcd).execute()
        existing = resp.data[0] if resp.data else None
        
        # projecttags 데이터 준비
        tag_data = {
            "tagnm": tagnm,
            "uicomponent": uicomponent,
            "useyn": useyn,
            "orderno": orderno
        }

        if existing:
            supabase.schema('rag').table('projecttags') \
                .update(tag_data).eq('projectid', projectid).eq("tagcd", tagcd).execute()
        else:
            tag_data.update({
                "projectid": projectid,
                "tagcd": tagcd,
                "creator": user_id
            })
            supabase.schema('rag').table('projecttags').insert(tag_data).execute()

        # -------------------------
        # 우측 값 정보 저장 처리 (전체 삭제 후 insert)
        # -------------------------
        values_json = request.POST.get('values_json')
        if values_json:
            values = json.loads(values_json)  # 리스트(dict)

            # 기존 값 전체 삭제
            supabase.schema("rag").table("projecttagvalues") \
                .delete().eq("projectid", projectid).eq("tagcd", tagcd).execute()
            
            # 새 값 insert
            insert_data = []
            for v in values:
                valuecd = v.get('valuecd')
                valuenm = v.get('valuenm')
                useyn_v = True if v.get('useyn') else False
                orderno_v = int(v.get('orderno')) if v.get('orderno') else None

                if not valuecd:
                    continue  # valuecd 없으면 스킵
                
                insert_data.append({
                    "projectid": projectid,
                    "tagcd": tagcd,
                    "valuecd": valuecd,
                    "valuenm": valuenm,
                    "useyn": useyn_v,
                    "orderno": orderno_v,
                    "creator": user_id
                })
            
            if insert_data:
                supabase.schema("rag").table("projecttagvalues").insert(insert_data).execute()

        return JsonResponse({
            'result': 'success',
            'message': '프로젝트 Tag 및 값 정보가 성공적으로 저장되었습니다.'
        })

    except Exception as e:
        return JsonResponse({
            'result': 'Failed',
            'error': f'저장 중 오류가 발생했습니다: {str(e)}'
        })

@require_http_methods(["POST"])
def master_rag_projecttags_delete(request):
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
            page = "master_rag_projecttags"
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
        tagcd = data.get('tagcd')

        # 프로젝트 상태 업데이트
        supabase.schema('rag').table('projecttags').delete().eq('projectid', projectid).eq('tagcd', tagcd).execute()
        supabase.schema('rag').table('projecttagvalues').delete().eq('projectid', projectid).eq('tagcd', tagcd).execute()
        
        return JsonResponse({'result': 'success', 'message': '프로젝트가 성공적으로 삭제되었습니다.'})
            
    except Exception as e:
        return JsonResponse({
            'result': 'Failed',
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })