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


def master_rag_files(request):
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
        page = "master_rag_files"
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
        files = supabase.schema('rag').table('files').select("*").order("createdts", desc=True).execute().data or []

        # 기초 자료 매핑
        for i in files:
            if i.get('projectid'):
                try:
                    i['projectnm'] = supabase.schema('rag').table('projects').select('*').eq('projectid', i['projectid']).execute().data[0]['projectnm']
                except Exception as e:
                    i['projectnm'] = ''
            if i.get('creator'):
                try:
                    creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
                    i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                except Exception as e:
                    i['creatornm'] = ''
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
        for i in files:
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
            'files': files,
            'projecttags': projecttags,
            'projecttagvalues': projecttagvalues,
            'projecttagvalues': projecttagvalues,
            'projecttagvalues_json': json.dumps(projecttagvalues_dict, cls=DjangoJSONEncoder),
            # 기존에 전달하던 tag1, tag2, tag3이 있다면 그대로 유지
        }

        # print(f'Context: {context}')
        
        return render(request, 'pages/master_rag_files.html', context)
        
    except Exception as e:
        print(f'Error: {str(e)}')
        return render(request, 'pages/master_rag_files.html', {
            'projects': [],
            'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        })

def upload_to_azure_blob(file, dirPath):
    """
    Azure Blob Storage에 파일 업로드
    
    Args:
        file: Django UploadedFile 객체
        dirPath: Blob 경로
    
    Returns:
        blob_url: 업로드된 파일의 URL
    """
    try:
        # BlobServiceClient 생성
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        
        # 컨테이너 클라이언트 가져오기
        container_client = blob_service_client.get_container_client(dirPath)
        
        # 컨테이너가 없으면 생성
        try:
            container_client.create_container()
        except:
            pass  # 이미 존재하는 경우 무시
        
        # Blob 이름 생성 (폴더 구조: projectid/fileuid_originalname)
        original_filename = file.name
        blob_name = f"source/{original_filename}"
        
        # Blob 클라이언트 가져오기
        blob_client = container_client.get_blob_client(blob_name)
        
        # 파일 업로드
        blob_client.upload_blob(file, overwrite=True)
        
        # 업로드된 파일의 URL 반환
        blob_url = blob_client.url
        
        return {
            'success': True,
            'blob_url': blob_url,
            'blob_name': blob_name
        }
        
    except Exception as e:
        print(f'Error Blob: {e}')
        return {
            'success': False,
            'error': str(e)
        }    

def delete_from_azure_blob(blob_name, dirPath):
    """
    Azure Blob Storage에서 파일 삭제
    
    Args:
        blob_name: 삭제할 Blob 이름 (예: "projectid/fileuid_filename.pdf")
    
    Returns:
        dict: 삭제 결과
    """
    try:
        # BlobServiceClient 생성
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        
        # 컨테이너 클라이언트 가져오기
        container_client = blob_service_client.get_container_client(
            dirPath
        )
        
        # Blob 클라이언트 가져오기
        blob_client = container_client.get_blob_client('source/' + blob_name)
        
        # Blob 삭제
        blob_client.delete_blob()
        
        return {
            'success': True,
            'message': 'Blob 삭제 완료'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@require_http_methods(["POST"])
def master_rag_files_save(request):
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
            file_uid = request.POST.get('fileuid')
            file_nm = request.POST.get('filenm')
            tag1 = request.POST.get('tag1')
            tag2 = request.POST.get('tag2')
            tag3 = request.POST.get('tag3')
            
            # 신규인 경우 UUID 생성
            if not file_uid:
                file_uid = str(uuid.uuid4())
            
            # 이미 동일한 프로젝트에 동일한 파일명 있으면 삽입 불가
            existing_filenm = supabase.schema('rag').table('files').select('*').eq('projectid', project_id).eq('filenm', file_nm).execute().data
            if existing_filenm:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일 명칭이 이미 존재합니다.'
                })

            # 파일 업로드 처리
            uploaded_file = request.FILES.get('file')
            blob_url = None
            blob_name = None
            file_extension = None

            existing = supabase.schema('rag').table('files').select('*').eq('fileuid', file_uid).execute().data
            if existing:
                blob_name = existing[0]['filenm']

            if uploaded_file:
                # 파일 확장자 추출
                file_extension = os.path.splitext(uploaded_file.name)[1]

                # 컨테이너
                dirPath = supabase.schema('rag').table('projects').select('dirpath').eq('projectid', project_id).execute().data[0]['dirpath']
                
                # 기존 존재 시 삭제
                if blob_name:
                    delete_from_azure_blob(blob_name, dirPath)
                    
                # Azure Blob Storage에 업로드
                upload_result = upload_to_azure_blob(uploaded_file, dirPath)
                
                if upload_result['success']:
                    blob_url = upload_result['blob_url']
                    blob_name = upload_result['blob_name']
                else:
                    return JsonResponse({
                        'result': 'error',
                        'message': f'파일 업로드 실패: {upload_result["error"]}'
                    })
            
            # Supabase에 메타데이터 저장
            data = {
                'fileuid': file_uid,
                'projectid': project_id,
                'filenm': file_nm,
                'tag1value': tag1,
                'tag2value': tag2,
                'tag3value': tag3,
                'creator': user_id,  # 또는 적절한 사용자 정보
                'createdts': datetime.now().isoformat(),
            }
            
            # 파일이 업로드된 경우 추가 정보 저장
            if blob_url:
                data['fileextension'] = file_extension[1:]
            #     data['bloburl'] = blob_url
            #     data['blobname'] = blob_name
            
            # Data Upsert
            result = supabase.schema('rag').table('files').upsert(data).execute()
            
            return JsonResponse({
                'result': 'success',
                'message': '저장되었습니다.',
                'blob_url': blob_url
            })
            
        except Exception as e:
            print(f'Save Error: {e}')
            return JsonResponse({
                'result': 'error',
                'message': f'오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({'result': 'error', 'message': 'Invalid request'})

@require_http_methods(["POST"])
def master_rag_files_delete(request):
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
            file_uid = data.get('fileuid')
            
            if not file_uid:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일 UID가 필요합니다.'
                })
            
            # Supabase에서 파일 정보 조회
            file_info = supabase.schema('rag').table('files').select('*').eq('fileuid', file_uid).execute()
            
            if not file_info.data:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일을 찾을 수 없습니다.'
                })
            
            file_data = file_info.data[0]
            project_id = file_data['projectid']
            blob_name = file_data.get('filenm')
            
            # Azure Blob Storage에서 파일 삭제 (blob_name이 있는 경우에만)
            if blob_name:
                # 컨테이너
                dirPath = supabase.schema('rag').table('projects').select('dirpath').eq('projectid', project_id).execute().data[0]['dirpath']

                # Blob 파일 삭제
                delete_result = delete_from_azure_blob(blob_name, dirPath)
                
                if not delete_result['success']:
                    # Blob 삭제 실패해도 계속 진행 (파일이 이미 없을 수도 있음)
                    print(f"Warning: Blob 삭제 실패 - {delete_result['error']}")
            
            # Supabase에서 메타데이터 삭제
            result = supabase.schema('rag').table('files').delete().eq('fileuid', file_uid).execute()
            
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