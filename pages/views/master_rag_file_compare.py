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

from utilsPrj.supabase_client import get_supabase_client
from sentence_transformers import SentenceTransformer, util


# 모델은 서버 시작 시 1회만 로딩
model = SentenceTransformer('all-MiniLM-L6-v2')


def extract_pdf_text(blob_path):
    """
    빈 페이지 제거
    하지만 PDF 실제 페이지 번호(original_page)는 유지
    """
    doc = fitz.open(blob_path)
    pages_text = []

    for page_number, page in enumerate(doc):
        text = page.get_text()

        if text.strip():  # 빈 페이지 제거
            pages_text.append({
                "original_page": page_number + 1,  # 실제 PDF 페이지 번호
                "text": text
            })

    return pages_text


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
        response['Content-Disposition'] = f'inline; filename="{blob_path.split("/")[-1]}"'

        return response

    except Exception as e:
        print("Exception in proxy_pdf:", e)
        traceback.print_exc()
        return HttpResponse(f"Error fetching PDF: {str(e)}", status=500)


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

        # 🔥 빈 페이지 제거된 비교용 리스트
        pages_text1 = extract_pdf_text(tmp_path1)
        pages_text2 = extract_pdf_text(tmp_path2)

        diff_list = []
        threshold = 0.85

        max_page = min(len(pages_text1), len(pages_text2))

        for i in range(max_page):

            page1 = pages_text1[i]
            page2 = pages_text2[i]

            sents1 = [
                s.strip()
                for s in re.split(r'(?<=[.!?])\s+', page1['text'].replace("\n", " "))
                if s.strip()
            ]

            sents2 = [
                s.strip()
                for s in re.split(r'(?<=[.!?])\s+', page2['text'].replace("\n", " "))
                if s.strip()
            ]

            if not sents1 and not sents2:
                continue

            embeddings1 = model.encode(sents1, convert_to_tensor=True)
            embeddings2 = model.encode(sents2, convert_to_tensor=True)

            diff_entries = []

            # 과거 → 현재
            for idx1, emb1 in enumerate(embeddings1):
                cos_scores = util.cos_sim(emb1, embeddings2)[0]
                if cos_scores.max() < threshold:
                    diff_entries.append(f"{sents1[idx1]} ==> (삭제/변경)")

            # 현재 → 과거
            for idx2, emb2 in enumerate(embeddings2):
                cos_scores = util.cos_sim(emb2, embeddings1)[0]
                if cos_scores.max() < threshold:
                    diff_entries.append(f"(추가/변경) ==> {sents2[idx2]}")

            if diff_entries:
                diff_list.append({
                    "left_page": page1["original_page"],
                    "right_page": page2["original_page"],
                    "summary_list": diff_entries
                })

        def to_b64(s):
            return base64.urlsafe_b64encode(s.encode('utf-8')).decode()

        context = {
            "pdf_url1_b64": to_b64(file1),
            "pdf_url2_b64": to_b64(file2),
            "diff_list": diff_list
        }

        return render(request, "pages/master_rag_file_compare.html", context)

    except Exception as e:
        print("Error:", str(e))
        traceback.print_exc()

        return render(request, "pages/master_rag_file_compare.html", {
            "error": str(e)
        })