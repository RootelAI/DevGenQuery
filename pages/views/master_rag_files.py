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
        filemasters = supabase.schema('rag').table('filemasters').select("*").order("createdts", desc=True).execute().data or []
        files = supabase.schema('rag').table('files').select("*").order("createdts").execute().data or []

        filestatus_cd = supabase.schema('rag').table('codemasters').select("*").eq('codenm', 'FileStatus').eq('useyn', True).execute().data or []
        filestatusuid = filestatus_cd[0]['codeuid']
        filestatus = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', filestatusuid).eq('useyn', True).order('orderno').execute().data

        revisiontype = supabase.schema('rag').table('codemasters').select("*").eq('codenm', 'RevisionTypes').eq('useyn', True).execute().data or []
        revisionuid = revisiontype[0]['codeuid']
        revisiontypes = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', revisionuid).eq('useyn', True).order('orderno').execute().data

        # 기초 자료 매핑
        for i in files:
            # 마스터명
            if i.get('filemastercd'):
                try:
                    i['filemasternm'] = supabase.schema('rag').table('filemasters').select('*').eq('filemastercd', i['filemastercd']).execute().data[0]['filemasternm']
                except Exception as e:
                    i['filemasternm'] = ''
            # 파일상태
            if i.get('filestatus'):
                try:
                    i['filestatusnm'] = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', filestatusuid).eq('valuecd', i['filestatus']).execute().data[0]['valuenm']
                except Exception as e:
                    i['filestatusnm'] = ''
            # 리비젼타입
            if i.get('revisiontype'):
                try:
                    i['revisiontypenm'] = supabase.schema('rag').table('codevalues').select('*').eq('codeuid', revisionuid).eq('valuecd', i['revisiontype']).execute().data[0]['valuenm']
                except Exception as e:
                    i['revisiontypenm'] = ''
            # 대체 파일 CD
            if i.get('supersedes_filecd'):
                try:
                    supersedes_file = supabase.schema('rag').table('files').select('*').eq('filecd', i['supersedes_filecd']).execute().data
                    
                    supfilenm = supersedes_file[0]['filenm']
                    extension = '.' + supersedes_file[0]['fileextension']
                    version = supersedes_file[0]['version']
                    supresedes_filenm = f'{supfilenm.replace(extension, "")}_{version}{extension}'

                    i['supersedes_filenm'] = supresedes_filenm
                except Exception as e:
                    i['supersedes_filenm'] = ''

            # 사용자명
            if i.get('creator'):
                try:
                    creatornm =  supabase.schema('public').table('users').select('*').eq('useruid', i['creator']).execute().data
                    i['creatornm'] = creatornm[0]['full_name'] if creatornm else ''
                except Exception as e:
                    i['creatornm'] = ''
            # 날짜 양식 맞춤
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

        context = {
            'filemasters': filemasters,
            'files': files,
            'filestatus': filestatus,
            'revisiontypes': revisiontypes,
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
            filemastercd = request.POST.get('filemasternm')
            filecd = request.POST.get('filecd')
            version = request.POST.get('version')
            filenm = request.POST.get('filenm')
            filestatus = request.POST.get('filestatus')
            revisiontype = request.POST.get('revisiontype')
            supersedes_filecd = request.POST.get('supersedes_filecd')
            approval_date = request.POST.get('approval_date') or None
            effective_date = request.POST.get('effective_date') or None
            obsolete_date = request.POST.get('obsolete_date') or None
            change_reason = request.POST.get('change_reason')
            
            # 이미 동일한 프로젝트에 동일한 파일명 있으면 삽입 불가
            # print(f'FileMasterCd: {filemastercd}')
            existing_filenm = supabase.schema('rag').table('files').select('*').eq('filemastercd', filemastercd).neq('filecd', filecd).eq('version', version).eq('filenm', filenm).execute().data
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

            existing = supabase.schema('rag').table('files').select('*').eq('filecd', filecd).execute().data
            if existing:
                filenm = existing[0]['filenm']
                version = existing[0]['version']
                blob_name = f'{filenm}_{version}'

            if uploaded_file:
                # 파일 확장자 추출
                file_extension = os.path.splitext(uploaded_file.name)[1]
                project_id = supabase.schema('rag').table('filemasters').select("projectid").eq('filemastercd', filemastercd).execute().data[0]['projectid']

                # 컨테이너
                dirPath = supabase.schema('rag').table('projects').select('dirpath').eq('projectid', project_id).execute().data[0]['dirpath']
                
                # 기존 존재 시 삭제
                if blob_name:
                    delete_from_azure_blob(blob_name, dirPath)

                # 원본 파일명과 확장자 분리
                original_name = uploaded_file.name
                name_without_ext, extension = os.path.splitext(original_name)

                # 새로운 파일명 생성
                uploaded_file.name = f'{name_without_ext}_{version}{extension}'


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
                
            if filecd:
                pass
            else:
                filecd = f'{filemastercd}_{version}'
            
            # Supabase에 메타데이터 저장
            data = {
                'filemastercd': filemastercd,
                'filecd': filecd,
                'version': version,
                'filenm': filenm,
                'filestatus': filestatus,
                'revisiontype': revisiontype,
                'supersedes_filecd': supersedes_filecd,
                'approval_date': approval_date,
                'effective_date': effective_date,
                'obsolete_date': obsolete_date,
                'change_reason': change_reason,
                'creator': user_id,  # 또는 적절한 사용자 정보
            }
            
            # 파일이 업로드된 경우 추가 정보 저장
            if blob_url:
                data['fileextension'] = file_extension[1:]
            #     data['bloburl'] = blob_url
            #     data['blobname'] = blob_name
            
            # print(f'Data: {data}')

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
            filecd = data.get('filecd')
            
            if not filecd:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일 CD가 필요합니다.'
                })
            
            # Supabase에서 파일 정보 조회
            file_info = supabase.schema('rag').table('files').select('*').eq('filecd', filecd).execute()
            
            if not file_info.data:
                return JsonResponse({
                    'result': 'error',
                    'message': '파일을 찾을 수 없습니다.'
                })
            
            file_data = file_info.data[0]
            project_id = file_data['projectid']
            filenm = file_data.get('filenm')
            fileextension = file_data.get('fileextension')
            
            # Azure Blob Storage에서 파일 삭제 (fileextension 이 있는 경우에만)
            if fileextension:
                supfilenm = filenm
                extension = '.' + fileextension
                version = file_data.get('version')
                blob_name = f'{supfilenm.replace(extension, "")}_{version}{extension}'

                # 컨테이너
                dirPath = supabase.schema('rag').table('projects').select('dirpath').eq('projectid', project_id).execute().data[0]['dirpath']

                # Blob 파일 삭제
                delete_result = delete_from_azure_blob(blob_name, dirPath)
                
                if not delete_result['success']:
                    # Blob 삭제 실패해도 계속 진행 (파일이 이미 없을 수도 있음)
                    print(f"Warning: Blob 삭제 실패 - {delete_result['error']}")
            
            # Supabase에서 메타데이터 삭제
            result = supabase.schema('rag').table('files').delete().eq('filecd', filecd).execute()
            
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