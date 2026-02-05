from django.shortcuts import render

def terms_conditions(request):
    # 세션에서 사용자 정보 가져오기
    user_info = request.session.get("user")

    # 세션에 정보가 없는 경우 (예: 로그인 안 했을 때)
    if not user_info:
        user_info = {
            "id": None,
            "email": None,
            "roleid": None,
            "tenantid" : 0,
            "tenantmanager": "N",
            "projectid" : 0,
            "projectmanager": "N",
            "editbuttonyn" : None,
            "billingmodelcd" : None,
        }

    # 템플릿으로 전달
    return render(request, 'pages/terms_conditions.html', {})