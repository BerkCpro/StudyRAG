# StudyRAG — FastAPI Endpoint & Mimari Kod Snippet'leri
**Proje:** StudyRAG (Advanced Computer Programming Dersi Final Sunumu)  
**Kaynak Dosya:** [main.py](file:///c:/Users/Berk/OneDrive/Desktop/rag_fastapi/deneme2/main.py)  

Bu dokümanda sunum slaytlarında birebir kullanabileceğiniz, koddan doğrudan alıntılanmış, maksimum 14 satırlık ve slayt genişliğine uygun FastAPI endpoint ve mimari kod parçaları yer almaktadır.

---

## 1. POST /upload-pdf
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** Yüklenen PDF dosyasını karşılar, sayfa/metin denetimi yapar, 2200 karaktere kadar slayt bütünlüğünü korur ve 25'li batch'ler halinde vektörleştirerek Qdrant ve yerel depoya kaydeder.
* **Kullanılan FastAPI Özellikleri:** `UploadFile`, `File(...)`, `Form(...)`, `Header(...)`, `HTTPException`
* **Dosya ve Satır:** `main.py:852-993`

```python
@app.post(
    "/upload-pdf",
    tags=["Döküman Yönetimi"],
    summary="Ders Notu (PDF) Yükleme ve Vektörleştirme",
    description="..."
)
async def upload_pdf(
    file: UploadFile = File(..., description="Yüklenecek PDF ders notu dosyası"),
    course_name: str = Form("Genel Ders", description="Materyalin ait olduğu ders adı"),
    user_id: Optional[str] = Form(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    pdf_bytes = await file.read()
    ...
    return {"message": "Ders notu başarıyla yüklendi!", "document": doc_info}
```

---

## 2. GET /documents
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** Aktif kullanıcının seçili dersteki veya tüm derslerdeki yüklenmiş PDF dökümanlarını, sayfa sayılarını ve meta verilerini listeler.
* **Kullanılan FastAPI Özellikleri:** `@app.get`, `Query(...)`, `Header(...)`
* **Dosya ve Satır:** `main.py:997-1019`

```python
@app.get(
    "/documents",
    tags=["Döküman Yönetimi"],
    summary="Yüklü Dökümanları Listeleme",
    description="..."
)
async def get_documents(
    course_name: Optional[str] = Query(None, description="Filtrelenecek ders adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    uid = (x_user_id or user_id or "").strip()
    ...
    return {"documents": user_docs}
```

---

## 3. DELETE /documents/{filename}
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** Belirtilen PDF dosyasını disk deposundan kaldırır, Qdrant vektör koleksiyonundaki noktalarını temizler ve zihin haritası önbelleğini sıfırlar.
* **Kullanılan FastAPI Özellikleri:** `@app.delete`, Path parametresi (`{filename}`), `Query(...)`, `Header(...)`
* **Dosya ve Satır:** `main.py:1022-1089`

```python
@app.delete(
    "/documents/{filename}",
    tags=["Döküman Yönetimi"],
    summary="Ders Notunu Silme",
    description="..."
)
async def delete_document(
    filename: str,
    course_name: Optional[str] = Query(None, description="PDF'in ait olduğu ders adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    qdrant_client.delete(collection_name=COLLECTION_NAME, points_selector=Filter(...))
    ...
    return {"message": f"'{filename}' başarıyla silindi.", "documents": user_docs}
```

---

## 4. DELETE /courses/{course_name}
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** Belirtilen dersi, o derse ait tüm PDF dosyalarını, Qdrant vektör kayıtlarını ve zihin haritası önbelleğini tamamen temizler.
* **Kullanılan FastAPI Özellikleri:** `@app.delete`, Path parametresi (`{course_name}`), `Query(...)`, `Header(...)`
* **Dosya ve Satır:** `main.py:1092-1147`

```python
@app.delete(
    "/courses/{course_name}",
    tags=["Döküman Yönetimi"],
    summary="Dersi ve Tüm Materyallerini Silme",
    description="..."
)
async def delete_course(
    course_name: str,
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    qdrant_client.delete(collection_name=COLLECTION_NAME, points_selector=Filter(...))
    ...
    return {"message": f"'{target_course}' dersi ve tüm materyalleri başarıyla silindi."}
```

---

## 5. GET /pdf-page-image
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** İstenen sayfa numarasını PyMuPDF ile anında render ederek PNG görseli olarak döner; kaynak teyidi için arayüzde doğrudan gösterilir.
* **Kullanılan FastAPI Özellikleri:** `@app.get`, `Response` (özel binary veri ve `Cache-Control`, `X-Total-Pages` başlıkları), `Query(...)`, `Header(...)`, `HTTPException`
* **Dosya ve Satır:** `main.py:1150-1195`

```python
@app.get(
    "/pdf-page-image",
    tags=["Döküman Yönetimi"],
    summary="PDF Sayfa Görseli Önizleme",
    description="..."
)
async def get_pdf_page_image(
    filename: str = Query(..., description="Görüntülenecek PDF dosya adı"),
    page: int = Query(1, description="Sayfa numarası (1-tabanlı)"),
    ...
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="..."),
    dpi: int = Query(140, description="Render çözünürlüğü (DPI, varsayılan 140)")
):
    ...
    return Response(content=img_bytes, media_type="image/png", headers={...})
```

---

## 6. GET /pdf-file/{filename} + GET /pdf-info
* **Grup (Tag):** `Döküman Yönetimi`
* **Ne Yapar:** PDF dosyasını tarayıcıda stream eder ve dökümanın toplam sayfa sayısı ile diskteki varlığını kontrol eder.
* **Kullanılan FastAPI Özellikleri:** `@app.get`, `FileResponse`, Path parametresi, `Query(...)`, `Header(...)`, `HTTPException`
* **Dosya ve Satır:** `main.py:1198-1242`

```python
@app.get("/pdf-file/{filename}", tags=["Döküman Yönetimi"], summary="PDF İndirme")
async def get_pdf_file(
    filename: str, user_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    ...
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)

@app.get("/pdf-info", tags=["Döküman Yönetimi"], summary="PDF Sayfa ve Durum Bilgisi")
async def get_pdf_info(filename: str = Query(...), ...):
    ...
    return {"filename": filename, "total_pages": total, "has_file": True}
```

---

## 7. POST /chat
* **Grup (Tag):** `Sohbet`
* **Ne Yapar:** Kullanıcı sorusunu ve opsiyonel görselini ilgili ders notlarıyla eşleştirerek sayfa referanslı yanıt döner.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `response_model=ChatResponse`, Pydantic Request Body, `HTTPException`
* **Dosya ve Satır:** `main.py:1442-1469`

```python
@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Sohbet"],
    summary="RAG Tabanlı Soru-Cevap (Standart JSON)",
    description="..."
)
async def chat_with_pdf(request: ChatRequest):
    ...
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents
    )
    return ChatResponse(answer=response.text, sources=sources)
```

---

## 8. POST /chat-stream
* **Grup (Tag):** `Sohbet`
* **Ne Yapar:** İlgili kaynak sayfaları ilk paket olarak iletir, ardından Gemini modelinin ürettiği token'ları Server-Sent Events (SSE) protokolüyle sıfır gecikmeli canlı akar.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `StreamingResponse`, Asenkron jeneratör (`async def event_generator`), `HTTPException`
* **Dosya ve Satır:** `main.py:1485-1561`

```python
@app.post(
    "/chat-stream",
    tags=["Sohbet"],
    summary="Canlı Akışlı RAG Asistanı (Server-Sent Events)",
    description="..."
)
async def chat_stream_with_pdf(request: ChatRequest):
    ...
    async def event_generator():
        yield f"data: {json.dumps({'sources': [s.model_dump() for s in sources]})}\n\n"
        for chunk in stream:
            yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", ...)
```

---

## 9. POST /generate-quiz
* **Grup (Tag):** `Çalışma Araçları`
* **Ne Yapar:** Seçili ders veya PDF'lerden, belirlenen zorluk ve adede (5, 10, 20) göre yapılandırılmış test üretir; geçmişte hata yapılan zayıf konulara odaklanabilir.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `response_model=QuizListResponse`, Pydantic Request Body, `Header(...)`, `asyncio.to_thread`
* **Dosya ve Satır:** `main.py:1564-1683`

```python
@app.post(
    "/generate-quiz",
    response_model=QuizListResponse,
    tags=["Çalışma Araçları"],
    summary="Kişiselleştirilmiş Sınav Simülatörü",
    description="..."
)
async def generate_quiz(
    request: QuizGenerateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    response = await asyncio.to_thread(_call_gemini_quiz, GEMINI_MODEL)
    return QuizListResponse.model_validate_json(response.text)
```

---

## 10. POST /generate-flashcards
* **Grup (Tag):** `Çalışma Araçları`
* **Ne Yapar:** Ders notlarındaki en kritik kavramları ön ve arka yüz olarak soru-cevap kart seti halinde derler.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `response_model=FlashcardListResponse`, Body + Query hibrit parametre, `Header(...)`, `asyncio.to_thread`
* **Dosya ve Satır:** `main.py:1686-1756`

```python
@app.post(
    "/generate-flashcards",
    response_model=FlashcardListResponse,
    tags=["Çalışma Araçları"],
    summary="Hızlı Tekrar Çalışma Kartları (Flashcards)",
    description="..."
)
async def generate_flashcards(
    payload: Optional[FlashcardGenerateRequest] = None,
    count: int = Query(5, description="Üretilecek kart sayısı"),
    course_name: Optional[str] = Query(None, description="Hedef ders adı"),
    ...
):
    ...
    response = await asyncio.to_thread(_call_gemini_flashcards, GEMINI_MODEL)
    return FlashcardListResponse.model_validate_json(response.text)
```

---

## 11. POST /generate-cheatsheet
* **Grup (Tag):** `Çalışma Araçları`
* **Ne Yapar:** Ders notlarındaki formülleri, teoremleri, tanımları ve sınav tuzaklarını KaTeX uyumlu markdown formatında tek sayfalık özet kağıdı olarak üretir.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `response_model=CheatSheetResponse`, Body + Query hibrit parametre, `Header(...)`, `asyncio.to_thread`
* **Dosya ve Satır:** `main.py:1759-1856`

```python
@app.post(
    "/generate-cheatsheet",
    response_model=CheatSheetResponse,
    tags=["Çalışma Araçları"],
    summary="Sınav Öncesi Formül & Kavram Kağıdı (Cheat Sheet)",
    description="..."
)
async def generate_cheatsheet(
    payload: Optional[CheatSheetRequest] = None,
    course_name: Optional[str] = Query(None, description="Hedef ders adı"),
    ...
):
    ...
    response = await asyncio.to_thread(_call_gemini_cheatsheet, GEMINI_MODEL)
    return CheatSheetResponse(course_name=course_title, ..., markdown_content=response.text)
```

---

## 12. POST /api/mindmap
* **Grup (Tag):** `Çalışma Araçları`
* **Ne Yapar:** Dersin veya seçili PDF'lerin kavram ağacını ve sayfa referanslarını hiyerarşik JSON olarak üretir; tekrar üretimleri SQLite önbelleğinden 5 milisaniyede döner.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, `JSONResponse`, Pydantic doğrulaması (`MindMapResponse`), `Header(...)`, `asyncio.to_thread`
* **Dosya ve Satır:** `main.py:1859-2083`

```python
@app.post(
    "/api/mindmap",
    tags=["Çalışma Araçları"],
    summary="Hiyerarşik Ders Zihin Haritası (Mindmap)",
    description="..."
)
async def generate_mindmap(
    payload: MindMapRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    if not refresh:
        cached_result = get_mindmap_cache(cache_key)
        if cached_result:
            return JSONResponse(content=cached_result)
    ...
    return JSONResponse(content=mindmap_data)
```

---

## 13. POST /submit-answer
* **Grup (Tag):** `İlerleme`
* **Ne Yapar:** Öğrencinin quiz sorusuna verdiği yanıtı kaydeder; yanlış yapılan soruların sayfa ve konu bilgilerini zayıf konu analitiğine ekler.
* **Kullanılan FastAPI Özellikleri:** `@app.post`, Pydantic Body doğrulaması, `Header(...)`
* **Dosya ve Satır:** `main.py:2086-2109`

```python
@app.post(
    "/submit-answer",
    tags=["İlerleme"],
    summary="Quiz Sorusu Cevap Kaydı & Zayıf Konu Tespiti",
    description="..."
)
async def submit_answer(
    submission: QuizAnswerSubmit,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    ...
    if not submission.is_correct:
        u_stats["weak_pages"][key] = u_stats["weak_pages"].get(key, 0) + 1
    save_storage()
    return {"status": "recorded", "stats": u_stats}
```

---

## 14. GET /dashboard-stats
* **Grup (Tag):** `İlerleme`
* **Ne Yapar:** Kullanıcının toplam çözdüğü soru adedini, doğru/yanlış oranlarını ve en çok zorlandığı sayfa/konu dağılımını döner.
* **Kullanılan FastAPI Özellikleri:** `@app.get`, `Query(...)`, `Header(...)`
* **Dosya ve Satır:** `main.py:2112-2124`

```python
@app.get(
    "/dashboard-stats",
    tags=["İlerleme"],
    summary="Öğrenci Başarı ve İstatistik Paneli",
    description="..."
)
async def get_dashboard_stats(
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="...")
):
    uid = (x_user_id or user_id or "default_user").strip()
    return get_user_quiz_stats(uid)
```

---

## 15. GET /, GET/HEAD /health, GET/HEAD /ping
* **Grup (Tag):** `Sistem`
* **Ne Yapar:** Sunucu ve arka plan servislerinin ayakta olduğunu teyit eder; ana sayfada `index.html` dosyasını sunar.
* **Kullanılan FastAPI Özellikleri:** `@app.get`, `@app.head`, çoklu route eşleme, `FileResponse`, `include_in_schema=False`
* **Dosya ve Satır:** `main.py:819-847`

```python
@app.get(
    "/health",
    tags=["Sistem"],
    summary="Sistem Canlılık ve Sağlık Kontrolü",
    description="..."
)
@app.get("/ping", include_in_schema=False)
@app.head("/health", include_in_schema=False)
@app.head("/ping", include_in_schema=False)
async def health_check():
    return {"status": "ok"}

@app.get("/", tags=["Sistem"], include_in_schema=False)
async def serve_frontend():
    return FileResponse("index.html")
```

---

## 🏛️ Endpoint Dışı FastAPI Mimari Snippet'leri

### A. FastAPI Uygulaması ve OpenAPI Tags Tanımı
* **Dosya ve Satır:** `main.py:332-362`
* **Açıklama:** Swagger UI dokümantasyonunu 5 işlevsel kategoriye ayıran ve uygulama başlığı/açıklamasını içeren ana konfigürasyon.

```python
tags_metadata = [
    {"name": "Döküman Yönetimi", "description": "PDF yükleme, listeleme, silme..."},
    {"name": "Sohbet", "description": "RAG tabanlı sohbet ve canlı akış (SSE)."},
    {"name": "Çalışma Araçları", "description": "Quiz, flashcard, formül kağıdı..."},
    {"name": "İlerleme", "description": "Quiz cevapları ve dashboard istatistikleri."},
    {"name": "Sistem", "description": "Sağlık kontrolü ve ana sayfa."},
]

app = FastAPI(
    title="StudyRAG - Akıllı Ders Çalışma Sistemi API",
    description="Üniversite ders notları ve slaytları üzerinde çalışan asenkron RAG platformu.",
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan
)
```

---

### B. Uygulama Yaşam Döngüsü (Lifespan Context Manager)
* **Dosya ve Satır:** `main.py:292-330`
* **Açıklama:** Sunucu ayağa kalkarken Qdrant koleksiyonu, SQLite tabloları ve kalıcı depolamayı başlatan; sunucu kapanırken verileri diske güvenle yazan modern FastAPI yaşam döngüsü yöneticisi.

```python
async def lifespan(app: FastAPI):
    global qdrant_client, gemini_client
    ...
    if not any(c.name == COLLECTION_NAME for c in collections):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
    load_storage()
    init_mindmap_db()
    yield
    save_storage()
    print("[STOP] Sistem kapatılıyor...", flush=True)
```

---

### C. Özel HTTP Middleware: İki Kademeli Rate Limiter
* **Dosya ve Satır:** `main.py:381-416`
* **Açıklama:** IP ve kullanıcı bazlı çalışan; ağır yapay zeka endpoint'leri için dakikada 25, genel endpoint'ler için dakikada 150 istek sınırlaması koyan ve `429 Too Many Requests` + `Retry-After: 60` başlığı dönen Starlette HTTP ara yazılımı.

```python
@app.middleware("http")
async def rate_limiting_middleware(request, call_next):
    path = request.url.path
    if path in ("/", "/health") or path.startswith("/static"):
        return await call_next(request)
    ...
    if path in AI_RATE_LIMITED_PATHS and len(_rate_limit_ai[track_key]) >= 25:
        return JSONResponse(
            status_code=429,
            content={"detail": "Çok fazla yapay zeka isteği gönderildi."},
            headers={"Retry-After": "60"}
        )
    return await call_next(request)
```

---

### D. CORS Middleware Entegrasyonu
* **Dosya ve Satır:** `main.py:364-370`
* **Açıklama:** Harici HTTPS tünelleri (Cloudflare) ve farklı portlardan gelen tarayıcı isteklerine izin veren evrensel CORS katmanı.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### E. Kullanıcı Kimlik Çözümleme Kalıbı (`X-User-Id` Header / Parametre Hibriti)
* **Dosya ve Satır:** `main.py:862-866, 1006-1008, 1435-1436`
* **Açıklama:** Projede ayrı bir `Depends(get_user_id)` fonksiyonu yerine, HTTP Request Header (`X-User-Id`) ile Form/Query parametresini tek merkezde birleştiren hafif bir oturum çözümleme kalıbı uygulanmıştır.

```python
async def endpoint_handler(
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Oturum başlığı")
):
    uid = (x_user_id or user_id or "default_user").strip()
```

---

### F. Pydantic v2 Veri Sözleşmeleri (Request, Response & Recursive Ağaç)
* **Dosya ve Satır:** `main.py:527-548, 566-586, 756-789`
* **Açıklama:** Çalışma zamanında tip doğrulama, Swagger örnek şemaları ve zihin haritası için özyinelemeli (recursive) ağaç modeli.

```python
class ChatRequest(BaseModel):
    question: str = Field(..., description="Kullanıcının ders sorusu")
    course_name: Optional[str] = Field(None, description="Ders adı")
    selected_docs: Optional[list[str]] = Field(None, description="Seçili PDF filtresi")

class SourceInfo(BaseModel):
    document_name: str
    page_number: int
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo] = Field(default_factory=list)

class MindMapLeaf(BaseModel):
    title: str = Field(description="Alt kavram")
    page: Optional[int] = Field(default=None)
    children: list["MindMapLeaf"] = Field(default_factory=list)

MindMapLeaf.model_rebuild()
```
