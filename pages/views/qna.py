from django.shortcuts import render, redirect
from utilsPrj.supabase_client import get_supabase_client
from datetime import datetime
from dateutil import parser

def qna_view(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if user:
        user_id = user.get("id")
        roleid = user.get("roleid", 0)
    else:
        user_id = None
        roleid = 0

    usernm_resp = supabase.schema("genquery").table("users").select("*").execute()
    usernm = usernm_resp.data if usernm_resp.data else []

    # useruid → usernm 매핑 딕셔너리 생성
    user_dict = {u["useruid"]: u.get("email") for u in usernm}

    qnas_resp = supabase.schema("genquery").table("qnas").select("*").order("createdts", desc=True).execute()
    qnas = qnas_resp.data if qnas_resp.data else []

    # 사용자 이름 매핑 추가
    for q in qnas:
        creator_uid = q.get("creator")
        answer_uid = q.get("answeruseruid")

        q["creatornm"] = user_dict.get(creator_uid, "Unknown")
        q["answernm"] = user_dict.get(answer_uid, "") if answer_uid else ""

        # 2025-12-04 Min
        if q.get('createdts'):
            try:
                dt = parser.parse(q['createdts']) if isinstance(q['createdts'], str) else q['createdts']
                q['createdts'] = dt.strftime("%y-%m-%d %H:%M")
            except Exception as e:
                q['createdts'] = ''

        if q.get('answerdts'):
            try:
                dt = parser.parse(q['answerdts']) if isinstance(q['answerdts'], str) else q['answerdts']
                q['answerdts'] = dt.strftime("%y-%m-%d %H:%M")
            except Exception as e:
                q['answerdts'] = ''

        # ----------------------------
        # 클릭 가능 여부 계산
        # 관리자(roleid=7)인 경우 항상 True
        # 일반 유저는 비공개(isprivate) 글일 경우 본인만 클릭 가능
        is_private = q.get("isprivate", False)
        if roleid == 7:
            q["can_click"] = True
        else:
            if is_private and creator_uid != user_id:
                q["can_click"] = False
            else:
                q["can_click"] = True

    return render(request, 'pages/qna.html', {
        'qnas': qnas,
        'roleid' : roleid
    })


def qna_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    user_id = user.get("id")
    roleid = user.get("roleid") if user else 0

    if request.method == "POST":
        qnauid = request.POST.get("qnauid")  # 편집일 경우 qnauid 존재
        title = request.POST.get("title")
        question = request.POST.get("question")
        isprivate = request.POST.get("isprivate")

        if qnauid:
            # 기존 QnA 편집
            supabase.schema("genquery").table("qnas").update({
                "title": title,
                "question": question,
                "isprivate": isprivate
            }).eq("qnauid", qnauid).execute()
        else:
            # 새 QnA 추가
            supabase.schema("genquery").table("qnas").insert({
                "title": title,
                "question": question,
                "isprivate": isprivate,
                "creator":user_id
            }).execute()

        return redirect('qna_view')  # 저장 후 FAQ 목록으로 이동

    # GET 요청 (편집)
    qnauid = request.GET.get("qnauid")
    qna = {}
    if qnauid:
        qna_resp = supabase.schema("genquery").table("qnas").select("*").eq("qnauid", qnauid).execute()
        qna = qna_resp.data[0] if qna_resp.data else {}

    return render(request, "pages/qna_save.html", {"qna": qna})


def qna_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    roleid = user.get("roleid") if user else 0

    # POST 요청으로 삭제 처리
    if request.method == "POST":
        qnauid = request.POST.get("qnauid")
        if qnauid:
            supabase.schema("genquery").table("qnas").delete().eq("qnauid", qnauid).execute()
        return redirect('qna_view')

    # GET 요청이면 확인 페이지 없이 바로 삭제 가능 (URL 호출용)
    qnauid = request.GET.get("qnauid")
    if qnauid:
        supabase.schema("genquery").table("qnas").delete().eq("qnauid", qnauid).execute()

    return redirect('qna_view')


def qna_answer_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    user_id = user.get("id")
    roleid = user.get("roleid") if user else 0

    # roleid 7이 아니면 접근 제한
    if roleid != 7:
        return redirect('qna_view')

    if request.method == "POST":
        qnauid = request.POST.get("qnauid")  # 편집일 경우 qnauid 존재
        answer = request.POST.get("answer")
        now = datetime.now().isoformat()

        if qnauid:
            # 기존 QnA 편집
            supabase.schema("genquery").table("qnas").update({
                "answer": answer,
                "answeruseruid": user_id,
                "answerdts": now
            }).eq("qnauid", qnauid).execute()
        else:
            pass

        return redirect('qna_view')  # 저장 후 FAQ 목록으로 이동

    # GET 요청 (편집)
    qnauid = request.GET.get("qnauid")
    qna = {}
    if qnauid:
        qna_resp = supabase.schema("genquery").table("qnas").select("*").eq("qnauid", qnauid).execute()
        qna = qna_resp.data[0] if qna_resp.data else {}

    return render(request, "pages/qna_save.html", {"qna": qna})

def qna_answer_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    roleid = user.get("roleid") if user else 0

    # roleid 7만 접근 가능
    if roleid != 7:
        return redirect('qna_view')

    if request.method == "POST":
        qnauid = request.POST.get("qnauid")
        if qnauid:
            # 답변 내용 삭제
            supabase.schema("genquery").table("qnas").update({
                "answer": None,
                "answeruseruid": None,
                "answerdts": None
            }).eq("qnauid", qnauid).execute()

    return redirect("qna_view")
