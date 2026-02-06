import os
import json
import uuid
import time

from django.shortcuts import render
from django.http import JsonResponse
from dateutil import parser

from utilsPrj.supabase_client import get_supabase_client
from utilsPrj.crypto_helper import encrypt_value, decrypt_value

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from utilsPrj.secrets_manager import secrets_manager

def master_servers(request):
    try:
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")
        
        supabase = get_supabase_client(access_token, refresh_token)
        
        user = request.session.get("user")
        id = user.get("id", "")
        
        # KeyVault 목록 조회
        response = supabase.schema('genquery').table('azure_key_vault')\
            .select('*')\
            .eq('creator', id)\
            .order('createdts', desc=True)\
            .execute()
        
        connectors = response.data if response.data else []
        
        for connector in connectors:
            # 유저
            if connector.get('creator'):
                try:
                    connector['creatornm'] = supabase.schema('genquery').table('users').select("usernm").eq("useruid", connector['creator']).execute().data[0]['usernm']
                except Exception as e:
                    connector['creatornm'] = ''

            # 기업명
            if connector.get('tenantid'):
                try:
                    connector['tenantnm'] = supabase.schema('genquery').table('tenants').select("tenantnm").eq("tenantid", connector['tenantid']).execute().data[0]['tenantnm']
                except Exception as e:
                    connector['tenantnm'] = ''

            # 일시
            if connector.get('createdts'):
                try:
                    dt = parser.parse(connector['createdts']) if isinstance(connector['createdts'], str) else connector['createdts']
                    connector['createdts'] = dt.strftime("%y-%m-%d %H:%M")
                except Exception as e:
                    connector['createdts'] = ''

            if connector.get('serverendpoint'):
                try:
                    connector['serverendpoint_dec'] = secrets_manager.get_secret(connector['serverendpoint'])
                except Exception as e:
                    connector['serverendpoint_dec'] = ''

        # dbtypes = {"MSSQL", "SUPABASE", "ORACLE"}  # 필요 시 추가 가능
        dbtypes = supabase.schema('genquery').table('dbms').select("*").execute().data

        # print(f'KeyVault: {connectors}')

        return render(request, 'pages/master_servers.html', {
            'connectors': connectors,
            'dbtypes': dbtypes,
        })
        
    except Exception as e:
        print(f'Error: {str(e)}')
        return render(request, 'pages/master_servers.html', {
            'keyvaults': [],
            'error': str(e)
        })

def master_servers_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        body = request.body.decode("utf-8")
        if not body:
            return JsonResponse({"error": "Empty request body"}, status=400)
        data = json.loads(body)

        user = request.session.get("user")
        user_id = user.get("id")
        tenantid = user.get("tenantid")

        access_key_uid = data.get('access_key_uid')
        access_key_nm = data.get('accesskeynm')
        server_endpoint = data.get('serverendpoint')
        userId = data.get('userid')
        secret_value = data.get('secret')
        dbms = data.get('dbms')

        # # Azure KeyVault 설정
        vault_url = os.getenv('AZURE_KEY_VAULT_URL')  # 예: https://your-vault.vault.azure.net

        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=vault_url, credential=credential)
        
        # KeyVault에 시크릿 저장 (여러 개의 시크릿으로 저장)
        # prefix 앞에 문자가 먼저 나와야 함으로 인한 특정 명칭 지정
        
        if access_key_uid:
            # print(access_key_uid)
            prefix = f"key-{access_key_uid}"
            Endpoint = f"{prefix}-Svr"
            Password = f"{prefix}-Pwd"

            
            # 기존 항목 업데이트
            secret_client.set_secret(Endpoint, server_endpoint)

            # 신규 들어올 시에만 작업
            if secret_value:
                # print('Not None')
                secret_client.set_secret(Password, secret_value)
            else:
                # print('None')
                pass
            

        else:
            access_key_uid = str(uuid.uuid4())
            
            prefix = f"key-{access_key_uid}"
            Endpoint = f"{prefix}-Svr"
            Password = f"{prefix}-Pwd"
        
            # 중복 체크: 이미 존재하는 accesskeynm인지 확인
            existing_key_nm = supabase.schema('genquery').table('azure_key_vault')\
                .select('accesskeynm')\
                .eq('accesskeynm', access_key_nm)\
                .execute()
            
            if existing_key_nm.data:
                return JsonResponse({
                    'error': f'이미 존재하는 연결자명입니다: {access_key_nm}'
                }, status=400)

            # KeyVault 에 값 저장
            secret_client.set_secret(Endpoint, server_endpoint)
            secret_client.set_secret(Password, secret_value)

        datas = {
                'access_key_uid': access_key_uid,
                'tenantid': tenantid,
                'accesskeynm': access_key_nm,
                'serverendpoint': Endpoint,
                'userid': userId,
                'key_vault_nm': 'QueryGen-Secret',
                'secret_nm': Password,
                'creator': user_id,
                'dbms': dbms
            }
        # print(f'Upsert_Data: {datas}')
        
        # DB에 값 저장
        supabase.schema('genquery').table('azure_key_vault').upsert(datas).execute()


        return JsonResponse({"status": "inserted"})

    except Exception as e:
        # print("Exception caught:", str(e))
        return JsonResponse({"error": str(e)}, status=500)

    
def master_servers_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        data = json.loads(request.body)
        body = json.loads(request.body)
        access_key_uid = body.get("access_key_uid")
        
        # DB에서 정보 조회
        vault_info = supabase.schema('genquery').table('azure_key_vault')\
            .select('*')\
            .eq('access_key_uid', access_key_uid)\
            .execute()
        
        # print(f'Del_keyvault": {vault_info}')

        if not vault_info.data:
            return JsonResponse({'error': '존재하지 않는 항목입니다'}, status=404)
        
        info = vault_info.data[0]
        
        # KeyVault에서 시크릿 삭제
        vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=vault_url, credential=credential)
        
        # 서버엔드포인트와 비밀번호 삭제
        secret_client.begin_delete_secret(info['serverendpoint']).wait()
        secret_client.begin_delete_secret(info['secret_nm']).wait()
        
        # DB에서 삭제
        supabase.schema('genquery').table('azure_key_vault')\
            .delete()\
            .eq('access_key_uid', access_key_uid)\
            .execute()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
