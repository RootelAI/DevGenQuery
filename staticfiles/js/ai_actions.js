// 공통 실행 스크립트 - 20250917

// 20251219 1535
// textarea 커서 위치를 추적하는 변수
let lastCursorPosition = 0;

// textarea 커서 위치를 저장하는 함수
function trackCursor() {
    const textarea = document.getElementById("prompt");
    if (textarea) {
        lastCursorPosition = textarea.selectionStart;
    }
}

// textarea에 텍스트를 삽입하는 함수
function insertTextAtCursor(text) {
    const textarea = document.getElementById("prompt");
    if (!textarea) return;
    
    const start = lastCursorPosition;
    const end = lastCursorPosition;
    const currentValue = textarea.value;
    
    // 텍스트 삽입
    textarea.value = currentValue.substring(0, start) + text + currentValue.substring(end);
    
    // 커서를 삽입된 텍스트 뒤로 이동
    const newPosition = start + text.length;
    textarea.setSelectionRange(newPosition, newPosition);
    textarea.focus();
    
    // 커서 위치 업데이트
    lastCursorPosition = newPosition;
}

// 페이지 로드 시 textarea에 이벤트 리스너 추가
document.addEventListener("DOMContentLoaded", function() {
    const textarea = document.getElementById("prompt");
    if (textarea) {
        textarea.addEventListener("click", trackCursor);
        textarea.addEventListener("keyup", trackCursor);
        textarea.addEventListener("focus", trackCursor);
    }
});
/////


function renderPreviewTable(table_header_json, table_data_json, data) {
    const box = document.getElementById("output-box");
    box.innerHTML = "";

    const table = document.createElement("table");
    table.style.borderCollapse = "collapse";
    table.style.width = "100%";

    const columns = Object.keys(data[0]); // 데이터의 컬럼명 기준

    // === 헤더 생성 ===
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    columns.forEach(col => {
        const th = document.createElement("th");
        th.textContent = col;

        const headerConf = table_header_json[col] || {};
        th.style.fontSize = (headerConf.fontsize || 14) + "px";
        th.style.fontWeight = headerConf.fontweight || "normal";
        th.style.textAlign = headerConf.align || "center";
        th.style.backgroundColor = headerConf.bgcolor || "#f0f0f0";
        th.style.color = headerConf.color || "#000000";
        th.style.padding = "4px 8px";

        trHead.appendChild(th);
    });

    thead.appendChild(trHead);
    table.appendChild(thead);

    // === 데이터 행 ===
    const tbody = document.createElement("tbody");
    data.forEach(row => {
        const tr = document.createElement("tr");
        columns.forEach(col => {
            const td = document.createElement("td");
            td.textContent = row[col];

            const conf = table_data_json[col] || {};
            td.style.fontSize = (conf.fontsize || 14) + "px";
            td.style.fontWeight = conf.fontweight || "normal";
            td.style.textAlign = conf.align || "center";
            td.style.color = conf.color || "#000000";
            td.style.backgroundColor = conf.bgcolor || "#ffffff";
            td.style.padding = "2px 6px";

            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    box.appendChild(table);
}


// 열이름을 가져오는 함수
function loadColumnList() {
    const docid = document.querySelector("[name=docid]")?.value;
    const chapteruid = document.querySelector("[name=chapteruid]")?.value;
    const objectnm = document.querySelector("[name=objectnm]")?.value;
    const datauid = document.querySelector("[name=datauid]")?.value;
    
    // 필수 값들이 모두 선택되었는지 확인
    if (!docid || !chapteruid || !objectnm || !datauid) {
        document.getElementById("column-list-output").innerHTML = '<strong>열이름  </strong>';
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) {
        document.getElementById("column-list-output").innerHTML = '<strong>열이름  </strong>CSRF 토큰 없음';
        return;
    }
    
    const params = new URLSearchParams({
        "docid": docid,
        "chapteruid": chapteruid,
        "objectnm": objectnm,
        "datauid": datauid,
    });

    // 로딩 표시
    document.getElementById("column-list-output").innerHTML = '<strong>열이름  </strong>로딩 중...';

    fetch("/master/ai_get_columns/", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken
        },
        body: params.toString(),
        credentials: "include"
    })
    .then(res => {
        return res.text().then(text => {
            console.log("서버 응답:", text);
            try {
                return JSON.parse(text);
            } catch (e) {
                throw new Error("JSON 파싱 실패. 서버 응답: " + text.substring(0, 200));
            }
        });
    })
    .then(data => {
        if (data.success) {
            const outputDiv = document.getElementById("column-list-output");
            outputDiv.innerHTML = '<strong>열이름  </strong>';
            
            data.columns.forEach((col, index) => {
                const colSpan = document.createElement("span");
                colSpan.textContent = col;
                colSpan.style.cursor = "pointer";
                colSpan.style.padding = "4px 4px";
                colSpan.style.marginRight = "4px";
                colSpan.style.backgroundColor = "#e9ecef";
                colSpan.style.borderRadius = "4px";
                colSpan.style.display = "inline-block";
                colSpan.style.marginBottom = "4px";
                colSpan.style.backgroundColor = "transparent";
                
                if (index === 0) {
                    colSpan.style.marginLeft = "20px";
                }
                
                // 호버 효과 (배경 대신 밑줄이나 색상 변경)
                colSpan.addEventListener("mouseenter", function() {
                    this.style.textDecoration = "underline";
                    this.style.textDecorationColor = "silver";  // 밑줄 색상
                    this.style.color = "black";  // 글자 색상 (진하게)
                    this.style.fontWeight = "bold"
                });
                colSpan.addEventListener("mouseleave", function() {
                    this.style.textDecoration = "none";
                    this.style.color = "inherit";
                    this.style.fontWeight = "normal";
                });
                
                // 클릭 시 textarea에 삽입
                colSpan.addEventListener("click", function() {
                    insertTextAtCursor(col);
                });
                
                outputDiv.appendChild(colSpan);
            });
        }
    })
    .catch(err => {
        document.getElementById("column-list-output").innerHTML = '<strong>열이름  </strong>에러 - ' + err.message;
        console.error("전체 오류:", err);
    });
}


// 20251216 추가 시작
function showPromptLoading() {
    const overlay = document.getElementById('preview_prompt');
    const previewBtn = document.getElementById('btn-prompt-form');
    const text = document.getElementById('run_prompt');
    
    // 오버레이 표시
    overlay.style.display = 'flex';
    
    // 메시지 설정
    // text.textContent = 'AI가 작성 중입니다...';
    
    // 버튼 로딩 상태로 변경
    if (previewBtn) {
        previewBtn.classList.add('btn-loading');
        previewBtn.disabled = true;
    }
}


function hidePromptLoading() {
    const overlay = document.getElementById('preview_prompt');
    const previewBtn = document.getElementById('btn-prompt-form');
    const text = document.getElementById('run_prompt');
    
    // 오버레이 숨기기
    overlay.style.display = 'none';
    
    // 메시지 초기화
    text.textContent = '';
    
    // 버튼 원래 상태로 복원
    if (previewBtn) {
        previewBtn.classList.remove('btn-loading');
        previewBtn.disabled = false;
    }
}
// 20251216 추가 끝


function initChatActions(config) {
    const { pageType, csrfToken, urls, context } = config;


    const promptSelect = document.getElementById("promptnm");

    if (promptSelect) {
        promptSelect.addEventListener("change", function() {
            // console.log("변경:", this.value);
            const url = new URL(window.location.href);
            if (this.value) {
                url.searchParams.set('promptnm', this.value);
            } 
            else {
                url.searchParams.delete('promptnm');
            }
            // console.log("URL:", url.toString());
            window.location.href = url.toString();
        });
    }

    // 데이터 목록 선택 시 열이름 버튼 표시/숨김 처리
    const datauidSelect = document.getElementById("datauid");
    const columnBtn = document.getElementById("btn-column-list");
    
    if (datauidSelect && columnBtn) {
        // 페이지 로드 시 초기 상태 설정
        if (datauidSelect.value) {
            columnBtn.style.display = "inline-block";
        } 
        else {
            columnBtn.style.display = "none";
        }

        // 데이터 목록 변경 시 버튼 표시/숨김
        datauidSelect.addEventListener("change", function() {
            if (this.value) {
                columnBtn.style.display = "inline-block";
            } 
            else {
                columnBtn.style.display = "none";
                // 열이름 출력도 초기화
                document.getElementById("column-list-output").textContent = "";
            }
        });
    }

    loadColumnList();
    
    // 기존 버튼 클릭 이벤트 (수동 새로고침용)
    if (columnBtn) {
        columnBtn.addEventListener("click", loadColumnList);
    }

    // === Preview 버튼 ===
    const previewBtn = document.getElementById("btn-prompt-form");
    if (previewBtn) {
        previewBtn.addEventListener("click", function (e) {
            e.preventDefault();

            const prompt = document.getElementById("prompt").value.trim();
            const outputArea = document.getElementById("output-box");

            showPromptLoading();    // 20251216 추가

            fetch(urls.preview, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrfToken
                },
                body: new URLSearchParams({
                    "prompt": prompt,
                    "docid": document.querySelector("[name=docid]").value,
                    "chapteruid": document.querySelector("[name=chapteruid]").value,
                    "objectnm": document.querySelector("[name=objectnm]").value,
                    "datauid": document.querySelector("[name=datauid]").value,
                    // "projectid": document.querySelector("[name=projectid]").value
                }),
                credentials: "include"
            })
            .then(res => res.json())
            .then(data => {
                hidePromptLoading();    // 20251216 추가
                outputArea.innerHTML = "";
                if (data.message_type === "image") {
                    const img = document.createElement("img");
                    img.src = "data:image/png;base64," + data.image_data.trim();
                    img.style.maxWidth = "100%";
                    outputArea.appendChild(img);
                } 
                else if (data.message_type === "text") {
                    // outputArea.innerHTML = data.message;
                    outputArea.innerText = data.message;
                } 
                else if (data.message_type === "table") {
                    const header_json = (typeof data.table_header_json === "string")
                        ? JSON.parse(data.table_header_json)
                        : data.table_header_json;

                    const data_json = (typeof data.table_data_json === "string")
                        ? JSON.parse(data.table_data_json)
                        : data.table_data_json;

                    renderPreviewTable(
                        header_json,
                        data_json,
                        data.data
                    )
                } 
                else if (data.message_type === "error") {
                    outputArea.innerHTML = `<div style="color:red;">오류: ${data.message}</div>`;
                } 
                else {
                    outputArea.innerHTML = `<div>결과가 없습니다.</div>`;
                }
            })
            .catch(err => {
                hidePromptLoading();    // 20251216 추가
                outputArea.innerHTML = `<div style="color:red;">에러: ${err.message}</div>`;
            });
        });
    }


    // === Reset 버튼 ===
    const resetBtn = document.getElementById("btn-reset");
    if (resetBtn) {
        resetBtn.addEventListener("click", function() {
            document.getElementById("prompt").value = "";
            document.getElementById("output-box").innerHTML = "";
        });
    }

    const saveBtn = document.getElementById("btn-save");
    if (saveBtn) {
        saveBtn.addEventListener("click", function() {
            // displaytype을 DOM에서 직접 가져오기
            let displaytype = "";
            
            // 차트 유형이 있는 경우 (CA 페이지)
            const chartTypeSelect = document.getElementById("chart_type");
            if (chartTypeSelect && chartTypeSelect.value) {
                displaytype = chartTypeSelect.value;
            }
            
            // 문장 유형이 있는 경우 (SA 페이지)
            const sentenceTypeSelect = document.getElementById("sentence_type");
            if (sentenceTypeSelect && sentenceTypeSelect.value) {
                displaytype = sentenceTypeSelect.value;
            }
            
            const payload = {
                chapteruid: document.querySelector("[name=chapteruid]").value,
                objectnm: document.querySelector("[name=objectnm]").value,
                datauid: document.querySelector("[name=datauid]").value,
                displaytype: displaytype,
                gptq: document.getElementById("prompt").value
            };
            
            fetch(urls.save, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify(payload),
                credentials: "include"
            })
            .then(res => {
                return res.text().then(text => {
                    console.log("서버 응답:", text);
                    try {
                        return JSON.parse(text);
                    } catch (e) {
                        throw new Error("JSON 파싱 실패: " + text.substring(0, 200));
                    }
                });
            })
            .then(data => {
                if (data.success) {
                    alert("저장되었습니다.");
                } else {
                    alert("저장 실패: " + (data.error || "알 수 없는 오류"));
                }
            })
            .catch(err => {
                alert("저장 요청 중 오류가 발생했습니다: " + err.message);
                console.error("전체 오류:", err);
            });
        });
    }    

    // === Delete 버튼 ===
    const deleteBtn = document.getElementById("btn-delete");
    if (deleteBtn) {
        deleteBtn.addEventListener("click", function() {
            if (!confirm("정말 삭제하시겠습니까?")) {
                return;
            }

            const payload = {
                objectuid: context.selected_objectuid,
                chapteruid: context.selected_chapteruid,
                objectnm: context.selected_objectnm,
                datauid: context.selected_datauid,
                gentypecd: context.object_type
            };

            fetch(urls.delete, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify(payload),
                credentials: "include"
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert("삭제되었습니다.");
                    window.location.reload();
                } else {
                    alert("삭제 실패: " + (data.error || "알 수 없는 오류"));
                }
            })
            .catch(err => {
                alert("삭제 요청 중 오류가 발생했습니다.");
                console.error(err);
            });
        });
    }

    // === Prompt Sample Save 버튼 ===
    const savePromptBtn = document.getElementById("btn-prompt-sample-save");
    if (savePromptBtn) {
        savePromptBtn.addEventListener("click", function() {
            console.log("버튼 클릭됨");
            
            // 팝업창으로 프롬프트 이름 입력받기
            // const promptName = prompt("샘플 프롬프트 이름을 입력하세요:");

            const samplePromptName = window.prompt("샘플 프롬프트 이름을 입력하세요.")
            
            // 사용자가 취소를 클릭한 경우 (null 반환)
            if (samplePromptName === null) {
                return;
            }
            
            // 입력된 이름을 trim하여 공백 제거
            const trimmedPromptName = samplePromptName.trim();
            console.log("프롬프트 이름:", trimmedPromptName);
            
            // 1. 프롬프트 이름 검증
            if (!trimmedPromptName) {
                alert("프롬프트 이름을 입력해주세요.");
                // 다시 입력받기 위해 재귀 호출 (선택사항)
                // savePromptBtn.click();
                return;
            }
            
            let displaytype = "";

            const objectTypeSelect = document.getElementById("object_type");
            const currentObjectType = objectTypeSelect ? objectTypeSelect.value : context.object_type;

            if (currentObjectType === "CA") {
                const chartElement = document.getElementById("chart_type");
                if (chartElement) {
                    displaytype = chartElement.value;
                }
            } 
            else if (currentObjectType === "SA") {
                const sentenceElement = document.getElementById("sentence_type");
                if (sentenceElement) {
                    displaytype = sentenceElement.value;
                }
            }
            else if (currentObjectType === "TA") {
                const tableElement = document.getElementById("table_type");
                if (tableElement) {
                    displaytype = tableElement.value;
                }
            }

            const payload = {
                objectuid: context.selected_objectuid,
                chapteruid: context.selected_chapteruid,
                objectnm: context.selected_objectnm,
                datauid: context.selected_datauid,
                promptuid: context.selected_prompt_uid,
                objecttypecd: context.object_type,
                displaytype: displaytype,
                prompt: document.getElementById("prompt").value,
                promptnm: trimmedPromptName,  // 팝업에서 입력받은 이름 사용
                promptdesc: document.getElementById("prompt-desc").value,
                force_update: false  // 초기값
            };

            sendSaveRequest(payload);
        });
    }
}


function sendSaveRequest(payload) {
    fetch(urls.prompt_save, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload),
        credentials: "include"
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("저장되었습니다.");
        } 
        else if (data.error === "name_required") {
            alert(data.message);
            document.getElementById("prompt-name").focus();
        } 
        else if (data.error === "duplicate_name") {
            if (confirm(data.message)) {
                payload.force_update = true;
                sendSaveRequest(payload);  // 재귀 호출
            } 
            else {
                alert("프롬프트 이름을 다시 입력해주세요.");
                document.getElementById("prompt-name").focus();
                document.getElementById("prompt-name").select(); // 기존 텍스트 선택
            }
        } 
        else {
            alert("저장 실패: " + (data.error || "알 수 없는 오류"));
        }
    })
    .catch(err => {
        alert("저장 요청 중 오류가 발생했습니다.");
        console.error(err);
    });
}

function setQueryParam(key, value) {
    const url = new URL(window.location.href);
    if (value === "" || value == null) {
        url.searchParams.delete(key);
    } 
    else {
        url.searchParams.set(key, value);
    }
    // 리로드 없이 주소만 갱신
    window.history.replaceState({}, "", url.toString());
}

(function bindTypeSelectors(){
const chartSel = document.getElementById("chart_type");
if (chartSel) {
    chartSel.addEventListener("change", (e) => {
    setQueryParam("chart_type", e.target.value);
    // 차트 유형 선택 시 요구사항: 열이름 다시 작성
    loadColumnList();
    });
}
const sentSel = document.getElementById("sentence_type");
if (sentSel) {
    sentSel.addEventListener("change", (e) => {
    setQueryParam("sentence_type", e.target.value);
    // 문장 유형 선택 시에도 동일 동작(요구 동일하게 처리)
    loadColumnList();
    });
}
})();


// === 샘플 프롬프트 모달 열기 ===
const modal = document.getElementById("samplePromptModal");
const openBtn = document.getElementById("btn-sample-prompt");
const closeBtn = document.getElementById("btn-modal-close");
// const cancelBtn = document.getElementById("btn-cancel-modal");
const applyBtn = document.getElementById("btn-apply-prompt");

const sampleList = document.getElementById("sampleList");
const modalPromptDesc = document.getElementById("modal-prompt-desc");
const modalPromptContent = document.getElementById("modal-prompt-content");

let selectedPromptData = null;

const samplePromptModalBtn = document.getElementById("btn-sample-prompt-wrapper");
if (samplePromptModalBtn) {
    samplePromptModalBtn.addEventListener("click", function() {
        document.getElementById("prompt").value = "";
        document.getElementById("output-box").innerHTML = "";
    });
}

// 모달 열기
if (openBtn && modal && closeBtn) {
    openBtn.addEventListener("click", function() {
        modal.style.display = "flex";
        // 초기화
        modalPromptDesc.value = "";
        modalPromptContent.value = "";
        selectedPromptData = null;
    });

    // 닫기 버튼
    closeBtn.addEventListener("click", function() {
        modal.style.display = "none";
    });

    // 배경 클릭 시 닫기
    modal.addEventListener("click", function(e) {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });

    // 샘플 목록 클릭 이벤트
    if (sampleList) {
        sampleList.addEventListener("click", function(e) {
            const li = e.target.closest("li");
            if (!li) return;

            // 기존 선택 해제
            sampleList.querySelectorAll("li").forEach(item => {
                item.style.backgroundColor = "";
                item.style.fontWeight = "";
            });

            // 현재 항목 선택 표시
            li.style.backgroundColor = "#e3f2fd";
            li.style.fontWeight = "bold";

            // 데이터 가져오기 - data-prompttext로 변경
            const promptDesc = li.getAttribute("data-promptdesc") || "";
            const promptText = li.getAttribute("data-prompttext") || "";

            console.log("=== 데이터 확인 ===");
            console.log("설명 길이:", promptDesc.length);
            console.log("프롬프트 길이:", promptText.length);
            console.log("프롬프트 내용:", promptText);

            selectedPromptData = {
                promptuid: li.getAttribute("data-promptuid"),
                promptnm: li.getAttribute("data-promptnm"),
                promptdesc: promptDesc,
                prompt: promptText
            };

            // 텍스트 영역에 표시
            modalPromptDesc.value = promptDesc;
            modalPromptContent.value = promptText;
        });
    }

    // 적용하기 버튼
    if (applyBtn) {
        applyBtn.addEventListener("click", function() {
            if (!selectedPromptData) {
                alert("샘플 프롬프트를 선택해주세요.");
                return;
            }

            if (!confirm("작성중인 프롬프트가 샘플 프롬프트로 대체됩니다. 실행할까요?")){
                return;
            }

            // 메인 페이지의 프롬프트 입력창에 적용
            const mainPrompt = document.getElementById("prompt");
            if (mainPrompt) {
                mainPrompt.value = selectedPromptData.prompt;
            }

            modal.style.display = "none";
        });
    }
}




// ==================== 컬러맵 관련 함수 ====================

/**
 * 컬러맵 샘플을 초기화하고 표시하는 함수
 */
function initializeColormap() {
    const container = document.getElementById("colormap-container");
    if (!container) {
        console.log("colormap-container를 찾을 수 없습니다.");
        return;
    }

    // 연속형 / perceptual / diverging / 계절
    const continuousColormaps = {
        viridis:  ["#440154","#3b528b","#21918c","#5ec962","#fde725"],
        plasma:   ["#0d0887","#7e03a8","#cb4679","#ed7953","#f0f921"],
        inferno:  ["#000004","#420a68","#932667","#dd513a","#fca50a","#fcffa4"],
        magma:    ["#000004","#3b0f70","#8f3b6b","#de7c2f","#fbfdbf"],
        cividis:  ["#00204d","#445c7a","#7ea5a7","#d6d6d6","#ffffe0"],
        turbo:    ["#30123b","#4145ab","#4687f0","#42b6c4","#7fdf58","#f9f71d","#f48c1b","#d7191c"],
        cool:     ["#00ffff","#ff00ff"],
        hot:      ["#000000","#ff0000","#ffff00","#ffffff"],
        coolwarm: ["#3b4cc0","#ffffff","#b40426"],
        rainbow:  ["red","orange","yellow","green","cyan","blue","purple"],
        terrain:  ["#333399","#66ccff","#00cc66","#ccff66","#cc9933"],
        ocean:    ["#0000cc","#0066cc","#00cccc","#00ff66","#99ff33"],
        cubehelix:["#000000","#3c1f54","#5b4693","#4d88b5","#69d2a7","#c2ff99"],
        flag:     ["red","white","blue","white","red"],
        spring:   ["#ffb7c5","#ffe6ea","#e6ffea","#b7ffd6"],
        summer:   ["#005f73","#0a9396","#94d2bd","#e9d8a6"],
        autumn:   ["#7f2f00","#cc5803","#e2711d","#ffb627"],
        winter:   ["#003049","#669bbc","#c9d4e3","#fdfcfa"]
    };

    // 범주형 / tab / Set / Pastel
    const categoricalColormaps = {
        tab10:   ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"],
        tab20:   ["#1f77b4","#aec7e8","#ff7f0e","#ffbb78","#2ca02c","#98df8a","#d62728","#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2","#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"],
        tab20b:  ["#393b79","#5254a3","#6b6ecf","#9c9ede","#637939","#8ca252","#b5cf6b","#cedb9c","#8c6d31","#bd9e39","#e7ba52","#e7cb94","#843c39","#ad494a","#d6616b","#e7969c","#7b4173","#a55194","#ce6dbd","#de9ed6"],
        Set1:    ["#e41a1c","#377eb8","#4daf4a","#984ea3","#ff7f00","#ffff33","#a65628","#f781bf","#999999"],
        Set2:    ["#66c2a5","#fc8d62","#8da0cb","#e78ac3","#a6d854","#ffd92f","#e5c494","#b3b3b3"],
        Set3:    ["#8dd3c7","#ffffb3","#bebada","#fb8072","#80b1d3","#fdb462","#b3de69","#fccde5","#d9d9d9","#bc80bd","#ccebc5","#ffed6f"],
        Pastel1: ["#fbb4ae","#b3cde3","#ccebc5","#decbe4","#fed9a6","#ffffcc","#e5d8bd","#fddaec","#f2f2f2"],
        Pastel2: ["#b3e2cd","#fdcdac","#cbd5e8","#f4cae4","#e6f5c9","#fff2ae","#f1e2cc","#cccccc"]
    };

    // 기존 내용 초기화
    container.innerHTML = "";

    // 연속형: gradient
    Object.entries(continuousColormaps).forEach(([name, colors]) => {
        const item = document.createElement("div");
        item.className = "cmap-item";

        const label = document.createElement("div");
        label.className = "cmap-name";
        label.innerText = name;

        const box = document.createElement("div");
        box.className = "cmap-box";
        box.style.background = `linear-gradient(to right, ${colors.join(",")})`;

        item.style.cursor = "pointer";
        item.addEventListener("click", function() {
            insertTextAtCursor(name);
        });

        item.appendChild(label);
        item.appendChild(box);
        container.appendChild(item);
    });

    // 범주형: 개별 블록
    Object.entries(categoricalColormaps).forEach(([name, colors]) => {
        const item = document.createElement("div");
        item.className = "cmap-item";

        const label = document.createElement("div");
        label.className = "cmap-name";
        label.innerText = name;

        const box = document.createElement("div");
        box.className = "cmap-box";
        box.style.display = "flex";
        box.style.gap = "3px";

        item.style.cursor = "pointer";
        item.addEventListener("click", function() {
            insertTextAtCursor(name);
        });

        colors.forEach(c => {
            const colorBlock = document.createElement("div");
            colorBlock.style.width = "28px";
            colorBlock.style.height = "24px";
            colorBlock.style.background = c;
            colorBlock.style.border = "1px solid #ccc";
            colorBlock.style.borderRadius = "4px";
            box.appendChild(colorBlock);
        });

        item.appendChild(label);
        item.appendChild(box);
        container.appendChild(item);
    });
    
    console.log("컬러맵 초기화 완료");
}

// /**
//  * 컬러맵 표시 상태를 업데이트하는 함수
//  */
function updateColormapVisibility() {
    const objectTypeSelect = document.getElementById("object_type");
    const colormapBtn = document.getElementById("toggle-colormap");
    const colorButtonArea = document.getElementById("color-button-area");
    
    const value = objectTypeSelect.value;

    if (value === "CA") {
        if (colorButtonArea) colorButtonArea.style.display = "flex";
        if (colormapBtn) colormapBtn.style.display = "inline-block";
    } 
    else if (value === "TA") {
        if (colorButtonArea) colorButtonArea.style.display = "flex";
        if (colormapBtn) colormapBtn.style.display = "none";  // 컬러맵 버튼만 숨김
    } 
    else if (value === "SA") {
        if (colorButtonArea) colorButtonArea.style.display = "none";
    }
}




/**
 * 컬러맵 토글 버튼 이벤트 설정
 */
function setupColormapToggle() {
    const toggleBtn = document.getElementById("toggle-colormap");
    const wrapper = document.getElementById("colormap-wrapper");
    
    if (!toggleBtn || !wrapper) {
        console.log("토글 버튼 또는 wrapper를 찾을 수 없습니다.");
        return;
    }

    toggleBtn.addEventListener("click", () => {
        const isHidden = wrapper.style.display === "none" || wrapper.style.display === "";
        wrapper.style.display = isHidden ? "block" : "none";
        toggleBtn.textContent = isHidden ? "컬러맵 숨기기" : "컬러맵 보기";
        // toggleBtn.textContent = isHidden ? "컬러맵 샘플 숨기기" : "컬러맵 샘플 보기";
        toggleBtn.setAttribute("aria-expanded", isHidden ? "true" : "false");
        console.log("컬러맵 토글:", isHidden ? "열림" : "닫힘");
    });
    
    console.log("토글 버튼 이벤트 등록 완료");
}

// /**
//  * 컬러맵 관련 모든 기능을 초기화하는 메인 함수
//  */

function initColormapFeature() {
    console.log("=== 컬러맵 초기화 시작 ===");
    
    // 컬러맵 샘플 생성
    initializeColormap();
    
    // ✅ CSS 색상 생성 추가
    initializeCSSColors();
    
    // 토글 버튼 설정
    setupColormapToggle();
    
    // ✅ CSS 색상 토글 버튼 설정 추가
    setupCSSColorsToggle();
    
    // 초기 표시 상태 업데이트
    updateColormapVisibility();
    
    // object_type 변경 이벤트 리스너
    const objectTypeSelect = document.getElementById("object_type");
    if (objectTypeSelect) {
        objectTypeSelect.addEventListener("change", updateColormapVisibility);
        console.log("object_type 변경 이벤트 등록 완료");
    }
    
    console.log("=== 컬러맵 초기화 완료 ===");
}


/**
 * CSS 기본 색상을 초기화하고 표시하는 함수
 */
function initializeCSSColors() {
    const container = document.getElementById("css-colors-container");
    if (!container) {
        console.log("css-colors-container를 찾을 수 없습니다.");
        return;
    }

    // CSS 기본 색상 (Named Colors)
    const cssColors = {
        // 빨강 계열
        red: "#FF0000", darkred: "#8B0000", lightcoral: "#F08080", 
        salmon: "#FA8072", crimson: "#DC143C", firebrick: "#B22222",
        
        // 주황 계열
        orange: "#FFA500", darkorange: "#FF8C00", coral: "#FF7F50",
        tomato: "#FF6347", orangered: "#FF4500",
        
        // 노랑 계열
        yellow: "#FFFF00", gold: "#FFD700", khaki: "#F0E68C",
        lightyellow: "#FFFFE0", lemonchiffon: "#FFFACD",
        
        // 녹색 계열
        green: "#008000", darkgreen: "#006400", lime: "#00FF00",
        limegreen: "#32CD32", lightgreen: "#90EE90", springgreen: "#00FF7F",
        seagreen: "#2E8B57", forestgreen: "#228B22", olive: "#808000",
        
        // 청록 계열
        cyan: "#00FFFF", aqua: "#00FFFF", turquoise: "#40E0D0",
        mediumturquoise: "#48D1CC", darkturquoise: "#00CED1", teal: "#008080",
        
        // 파랑 계열
        blue: "#0000FF", darkblue: "#00008B", navy: "#000080",
        mediumblue: "#0000CD", royalblue: "#4169E1", steelblue: "#4682B4",
        lightblue: "#ADD8E6", skyblue: "#87CEEB", deepskyblue: "#00BFFF",
        
        // 보라 계열
        purple: "#800080", indigo: "#4B0082", violet: "#EE82EE",
        magenta: "#FF00FF", orchid: "#DA70D6", plum: "#DDA0DD",
        
        // 분홍 계열
        pink: "#FFC0CB", hotpink: "#FF69B4", deeppink: "#FF1493",
        lightpink: "#FFB6C1", palevioletred: "#DB7093",
        
        // 갈색 계열
        brown: "#A52A2A", maroon: "#800000", chocolate: "#D2691E",
        sienna: "#A0522D", peru: "#CD853F", tan: "#D2B48C",
        
        // 회색 계열
        black: "#000000", gray: "#808080", silver: "#C0C0C0",
        white: "#FFFFFF", darkgray: "#A9A9A9", lightgray: "#D3D3D3",
        dimgray: "#696969", slategray: "#708090"
    };

    container.innerHTML = "";

    Object.entries(cssColors).forEach(([name, hex]) => {
        const item = document.createElement("div");
        item.style.display = "flex";
        item.style.flexDirection = "column";
        item.style.gap = "4px";
        
        const colorName = document.createElement("div");
        colorName.style.fontSize = "0.85rem";
        colorName.style.fontWeight = "600";
        colorName.textContent = name;
        
        const colorBox = document.createElement("div");
        colorBox.style.height = "24px";
        colorBox.style.borderRadius = "6px";
        colorBox.style.border = "1px solid #ccc";
        colorBox.style.background = hex;
        colorBox.title = hex;
        
        item.style.cursor = "pointer";
        item.addEventListener("click", function() {
            console.log("name: ", name);
            console.log("hex: ", hex);
            console.log("결과: ", `${name}(${hex})`)
            insertTextAtCursor(`${name}(${hex})`);
            // insertTextAtCursor(name);  // 색상 이름 삽입
            // 또는
            // insertTextAtCursor(hex);  // HEX 코드 삽입
        });

        item.appendChild(colorName);
        item.appendChild(colorBox);
        container.appendChild(item);
    });
    
    console.log("CSS 색상 초기화 완료");
}

/**
 * CSS 색상 토글 버튼 설정
 */
function setupCSSColorsToggle() {
    const toggleBtn = document.getElementById("toggle-css-colors");
    const wrapper = document.getElementById("css-colors-wrapper");
    const colormapWrapper = document.getElementById("colormap-wrapper");
    
    if (!toggleBtn || !wrapper) {
        console.log("CSS 색상 토글 버튼 또는 wrapper를 찾을 수 없습니다.");
        return;
    }

    toggleBtn.addEventListener("click", () => {
        const isHidden = wrapper.style.display === "none" || wrapper.style.display === "";
        
        // CSS 색상 토글
        wrapper.style.display = isHidden ? "block" : "none";
        toggleBtn.textContent = isHidden ? "색상 숨기기" : "색상 보기";
        // toggleBtn.textContent = isHidden ? "CSS 색상 숨기기" : "CSS 색상 보기";
        toggleBtn.setAttribute("aria-expanded", isHidden ? "true" : "false");
        
        // 컬러맵은 닫기
        if (isHidden && colormapWrapper) {
            colormapWrapper.style.display = "none";
            const colormapBtn = document.getElementById("toggle-colormap");
            if (colormapBtn) {
                colormapBtn.textContent = "컬러맵 보기";
                colormapBtn.setAttribute("aria-expanded", "false");
            }
        }
        
        console.log("CSS 색상 토글:", isHidden ? "열림" : "닫힘");
    });
    
    console.log("CSS 색상 토글 버튼 이벤트 등록 완료");
}



