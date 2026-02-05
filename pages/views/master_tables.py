from django.shortcuts import render
from utilsPrj.supabase_client import get_supabase_client

def master_tables(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return render(request, "pages/home.html", {
            "code": "login",
            "text": "로그인이 필요합니다.",
            "page": "master_projects",
        })

    useruid = user.get("id")

    try:
        # 1. 사용자 소속 프로젝트 조회
        projectusers_response = (
            supabase.schema("genquery")
            .table("projectusers")
            .select("projectid")
            .eq("useruid", useruid)
            .order("createdts", desc=True)
            .execute()
        )
        projectusers = projectusers_response.data or []
        project_ids = [pu["projectid"] for pu in projectusers]

        # 2. 프로젝트 목록 조회 (권한 기반)
        projects = []
        if project_ids:
            projects_response = (
                supabase.schema("genquery")
                .table("projects")
                .select("*")
                .in_("projectid", project_ids)
                .execute()
            )
            projects = projects_response.data or []

        # 3. 프로젝트 자동 선택
        projectid = None
        if len(projects) == 1:
            projectid = projects[0]["projectid"]

        # 4. 테이블 조회
        tables = []
        if projectid:
            tables_response = (
                supabase.schema("genquery")
                .table("tables")
                .select("*")
                .eq("projectid", projectid)
                .order("schema_name")
                .order("physical_name")
                .execute()
            )
            tables = tables_response.data or []

        context = {
            "projects": projects,
            "tables": tables,
            "projectid": projectid,
        }

        return render(request, "pages/master_tables.html", context)

    except Exception as e:
        return render(request, "pages/master_tables.html", {
            "projects": [],
            "tables": [],
            "error": f"데이터 조회 중 오류가 발생했습니다: {str(e)}",
        })

