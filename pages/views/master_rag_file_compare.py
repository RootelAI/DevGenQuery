import os
import base64
import tempfile
import urllib.parse
import traceback
import re

from django.shortcuts import render
from django.http import HttpResponse
from azure.storage.blob import BlobServiceClient
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util

from utilsPrj.supabase_client import get_supabase_client

# 서버 시작 시 1회만 모델 로딩
model = SentenceTransformer('all-MiniLM-L6-v2')


# 🔥 제목 기반 섹션 추출 + 시작 페이지 추적
def extract_sections_from_pdf(blob_path):
    doc = fitz.open(blob_path)
    section_pattern = re.compile(r'^\s*(제\s*\d+\s*[장조항절]\s*.*|\d+(\.\d+)*\s+.*)')

    sections = {}
    current_title = "PREAMBLE"
    sections[current_title] = {"text": "", "start_page": 1}

    for page_number, page in enumerate(doc):
        text = page.get_text()
        if not text.strip():
            continue

        # 줄바꿈 제거 + 공백 정리
        text = " ".join([line.strip() for line in text.splitlines() if line.strip()])

        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if section_pattern.match(stripped):
                current_title = stripped
                sections[current_title] = {"text": "", "start_page": page_number + 1}
            else:
                sections[current_title]["text"] += stripped + " "

    return sections


# 🔹 PDF Proxy
def proxy_pdf(request):
    file_b64 = request.GET.get('file')
    if not file_b64:
        return HttpResponse("Missing file parameter", status=400)

    try:
        file_b64 = urllib.parse.unquote(file_b64)
        blob_path = base64.urlsafe_b64decode(file_b64.encode()).decode()

        project_id = 1
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")

        supabase = get_supabase_client(access_token, refresh_token)
        dirPath = supabase.schema('rag').table('projects') \
            .select('dirpath').eq('projectid', project_id) \
            .execute().data[0]['dirpath']

        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        container_client = blob_service_client.get_container_client(dirPath)
        blob = container_client.download_blob(blob_path)
        pdf_bytes = blob.readall()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(blob_path)}"'
        return response

    except Exception as e:
        print("Exception in proxy_pdf:", e)
        traceback.print_exc()
        return HttpResponse(f"Error fetching PDF: {str(e)}", status=500)


# 🔹 섹션 기반 비교 (전체 PDF)
# 🔹 섹션 기반 비교 (전체 PDF) + 전처리 강화
def master_rag_file_compare(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    user = request.session.get("user")

    if not user:
        return render(request, "pages/home.html", {
            "code": "login",
            "text": "로그인이 필요합니다.",
            "page": "master_rag_files",
        })

    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        project_id = 1
        supabase = get_supabase_client(access_token, refresh_token)
        dirPath = supabase.schema('rag').table('projects') \
            .select('dirpath').eq('projectid', project_id) \
            .execute().data[0]['dirpath']

        # 비교 대상 PDF
        file1 = "source/완제의약품 제조 및 품질관리기준(GMP) 가이던스(제2개정판 및 추보).pdf"
        file2 = "source/완제의약품_제조_및_품질관리기준(GMP)_가이던스.pdf"

        container_client = blob_service_client.get_container_client(dirPath)
        blob1 = container_client.download_blob(file1).readall()
        blob2 = container_client.download_blob(file2).readall()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
            tmp1.write(blob1)
            tmp_path1 = tmp1.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
            tmp2.write(blob2)
            tmp_path2 = tmp2.name

        sections1 = extract_sections_from_pdf(tmp_path1)
        sections2 = extract_sections_from_pdf(tmp_path2)

        threshold = 0.85
        diff_list = []

        # 공통 섹션 비교
        common_titles = set(sections1.keys()).intersection(set(sections2.keys()))
        for title in common_titles:
            left_page = sections1[title]["start_page"]
            right_page = sections2[title]["start_page"]

            # 텍스트 전처리
            text1 = re.sub(r'\[\S+\]', '', sections1[title]["text"])  # [별첨2] 등 제거
            text2 = re.sub(r'\[\S+\]', '', sections2[title]["text"])
            text1 = re.sub(r'\s+', ' ', text1).strip()
            text2 = re.sub(r'\s+', ' ', text2).strip()

            # 문장 단위 분리 (한글 + 영어 + 숫자 고려)
            sents1 = re.split(r'(?<=[.!?])\s+(?=[A-Z가-힣0-9])', text1)
            sents2 = re.split(r'(?<=[.!?])\s+(?=[A-Z가-힣0-9])', text2)

            if not sents1 or not sents2:
                continue

            embeddings1 = model.encode(sents1, convert_to_tensor=True)
            embeddings2 = model.encode(sents2, convert_to_tensor=True)

            matched_r = set()
            html_rows = []

            # Left → Right 비교
            for idx1, emb1 in enumerate(embeddings1):
                cos_scores = util.cos_sim(emb1, embeddings2)[0]
                max_score = cos_scores.max().item()
                idx2 = cos_scores.argmax().item()
                if max_score < threshold:
                    html_rows.append({
                        "side": "Left 삭제/변경",
                        "sentence": sents1[idx1],
                        "compare_sentence": sents2[idx2],
                        "similarity": f"{max_score:.3f}"
                    })
                matched_r.add(idx2)

            # Right → Left 비교 (아직 매칭 안 된 문장만)
            for idx2, emb2 in enumerate(embeddings2):
                if idx2 in matched_r:
                    continue
                cos_scores = util.cos_sim(emb2, embeddings1)[0]
                max_score = cos_scores.max().item()
                idx1 = cos_scores.argmax().item()
                if max_score < threshold:
                    html_rows.append({
                        "side": "Right 추가/변경",
                        "sentence": sents2[idx2],
                        "compare_sentence": sents1[idx1],
                        "similarity": f"{max_score:.3f}"
                    })

            if html_rows:
                diff_list.append({
                    "section_title": title,
                    "left_page": left_page,
                    "right_page": right_page,
                    "rows": html_rows
                })

        # 신설 섹션
        added_sections = set(sections2.keys()) - set(sections1.keys())
        for title in added_sections:
            diff_list.append({
                "section_title": title,
                "left_page": None,
                "right_page": sections2[title]["start_page"],
                "rows": [{"side":"신설 섹션","sentence":"-","compare_sentence":"-","similarity":"-"}]
            })

        # 삭제 섹션
        deleted_sections = set(sections1.keys()) - set(sections2.keys())
        for title in deleted_sections:
            diff_list.append({
                "section_title": title,
                "left_page": sections1[title]["start_page"],
                "right_page": None,
                "rows": [{"side":"삭제 섹션","sentence":"-","compare_sentence":"-","similarity":"-"}]
            })

        context = {
            "pdf_url1_b64": base64.urlsafe_b64encode(file1.encode()).decode(),
            "pdf_url2_b64": base64.urlsafe_b64encode(file2.encode()).decode(),
            "diff_list": diff_list
        }

        return render(request, "pages/master_rag_file_compare.html", context)

    except Exception as e:
        print("Error:", str(e))
        traceback.print_exc()
        return render(request, "pages/master_rag_file_compare.html", {"error": str(e)})