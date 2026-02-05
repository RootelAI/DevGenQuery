# views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

import json
import random
import re

from utilsPrj.sms_sender import NaverSMSSender

# Supabase 연동 (선택사항)
try:
    from supabase import create_client
    from django.conf import settings
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    SUPABASE_ENABLED = True
except:
    SUPABASE_ENABLED = False

# 임시 저장소 (실제 환경에서는 Redis나 DB 사용 권장)
verification_storage = {}

def sms_verification_page(request):
    """SMS 인증 페이지 렌더링"""
    return render(request, 'sms_verification.html')

@csrf_exempt
@require_http_methods(["POST"])
def send_verification_sms(request):
    """인증번호 SMS 발송"""
    try:
        # JSON 데이터 파싱
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        phone_number = data.get('phone_number', '').strip()
        
        # 휴대폰 번호 유효성 검사
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'message': '휴대폰 번호를 입력해주세요.'
            })
        
        # 휴대폰 번호 형식 검증 (010-XXXX-XXXX 또는 01012345678)
        phone_pattern = re.compile(r'^01[016789]-?\d{3,4}-?\d{4}$')
        if not phone_pattern.match(phone_number):
            return JsonResponse({
                'success': False, 
                'message': '올바른 휴대폰 번호 형식이 아닙니다.'
            })
        
        # 하이픈 제거
        clean_phone = re.sub(r'[^0-9]', '', phone_number)
        
        # 6자리 인증번호 생성
        verification_code = str(random.randint(100000, 999999))
        
        # 만료시간 설정 (5분)
        expires_at = timezone.now() + timedelta(minutes=5)
        
        # SMS 발송
        sms_sender = NaverSMSSender()
        content = f"[Web발신] 본인 인증 번호: {verification_code}\n5분 내에 입력해주세요."
        
        sms_result = sms_sender.send_sms(clean_phone, content)
        
        if sms_result['success']:
            # 인증번호 저장 (실제 환경에서는 DB나 Redis 사용)
            verification_storage[clean_phone] = {
                'code': verification_code,
                'expires_at': expires_at,
                'attempts': 0,
                'verified': False
            }
            
            # Supabase 저장 (선택사항)
            if SUPABASE_ENABLED:
                try:
                    supabase.table('sms_verifications').upsert({
                        'phone_number': clean_phone,
                        'verification_code': verification_code,
                        'expires_at': expires_at.isoformat(),
                        'is_verified': False,
                        'attempts': 0
                    }).execute()
                except Exception as e:
                    print(f"Supabase 저장 오류: {e}")
            
            return JsonResponse({
                'success': True,
                'message': '인증번호가 발송되었습니다.',
                'phone_number': clean_phone
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'SMS 발송 실패: {sms_result["message"]}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def verify_sms_code(request):
    """인증번호 확인"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        phone_number = data.get('phone_number', '').strip()
        input_code = data.get('verification_code', '').strip()
        
        if not phone_number or not input_code:
            return JsonResponse({
                'success': False,
                'message': '휴대폰 번호와 인증번호를 모두 입력해주세요.'
            })
        
        clean_phone = re.sub(r'[^0-9]', '', phone_number)
        
        # 저장된 인증번호 확인
        stored_data = verification_storage.get(clean_phone)
        
        if not stored_data:
            return JsonResponse({
                'success': False,
                'message': '인증번호 발송 기록이 없습니다. 다시 요청해주세요.'
            })
        
        # 만료시간 확인
        if timezone.now() > stored_data['expires_at']:
            del verification_storage[clean_phone]
            return JsonResponse({
                'success': False,
                'message': '인증번호가 만료되었습니다. 다시 요청해주세요.'
            })
        
        # 시도 횟수 확인 (5회 제한)
        if stored_data['attempts'] >= 5:
            del verification_storage[clean_phone]
            return JsonResponse({
                'success': False,
                'message': '인증 시도 횟수를 초과했습니다. 다시 요청해주세요.'
            })
        
        # 인증번호 확인
        if input_code == stored_data['code']:
            # 인증 성공
            verification_storage[clean_phone]['verified'] = True
            
            # Supabase 업데이트 (선택사항)
            if SUPABASE_ENABLED:
                try:
                    supabase.table('sms_verifications').update({
                        'is_verified': True,
                        'verified_at': timezone.now().isoformat()
                    }).eq('phone_number', clean_phone).execute()
                except Exception as e:
                    print(f"Supabase 업데이트 오류: {e}")
            
            request.session["phone"] = clean_phone

            return JsonResponse({
                'success': True,
                'message': '인증이 완료되었습니다.',
                'verified': True
            })
        else:
            # 인증 실패
            verification_storage[clean_phone]['attempts'] += 1
            remaining_attempts = 5 - verification_storage[clean_phone]['attempts']
            
            return JsonResponse({
                'success': False,
                'message': f'인증번호가 일치하지 않습니다. (남은 시도: {remaining_attempts}회)',
                'remaining_attempts': remaining_attempts
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류: {str(e)}'
        })

def check_verification_status(request):
    """인증 상태 확인"""
    phone_number = request.GET.get('phone_number', '').strip()
    
    if not phone_number:
        return JsonResponse({
            'success': False,
            'message': '휴대폰 번호를 입력해주세요.'
        })
    
    clean_phone = re.sub(r'[^0-9]', '', phone_number)
    stored_data = verification_storage.get(clean_phone)
    
    if stored_data and stored_data.get('verified', False):
        return JsonResponse({
            'success': True,
            'verified': True,
            'message': '인증 완료됨'
        })
    else:
        return JsonResponse({
            'success': True,
            'verified': False,
            'message': '인증 필요'
        })

# 일반 폼 처리용 뷰 (HTML 폼 submit용)
def process_sms_verification(request):
    """일반 HTML 폼으로 SMS 인증 처리"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'send_sms':
            # SMS 발송 처리
            phone_number = request.POST.get('phone_number', '').strip()
            
            if not phone_number:
                messages.error(request, '휴대폰 번호를 입력해주세요.')
                return render(request, 'sms_verification.html')
            
            # 인증번호 발송 로직 (위의 send_verification_sms와 동일)
            clean_phone = re.sub(r'[^0-9]', '', phone_number)
            verification_code = str(random.randint(100000, 999999))
            expires_at = timezone.now() + timedelta(minutes=5)
            
            sms_sender = NaverSMSSender()
            content = f"[Web발신] 본인 인증 번호: {verification_code}\n5분 내에 입력해주세요."
            sms_result = sms_sender.send_sms(clean_phone, content)
            
            if sms_result['success']:
                verification_storage[clean_phone] = {
                    'code': verification_code,
                    'expires_at': expires_at,
                    'attempts': 0,
                    'verified': False
                }
                messages.success(request, '인증번호가 발송되었습니다.')
                return render(request, 'sms_verification.html', {
                    'phone_number': clean_phone,
                    'sms_sent': True
                })
            else:
                messages.error(request, f'SMS 발송 실패: {sms_result["message"]}')
                
        elif action == 'verify_code':
            # 인증번호 확인 처리
            phone_number = request.POST.get('phone_number', '').strip()
            verification_code = request.POST.get('verification_code', '').strip()
            
            clean_phone = re.sub(r'[^0-9]', '', phone_number)
            stored_data = verification_storage.get(clean_phone)
            
            if stored_data and verification_code == stored_data['code']:
                if timezone.now() <= stored_data['expires_at']:
                    verification_storage[clean_phone]['verified'] = True
                    messages.success(request, '인증이 완료되었습니다!')
                    return render(request, 'sms_verification.html', {
                        'verified': True,
                        'phone_number': clean_phone
                    })
                else:
                    messages.error(request, '인증번호가 만료되었습니다.')
            else:
                messages.error(request, '인증번호가 일치하지 않습니다.')
    
    return render(request, 'sms_verification.html')