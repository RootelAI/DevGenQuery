from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings

# 1) 문의 폼 보여주기
def register_qna(request):
    return render(request, 'pages/register_qna.html')

# 2) 폼 제출 처리 + Gmail SMTP로 발송
def register_qna_submit(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        title = request.POST.get("title")
        message = request.POST.get("message")

        # 필수값 체크
        if not all([name, email, title, message]):
            return JsonResponse({
                "result": "Failed",
                "message": "모든 필드를 입력해주세요."
            })

        # 메일 제목/본문 구성
        subject = f"[GenQuery 홈페이지 문의] {title}"
        body = f"""
이름: {name}
이메일: {email}

문의 내용:
{message}
        """

        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,       # 보내는 사람
                [settings.EMAIL_HOST_USER],         # 받는 사람
                fail_silently=False
            )
            return JsonResponse({
                "result": "success",
                "message": "문의가 성공적으로 전송되었습니다."
            })
        except Exception as e:
            return JsonResponse({
                "result": "Failed",
                "message": f"메일 전송 실패: {str(e)}"
            })
    else:
        return JsonResponse({
            "result": "Failed",
            "message": "잘못된 요청입니다."
        })
