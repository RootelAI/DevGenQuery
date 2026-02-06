from django.shortcuts import render
from django.http import JsonResponse
import json
from utilsPrj.supabase_client import get_supabase_client
from .master_tables import master_tables_json_create
from django.http import JsonResponse
import json

def master_columns(request):
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
        project_map = {}
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

        # 3. 모든 테이블 조회 (좌측 목록용)
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
        table_ids = [t["tableuid"] for t in tables]

        # 각 테이블에 projectnm 추가
        for table in tables:
            table["projectnm"] = project_map.get(table["projectid"], "-")

        # 4. 컬럼 정보 조회
        columns_response = (
            supabase.schema("genquery")
            .table("columns")
            .select("*")
            .in_("tableuid", table_ids)
            .execute()
        )
        columns = columns_response.data or []

        # 5. values 조회
        values_response = (
            supabase.schema("genquery")
            .table("values")
            .select("*")
            .in_("tableuid", table_ids)
            .execute()
        )
        values = values_response.data or []

        # 6. 데이터 타입 정보 조회
        datatype_response = (
            supabase.schema("genquery")
            .table("col_data_types")
            .select("*")
            .execute()
        )
        datatype = datatype_response.data or []

        # 7. 컬럼별 value 개수 계산
        from collections import defaultdict
        value_count_map = defaultdict(int)
        for val in values:
            key = (val["tableuid"], val["column_name"])
            value_count_map[key] += 1

        # columns에 value_count 추가
        for col in columns:
            key = (col["tableuid"], col["column_name"])
            col["value_count"] = value_count_map.get(key, 0)

        context = {
            "tables": tables,      # 좌측 전체 테이블 목록
            "columns": columns,    # 컬럼 + value_count
            "values": values,      # 전체 values
            "datatype": datatype,  # 데이터 타입
            "projects": projects,  # 프로젝트 목록
        }

        return render(request, "pages/master_columns.html", context)

    except Exception as e:
        return render(request, "pages/master_columns.html", {
            "projects": [],
            "tables": [],
            "columns": [],
            "values": [],
            "datatype": [],
            "error": "데이터 조회 중 오류가 발생했습니다.",
        })

def master_columns_save(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST 요청만 허용됩니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"success": False, "error": "로그인이 필요합니다."})

    user_id = user.get("id")
    useruid = user.get("id")

    try:
        body = json.loads(request.body)
        columns = body.get("columns", [])

        if not columns:
            return JsonResponse({"success": False, "error": "저장할 컬럼 데이터가 없습니다."})

        # ==============================
        # 1. 테이블 UID 목록 추출
        # ==============================
        table_uids = list({c["tableuid"] for c in columns})

        # ==============================
        # 2. 테이블 권한 체크
        # ==============================
        table_resp = (
            supabase.schema("genquery")
            .table("tables")
            .select("tableuid, projectid")
            .in_("tableuid", table_uids)
            .execute()
        )

        if not table_resp.data:
            return JsonResponse({"success": False, "error": "테이블 정보를 찾을 수 없습니다."})

        project_ids = [t["projectid"] for t in table_resp.data]

        projectusers_resp = (
            supabase.schema("genquery")
            .table("projectusers")
            .select("projectid")
            .eq("useruid", useruid)
            .execute()
        )

        user_project_ids = [p["projectid"] for p in projectusers_resp.data or []]

        for pid in project_ids:
            if pid not in user_project_ids:
                return JsonResponse({
                    "success": False,
                    "error": "저장 권한이 없는 테이블이 있습니다."
                })

        # ==============================
        # 3. 테이블 단위 삭제 → insert
        # ==============================
        for tableuid in table_uids:

            # (1) 해당 테이블 컬럼 전부 삭제
            supabase.schema("genquery") \
                .table("columns") \
                .delete() \
                .eq("tableuid", tableuid) \
                .execute()

            # (2) 프론트에서 넘어온 컬럼만 다시 insert
            insert_rows = []
            for col in columns:
                if col["tableuid"] != tableuid:
                    continue

                insert_rows.append({
                    "tableuid": tableuid,
                    "column_name": col.get("column_name"),
                    "logical_name": col.get("logical_name"),
                    "aliases": col.get("aliases"),
                    "data_type": col.get("data_type"),
                    "creator": user_id
                })

            if insert_rows:
                supabase.schema("genquery") \
                    .table("columns") \
                    .insert(insert_rows) \
                    .execute()
        
        master_tables_json_create(supabase, tableuid)  # ← 여기에 tableuid 전달

        return JsonResponse({
            "success": True,
            "message": "컬럼 저장 완료"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": "저장 중 오류 발생"
        })

def master_columns_delete(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST 요청만 가능합니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"success": False, "error": "로그인이 필요합니다."})

    useruid = user.get("id")

    try:
        body = json.loads(request.body)
        tableuid = body.get("tableuid")
        if not tableuid:
            return JsonResponse({"success": False, "error": "삭제할 테이블 정보가 없습니다."})

        # 권한 체크: 사용자가 테이블 프로젝트에 속하는지
        table_resp = (
            supabase.schema("genquery")
            .table("tables")
            .select("projectid")
            .eq("tableuid", tableuid)
            .execute()
        )
        if not table_resp.data:
            return JsonResponse({"success": False, "error": "테이블 정보를 찾을 수 없습니다."})

        table_project_id = table_resp.data[0]["projectid"]

        projectusers_resp = (
            supabase.schema("genquery")
            .table("projectusers")
            .select("projectid")
            .eq("useruid", useruid)
            .execute()
        )
        user_project_ids = [p["projectid"] for p in projectusers_resp.data or []]

        if table_project_id not in user_project_ids:
            return JsonResponse({"success": False, "error": "삭제 권한이 없습니다."})

        # 컬럼 삭제 (해당 테이블 모든 컬럼)
        supabase.schema("genquery").table("columns").delete().eq("tableuid", tableuid).execute()
        supabase.schema("genquery").table("values").delete().eq("tableuid", tableuid).execute()

        return JsonResponse({"success": True, "message": "해당 테이블의 컬럼이 모두 삭제되었습니다."})

    except Exception as e:
        return JsonResponse({"success": False, "error": "삭제 중 오류 발생"})

def master_values_save(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST 요청만 허용됩니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"success": False, "error": "로그인이 필요합니다."})

    user_id = user.get("id")
    useruid = user.get("id")

    try:
        body = json.loads(request.body)
        values_data = body.get("values", [])

        if not values_data:
            return JsonResponse({"success": False, "error": "저장할 값 데이터가 없습니다."})

        # 테이블 UID + 컬럼명 추출
        table_column_pairs = list({(v["tableuid"], v["column_name"]) for v in values_data})

        # 권한 체크
        table_uids = [pair[0] for pair in table_column_pairs]
        table_resp = supabase.schema("genquery").table("tables").select("tableuid, projectid").in_("tableuid", table_uids).execute()
        if not table_resp.data:
            return JsonResponse({"success": False, "error": "테이블 정보를 찾을 수 없습니다."})

        project_ids = [t["projectid"] for t in table_resp.data]
        projectusers_resp = supabase.schema("genquery").table("projectusers").select("projectid").eq("useruid", useruid).execute()
        user_project_ids = [p["projectid"] for p in projectusers_resp.data or []]

        for pid in project_ids:
            if pid not in user_project_ids:
                return JsonResponse({"success": False, "error": "저장 권한이 없는 테이블이 있습니다."})

        # 테이블 단위로 값 삭제 → insert
        for tableuid, column_name in table_column_pairs:
            # 해당 컬럼 값 전체 삭제
            supabase.schema("genquery").table("values").delete().eq("tableuid", tableuid).eq("column_name", column_name).execute()

            # 프론트에서 넘어온 값만 insert
            insert_rows = []
            for v in values_data:
                if v["tableuid"] == tableuid and v["column_name"] == column_name:
                    insert_rows.append({
                        "tableuid": tableuid,
                        "column_name": column_name,
                        "value": v.get("value"),
                        "logical_name": v.get("logical_name"),
                        "aliases": v.get("aliases"),
                        "orderno": v.get("orderno"),
                        "creator": user_id
                    })
            if insert_rows:
                supabase.schema("genquery").table("values").insert(insert_rows).execute()

        master_tables_json_create(supabase, tableuid)  # ← 여기에 tableuid 전달
        
        return JsonResponse({"success": True, "message": "값 저장 완료"})

    except Exception as e:
        return JsonResponse({"success": False, "error": "저장 중 오류 발생"})


def master_value_delete(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST 요청만 허용됩니다."})

    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    supabase = get_supabase_client(access_token, refresh_token)

    user = request.session.get("user")
    if not user:
        return JsonResponse({"success": False, "error": "로그인이 필요합니다."})

    useruid = user.get("id")

    try:
        body = json.loads(request.body)
        tableuid = body.get("tableuid")
        column_name = body.get("column_name")

        if not tableuid or not column_name:
            return JsonResponse({"success": False, "error": "삭제할 컬럼 정보가 없습니다."})

        # 권한 체크
        table_resp = supabase.schema("genquery").table("tables").select("projectid").eq("tableuid", tableuid).execute()
        if not table_resp.data:
            return JsonResponse({"success": False, "error": "테이블 정보를 찾을 수 없습니다."})

        table_project_id = table_resp.data[0]["projectid"]

        projectusers_resp = supabase.schema("genquery").table("projectusers").select("projectid").eq("useruid", useruid).execute()
        user_project_ids = [p["projectid"] for p in projectusers_resp.data or []]

        if table_project_id not in user_project_ids:
            return JsonResponse({"success": False, "error": "삭제 권한이 없습니다."})

        # 값 전체 삭제
        supabase.schema("genquery").table("values").delete().eq("tableuid", tableuid).eq("column_name", column_name).execute()

        return JsonResponse({"success": True, "message": "해당 컬럼의 모든 값이 삭제되었습니다."})

    except Exception as e:
        return JsonResponse({"success": False, "error": "삭제 중 오류 발생"})
