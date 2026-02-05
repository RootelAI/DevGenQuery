from django.shortcuts import render, redirect
from utilsPrj.supabase_client import get_supabase_client

def faq_view(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    # user_id = user.get("id")
    roleid = user.get("roleid") if user else 0  # user 없으면 0

    faqs_resp = supabase.schema("genquery").table("faqs").select("*").order("orderno").execute()
    faqs = faqs_resp.data if faqs_resp.data else []

    return render(request, 'pages/faq.html', {
        'faqs': faqs,
        'roleid' : roleid
    })

def faq_save(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    user_id = user.get("id")
    roleid = user.get("roleid") if user else 0

    # roleid 7이 아니면 접근 제한
    if roleid != 7:
        return redirect('faq_view')

    if request.method == "POST":
        faquid = request.POST.get("faquid")  # 편집일 경우 faquid 존재
        title = request.POST.get("title")
        question = request.POST.get("question")
        answer = request.POST.get("answer")
        orderno = int(request.POST.get("orderno"))

        if faquid:
            # 기존 FAQ 편집
            supabase.schema("genquery").table("faqs").update({
                "title": title,
                "question": question,
                "answer": answer,
                "orderno": orderno
            }).eq("faquid", faquid).execute()
        else:
            # 새 FAQ 추가
            supabase.schema("genquery").table("faqs").insert({
                "title": title,
                "question": question,
                "answer": answer,
                "orderno": orderno,
                "creator":user_id
            }).execute()

        return redirect('faq_view')  # 저장 후 FAQ 목록으로 이동

    # GET 요청 (편집)
    faquid = request.GET.get("faquid")
    faq = {}
    if faquid:
        faq_resp = supabase.schema("genquery").table("faqs").select("*").eq("faquid", faquid).execute()
        faq = faq_resp.data[0] if faq_resp.data else {}

    return render(request, "pages/faq_save.html", {"faq": faq})

def faq_delete(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    roleid = user.get("roleid") if user else 0

    # roleid 7이 아니면 접근 제한
    if roleid != 7:
        return redirect('faq_view')

    # POST 요청으로 삭제 처리
    if request.method == "POST":
        faquid = request.POST.get("faquid")
        if faquid:
            supabase.schema("genquery").table("faqs").delete().eq("faquid", faquid).execute()
        return redirect('faq_view')

    # GET 요청이면 확인 페이지 없이 바로 삭제 가능 (URL 호출용)
    faquid = request.GET.get("faquid")
    if faquid:
        supabase.schema("genquery").table("faqs").delete().eq("faquid", faquid).execute()

    return redirect('faq_view')
