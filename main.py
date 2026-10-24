import os
import sys
import ssl

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Windows SSL / ASN1 sertifika hatasını çözen yerleşik (harici paket gerektirmeyen) yama
    def _patched_load_windows_store_certs(self, storename, purpose):
        try:
            for cert, encoding, trust in ssl.enum_certificates(storename):
                if encoding == "x509_asn" and (trust is True or purpose.oid in trust):
                    try:
                        self.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(cert))
                    except Exception:
                        pass
        except Exception:
            pass

    ssl.SSLContext._load_windows_store_certs = _patched_load_windows_store_certs

import uuid
import json
import random
import asyncio
import pymupdf
from typing import Literal, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from google import genai
from google.genai import types

# ==========================================
# 1. SABİT AYARLAR
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6KlANRxnfnM_uT_hqwWtKLWV9RT7txe6EttKtRp4b_G6A")
GEMINI_MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"
COLLECTION_NAME = "study_rag_collection"

# Global istemciler ve geçici (In-Memory) durum takibi
qdrant_client: QdrantClient = None
gemini_client: genai.Client = None

# Yüklenen PDF'lerin ve çözülen soruların kullanıcı bazlı takibi
uploaded_documents = []
quiz_stats = {}


def get_user_quiz_stats(uid: str):
    if uid not in quiz_stats:
        quiz_stats[uid] = {
            "total_solved": 0,
            "correct": 0,
            "wrong": 0,
            "weak_pages": {}
        }
    return quiz_stats[uid]


# ==========================================
# 2. LIFESPAN (BAŞLANGIÇ YÜKLEMELERİ)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_client, gemini_client
    print("[INFO] Qdrant (:memory:) ve Gemini istemcisi baslatiliyor...", flush=True)

    # 1. Qdrant'ı RAM'de başlat (Boyut: 3072 - gemini-embedding-001 standardı)
    qdrant_client = QdrantClient(":memory:")
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
    )

    # 2. Gemini İstemcisini başlat
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"[OK] Sistem hazir! Model: {GEMINI_MODEL}", flush=True)
    print("-> Arayuz: http://127.0.0.1:8000", flush=True)
    print("-> Swagger Docs: http://127.0.0.1:8000/docs", flush=True)
    yield
    print("[STOP] Sistem kapatiliyor...", flush=True)


app = FastAPI(
    title="StudyRAG - Akıllı Ders Çalışma Sistemi",
    version="1.0.0",
    lifespan=lifespan
)

# HTML arayüzünden ve Dev Tunnels / harici linklerden sorunsuz istek atabilmek için evrensel CORS izni
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 3. YARDIMCI FONKSİYONLAR (CHUNKING & EMBED)
# ==========================================
def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Metni cümle bütünlüğünü koruyacak şekilde kesişimli (overlap) parçalara böler."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) > 30:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Metin listesini Gemini Embedding API ile vektöre çevirir (Hata ve kota korumalı)."""
    import time
    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
            )
            return [emb.values for emb in response.embeddings]
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise e


# ==========================================
# 4. PYDANTIC ŞEMALARI (VERİ DOĞRULAMA)
# ==========================================
class ChatRequest(BaseModel):
    question: str
    course_name: Optional[str] = None
    eli5_mode: bool = False  # "Basitçe Anlat" modu
    user_id: Optional[str] = "default_user"


class SourceInfo(BaseModel):
    document_name: str
    page_number: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]


# --- Quiz Şemaları (Structured Output için) ---
class QuizQuestion(BaseModel):
    question_type: Literal["mcq", "tf", "fill", "open"] = Field(
        description="Soru tipi: mcq (çoktan seçmeli), tf (doğru/yanlış), fill (boşluk doldurma), open (açık uçlu)"
    )
    question_text: str = Field(description="Sorunun metni")
    options: list[str] = Field(
        default=[],
        description="Sadece 'mcq' ise 4 şık (A, B, C, D), 'tf' ise ['Doğru', 'Yanlış'], diğerlerinde boş liste"
    )
    correct_answer: str = Field(description="Sorunun doğru cevabı")
    explanation: str = Field(description="Cevabın neden doğru olduğunun kısa açıklaması")
    source_document: str = Field(description="Bilginin alındığı PDF adı")
    page_number: int = Field(description="Bilginin alındığı sayfa numarası")


class QuizListResponse(BaseModel):
    questions: list[QuizQuestion]


class QuizGenerateRequest(BaseModel):
    question_type: Literal["mixed", "mcq", "tf", "fill", "open"] = "mixed"
    difficulty: str = "Orta"
    count: int = 5
    course_name: Optional[str] = None
    user_id: Optional[str] = "default_user"


# --- Flashcard Şemaları ---
class FlashcardItem(BaseModel):
    front: str = Field(description="Kartın ön yüzü: Kavram veya kısa soru")
    back: str = Field(description="Kartın arka yüzü: Net ve kısa açıklama")
    source_document: str
    page_number: int


class FlashcardListResponse(BaseModel):
    cards: list[FlashcardItem]


class FlashcardGenerateRequest(BaseModel):
    count: Optional[int] = 5
    course_name: Optional[str] = None
    user_id: Optional[str] = "default_user"


# --- Quiz Sonuç Gönderme (Zayıf Konu Tespiti) ---
class QuizAnswerSubmit(BaseModel):
    is_correct: bool
    source_document: str
    page_number: int
    user_id: Optional[str] = "default_user"


# ==========================================
# 5. ENDPOINT'LER
# ==========================================

# Ana sayfaya girildiğinde index.html varsa onu açar
@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "StudyRAG API çalışıyor! Arayüz için index.html dosyasını aynı klasöre koyun veya /docs adresine gidin."}


# 1. PDF Yükleme ve Qdrant'a Kaydetme
@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    course_name: str = Form("Genel Ders"),
    user_id: Optional[str] = Form(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or user_id or "default_user").strip()

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Lütfen sadece PDF dosyası yükleyin.")

    pdf_bytes = await file.read()
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    chunks_to_embed = []
    payloads = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text("text")
        page_chunks = split_text(text)

        for chunk in page_chunks:
            chunks_to_embed.append(chunk)
            payloads.append({
                "user_id": uid,
                "document_name": file.filename,
                "course_name": course_name,
                "page_number": page_index + 1,
                "text": chunk
            })

    if not chunks_to_embed:
        raise HTTPException(status_code=400, detail="PDF içinden metin okunamadı.")

    # Gemini API ile 25'erli paketler halinde güvenli, kotalı ve non-blocking vektöre çevir
    embeddings = []
    batch_size = 25
    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i:i + batch_size]
        batch_embs = await asyncio.to_thread(get_embeddings, batch)
        embeddings.extend(batch_embs)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload=payload
        )
        for embedding, payload in zip(embeddings, payloads)
    ]

    # Qdrant koleksiyon boyutu kontrolü (vektör boyutu uyumsuzluğunu otomatik önler)
    try:
        col_info = qdrant_client.get_collection(COLLECTION_NAME)
        if col_info.config.params.vectors.size != len(embeddings[0]):
            qdrant_client.delete_collection(COLLECTION_NAME)
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=len(embeddings[0]), distance=Distance.COSINE),
            )
    except Exception:
        try:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=len(embeddings[0]), distance=Distance.COSINE),
            )
        except Exception:
            pass

    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

    doc_info = {
        "user_id": uid,
        "filename": file.filename,
        "course_name": course_name,
        "total_pages": len(doc),
        "total_chunks": len(points)
    }

    # Aynı dosya varsa eski kaydı güncelle
    existing_idx = next((i for i, d in enumerate(uploaded_documents) if d.get("user_id") == uid and d.get("filename") == file.filename and d.get("course_name", "").strip().lower() == course_name.strip().lower()), None)
    if existing_idx is not None:
        uploaded_documents[existing_idx] = doc_info
    else:
        uploaded_documents.append(doc_info)

    print(f"[UPLOAD OK] '{file.filename}' ({course_name}) [User: {uid}] -> {len(doc)} sayfa, {len(points)} parca basariyla eklendi.", flush=True)

    return {"message": "PDF başarıyla indekslendi!", "document": doc_info}


# 2. Yüklü PDF'leri Listeleme (Kullanıcı ve Ders filtreli)
@app.get("/documents")
async def get_documents(
    course_name: Optional[str] = None,
    user_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or user_id or "default_user").strip()
    user_docs = [d for d in uploaded_documents if d.get("user_id", "default_user") == uid]

    if course_name and course_name.strip():
        target = course_name.strip().lower()
        filtered = [d for d in user_docs if d.get("course_name", "").strip().lower() == target]
        return {"documents": filtered}
    return {"documents": user_docs}


# 2.1 PDF Silme Endpoint'i (Garantili Silme & İzolasyon)
@app.delete("/documents/{filename}")
async def delete_document(
    filename: str,
    course_name: Optional[str] = None,
    user_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    global uploaded_documents
    uid = (x_user_id or user_id or "default_user").strip()
    target_course = course_name.strip().lower() if (course_name and course_name.strip()) else None

    # Qdrant'tan vektörleri sil
    try:
        must_conditions = [
            FieldCondition(key="document_name", match=MatchValue(value=filename)),
            FieldCondition(key="user_id", match=MatchValue(value=uid))
        ]
        qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=must_conditions)
        )
    except Exception as e:
        print(f"[WARN] Qdrant silme: {e}", flush=True)

    # In-memory listeden sil:
    # 1. Önce ders adıyla tam eşleşeni kaldırmayı dene
    initial_count = len(uploaded_documents)
    uploaded_documents = [
        d for d in uploaded_documents
        if not (
            d.get("user_id", "default_user") == uid and
            d.get("filename") == filename and
            (not target_course or d.get("course_name", "").strip().lower() == target_course)
        )
    ]
    # 2. Eğer ders ismi hafif farklı kaldığı için silinemediyse bile, o kullanıcının dökümanını kesin olarak sil
    if len(uploaded_documents) == initial_count:
        uploaded_documents = [
            d for d in uploaded_documents
            if not (
                d.get("user_id", "default_user") == uid and
                d.get("filename") == filename
            )
        ]

    user_docs = [d for d in uploaded_documents if d.get("user_id", "default_user") == uid]
    if target_course:
        user_docs = [d for d in user_docs if d.get("course_name", "").strip().lower() == target_course]
    return {"message": f"'{filename}' başarıyla silindi.", "documents": user_docs}


# 3. RAG Sohbet & Özet & "Basitçe Anlat" Modu
def build_chat_context_and_prompt(request: ChatRequest):
    query_vector = get_embeddings([request.question])[0]
    uid = (request.user_id or "default_user").strip()

    must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=uid))]
    if request.course_name and request.course_name.strip():
        must_conditions.append(FieldCondition(key="course_name", match=MatchValue(value=request.course_name.strip())))

    query_filter = Filter(must=must_conditions)

    # Genel özet ve geniş kapsam için limit 8
    search_results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=8
    ).points

    if not search_results:
        raise HTTPException(status_code=404, detail="Yüklenen dökümanlar arasında bu soruyla ilgili içerik bulunamadı. Lütfen sol menüden PDF yüklediğinizden emin olun.")

    context_parts = []
    sources = []
    seen_sources = set()

    for hit in search_results:
        p = hit.payload
        doc_key = f"{p['document_name']}_{p['page_number']}"
        context_parts.append(f"[Kaynak: {p['document_name']}, Sayfa {p['page_number']}]\n{p['text']}")
        if doc_key not in seen_sources:
            seen_sources.add(doc_key)
            sources.append(SourceInfo(
                document_name=p["document_name"],
                page_number=p["page_number"],
                snippet=p["text"][:140] + "..."
            ))

    context_text = "\n\n---\n\n".join(context_parts)

    style_instruction = (
        "Konuyu hiç bilmeyen birine anlatır gibi günlük hayattan benzetmelerle çok sade ve basitçe anlat."
        if request.eli5_mode else
        "Akademik, net, öğretici ve sınava yönelik bir dille açıkla."
    )

    prompt = f"""Sen üniversite öğrencilerine ders çalışma ve sınav hazırlığında rehberlik eden uzman bir yapay zeka asistanısın.
Tarzın: {style_instruction}

Aşağıda öğrencinin yüklediği ilgili [DERS NOTLARI] parçaları verilmiştir.

YÖNERGELER:
1. Öğrencinin [SORU]'sunu verilen [DERS NOTLARI]'ndan faydalanarak kapsamlı, anlaşılır ve eğitici bir şekilde yanıtla.
2. Öğrenci "özet", "en kritik sınav konuları", "önemli kavramlar" gibi genel bir soru soruyorsa; notlardaki ana başlıkları, tanımları ve önemli konuları sentezleyerek öğrencinin sınava çalışabileceği maddeli net bir analiz hazırla.
3. Notlardaki bilgileri açıklarken ilgili sayfayı cümle sonlarında mutlaka [Sayfa X] şeklinde belirt.
4. Yalnızca soru ders notlarının alanıyla tamamen ilgisizse ve notlarda hiçbir ipucu yoksa 'Yüklenen ders notlarında bu konu hakkında bilgi yer almıyor' de.

[DERS NOTLARI]:
{context_text}

[SORU]:
{request.question}
"""
    return prompt, sources


# 3. RAG Sohbet & Özet (Standart JSON Yanıt)
@app.post("/chat", response_model=ChatResponse)
async def chat_with_pdf(request: ChatRequest):
    prompt, sources = build_chat_context_and_prompt(request)
    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return ChatResponse(answer=response.text, sources=sources)


# 3.1 Canlı Akış (Streaming SSE - Kayan Metin)
@app.post("/chat-stream")
async def chat_stream_with_pdf(request: ChatRequest):
    prompt, sources = build_chat_context_and_prompt(request)
    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)

    async def event_generator():
        # 1. İlk olarak kaynakları gönder
        yield f"data: {json.dumps({'sources': [s.model_dump() for s in sources]})}\n\n"

        # 2. Gemini akışını canlı token olarak ilet
        try:
            stream = client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=prompt
            )
            for chunk in stream:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            # Yedek modele düş
            try:
                stream = client.models.generate_content_stream(
                    model="gemini-3.5-flash",
                    contents=prompt
                )
                for chunk in stream:
                    if chunk.text:
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            except Exception as e2:
                yield f"data: {json.dumps({'error': str(e2)})}\n\n"

        # 3. Tamamlandı sinyali
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# 4. Pydantic Şemalı Otomatik Quiz Üretici
@app.post("/generate-quiz", response_model=QuizListResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or request.user_id or "default_user").strip()
    must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=uid))]
    if request.course_name:
        must_conditions.append(FieldCondition(key="course_name", match=MatchValue(value=request.course_name)))

    scroll_filter = Filter(must=must_conditions)

    # Qdrant'tan kayıtlı parçaları çek (seçili ders filtreli)
    scroll_result, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=50
    )

    if not scroll_result:
        course_msg = f"'{request.course_name}' dersi için" if request.course_name else "Bu çalışma alanı için"
        raise HTTPException(status_code=404, detail=f"{course_msg} henüz PDF yüklenmedi. Lütfen sol menüden bu derse en az bir PDF ekleyin.")

    # Rastgele en fazla 5 parça seç
    sampled_points = random.sample(scroll_result, min(len(scroll_result), 5))
    context_text = "\n\n---\n\n".join(
        [f"[PDF: {p.payload['document_name']} | Sayfa: {p.payload['page_number']}]\n{p.payload['text']}" for p in sampled_points]
    )

    type_desc = {
        "mixed": "çoktan seçmeli (mcq), doğru/yanlış (tf), boşluk doldurma (fill) ve açık uçlu (open) karışık",
        "mcq": "sadece 4 şıklı çoktan seçmeli (mcq)",
        "tf": "sadece Doğru/Yanlış (tf)",
        "fill": "sadece boşluk doldurma (fill)",
        "open": "sadece klasik açık uçlu (open)"
    }.get(request.question_type, "karışık")

    prompt = f"""Aşağıdaki ders notlarından {request.difficulty} zorluk seviyesinde toplam {request.count} adet {type_desc} sınav sorusu üret.
Her sorunun doğru cevabını, açıklamasını ve kaynak PDF ile sayfa numarasını eksiksiz doldur.

[DERS NOTLARI]:
{context_text}
"""

    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)

    def _call_gemini_quiz(model_name: str):
        return client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuizListResponse,
            ),
        )

    try:
        response = await asyncio.to_thread(_call_gemini_quiz, GEMINI_MODEL)
    except Exception:
        response = await asyncio.to_thread(_call_gemini_quiz, "gemini-3.8-flash")

    return QuizListResponse.model_validate_json(response.text)


# 5. Otomatik Flashcard Üretici (Ultra Hızlı ve Non-blocking)
@app.post("/generate-flashcards", response_model=FlashcardListResponse)
async def generate_flashcards(
    payload: Optional[FlashcardGenerateRequest] = None,
    count: int = 5,
    course_name: Optional[str] = None,
    user_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or (payload.user_id if payload else None) or user_id or "default_user").strip()
    target_count = (payload.count if payload and payload.count else count) or 5
    target_course = (payload.course_name if payload and payload.course_name else course_name) or None
    actual_count = min(max(target_count, 3), 5)

    must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=uid))]
    if target_course:
        must_conditions.append(FieldCondition(key="course_name", match=MatchValue(value=target_course)))

    scroll_filter = Filter(must=must_conditions)

    # Qdrant'tan parçaları çek (seçili ders filtreli)
    scroll_result, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=50
    )

    if not scroll_result:
        course_msg = f"'{target_course}' dersi için" if target_course else "Bu çalışma alanı için"
        raise HTTPException(status_code=404, detail=f"{course_msg} henüz PDF yüklenmedi. Lütfen sol menüden bu derse en az bir PDF ekleyin.")

    sampled_points = random.sample(scroll_result, min(len(scroll_result), 4))
    context_text = "\n\n---\n\n".join(
        [f"[PDF: {p.payload['document_name']} | Sayfa: {p.payload['page_number']}]\n{p.payload['text']}" for p in sampled_points]
    )

    prompt = f"""Aşağıdaki ders notlarından sınavda çıkabilecek en kritik {actual_count} kavram için soru-cevap (Flashcard) hazırla.
KURALLAR (HIZLI VE ETKİLİ ÖĞRENME İÇİN):
- 'front': 1-4 kelimelik net bir terim, kavram veya kısa soru olmalı.
- 'back': En fazla 1-2 cümlelik, net, vurucu ve akılda kalıcı tanım veya cevap olmalı.
- 'source_document' ve 'page_number' alanlarını referans notlardan al.

[DERS NOTLARI]:
{context_text}
"""

    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)

    def _call_gemini_flashcards(model_name: str):
        return client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FlashcardListResponse,
            ),
        )

    try:
        response = await asyncio.to_thread(_call_gemini_flashcards, GEMINI_MODEL)
    except Exception as e:
        print(f"[WARN] Flashcard lite model hatasi: {e}, yedek modele geciliyor...", flush=True)
        response = await asyncio.to_thread(_call_gemini_flashcards, "gemini-3.8-flash")

    return FlashcardListResponse.model_validate_json(response.text)


# 6. Zayıf Konu Tespiti & Dashboard İstatistikleri
@app.post("/submit-answer")
async def submit_answer(
    submission: QuizAnswerSubmit,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or submission.user_id or "default_user").strip()
    u_stats = get_user_quiz_stats(uid)
    u_stats["total_solved"] += 1
    if submission.is_correct:
        u_stats["correct"] += 1
    else:
        u_stats["wrong"] += 1
        key = f"{submission.source_document} (Sayfa {submission.page_number})"
        u_stats["weak_pages"][key] = u_stats["weak_pages"].get(key, 0) + 1

    return {"status": "recorded", "stats": u_stats}


@app.get("/dashboard-stats")
async def get_dashboard_stats(
    user_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    uid = (x_user_id or user_id or "default_user").strip()
    return get_user_quiz_stats(uid)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)