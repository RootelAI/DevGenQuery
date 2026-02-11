# views.py
import json
import os
import uuid
from datetime import datetime
from dateutil import parser
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value
from azure.storage.blob import BlobServiceClient


def master_rag_filemasters(request):
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
        page = "master_rag_filemasters"
        return render(request, "pages/home.html", {
        "code": code,
        "text": text,
        "page": page,
        "request": request
    })
    user_id = user.get("id")

    try:# projects 테이블에서 데이터 조회
        projects = supabase.schema('rag').table('projects').select('*').order('createdts', desc=True).execute().data or []
        projecttags = supabase.schema('rag').table('projecttags').select('*').eq('useyn', True).execute().data or []
        projecttagvalues = supabase.schema('rag').table('projecttagvalues').select('*').eq('useyn', True).execute().data or []
        filemasters = supabase.schema('rag').table('filemasters').select("*").order("createdts", desc=True).execute().data or []
        department = supabase.schema('rag').table('codemasters').select("*").eq('codenm', 'Departments').eq('useyn', True).execute().data or []
        departmentuid = department[0]['codeuid']

        departments = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', departmentuid).eq('useyn', True).order('orderno').execute().data

        # 기초 자료 매핑
        for i in filemasters:
            if i.get('projectid'):
                try:
                    i['projectnm'] = supabase.schema('rag').table('projects').select('*').eq('projectid', i['projectid']).execute().data[0]['projectnm']
                except Exception as e:
                    i['projectnm'] = ''
            # 부서 정리
            if i.get('owner_dept'):
                try:
                    i['owner_deptnm'] = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', departmentuid).eq('useyn', True).eq('valuecd', i['owner_dept']).execute().data[0]['valuenm']
                except Exception as e:
                    i['owner_deptnm'] = ''
            if i.get('support_dept'):
                try:
                    i['support_deptnm'] = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', departmentuid).eq('useyn', True).eq('valuecd', i['support_dept']).execute().data[0]['valuenm']
                except Exception as e:
                    i['support_deptnm'] = ''
            if i.get('approver_dept'):
                try:
                    i['approver_deptnm'] = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', departmentuid).eq('useyn', True).eq('valuecd', i['approver_dept']).execute().data[0]['valuenm']
                except Exception as e:
                    i['approver_deptnm'] = ''
            # 사용자 정리
            if i.get('creator'):
                try:
                    creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
                    i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                except Exception as e:
                    i['creatornm'] = ''
            # 일시 정리
            if i.get("createdts"):
                try:
                    dt = parser.parse(i['createdts']) if isinstance(i['createdts'], str) else i['createdts']
                    i['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    i['createdts'] = ''
            if i.get("processdts"):
                try:
                    dt = parser.parse(i['processdts']) if isinstance(i['processdts'], str) else i['processdts']
                    i['processdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    i['processdts'] = ''

        def valuenm(projectid, tagcd, valuecd):
            valuenm = supabase.schema('rag').table('projecttagvalues').select('valuenm').eq('projectid', projectid).eq('tagcd', tagcd).eq('valuecd', valuecd).execute().data[0]['valuenm']
            return valuenm

        # Tag 자료 매핑
        for i in filemasters:
            if i.get("tag1value"):
                try:
                    i['tag1valuenm'] = valuenm(i['projectid'], 'tag1', i['tag1value'])
                except Exception as e:
                    i['tag1valuenm'] = ''
            if i.get("tag2value"):
                try:
                    i['tag2valuenm'] = valuenm(i['projectid'], 'tag2', i['tag2value'])
                except Exception as e:
                    i['tag2valuenm'] = ''
            if i.get("tag3value"):
                try:
                    i['tag3valuenm'] = valuenm(i['projectid'], 'tag3', i['tag3value'])
                except Exception as e:
                    i['tag3valuenm'] = ''
            if i.get("tag4value"):
                try:
                    i['tag4valuenm'] = valuenm(i['projectid'], 'tag4', i['tag4value'])
                except Exception as e:
                    i['tag4valuenm'] = ''
            if i.get("tag5value"):
                try:
                    i['tag5valuenm'] = valuenm(i['projectid'], 'tag5', i['tag5value'])
                except Exception as e:
                    i['tag5valuenm'] = ''
        
        # projecttagvalues를 JavaScript에서 사용하기 쉽게 구조화
        # 형식: { "projectid_tagcd": [{ valuecd, valuenm, orderno }, ...] }
        projecttagvalues_dict = {}
        
        for value in projecttagvalues:
            key = f"{value['projectid']}_{value['tagcd']}"
            if key not in projecttagvalues_dict:
                projecttagvalues_dict[key] = []
            
            projecttagvalues_dict[key].append({
                'valuecd': value['valuecd'],
                'valuenm': value['valuenm'],
                'orderno': value.get('orderno', 0)  # orderno가 없을 경우 0으로 처리
            })
        
        # orderno로 정렬
        for key in projecttagvalues_dict:
            projecttagvalues_dict[key].sort(key=lambda x: x['orderno'])
            

        context = {
            'projects': projects,
            'filemasters': filemasters,
            'projecttags': projecttags,
            'projecttagvalues': projecttagvalues,
            'projecttagvalues': projecttagvalues,
            'projecttagvalues_json': json.dumps(projecttagvalues_dict, cls=DjangoJSONEncoder),
            # 기존에 전달하던 tag1, tag2, tag3이 있다면 그대로 유지
            'departments': departments
        }
        
        return render(request, 'pages/master_rag_filemasters.html', context)
        
    except Exception as e:
        print(f'Error: {str(e)}')
        return render(request, 'pages/master_rag_filemasters.html', {
            'projects': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })


@require_http_methods(["POST"])
def master_rag_filemasters_save(request):
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

    if request.method == 'POST':
        try:
            # 폼 데이터 가져오기
            project_id = request.POST.get('projectid')
            filemastercd = request.POST.get('filemastercd')
            filemasternm = request.POST.get('filemasternm')
            tag1 = request.POST.get('tag1')
            tag2 = request.POST.get('tag2')
            tag3 = request.POST.get('tag3')
            tag4 = request.POST.get('tag4')
            tag5 = request.POST.get('tag5')
            owner_dept = request.POST.get('owner_dept')
            support_dept = request.POST.get('support_dept')
            approver_dept = request.POST.get('approver_dept')
            
            # 이미 동일한 프로젝트에 동일한 파일명 있으면 삽입 불가
            existing_filenm = supabase.schema('rag').table('filemasters').select('*').eq('projectid', project_id).neq('filemastercd', filemastercd).eq('filemasternm', filemasternm).execute().data
            if existing_filenm:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일 명칭이 이미 존재합니다.'
                })
            
            # Supabase에 메타데이터 저장
            data = {
                'projectid': project_id,
                'filemastercd': filemastercd,
                'filemasternm': filemasternm,
                'tag1value': tag1,
                'tag2value': tag2,
                'tag3value': tag3,
                'tag4value': tag4,
                'tag5value': tag5,
                'owner_dept': owner_dept,
                'support_dept': support_dept,
                'approver_dept': approver_dept,
                'creator': user_id,  # 또는 적절한 사용자 정보
                'createdts': datetime.now().isoformat(),
            }

            # 기존 데이터 조회 (수정인 경우)
            if filemastercd:
                existing_data = supabase.schema('rag').table('filemasters')\
                    .select('*')\
                    .eq('filemastercd', filemastercd)\
                    .execute().data
                
                if existing_data:
                    old_data = existing_data[0]
                    
                    # Tag 값 변경 감지
                    if (old_data.get('tag1value') != tag1 or 
                        old_data.get('tag2value') != tag2 or 
                        old_data.get('tag3value') != tag3 or 
                        old_data.get('tag4value') != tag4 or 
                        old_data.get('tag5value') != tag5):
                        
                        # print('기존 값과 변경 감지')
                        # print(f'기존 Tag1: {old_data.get("tag1value")} -> 새로운 Tag1: {tag1}')
                        # print(f'기존 Tag2: {old_data.get("tag2value")} -> 새로운 Tag2: {tag2}')
                        # print(f'기존 Tag3: {old_data.get("tag3value")} -> 새로운 Tag3: {tag3}')
                        # print(f'기존 Tag4: {old_data.get("tag4value")} -> 새로운 Tag4: {tag4}')
                        # print(f'기존 Tag5: {old_data.get("tag5value")} -> 새로운 Tag5: {tag5}')
                        data['processcd'] = 'N'

            # Data Upsert
            result = supabase.schema('rag').table('filemasters').upsert(data).execute()
            
            return JsonResponse({
                'result': 'success',
                'message': '저장되었습니다.',
            })
            
        except Exception as e:
            print(f'Save Error: {e}')
            return JsonResponse({
                'result': 'error',
                'message': f'오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({'result': 'error', 'message': 'Invalid request'})

@require_http_methods(["POST"])
def master_rag_filemasters_delete(request):
    """
    파일 삭제 (Supabase 메타데이터 + Azure Blob Storage 파일)
    """
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

    if request.method == 'POST':
        try:
            # JSON 데이터 파싱
            data = json.loads(request.body)
            filemastercd = data.get('filemastercd')
            
            if not filemastercd:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일 UID가 필요합니다.'
                })
            
            # Supabase에서 메타데이터 삭제
            result = supabase.schema('rag').table('filemasters').delete().eq('filemastercd', filemastercd).execute()
            
            return JsonResponse({
                'result': 'success',
                'message': '파일이 삭제되었습니다.'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'result': 'error',
                'message': 'JSON 파싱 오류'
            })
        except Exception as e:
            return JsonResponse({
                'result': 'error',
                'message': f'오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({
        'result': 'error',
        'message': 'Invalid request method'
    })