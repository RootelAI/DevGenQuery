from django.shortcuts import render
from django.http import JsonResponse
import json
from utilsPrj.supabase_client import get_supabase_client
import re

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

        # 2. 프로젝트 목록 조회 (권한 기반, 우측 selectbox용)
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
            project_map = {p["projectid"]: p["projectnm"] for p in projects}

        # 3. 모든 테이블 조회 (필터 없이, 좌측 목록용)
        tables_response = (
            supabase.schema("genquery")
            .table("tables")
            .select("*")
            .in_("projectid", project_ids)
            .order("schema_name")
            .order("physical_name")
            .execute()
        )
        tables = tables_response.data or []

        # 각 테이블에 projectnm 추가
        for table in tables:
            table["projectnm"] = project_map.get(table["projectid"], "-")
            
        context = {
            "projects": projects,  # 우측 selectbox용
            "tables": tables,      # 좌측 전체 테이블 목록
        }
        return render(request, "pages/master_tables.html", context)

    except Exception as e:
        return render(request, "pages/master_tables.html", {
            "projects": [],
            "tables": [],
            "error": "데이터 조회 중 오류가 발생했습니다.",
        })

def master_tables_save(request):
    if request.method != "POST":
        return JsonResponse({"result": "Failed", "error": "POST 요청만 허용됩니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"result": "Failed", "error": "로그인이 필요합니다."})

    user_id = user.get("id")
    useruid = user.get("id")

    # 사용자 소속 프로젝트 조회 (권한 체크용)
    projectusers_response = (
        supabase.schema("genquery")
        .table("projectusers")
        .select("projectid")
        .eq("useruid", useruid)
        .execute()
    )
    projectusers = projectusers_response.data or []
    user_project_ids = [pu["projectid"] for pu in projectusers]

    # POST 데이터 가져오기
    data = {
        "projectid": request.POST.get("projectid"),
        "schema_name": request.POST.get("schema_name"),
        "physical_name": request.POST.get("physical_name"),
        "logical_name": request.POST.get("logical_name"),
        "aliases": request.POST.get("aliases"),
        "source_type": request.POST.get("source_type"),
        "primary_key": request.POST.get("primary_key"),
        "default_time_column": request.POST.get("default_time_column"),
        "grain": request.POST.get("grain"),
        "purpose": request.POST.get("purpose"),
        "query_examples": request.POST.get("query_examples"),
        "description" : request.POST.get("description"),
        "parent_schema": request.POST.get("parent_schema"),
        "parent_table": request.POST.get("parent_table"),
        "parent_column": request.POST.get("parent_column"),
        "child_column": request.POST.get("child_column"),
    }

    tableuid = request.POST.get("tableuid")
    target_projectid = request.POST.get("projectid")

    try:
        target_projectid = int(target_projectid)
    except (TypeError, ValueError):
        return JsonResponse({"result": "Failed", "error": "잘못된 프로젝트 정보입니다."})

    # 권한 체크: 사용자가 프로젝트에 속해 있는지
    if target_projectid not in user_project_ids:
        return JsonResponse({"result": "Failed", "error": "저장 권한이 없습니다."})

    try:
        if tableuid:  # 기존 테이블 업데이트
            # 기존 테이블의 projectid 확인 (추가 권한 체크)
            table_response = (
                supabase.schema("genquery")
                .table("tables")
                .select("projectid")
                .eq("tableuid", tableuid)
                .execute()
            )
            if not table_response.data:
                return JsonResponse({"result": "Failed", "error": "테이블을 찾을 수 없습니다."})
            if table_response.data[0]["projectid"] not in user_project_ids:
                return JsonResponse({"result": "Failed", "error": "수정 권한이 없습니다."})

            response = (
                supabase.schema("genquery")
                .table("tables")
                .update(data)
                .eq("tableuid", tableuid)
                .execute()
            )
        else:  # 신규 테이블 삽입
            data["creator"] = user_id
            response = (
                supabase.schema("genquery")
                .table("tables")
                .insert(data)
                .execute()
            )

        if response.data:
            # 저장 성공 후 tableuid 전달해서 master_tables_json_create 호출
            saved_tableuid = response.data[0].get("tableuid")
            master_tables_json_create(supabase, saved_tableuid)  # ← 여기에 tableuid 전달

        if response.data:
            return JsonResponse({
                "result": "success",
                "table": response.data[0],
                "message": "테이블이 성공적으로 저장되었습니다."
            })
        else:
            return JsonResponse({
                "result": "Failed",
                "error": "테이블 저장에 실패했습니다."
            })

    except Exception as e:
        return JsonResponse({
            "result": "Failed",
            "error": "저장 중 오류가 발생했습니다."
        })

def master_tables_delete(request):
    if request.method != "POST":
        return JsonResponse({"result": "Failed", "error": "POST 요청만 가능합니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"result": "Failed", "error": "로그인이 필요합니다."})

    useruid = user.get("id")

    # 사용자 소속 프로젝트 조회 (권한 체크용)
    projectusers_response = (
        supabase.schema("genquery")
        .table("projectusers")
        .select("projectid")
        .eq("useruid", useruid)
        .execute()
    )
    projectusers = projectusers_response.data or []
    user_project_ids = [pu["projectid"] for pu in projectusers]

    try:
        body = json.loads(request.body)
        tableuid = body.get("tableuid")
        if not tableuid:
            return JsonResponse({"result": "Failed", "error": "삭제할 테이블 정보가 없습니다."})

        # 삭제 전 권한 체크
        table_response = (
            supabase.schema("genquery")
            .table("tables")
            .select("projectid")
            .eq("tableuid", tableuid)
            .execute()
        )

        if not table_response.data:
            return JsonResponse({"result": "Failed", "error": "테이블을 찾을 수 없습니다."})

        table_project_id = table_response.data[0]["projectid"]

        # user가 해당 프로젝트에 속해 있는지 확인
        if table_project_id not in user_project_ids:
            return JsonResponse({"result": "Failed", "error": "삭제 권한이 없습니다."})

        # 삭제 실행 (성공 여부는 try/except와 권한 체크로 판단)
        supabase.schema("genquery").table("tables").delete().eq("tableuid", tableuid).execute()

        # 성공 처리
        return JsonResponse({"result": "success", "message": "테이블이 삭제되었습니다."})

    except Exception as e:
        return JsonResponse({"result": "Failed", "error": "삭제 중 오류가 발생했습니다."})

def parse_aliases(s):
    """문자열에서 " " 로 감싼 alias들을 리스트로 반환"""
    if not s:
        return []
    return re.findall(r'"(.*?)"', s)

def parse_multiline(s):
    if not s:
        return []

    lines = re.split(r'[\r\n]+', s)
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # "내용",  → 내용
        line = re.sub(r'^"\s*|\s*",?$', '', line)

        cleaned.append(line)

    return cleaned

def master_tables_json_create(supabase, tableuid):
    try:
        # ------------------ tables (필수) ------------------
        table_resp = (
            supabase.schema("genquery")
            .table("tables")
            .select("*")
            .eq("tableuid", tableuid)
            .execute()
        )
        if not table_resp.data:
            return None  # ❌ 즉시 종료

        table = table_resp.data[0]

        # ------------------ columns (필수) ------------------
        columns_resp = (
            supabase.schema("genquery")
            .table("columns")
            .select("*")
            .eq("tableuid", tableuid)
            .execute()
        )
        if not columns_resp.data:
            return None  # ❌ 즉시 종료

        # ------------------ values (선택) ------------------
        values_resp = (
            supabase.schema("genquery")
            .table("values")
            .select("*")
            .eq("tableuid", tableuid)
            .execute()
        )
        values_data = values_resp.data or []

        # ------------------ 테이블 기본 JSON ------------------
        table_json = {
            "schema": table["schema_name"],
            "physical_name": table["physical_name"],
            "logical_name": table.get("logical_name", ""),
            "aliases": parse_aliases(table.get("aliases", "")),
            "source_type": table.get("source_type", ""),
            "description": table.get("description", ""),
            "primary_key": parse_aliases(table.get("primary_key", "")),
            "grain": table.get("grain", "").strip('" '),
            "default_time_column": table.get("default_time_column", ""),
            "purpose": parse_multiline(table.get("purpose", "")),
            "query_examples": parse_multiline(table.get("query_examples", "")),
            "columns": {}
        }

        # ------------------ 컬럼 메타 ------------------
        for col in columns_resp.data:
            table_json["columns"][col["column_name"]] = {
                "logical_name": col.get("logical_name", ""),
                "aliases": parse_aliases(col.get("aliases", "")),
                "data_type": col.get("data_type", "string")
            }

        # ------------------ values 매핑 ------------------
        for v in values_data:
            col_name = v["column_name"]
            if col_name not in table_json["columns"]:
                continue  # 방어 코드

            col_entry = table_json["columns"][col_name]
            values_obj = col_entry.setdefault("values", {})

            values_obj[v["value"]] = {
                "logical_name": v.get("logical_name", ""),
                "aliases": parse_aliases(v.get("aliases", ""))
            }

        # ------------------ 저장 ------------------
        supabase.schema("genquery") \
            .table("tables") \
            .update({"json": table_json}) \
            .eq("tableuid", tableuid) \
            .execute()

        return table_json

    except Exception:
        return None
