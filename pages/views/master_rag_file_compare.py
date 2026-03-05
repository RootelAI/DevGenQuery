# views.py
import os
import re
import traceback
import base64
from django.shortcuts import render
from azure.storage.blob import BlobServiceClient
from utilsPrj.supabase_client import get_supabase_client

import fitz  # PyMuPDF
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import difflib

client = OpenAI()
embeddings_model = "text-embedding-3-large"
MAX_TOKENS = 2000
SIMILARITY_THRESHOLD = 0.85

# ==============================
# OpenAI Embedding (chunk-safe)
# ==============================
def chunk_text(text, max_tokens=MAX_TOKENS):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if len(current.split()) + len(s.split()) > max_tokens:
            chunks.append(current)
            current = s
        else:
            current += " " + s
    if current.strip():
        chunks.append(current)
    return chunks

def get_embedding(text):
    chunks = chunk_text(text)
    embeddings = []
    for c in chunks:
        res = client.embeddings.create(model=embeddings_model, input=c)
        embeddings.append(res.data[0].embedding)
    return np.mean(embeddings, axis=0)

# ==============================
# PDF 텍스트 추출
# ==============================
def extract_text_from_pdf(blob_bytes):
    doc = fitz.open(stream=blob_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text

# ==============================
# 섹션 분리 (숫자 기반)
# ==============================
def split_sections(text):
    pattern = r"(\d+(\.\d+)*\s+[^\n]+)"
    parts = re.split(pattern, text)
    sections = {}
    current_title = "PREAMBLE"
    sections[current_title] = ""
    i = 0
    while i < len(parts):
        part = parts[i].strip() if parts[i] else ""
        if re.match(r"\d+(\.\d+)*\s+", part):
            current_title = part
            next_part = parts[i + 1] if (i + 1) < len(parts) and parts[i + 1] else ""
            sections[current_title] = next_part
            i += 2
        else:
            if sections.get(current_title) is None:
                sections[current_title] = ""
            sections[current_title] += part
            i += 1
    return sections

# ==============================
# 섹션 → 페이지 맵핑
# ==============================
def map_section_to_page(blob_bytes, sections):
    doc = fitz.open(stream=blob_bytes, filetype="pdf")
    section_pages = {}
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        for section_title in sections.keys():
            if section_title in text and section_title not in section_pages:
                section_pages[section_title] = i
    return section_pages

# ==============================
# 문장 단위 diff
# ==============================
def sentence_level_diff(old_text, new_text):
    old_sentences = re.split(r'(?<=[.?!])\s+', old_text.strip())
    new_sentences = re.split(r'(?<=[.?!])\s+', new_text.strip())
    diff_pairs = []

    sm = difflib.SequenceMatcher(None, old_sentences, new_sentences)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'replace' or tag == 'delete' or tag == 'insert':
            old_sents = " ".join(old_sentences[i1:i2])
            new_sents = " ".join(new_sentences[j1:j2])
            diff_pairs.append({"old": old_sents, "new": new_sents})
    return diff_pairs

# ==============================
# 섹션 비교
# ==============================
def match_sections(sections1, sections2, threshold=SIMILARITY_THRESHOLD):
    diff_list = []
    titles1 = list(sections1.keys())
    titles2 = list(sections2.keys())

    emb1 = np.array([get_embedding(t + " " + sections1[t]) for t in titles1])
    emb2 = np.array([get_embedding(t + " " + sections2[t]) for t in titles2])

    cos_scores = cosine_similarity(emb1, emb2)
    matched_2 = set()

    for i, title1 in enumerate(titles1):
        max_idx = cos_scores[i].argmax()
        max_sim = cos_scores[i][max_idx]
        title2 = titles2[max_idx]

        if max_sim >= threshold:
            if sections1[title1].strip() != sections2[title2].strip():
                sentence_diffs = sentence_level_diff(sections1[title1], sections2[title2])
                diff_list.append({
                    "section_title_old": title1,
                    "section_title_new": title2,
                    "change_type": "내용 변경",
                    "rows": sentence_diffs
                })
            matched_2.add(max_idx)
        else:
            diff_list.append({
                "section_title_old": title1,
                "section_title_new": "-",
                "change_type": "삭제",
                "rows": []
            })

    for j, title2 in enumerate(titles2):
        if j not in matched_2:
            diff_list.append({
                "section_title_old": "-",
                "section_title_new": title2,
                "change_type": "신규",
                "rows": []
            })

    return diff_list

# ==============================
# PDF 비교 View
# ==============================
def master_rag_file_compare(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    user = request.session.get("user")

    if not user:
        return render(request, "pages/home.html", {"code": "login", "text": "로그인이 필요합니다."})

    try:
        project_id = 1
        supabase = get_supabase_client(access_token, refresh_token)
        dirPath = supabase.schema('rag').table('projects') \
            .select('dirpath').eq('projectid', project_id) \
            .execute().data[0]['dirpath']

        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        container_client = blob_service_client.get_container_client(dirPath)

        # PDF Blob 다운로드
        blob1 = container_client.download_blob("source/문서_01.pdf").readall()
        blob2 = container_client.download_blob("source/문서_02.pdf").readall()

        # Base64 변환
        url_left = "data:application/pdf;base64," + base64.b64encode(blob1).decode()
        url_right = "data:application/pdf;base64," + base64.b64encode(blob2).decode()

        # 텍스트 추출 및 섹션 분리
        text1 = extract_text_from_pdf(blob1)
        text2 = extract_text_from_pdf(blob2)
        sections1 = split_sections(text1)
        sections2 = split_sections(text2)

        # 섹션 → 페이지 번호 매핑
        section_pages1 = map_section_to_page(blob1, sections1)

        # 섹션 비교
        diff_list = match_sections(sections1, sections2)

        # 페이지 번호 diff_list에 추가
        for diff in diff_list:
            diff['page_number'] = section_pages1.get(diff['section_title_old'], 1)

        return render(request, "pages/master_rag_file_compare.html", {
            "diff_list": diff_list,
            "url_left": url_left,
            "url_right": url_right
        })

    except Exception as e:
        traceback.print_exc()
        return render(request, "pages/master_rag_file_compare.html", {"error": str(e)})