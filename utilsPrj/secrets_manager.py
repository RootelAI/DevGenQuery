from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
import os

class AzureSecretsManager:
    def __init__(self):
        # 환경변수에서 인증 정보 로드
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        vault_name = os.getenv('KEY_VAULT_NAME')
        
        if not all([tenant_id, client_id, client_secret, vault_name]):
            raise ValueError("Azure 인증 정보가 환경변수에 설정되지 않았습니다.")
        
        # 인증 설정
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Secret Client 생성
        vault_url = f"https://{vault_name}.vault.azure.net"
        self.client = SecretClient(vault_url=vault_url, credential=credential)
        
        # 캐시 (한 번만 로드)
        self._secrets_cache = {}
    
    def get_secret(self, secret_name: str) -> str:
        """Key Vault에서 Secret 가져오기 (캐싱)"""
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]
        
        try:
            secret = self.client.get_secret(secret_name)
            self._secrets_cache[secret_name] = secret.value
            return secret.value
        except Exception as e:
            raise Exception(f"Secret '{secret_name}' 가져오기 실패: {str(e)}")

# 싱글톤 인스턴스
secrets_manager = AzureSecretsManager()