import os
import base64
import tempfile
import urllib.parse
import traceback
import re

from django.shortcuts import render
from django.http import HttpResponse
from azure.storage.blob import BlobServiceClient
import fitz
from sentence_transformers import SentenceTransformer, util
from utilsPrj.supabase_client import get_supabase_client

# 서버 시작 시 1회만 모델 로딩
model = SentenceTransformer('all-MiniLM-L6-v2')

# ==============================
# 1️⃣ 섹션 추출
# ==============================
def extract_sections_from_pdf(blob_path):
    doc = fitz.open(blob_path)

    section_pattern = re.compile(
        r'^\s*(제\s*\d+\s*[장조항절]\s*.*|\d+(\.\d+)*\s+.*)'
    )

    sections = {}
    current_title = "PREAMBLE"
    current_number = "0"
    sections[current_title] = {"text": "", "start_page": 1, "number": current_number}

    for page_number, page in enumerate(doc):
        text = page.get_text()
        if not text.strip():
            continue

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            match = section_pattern.match(line)
            if match:
                number_match = re.match(r'제?\s*(\d+)', line)
                current_number = number_match.group(1) if number_match else "0"
                current_title = line
                sections[current_title] = {
                    "text": "",
                    "start_page": page_number + 1,
                    "number": current_number
                }
            else:
                sections[current_title]["text"] += line + "\n"

    return sections

# ==============================
# 2️⃣ 문장 분리
# ==============================
def split_into_sentences(text):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# ==============================
# 3️⃣ PDF Proxy
# ==============================
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
        traceback.print_exc()
        return HttpResponse(f"Error fetching PDF: {str(e)}", status=500)

# ==============================
# 4️⃣ 3단계 비교: 번호 + 제목 + 본문 + 문장
# ==============================
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

        diff_list = []

        # 섹션 번호 기준 매칭
        numbers1 = {v["number"]: k for k, v in sections1.items()}
        numbers2 = {v["number"]: k for k, v in sections2.items()}

        for num, title1 in numbers1.items():
            rows = []
            if num in numbers2:
                title2 = numbers2[num]

                # 제목 embedding 비교
                emb_title1 = model.encode(title1, convert_to_tensor=True)
                emb_title2 = model.encode(title2, convert_to_tensor=True)
                title_sim = util.cos_sim(emb_title1, emb_title2).item()

                # 본문 문장 단위 비교
                left_sentences = split_into_sentences(sections1[title1]["text"])
                right_sentences = split_into_sentences(sections2[title2]["text"])

                if left_sentences and right_sentences:
                    emb_left = model.encode(left_sentences, convert_to_tensor=True)
                    emb_right = model.encode(right_sentences, convert_to_tensor=True)
                    cos_scores = util.cos_sim(emb_left, emb_right)

                    # 각 문장별 최대 유사도 비교
                    for i, sent in enumerate(left_sentences):
                        max_idx = cos_scores[i].argmax().item()
                        max_sim = cos_scores[i, max_idx].item()
                        if max_sim < 0.85:
                            rows.append({
                                "side": "과거",
                                "sentence": sent,
                                "compare_sentence": right_sentences[max_idx],
                                "similarity": f"{max_sim:.3f}"
                            })
                    for j, sent in enumerate(right_sentences):
                        if cos_scores[:, j].max().item() < 0.85:
                            rows.append({
                                "side": "현재",
                                "sentence": sent,
                                "compare_sentence": "",
                                "similarity": "-"
                            })
                    low_sim_mean = cos_scores.min(dim=1).values.mean().item()
                else:
                    low_sim_mean = 1.0

                # 변경 여부 판단
                if title_sim < 0.85 or low_sim_mean < 0.75:
                    diff_list.append({
                        "section_title_old": title1,
                        "section_title_new": title2,
                        "left_page": sections1[title1]["start_page"],
                        "right_page": sections2[title2]["start_page"],
                        "similarity": f"{low_sim_mean:.3f}",
                        "change_type": "내용 변경",
                        "rows": rows
                    })
            else:
                # 번호 없음 → 신규 섹션
                diff_list.append({
                    "section_title_old": "-",
                    "section_title_new": title1,
                    "left_page": "-",
                    "right_page": sections1[title1]["start_page"],
                    "similarity": "-",
                    "change_type": "신규 섹션",
                    "rows": []
                })

        # 번호로 못 찾은 섹션 (신규)
        for num, title2 in numbers2.items():
            if num not in numbers1:
                diff_list.append({
                    "section_title_old": "-",
                    "section_title_new": title2,
                    "left_page": "-",
                    "right_page": sections2[title2]["start_page"],
                    "similarity": "-",
                    "change_type": "신규 섹션",
                    "rows": []
                })

        # 페이지 순으로 정렬
        diff_list = sorted(
            diff_list,
            key=lambda x: (x["left_page"] if isinstance(x["left_page"], int) else 9999,
                           x["right_page"] if isinstance(x["right_page"], int) else 9999)
        )

        return render(request, "pages/master_rag_file_compare.html", {
            "diff_list": diff_list,
            "pdf_url1_b64": base64.urlsafe_b64encode(file1.encode()).decode(),
            "pdf_url2_b64": base64.urlsafe_b64encode(file2.encode()).decode(),
        })

    except Exception as e:
        traceback.print_exc()
        return render(request, "pages/master_rag_file_compare.html", {
            "error": str(e)
        })