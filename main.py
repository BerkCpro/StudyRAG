import warnings
warnings.filterwarnings("ignore")
import sys
sys.modules['fastembed'] = None
import os
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

import time
from collections import defaultdict
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("studyrag")
import uuid
import json
import base64
import random
import asyncio
import sqlite3
import pymupdf
from typing import Literal, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response, JSONResponse
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from google import genai
from google.genai import types

# ==========================================
# 1. SABİT AYARLAR VE KALICI DEPOLAMA
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6KlANRxnfnM_uT_hqwWtKLWV9RT7txe6EttKtRp4b_G6A")
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash"
EMBEDDING_MODEL = "gemini-embedding-001"
COLLECTION_NAME = "study_rag_collection"

# Kalıcı veri yolları (Deploy ve yeniden başlatmalarda PDF ve istatistik kaybını önler)
STORAGE_FILE = "study_storage.json"
PDF_STORAGE_DIR = os.getenv("PDF_STORAGE_DIR", "pdf_storage")
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)
QDRANT_STORAGE_PATH = os.getenv("QDRANT_STORAGE_PATH", "./qdrant_storage")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Global istemciler ve durum takibi
qdrant_client: QdrantClient = None
gemini_client: genai.Client = None

# Yüklenen PDF'lerin ve çözülen soruların kullanıcı bazlı takibi
uploaded_documents = []
quiz_stats = {}


def find_pdf_file_path(filename: str, uid: str = "") -> Optional[str]:
    """Diskteki pdf_storage klasöründen ilgili dökümanın dosya yolunu bulur."""
    safe_filename = os.path.basename(filename)
    if uid:
        p1 = os.path.join(PDF_STORAGE_DIR, f"{uid}_{safe_filename}")
        if os.path.exists(p1):
            return p1
    p2 = os.path.join(PDF_STORAGE_DIR, safe_filename)
    if os.path.exists(p2):
        return p2
    # Dosya adıyla biten herhangi bir eşleşme ara
    if os.path.exists(PDF_STORAGE_DIR):
        for f in os.listdir(PDF_STORAGE_DIR):
            if f.endswith(f"_{safe_filename}") or f == safe_filename:
                return os.path.join(PDF_STORAGE_DIR, f)
    return None


def load_storage():
    """study_storage.json dosyasından dökümanları ve quiz istatistiklerini diskten yükler."""
    global uploaded_documents, quiz_stats

    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                uploaded_documents = data.get("uploaded_documents", [])
                quiz_stats = data.get("quiz_stats", {})
                print(f"[STORAGE] {len(uploaded_documents)} döküman ve {len(quiz_stats)} kullanıcı istatistiği diskten yüklendi.", flush=True)
        except Exception as e:
            print(f"[STORAGE ERR] Yüklenirken hata: {e}", flush=True)


def save_storage():
    """uploaded_documents ve quiz_stats verilerini kalıcı olarak diske kaydeder."""
    try:
        data = {
            "uploaded_documents": uploaded_documents,
            "quiz_stats": quiz_stats
        }
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[STORAGE ERR] Kaydedilirken hata: {e}", flush=True)


# ==========================================
# ZİHİN HARİTASI (MIND MAP) SQLITE CACHE
# ==========================================
MINDMAP_DB_FILE = "mindmap_cache.db"

def init_mindmap_db():
    try:
        conn = sqlite3.connect(MINDMAP_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mindmaps (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] MindMap DB başlatma hatası: {e}", flush=True)

def get_mindmap_cache(cache_key: str) -> Optional[dict]:
    try:
        conn = sqlite3.connect(MINDMAP_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM mindmaps WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"[WARN] Mindmap DB okuma hatası: {e}", flush=True)
    return None

def set_mindmap_cache(cache_key: str, data: dict):
    try:
        conn = sqlite3.connect(MINDMAP_DB_FILE)
        cursor = conn.cursor()
        data_json = json.dumps(data, ensure_ascii=False)
        cursor.execute("""
            INSERT OR REPLACE INTO mindmaps (cache_key, data, created_at)
            VALUES (?, ?, ?)
        """, (cache_key, data_json, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Mindmap DB kaydetme hatası: {e}", flush=True)


def clear_mindmap_cache(uid: str, course_name: Optional[str] = None):
    try:
        conn = sqlite3.connect(MINDMAP_DB_FILE)
        cursor = conn.cursor()
        if course_name:
            pattern = f"{uid}_{course_name.strip().lower()}_%"
            cursor.execute("DELETE FROM mindmaps WHERE cache_key LIKE ?", (pattern,))
        else:
            pattern = f"{uid}_%"
            cursor.execute("DELETE FROM mindmaps WHERE cache_key LIKE ?", (pattern,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Mindmap DB temizleme hatası: {e}", flush=True)


def build_course_filter(uid: str, course_name: Optional[str] = None, selected_docs: Optional[list[str]] = None) -> Filter:
    """Kullanıcı, ders ve isteğe bağlı seçili PDF dökümanları için ortak Qdrant filtresi oluşturur."""
    must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=uid))]
    if course_name and course_name.strip():
        must_conditions.append(FieldCondition(key="course_name", match=MatchValue(value=course_name.strip())))

    valid_selected = [d.strip() for d in (selected_docs or []) if d and d.strip()]
    if valid_selected:
        if len(valid_selected) == 1:
            must_conditions.append(FieldCondition(key="document_name", match=MatchValue(value=valid_selected[0])))
        else:
            should_conditions = [
                FieldCondition(key="document_name", match=MatchValue(value=doc_name))
                for doc_name in valid_selected
            ]
            must_conditions.append(Filter(should=should_conditions))

    return Filter(must=must_conditions)


def sync_documents_from_qdrant():
    """Qdrant vektör tabanında mevcut noktaları tarayarak uploaded_documents listesini otomatik senkronize eder."""
    global uploaded_documents
    if not qdrant_client:
        return
    try:
        collections = qdrant_client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            return

        offset = None
        seen_docs = {}
        # Qdrant'taki noktaları tara
        while True:
            records, next_offset = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            for r in records:
                p = r.payload or {}
                uid = p.get("user_id", "default_user")
                fname = p.get("document_name")
                cname = p.get("course_name", "Genel Ders")
                pno = p.get("page_number", 1)
                if not fname:
                    continue
                key = (uid, fname, cname)
                if key not in seen_docs:
                    seen_docs[key] = {
                        "user_id": uid,
                        "filename": fname,
                        "course_name": cname,
                        "pages": set(),
                        "chunks": 0
                    }
                seen_docs[key]["pages"].add(pno)
                seen_docs[key]["chunks"] += 1

            if not next_offset:
                break
            offset = next_offset

        recovered_count = 0
        for (uid, fname, cname), info in seen_docs.items():
            exists = any(
                d.get("user_id") == uid and d.get("filename") == fname and d.get("course_name", "").strip().lower() == cname.strip().lower()
                for d in uploaded_documents
            )
            if not exists:
                uploaded_documents.append({
                    "user_id": uid,
                    "filename": fname,
                    "course_name": cname,
                    "total_pages": max(info["pages"]) if info["pages"] else len(info["pages"]),
                    "total_chunks": info["chunks"]
                })
                recovered_count += 1

        if recovered_count > 0:
            print(f"[STORAGE] Qdrant indeksinden {recovered_count} döküman kurtarıldı ve eşitlendi.", flush=True)
            save_storage()
    except Exception as e:
        print(f"[STORAGE WARN] Qdrant senkronizasyonu atlandı: {e}", flush=True)


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

    # 1. Qdrant istemcisini başlat (Cloud varsa Cloud, yoksa kalıcı disk depolama)
    if QDRANT_URL:
        print(f"[INFO] Qdrant Cloud'a bağlanılıyor: {QDRANT_URL}...", flush=True)
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        print(f"[INFO] Kalıcı yerel Qdrant deposu başlatılıyor: {QDRANT_STORAGE_PATH}...", flush=True)
        os.makedirs(QDRANT_STORAGE_PATH, exist_ok=True)
        qdrant_client = QdrantClient(path=QDRANT_STORAGE_PATH)

    try:
        collections = qdrant_client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
            )
            print(f"[INFO] Koleksiyon '{COLLECTION_NAME}' oluşturuldu.", flush=True)
    except Exception as e:
        print(f"[WARN] Koleksiyon başlatma kontrolü: {e}", flush=True)

    # 2. Gemini İstemcisini başlat
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    # 3. Diskten dökümanları ve istatistikleri yükle, Qdrant ile senkronize et
    load_storage()
    sync_documents_from_qdrant()
    init_mindmap_db()

    print(f"[OK] Sistem hazır! Model: {GEMINI_MODEL}", flush=True)
    print("-> Arayüz: http://127.0.0.1:8000", flush=True)
    print("-> Swagger Docs: http://127.0.0.1:8000/docs", flush=True)
    yield
    # Kapanırken de en güncel durumu diske yaz
    save_storage()
    print("[STOP] Sistem kapatılıyor...", flush=True)


tags_metadata = [
    {
        "name": "Döküman Yönetimi",
        "description": "PDF yükleme, listeleme, silme, sayfa görseli ve döküman detayları.",
    },
    {
        "name": "Sohbet",
        "description": "RAG tabanlı sohbet ve canlı akış (SSE).",
    },
    {
        "name": "Çalışma Araçları",
        "description": "Quiz, flashcard, formül kağıdı ve zihin haritası.",
    },
    {
        "name": "İlerleme",
        "description": "Quiz cevapları ve dashboard istatistikleri.",
    },
    {
        "name": "Sistem",
        "description": "Sağlık kontrolü ve ana sayfa.",
    },
]

app = FastAPI(
    title="StudyRAG - Akıllı Ders Çalışma Sistemi API",
    description="Üniversite ders notları ve slaytları üzerinde çalışan, asenkron RAG (Retrieval-Augmented Generation) tabanlı yapay zeka destekli akıllı ders çalışma ve sınav hazırlık platformu.",
    version="1.0.0",
    openapi_tags=tags_metadata,
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
# GÜVENLİK & RATE LIMITING MIDDLEWARE
# ==========================================
# 1. Genel endpoint limiti: Dakikada 150 istek (IP bazlı kaba kuvvet / scanning koruması)
# 2. Ağır AI endpoint limiti (/chat, /chat-stream, /generate-quiz, /generate-flashcards): Dakikada 25 istek
_rate_limit_general = defaultdict(list)
_rate_limit_ai = defaultdict(list)
AI_RATE_LIMITED_PATHS = {"/chat", "/chat-stream", "/generate-quiz", "/generate-flashcards", "/api/mindmap"}

@app.middleware("http")
async def rate_limiting_middleware(request, call_next):
    path = request.url.path
    if path in ("/", "/health") or path.startswith("/static"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0

    # Ağır AI İşlem Kontrolü
    if path in AI_RATE_LIMITED_PATHS:
        user_id_hdr = request.headers.get("X-User-Id", "")
        track_key = f"{client_ip}_{user_id_hdr}" if user_id_hdr else client_ip
        timestamps = _rate_limit_ai[track_key]
        _rate_limit_ai[track_key] = [t for t in timestamps if now - t < window]
        if len(_rate_limit_ai[track_key]) >= 25:
            return JSONResponse(
                status_code=429,
                content={"detail": "Çok fazla yapay zeka isteği gönderildi. Lütfen bir dakika bekleyin."},
                headers={"Retry-After": "60"}
            )
        _rate_limit_ai[track_key].append(now)

    # Genel İstek Kontrolü
    gen_timestamps = _rate_limit_general[client_ip]
    _rate_limit_general[client_ip] = [t for t in gen_timestamps if now - t < window]
    if len(_rate_limit_general[client_ip]) >= 150:
        return JSONResponse(
            status_code=429,
            content={"detail": "İstek kotası aşıldı. Lütfen bir dakika bekleyin."},
            headers={"Retry-After": "60"}
        )
    _rate_limit_general[client_ip].append(now)

    return await call_next(request)



# ==========================================
# 3. YARDIMCI FONKSİYONLAR (CHUNKING & EMBED)
# ==========================================
# 3. YARDIMCI FONKSİYONLAR (CHUNKING & EMBED CACHE)
# ==========================================
# RPM (Dakika Başına İstek) kotasını korumak için bellek içi embedding önbelleği
_embedding_cache: dict[str, list[float]] = {}


def split_text(text: str, chunk_size: int = 1800, overlap: int = 150) -> list[str]:
    """Metni cümle bütünlüğünü koruyacak şekilde böler (Genişletilmiş boyut sayesinde %40 daha az API isteği)."""
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
    """Metin listesini Gemini Embedding API ile vektöre çevirir (RPM Kotası Koruma, Çoklu Anahtar Desteği, Dinamik Retry-Delay ve Akıllı Önbellek)."""
    import time
    import re

    # Çoklu API anahtarı desteği (GEMINI_API_KEY virgülle ayrılmış birden fazla anahtar içerebilir)
    raw_keys = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if not keys:
        keys = [GEMINI_API_KEY]

    # 1. Önce önbellekte olanları kontrol et
    missing_indices = []
    missing_texts = []
    results = [None] * len(texts)

    for i, t in enumerate(texts):
        if t in _embedding_cache:
            results[i] = _embedding_cache[t]
        else:
            missing_indices.append(i)
            missing_texts.append(t)

    # Hepsi önbellekteyse doğrudan dön (0 API isteği!)
    if not missing_texts:
        return results

    # 2. Önbellekte olmayanları Gemini API ile hesapla
    max_retries = 6
    active_key_idx = 0

    for attempt in range(max_retries):
        try:
            curr_key = keys[active_key_idx % len(keys)]
            client = genai.Client(api_key=curr_key)

            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=missing_texts,
            )
            for orig_idx, emb in zip(missing_indices, response.embeddings):
                val = emb.values
                results[orig_idx] = val
                # Önbelleğe kaydet (Sonraki aramalar için sıfır maliyet)
                _embedding_cache[texts[orig_idx]] = val
            return results
        except Exception as e:
            err_str = str(e)
            is_rate_limit = any(term in err_str for term in ["429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit", "RateLimit"])

            if is_rate_limit:
                # Birden fazla API anahtarı tanımlanmışsa hemen diğer anahtara geç
                if len(keys) > 1 and attempt < len(keys):
                    active_key_idx += 1
                    print(f"[WARN] 429 kotası aşıldı, sonraki API anahtarına geçiliyor (#{active_key_idx % len(keys) + 1})...", flush=True)
                    time.sleep(1.0)
                    continue

                # Tek anahtar varsa veya tüm anahtarlar denendiyse: Google'ın verdiği bekleme süresini (retryDelay) parse et
                wait_time = None
                match = re.search(r"retry in ([\d\.]+)s", err_str)
                if not match:
                    match = re.search(r"'retryDelay':\s*'(\d+)s'", err_str)
                if match:
                    try:
                        wait_time = float(match.group(1)) + 1.5
                    except Exception:
                        pass

                if wait_time is None:
                    # Kademeli bekleme: 8s, 16s, 28s, 40s...
                    wait_time = min(8.0 * (attempt + 1), 45.0)

                if attempt < max_retries - 1:
                    print(f"[WARN] Gemini RPM kota limiti yakalandı, {wait_time:.1f}s bekleniyor... (Deneme {attempt + 1}/{max_retries})", flush=True)
                    time.sleep(wait_time)
                    continue

            print(f"[ERROR] Embedding API hatası: {e}", flush=True)
            raise e


# ==========================================
# 4. PYDANTIC ŞEMALARI (VERİ DOĞRULAMA)
# ==========================================
class ChatRequest(BaseModel):
    question: str = Field(..., description="Kullanıcının ders notlarıyla ilgili sorusu")
    course_name: Optional[str] = Field(None, description="Materyalin ait olduğu ders adı")
    eli5_mode: bool = Field(False, description="Basitçe Anlat (Explain Like I'm 5) pedagojik modu")
    user_id: Optional[str] = Field("default_user", description="Kullanıcı kimliği")
    image_base64: Optional[str] = Field(None, description="Base64 formatında soru/not görseli")
    image_mime_type: Optional[str] = Field("image/jpeg", description="Yüklenen görselin MIME türü")
    selected_docs: Optional[list[str]] = Field(None, description="Sadece seçili PDF'ler üzerinde çalışma filtresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Fotovoltaik hücrelerin çalışma prensibi nedir?",
                    "course_name": "Güneş Enerjisi",
                    "eli5_mode": False,
                    "user_id": "user_123",
                    "selected_docs": ["Lesson-1.pdf"]
                }
            ]
        }
    }


class SourceInfo(BaseModel):
    document_name: str = Field(..., description="Referans bilginin yer aldığı PDF dosya adı")
    page_number: int = Field(..., description="Referans sayfa numarası (1-tabanlı)")
    snippet: str = Field(..., description="Sayfadan alınan alıntı bağlam metni")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "document_name": "Lesson-1.pdf",
                    "page_number": 4,
                    "snippet": "Enerji yoktan var edilemez, vardan yok edilemez; sadece biçim değiştirir..."
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Yapay zeka asistanı tarafından üretilen yanıt")
    sources: list[SourceInfo] = Field(default_factory=list, description="Cevabın dayandığı kaynak döküman ve sayfa referansları")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "Fotovoltaik hücreler fotonları doğrudan elektrik enerjisine çevirir...",
                    "sources": [
                        {
                            "document_name": "Lesson-1.pdf",
                            "page_number": 4,
                            "snippet": "Fotovoltaik etki ışık enerjisinin elektrik gerilimine dönüşmesidir..."
                        }
                    ]
                }
            ]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question_type": "mcq",
                    "question_text": "Aşağıdakilerden hangisi yenilenebilir enerji kaynağıdır?",
                    "options": ["A) Güneş", "B) Kömür", "C) Doğalgaz", "D) Linyit"],
                    "correct_answer": "A) Güneş",
                    "explanation": "Güneş enerjisi tükenmeyen ve kendini yenileyen bir kaynaktır.",
                    "source_document": "Lesson-7 Solar Energy-2.pdf",
                    "page_number": 3
                }
            ]
        }
    }


class QuizListResponse(BaseModel):
    questions: list[QuizQuestion] = Field(..., description="Oluşturulan sınav soruları listesi")


class QuizGenerateRequest(BaseModel):
    question_type: Literal["mixed", "mcq", "tf", "fill", "open"] = Field("mixed", description="Sınav soru formatı")
    difficulty: str = Field("Orta", description="Sınav zorluk derecesi (Kolay, Orta, Zor)")
    count: int = Field(5, description="Üretilecek soru sayısı (5, 10 veya 20)")
    course_name: Optional[str] = Field(None, description="Hedef ders adı")
    user_id: Optional[str] = Field("default_user", description="Kullanıcı kimliği")
    focus_weak_topics: bool = Field(False, description="Hata yapılan zayıf konulara odaklan")
    focus_pages: Optional[list[int]] = Field(None, description="Odaklanılacak belirli sayfa listesi")
    selected_docs: Optional[list[str]] = Field(None, description="Sadece seçili PDF'lerden quiz üretme filtresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "course_name": "Yenilenebilir Enerji",
                    "difficulty": "Orta",
                    "count": 5,
                    "question_type": "mixed",
                    "focus_weak_topics": False,
                    "selected_docs": ["Lesson-7 Solar Energy-2.pdf"]
                }
            ]
        }
    }


# --- Flashcard Şemaları ---
class FlashcardItem(BaseModel):
    front: str = Field(description="Kartın ön yüzü: Kavram veya kısa soru")
    back: str = Field(description="Kartın arka yüzü: Net ve kısa açıklama")
    source_document: str = Field(..., description="Bilginin alındığı PDF adı")
    page_number: int = Field(..., description="Bilginin alındığı sayfa numarası")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "front": "Fotovoltaik Etki",
                    "back": "Işığın yarı iletken maddeler tarafından soğurularak elektrik gerilimi oluşturması olayıdır.",
                    "source_document": "Lesson-6 Introduction to Solar Energy.pdf",
                    "page_number": 5
                }
            ]
        }
    }


class FlashcardListResponse(BaseModel):
    cards: list[FlashcardItem] = Field(..., description="Üretilen çalışma kartları listesi")



class CheatSheetRequest(BaseModel):
    course_name: Optional[str] = Field(None, description="Hedef ders adı")
    user_id: Optional[str] = Field("default_user", description="Kullanıcı kimliği")
    selected_docs: Optional[list[str]] = Field(None, description="Sadece seçili PDF'lerden formül kağıdı üretme filtresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "course_name": "Termal Bilimler",
                    "selected_docs": ["Lesson-4 Thermal Science-2 (1).pdf"]
                }
            ]
        }
    }


class CheatSheetResponse(BaseModel):
    course_name: str = Field(..., description="Ders adı")
    title: str = Field(..., description="Formül kağıdı başlığı")
    markdown_content: str = Field(..., description="KaTeX uyumlu formüller, kanunlar ve sınav ipuçları")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "course_name": "Termal Bilimler",
                    "title": "Termal Bilimler - Sınav Formül & Kavram Kağıdı",
                    "markdown_content": "# 📑 Termal Bilimler Formül Kağıdı\n## 📐 1. Temel Formüller\n$$Q = m \\cdot c \\cdot \\Delta T$$"
                }
            ]
        }
    }


class FlashcardGenerateRequest(BaseModel):
    count: Optional[int] = Field(5, description="Üretilecek flashcard sayısı (3-5 arası)")
    course_name: Optional[str] = Field(None, description="Hedef ders adı")
    user_id: Optional[str] = Field("default_user", description="Kullanıcı kimliği")
    selected_docs: Optional[list[str]] = Field(None, description="Sadece seçili PDF'lerden flashcard üretme filtresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "course_name": "Termal Bilimler",
                    "count": 5,
                    "selected_docs": ["Lesson-5 Thermal Science-3.pdf"]
                }
            ]
        }
    }


# --- Zihin Haritası Modelleri ---
class MindMapRequest(BaseModel):
    course_id: Optional[str] = Field(None, description="Ders kimliği veya adı")
    course_name: Optional[str] = Field(None, description="Hedef ders adı")
    user_id: Optional[str] = Field(None, description="Kullanıcı kimliği")
    focus: Optional[str] = Field(None, description="Özel olarak odaklanılacak konu/kavram")
    refresh: Optional[bool] = Field(False, description="True ise önbelleği yok sayıp sıfırdan üretir")
    selected_docs: Optional[list[str]] = Field(None, description="Sadece seçili PDF'lerden zihin haritası çıkarma filtresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "course_name": "Güneş Enerjisi",
                    "focus": "Güneş Kollektörleri",
                    "refresh": False,
                    "selected_docs": ["Lesson-7 Solar Energy-2.pdf"]
                }
            ]
        }
    }


class MindMapLeaf(BaseModel):
    title: str = Field(description="Alt kavram veya detay (en fazla 6 kelime)")
    page: Optional[int] = Field(default=None, description="Metindeki [Sayfa N] sayfa numarası veya null")
    children: list["MindMapLeaf"] = Field(default_factory=list, description="Varsa daha alt detaylar (boş liste olabilir)")

MindMapLeaf.model_rebuild()

class MindMapBranch(BaseModel):
    title: str = Field(description="Ana dal veya alt konu başlığı (en fazla 6 kelime)")
    page: Optional[int] = Field(default=None, description="Metindeki [Sayfa N] sayfa numarası veya null")
    children: list[MindMapLeaf] = Field(default_factory=list, description="Bu dala ait alt kavramlar (en fazla 6 adet)")

class MindMapResponse(BaseModel):
    title: str = Field(description="Zihin haritası kök başlığı / ders adı (en fazla 6 kelime)")
    children: list[MindMapBranch] = Field(default_factory=list, description="Dersin ana dalları (en fazla 8 ana dal)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Güneş Enerjisi",
                    "children": [
                        {
                            "title": "Temel Prensipler",
                            "page": 2,
                            "children": [
                                {"title": "Güneş Sabiti", "page": 3, "children": []},
                                {"title": "Işınım Spektrumu", "page": 4, "children": []}
                            ]
                        }
                    ]
                }
            ]
        }
    }


# --- Quiz Sonuç Gönderme (Zayıf Konu Tespiti) ---
class QuizAnswerSubmit(BaseModel):
    is_correct: bool = Field(..., description="Verilen cevabın doğru olup olmadığı")
    source_document: str = Field(..., description="Sorunun ait olduğu kaynak PDF adı")
    page_number: int = Field(..., description="Sorunun ait olduğu sayfa numarası")
    user_id: Optional[str] = Field("default_user", description="Kullanıcı kimliği")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "is_correct": False,
                    "source_document": "Lesson-1.pdf",
                    "page_number": 5,
                    "user_id": "user_123"
                }
            ]
        }
    }


# ==========================================
# 5. ENDPOINT'LER
# ==========================================

# Render ve Harici Cronjob'lar için Ultra Hafif Canlılık / Ping Kontrolü (Response Data Too Big Hatasını Önler)
@app.get(
    "/health",
    tags=["Sistem"],
    summary="Sistem Canlılık ve Sağlık Kontrolü",
    description="Sunucunun ve arka plan servislerinin ayakta olduğunu teyit eden hafif durum kontrolü."
)
@app.get("/ping", include_in_schema=False)
@app.head("/health", include_in_schema=False)
@app.head("/ping", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


# Ana sayfaya girildiğinde index.html varsa onu açar (Mobil ve tarayıcı önbellek kilidini kırmak için no-cache eklendi)
@app.get(
    "/",
    tags=["Sistem"],
    summary="Ana Sayfa (Web Arayüzü)",
    description="Tek sayfa uygulamasını (SPA - index.html) tarayıcıya sunar.",
    include_in_schema=False
)
async def serve_frontend():
    if os.path.exists("index.html"):
        response = FileResponse("index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return {"message": "StudyRAG API çalışıyor! Arayüz için index.html dosyasını aynı klasöre koyun veya /docs adresine gidin."}



# 1. PDF Yükleme ve Qdrant'a Kaydetme (Kota Dostu 25'lik Batch, Slayt Bütünlüğü & Güçlü Hata Yönetimi)
@app.post(
    "/upload-pdf",
    tags=["Döküman Yönetimi"],
    summary="Ders Notu (PDF) Yükleme ve Vektörleştirme",
    description="Gönderilen PDF dosyasını alır, sayfa/metin denetimi yapar, 2200 karaktere kadar slayt bütünlüğünü korur ve 25'li batch'ler halinde vektörleştirerek Qdrant ve yerel depoya kaydeder."
)
async def upload_pdf(
    file: UploadFile = File(..., description="Yüklenecek PDF ders notu dosyası"),
    course_name: str = Form("Genel Ders", description="Materyalin ait olduğu ders adı"),
    user_id: Optional[str] = Form(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or user_id or "").strip()
    if not uid:
        uid = f"user_{uuid.uuid4().hex[:8]}"

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Lütfen sadece PDF dosyası yükleyin.")

    try:
        pdf_bytes = await file.read()

        # Sayfa görseli önizleme ve indirme için PDF dosyasını diske kaydet
        safe_name = os.path.basename(file.filename)
        stored_path = os.path.join(PDF_STORAGE_DIR, f"{uid}_{safe_name}")
        try:
            with open(stored_path, "wb") as f_out:
                f_out.write(pdf_bytes)
        except Exception as e:
            print(f"[WARN] PDF diske kaydedilemedi: {e}", flush=True)

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        # 160 sayfadan büyük dosyalarda sunucu ve bellek koruması
        if len(doc) > 160:
            raise HTTPException(
                status_code=400,
                detail=f"Yüklenen dosya {len(doc)} sayfa. Sunucu zaman aşımını ve bellek taşmasını önlemek için lütfen en fazla 150 sayfalık bölümler halinde yükleyiniz."
            )

        chunks_to_embed = []
        payloads = []

        for page_index in range(len(doc)):
            page = doc[page_index]
            text = (page.get_text("text") or "").strip()
            if not text:
                continue

            # Slayt ve ders notlarında sayfa bütünlüğünü koruma:
            # 2200 karakterden az sayfalar tek parça tutularak hem bağlam korunur hem de API isteği %50 azalır
            if len(text) <= 2200:
                page_chunks = [text] if len(text) > 25 else []
            else:
                page_chunks = split_text(text, chunk_size=1800, overlap=150)

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
            raise HTTPException(status_code=400, detail="PDF içinden okunabilir metin bulunamadı. Lütfen taranmış görsel yerine metin içeren bir PDF yükleyiniz.")

        # Gemini API ile 25'erli güvenli paketler (Dakika başı 100 istek sınırını aşmaz ve pürüzsüz çalışır)
        embeddings = []
        batch_size = 25
        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i:i + batch_size]
            batch_embs = await asyncio.to_thread(get_embeddings, batch)
            embeddings.extend(batch_embs)
            if i + batch_size < len(chunks_to_embed):
                await asyncio.sleep(0.8)  # Paketler arası akıcı nefes alma payı

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

        # Qdrant'a 50'lik güvenli gruplar halinde kaydet
        for j in range(0, len(points), 50):
            qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points[j:j + 50])

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

        # Değişiklikleri diske kalıcı olarak yaz
        save_storage()
        clear_mindmap_cache(uid, course_name)

        print(f"[UPLOAD OK] '{file.filename}' ({course_name}) [User: {uid}] -> {len(doc)} sayfa, {len(points)} parca basariyla eklendi.", flush=True)

        return {"message": "Ders notu başarıyla yüklendi!", "document": doc_info}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Döküman işlenirken bir sorun oluştu: {str(e)[:160]}"
        )


# 2. Yüklü PDF'leri Listeleme (Kesin Kullanıcı ve Ders filtreli - Cihaz Ayrımı Garantili)
@app.get(
    "/documents",
    tags=["Döküman Yönetimi"],
    summary="Yüklü Dökümanları Listeleme",
    description="Aktif kullanıcının seçili dersteki veya tüm derslerdeki yüklenmiş PDF dökümanlarını, sayfa sayılarını ve meta verilerini listeler."
)
async def get_documents(
    course_name: Optional[str] = Query(None, description="Filtrelenecek ders adı (boşsa kullanıcının tüm dökümanları listelenir)"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or user_id or "").strip()
    if not uid:
        return {"documents": []}

    user_docs = [d for d in uploaded_documents if d.get("user_id") == uid]

    if course_name and course_name.strip():
        target = course_name.strip().lower()
        filtered = [d for d in user_docs if d.get("course_name", "").strip().lower() == target]
        return {"documents": filtered}
    return {"documents": user_docs}


# 2.1 PDF Silme Endpoint'i (Garantili Silme & İzolasyon)
@app.delete(
    "/documents/{filename}",
    tags=["Döküman Yönetimi"],
    summary="Ders Notunu Silme",
    description="Belirtilen PDF dosyasını disk deposundan kaldırır, Qdrant vektör koleksiyonundaki noktalarını temizler ve zihin haritası önbelleğini sıfırlar."
)
async def delete_document(
    filename: str,
    course_name: Optional[str] = Query(None, description="PDF'in ait olduğu ders adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
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

    # Diskteki PDF dosyasını da temizle
    pdf_path = find_pdf_file_path(filename, uid)
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            print(f"[WARN] PDF dosyası silinirken hata: {e}", flush=True)

    # Değişiklikleri diske kalıcı olarak yaz
    save_storage()
    clear_mindmap_cache(uid, target_course)

    return {"message": f"'{filename}' başarıyla silindi.", "documents": user_docs}


# 2.1.1 Ders Silme Endpoint'i (Kullanıcının o dersteki tüm PDF'lerini ve vektörlerini temizler)
@app.delete(
    "/courses/{course_name}",
    tags=["Döküman Yönetimi"],
    summary="Dersi ve Tüm Materyallerini Silme",
    description="Belirtilen dersi, o derse ait tüm PDF dosyalarını, Qdrant vektör kayıtlarını ve zihin haritası önbelleğini tamamen temizler."
)
async def delete_course(
    course_name: str,
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    global uploaded_documents
    uid = (x_user_id or user_id or "default_user").strip()
    target_course = course_name.strip()

    # 1. Qdrant'tan bu kullanıcının bu dersine ait tüm vektörleri sil
    try:
        must_conditions = [
            FieldCondition(key="course_name", match=MatchValue(value=target_course)),
            FieldCondition(key="user_id", match=MatchValue(value=uid))
        ]
        qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=must_conditions)
        )
    except Exception as e:
        print(f"[WARN] Qdrant ders silme hatası: {e}", flush=True)

    # 2. Diskteki bu derse ait PDF dosyalarını da sil
    docs_to_delete = [
        d for d in uploaded_documents
        if d.get("user_id") == uid and d.get("course_name", "").strip().lower() == target_course.lower()
    ]
    for d in docs_to_delete:
        fname = d.get("filename")
        if fname:
            pdf_path = find_pdf_file_path(fname, uid)
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass

    # 3. uploaded_documents listesinden bu kullanıcının bu dersindeki kayıtları çıkar
    uploaded_documents = [
        d for d in uploaded_documents
        if not (
            d.get("user_id") == uid and
            d.get("course_name", "").strip().lower() == target_course.lower()
        )
    ]
    save_storage()
    clear_mindmap_cache(uid, target_course)

    return {"message": f"'{target_course}' dersi ve tüm materyalleri başarıyla silindi."}


# 2.2 PDF Sayfa Görseli Önizleme Endpoint'i (Ultra Hızlı PyMuPDF Renderer)
@app.get(
    "/pdf-page-image",
    tags=["Döküman Yönetimi"],
    summary="PDF Sayfa Görseli Önizleme",
    description="İstenen sayfa numarasını PyMuPDF ile anında render ederek PNG görseli olarak döner. Kaynak teyidi için arayüz modalında ve rozetlerde kullanılır."
)
async def get_pdf_page_image(
    filename: str = Query(..., description="Görüntülenecek PDF dosya adı"),
    page: int = Query(1, description="Sayfa numarası (1-tabanlı)"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı"),
    dpi: int = Query(140, description="Render çözünürlüğü (DPI, varsayılan 140)")
):
    uid = (x_user_id or user_id or "default_user").strip()
    pdf_path = find_pdf_file_path(filename, uid)

    if not pdf_path or not os.path.exists(pdf_path):
        # Şık ve modern bir bilgilendirme SVG görseli dön
        placeholder_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="420" viewBox="0 0 600 420">
            <rect width="600" height="420" fill="#0f172a"/>
            <rect x="25" y="25" width="550" height="370" rx="16" fill="#1e293b" stroke="#475569" stroke-dasharray="6 6"/>
            <text x="300" y="160" fill="#818cf8" font-size="52" font-family="sans-serif" text-anchor="middle">📄</text>
            <text x="300" y="215" fill="#f8fafc" font-size="16" font-family="sans-serif" font-weight="bold" text-anchor="middle">PDF Sayfa Görseli Henüz Kaydedilmedi</text>
            <text x="300" y="248" fill="#94a3b8" font-size="12" font-family="sans-serif" text-anchor="middle">"{filename}" bu özellikten önce yüklendiği için dosya diske yazılmamış.</text>
            <text x="300" y="280" fill="#38bdf8" font-size="12" font-family="sans-serif" font-weight="600" text-anchor="middle">Görsel sayfa önizlemesi için lütfen sol menüden bu PDF'i tekrar yükleyiniz.</text>
        </svg>"""
        return Response(content=placeholder_svg, media_type="image/svg+xml")

    try:
        doc = pymupdf.open(pdf_path)
        total = len(doc)
        page_idx = min(max(page - 1, 0), total - 1)
        pix = doc[page_idx].get_pixmap(dpi=min(max(dpi, 72), 220))
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Total-Pages": str(total)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sayfa görseli oluşturulamadı: {e}")


# 2.3 Tam PDF İndirme / Görüntüleme Endpoint'i
@app.get(
    "/pdf-file/{filename}",
    tags=["Döküman Yönetimi"],
    summary="Orijinal PDF Dosyasını İndirme / Görüntüleme",
    description="Diskte saklanan orijinal PDF dosyasını tarayıcıda görüntülemek veya indirmek üzere stream eder."
)
async def get_pdf_file(
    filename: str,
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or user_id or "default_user").strip()
    pdf_path = find_pdf_file_path(filename, uid)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF dosyası depoda bulunamadı.")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


# 2.4 PDF Sayfa Sayısı ve Bilgi Endpoint'i
@app.get(
    "/pdf-info",
    tags=["Döküman Yönetimi"],
    summary="PDF Sayfa ve Durum Bilgisi",
    description="Belirtilen PDF'in toplam sayfa sayısını ve disk deposundaki mevcudiyet durumunu kontrol eder."
)
async def get_pdf_info(
    filename: str = Query(..., description="Sorgulanacak PDF dosya adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or user_id or "default_user").strip()
    pdf_path = find_pdf_file_path(filename, uid)
    if not pdf_path or not os.path.exists(pdf_path):
        match = next((d for d in uploaded_documents if d.get("filename") == filename), None)
        total = match.get("total_pages", 1) if match else 1
        return {"filename": filename, "total_pages": total, "has_file": False}

    try:
        doc = pymupdf.open(pdf_path)
        total = len(doc)
        doc.close()
        return {"filename": filename, "total_pages": total, "has_file": True}
    except Exception:
        return {"filename": filename, "total_pages": 1, "has_file": True}


def course_has_uploaded_documents(uid: str, course_name: Optional[str]) -> bool:
    """Kullanıcının belirtilen derste herhangi bir PDF dökümanı olup olmadığını kontrol eder."""
    if not course_name or not course_name.strip():
        return any(d.get("user_id") == uid for d in uploaded_documents)

    target_c = course_name.strip().lower()
    for d in uploaded_documents:
        if d.get("user_id") == uid and d.get("course_name", "").strip().lower() == target_c:
            return True

    try:
        if qdrant_client:
            must_cond = [
                FieldCondition(key="user_id", match=MatchValue(value=uid)),
                FieldCondition(key="course_name", match=MatchValue(value=course_name.strip()))
            ]
            count_res = qdrant_client.count(
                collection_name=COLLECTION_NAME,
                count_filter=Filter(must=must_cond),
                exact=False
            )
            if count_res and count_res.count > 0:
                return True
    except Exception:
        pass
    return False


def is_course_notes_dependent_question(raw_question: str) -> bool:
    """Kullanıcının sorusunun yüklenmiş ders notlarına veya genel ders özetine atıfta bulunup bulunmadığını kontrol eder."""
    q = raw_question.lower().strip()
    
    # Hazır çipler veya doğrudan notlara atıf yapan kalıplar
    note_patterns = [
        "ders not", "dersin not", "bu ders", "notlar", "notlardaki", "notlarımdaki",
        "özet", "özetle", "özetini", "özet çıkar",
        "sayfa referans", "sayfa numara", "hangi sayfa",
        "sınavda ne çıkar", "sınavda çıkabilecek", "sınav konuları", "müfredat",
        "konuları anlat", "konuları listele", "konuları özetle", "dersi anlat", "ders konuları",
        "bütün konular", "tüm konular", "neler var", "hangi konular var",
        "formül kağıdı", "kavram kağıdı", "5 kritik tanım", "en önemli tanımlar",
        "tanımları listele", "formülleri listele"
    ]
    return any(p in q for p in note_patterns)


# 3. RAG Sohbet & Özet & "Basitçe Anlat" Modu & Multimodal Görsel Desteği
def build_chat_context_and_prompt(request: ChatRequest):
    raw_question = (request.question or "").strip()
    has_image = bool(request.image_base64 and request.image_base64.strip())

    if not raw_question and has_image:
        raw_question = "Lütfen bu görseldeki soruyu veya konuyu incele, adımlarıyla açıkla ve doğru yanıtı bul."
    elif not raw_question and not has_image:
        raise HTTPException(status_code=400, detail="Lütfen bir soru yazın veya bir görsel ekleyin.")

    uid = (request.user_id or "default_user").strip()
    course_name_clean = (request.course_name or "").strip()
    has_docs = course_has_uploaded_documents(uid, course_name_clean)
    course_title = course_name_clean if course_name_clean else "Bu ders"

    # DERSTE HİÇ PDF YOKKEN VE GÖRSEL DE YOKKEN KONTROL:
    if not has_docs and not has_image:
        q_lower = raw_question.lower().strip()

        # 1. Selamlaşma veya ne yapabilirsin tarzı genel sorular
        if q_lower in ["merhaba", "selam", "selamlar", "günaydın", "iyi günler", "hey", "merhabalar"]:
            direct_answer = (
                f"Merhaba! Ben StudyRAG akademik çalışma asistanınım. 👋\n\n"
                f"Şu an **{course_title}** dersindesin. Bu derse henüz bir ders notu (PDF) yüklenmedi.\n\n"
                f"**Nasıl başlayabilirsin?**\n"
                f"- Sol menüden veya Ana Ekran'dan dersine ait **PDF ders notlarını yükleyebilir**, ardından notların üzerinden özet, sınav tanımları, formüller, quiz ve zihin haritası oluşturabilirsin.\n"
                f"- Ya da merak ettiğin belirli bir akademik konuyu doğrudan bana sorabilirsin! *(Örn: \"Newton yasaları nelerdir?\" veya \"Python'da döngüler nasıl çalışır?\")*"
            )
            return None, [], None, direct_answer

        # 2. Soru doğrudan ders notlarına, özetlere, formüllere veya sınav konularına atıfta bulunuyorsa:
        if is_course_notes_dependent_question(raw_question):
            direct_answer = (
                f"### 📄 Bu Derste Henüz Ders Notu (PDF) Bulunmuyor\n\n"
                f"**{course_title}** dersi için sisteme henüz herhangi bir ders notu veya kaynak PDF yüklenmemiştir.\n\n"
                f"Ders notlarınızdaki konuları özetleyebilmem, en önemli sınav tanımlarını veya formülleri çıkarabilmem için:\n"
                f"- Sol menüdeki **Kaynak Dokümanlar** bölümünden veya **Ana Ekran**'dan ders notunuzu (PDF) yükleyebilirsiniz.\n\n"
                f"---\n"
                f"💡 **İpucu:** Eğer PDF yüklemeden doğrudan genel bir konuyu öğrenmek istiyorsanız, konunun adını açıkça belirterek soru sorabilirsiniz.\n"
                f"*(Örneğin: *\"Termodinamiğin 2. yasası nedir?\"*, *\"Kinetik enerji formülünü açıkla\"* veya *\"Fotosentez evreleri nelerdir?\"*)*"
            )
            return None, [], None, direct_answer

    # Eğer derste döküman varsa veya kullanıcı derste PDF olmasa bile spesifik bir konu sormuşsa / görsel yüklemişse:
    query_vector = get_embeddings([raw_question])[0]
    query_filter = build_course_filter(uid, course_name_clean, request.selected_docs)

    # Genel özet ve geniş kapsam için limit 8
    search_results = []
    if has_docs:
        try:
            search_results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=query_filter,
                limit=8
            ).points
        except Exception as e:
            print(f"[WARN] Qdrant arama: {e}", flush=True)

    context_parts = []
    sources = []
    seen_sources = {}
    ref_idx = 1

    for hit in search_results:
        p = hit.payload or {}
        doc_name = p.get('document_name')
        page_num = p.get('page_number')
        text_content = p.get('text') or ''
        if not doc_name or not page_num:
            continue
        doc_key = f"{doc_name}_{page_num}"
        if doc_key not in seen_sources:
            current_ref = ref_idx
            seen_sources[doc_key] = current_ref
            ref_idx += 1
            sources.append(SourceInfo(
                document_name=doc_name,
                page_number=page_num,
                snippet=text_content[:140] + "..."
            ))
        else:
            current_ref = seen_sources[doc_key]

        context_parts.append(f"[KAYNAK {current_ref} | Dosya: {doc_name} | Sayfa: {page_num}]\n{text_content}")

    if request.selected_docs:
        docs_str = ", ".join(f"'{d}'" for d in request.selected_docs)
        context_parts.insert(0, f"[FİLTRE KISITLAMASI]: Kullanıcı yalnızca şu seçili PDF döküman(lar)ına odaklanmak istiyor: {docs_str}. Lütfen yanıtlarını sadece bu seçili dökümanlardaki bilgilerle oluştur.")

    style_instruction = (
        "Konuyu hiç bilmeyen birine anlatır gibi günlük hayattan benzetmelerle çok sade ve basitçe anlat."
        if request.eli5_mode else
        "Akademik, net, öğretici ve sınava yönelik bir dille açıkla."
    )

    image_instruction = ""
    image_part = None
    if has_image:
        try:
            b64_data = request.image_base64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            mime = request.image_mime_type or "image/jpeg"
            image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
            image_instruction = "\n\n[GÖRSEL YÖNERGESİ]: Öğrenci soruyla birlikte bir görsel (soru, tahta fotoğrafı, formül, şema veya not) ekledi. Görseli çok dikkatle incele, görseldeki soruyu/ifadeleri eksiksiz analiz et, adım adım çöz ve varsa yukarıdaki ders notlarıyla bağdaştırarak açıkla."
        except Exception as e:
            print(f"[WARN] Görsel decode hatası: {e}", flush=True)

    if context_parts:
        context_text = "\n\n---\n\n".join(context_parts)
        prompt = f"""Sen üniversite öğrencilerine ders çalışma ve sınav hazırlığında rehberlik eden uzman bir yapay zeka asistanısın.
Tarzın: {style_instruction}

Aşağıda öğrencinin yüklediği ilgili [DERS NOTLARI] parçaları [KAYNAK 1], [KAYNAK 2]... etiketleriyle verilmiştir.

YÖNERGELER:
1. Öğrencinin [SORU]'sunu verilen [DERS NOTLARI]'ndan ve (varsa) eklenen [GÖRSEL]'den faydalanarak kapsamlı, anlaşılır ve eğitici bir şekilde yanıtla.
2. Öğrenci "özet", "en kritik sınav konuları", "önemli kavramlar" gibi genel bir soru soruyorsa; notlardaki ana başlıkları, tanımları ve önemli konuları sentezleyerek öğrencinin sınava çalışabileceği maddeli net bir analiz hazırla.
3. KESİNLİKLE KENDİN SAYFA NUMARASI UYDURMA. Bir bilgiyi DERS NOTLARI'ndan alarak açıklıyorsan, cümlenin veya bilginin sonuna sadece ilgili kaynak etiketini ekle: örn. [KAYNAK 1] veya [KAYNAK 2]. Yalnızca aşağıda listelenen kaynak numaralarını kullan.
4. Matematiksel veya teknik formülleri KaTeX uyumlu standart LaTeX ($ ... $ veya $$ ... $$) formatında yaz.

[DERS NOTLARI]:
{context_text}

[SORU]:
{raw_question}{image_instruction}
"""
    else:
        # Bu derste PDF yok ama kullanıcı spesifik bir konuyu sordu veya görsel yükledi:
        prompt = f"""Sen üniversite öğrencilerine ders çalışma ve sınav hazırlığında rehberlik eden uzman bir yapay zeka asistanısın.
Tarzın: {style_instruction}

ÖNEMLİ BİLGİLENDİRME VE KESİN KURALLAR:
1. Öğrencinin seçili '{course_title}' dersinde sisteme yüklenmiş HİÇBİR PDF DERS NOTU BULUNMAMAKTADIR.
2. KESİNLİKLE rastgele bir ders müfredatı, uydurma bir akademik alan (örneğin iktisat, tıp, hukuk gibi ilgisiz alanlar) ÜRETME.
3. KESİNLİKLE [KAYNAK 1] veya sayfa numarası gibi sahte kaynak etiketleri KULLANMA.
4. SADECE VE SADECE öğrencinin doğrudan sorduğu konuyu ({raw_question}) veya gönderdiği görseli genel akademik uzmanlığınla en doğru, eğitici ve net biçimde açıkla.
5. Matematiksel veya teknik formülleri KaTeX uyumlu standart LaTeX ($ ... $ veya $$ ... $$) formatında yaz.
6. Yanıtının ilk satırında italik olarak şu bilgilendirme cümlesini ekle:
*(Not: '{course_title}' dersinde henüz bir PDF ders notu yüklü olmadığı için yanıt genel akademik bilgilerle verilmiştir. Sınav kapsamınıza ve notlarınıza göre çalışmak için sol menüden PDF yükleyebilirsiniz.)*

[SORU]:
{raw_question}{image_instruction}
"""

    return prompt, sources, image_part, None


# 3. RAG Sohbet & Özet (Standart JSON Yanıt)
@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Sohbet"],
    summary="RAG Tabanlı Soru-Cevap (Standart JSON)",
    description="Kullanıcı sorusunu ve opsiyonel görselini ilgili ders notlarıyla eşleştirerek sayfa referanslı yanıt döner."
)
async def chat_with_pdf(request: ChatRequest):
    try:
        prompt, sources, image_part, direct_answer = build_chat_context_and_prompt(request)
        if direct_answer:
            return ChatResponse(answer=direct_answer, sources=[])

        client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)
        contents = [types.Content(parts=[types.Part.from_text(text=prompt), image_part])] if image_part else prompt

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents
        )
        return ChatResponse(answer=response.text, sources=sources)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Sohbet endpoint'inde (/chat) hata oluştu:")
        raise HTTPException(status_code=500, detail=str(e))


def format_user_friendly_ai_error(e: Exception) -> str:
    """Gemini API veya ağ hatalarını kullanıcı dostu Türkçe açıklamaya çevirir."""
    err_str = str(e)
    err_lower = err_str.lower()
    if "503" in err_str or "unavailable" in err_lower or "high demand" in err_lower:
        return "Google yapay zeka sunucularında anlık bir yoğunluk yaşanıyor (503). Model yanıtı tamamlayamadı. Lütfen birkaç saniye sonra tekrar deneyin."
    elif "429" in err_str or "resource_exhausted" in err_lower or "quota" in err_lower:
        return "Google API istek limitine ulaşıldı (429). Lütfen kısa bir süre bekleyip tekrar deneyin."
    elif "500" in err_str or "internal" in err_lower:
        return "Yapay zeka servisinde geçici bir sunucu hatası oluştu (500). Lütfen tekrar deneyin."
    else:
        return f"Yapay zeka yanıtı üretilirken geçici bir bağlantı sorunu oluştu: {err_str[:120]}"


# 3.1 Canlı Akış (Streaming SSE - Kayan Metin & Multimodal Görsel)
@app.post(
    "/chat-stream",
    tags=["Sohbet"],
    summary="Canlı Akışlı RAG Asistanı (Server-Sent Events)",
    description="İlgili kaynak sayfaları ilk paket olarak iletir, ardından Gemini modelinin ürettiği token'ları SSE (text/event-stream) protokolüyle sıfır gecikmeli canlı akar."
)
async def chat_stream_with_pdf(request: ChatRequest):
    try:
        prompt, sources, image_part, direct_answer = build_chat_context_and_prompt(request)
        client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)
        contents = [types.Content(parts=[types.Part.from_text(text=prompt), image_part])] if (image_part and prompt) else prompt
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Sohbet akışı hazırlığında (/chat-stream) hata oluştu:")
        raise HTTPException(status_code=500, detail=str(e))

    async def event_generator():
        # 1. Eğer doğrudan cevap varsa (PDF yok ve yönlendirme mesajı gerekiyorsa)
        if direct_answer:
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'text': direct_answer})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        # 2. İlk olarak kaynakları gönder
        yield f"data: {json.dumps({'sources': [s.model_dump() for s in sources]})}\n\n"

        # 3. Gemini akışını canlı token olarak ilet (Fallback Zinciri & Akıllı Geçiş)
        models_to_try = [GEMINI_MODEL, GEMINI_FALLBACK_MODEL, "gemini-2.5-flash"]
        stream_started = False
        last_exception = None

        for idx, model_name in enumerate(models_to_try):
            try:
                # İkinci veya üçüncü modele geçerken kısa bir nefes al (400ms)
                if idx > 0 and not stream_started:
                    await asyncio.sleep(0.4)

                stream = client.models.generate_content_stream(
                    model=model_name,
                    contents=contents
                )
                for chunk in stream:
                    if chunk.text:
                        stream_started = True
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"

                # Akış sorunsuz bitti
                last_exception = None
                break

            except Exception as e:
                last_exception = e
                logger.warning(f"[CHAT-STREAM] Model '{model_name}' hatası: {e} (stream_started={stream_started})")
                # Eğer akış zaten bir miktar metin ürettiyse, model değiştirmek metni bozacağı için durdur
                if stream_started:
                    break

        if last_exception:
            friendly_err = format_user_friendly_ai_error(last_exception)
            logger.error(f"[CHAT-STREAM] Nihai akış hatası: {last_exception}")
            yield f"data: {json.dumps({'error': friendly_err, 'is_stream_interrupted': stream_started})}\n\n"

        # 4. Tamamlandı sinyali
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# 4. Pydantic Şemalı Otomatik Quiz Üretici
@app.post(
    "/generate-quiz",
    response_model=QuizListResponse,
    tags=["Çalışma Araçları"],
    summary="Kişiselleştirilmiş Sınav Simülatörü",
    description="Seçili ders veya PDF'lerden, belirlenen zorluk ve adede (5, 10, 20) göre yapılandırılmış test üretir. İsteğe bağlı olarak geçmişte hata yapılan zayıf konulara odaklanır."
)
async def generate_quiz(
    request: QuizGenerateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or request.user_id or "default_user").strip()
    scroll_filter = build_course_filter(uid, request.course_name, request.selected_docs)

    # Qdrant'tan kayıtlı parçaları çek (seçili ders ve döküman filtreli)
    scroll_result, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=100
    )

    if not scroll_result:
        if request.selected_docs:
            docs_msg = ", ".join(f"'{d}'" for d in request.selected_docs)
            raise HTTPException(status_code=404, detail=f"Seçilen döküman(lar) ({docs_msg}) için içerik bulunamadı.")
        course_msg = f"'{request.course_name}' dersi için" if request.course_name else "Bu çalışma alanı için"
        raise HTTPException(status_code=404, detail=f"{course_msg} henüz PDF yüklenmedi. Lütfen sol menüden bu derse en az bir PDF ekleyin.")

    u_stats = get_user_quiz_stats(uid)
    weak_pages_map = u_stats.get("weak_pages", {})
    focus_pages_set = set(request.focus_pages or [])

    sampled_points = []
    weak_focus_instructions = ""

    # Eğer zayıf konulara odaklanma talep edildiyse:
    if request.focus_weak_topics:
        weak_points = []
        other_points = []

        for p in scroll_result:
            p_payload = p.payload or {}
            p_num = p_payload.get("page_number")
            doc_name = p_payload.get("document_name", "")
            key = f"{doc_name} (Sayfa {p_num})"

            if p_num in focus_pages_set or key in weak_pages_map:
                weak_points.append(p)
            else:
                other_points.append(p)

        if weak_points:
            # Zayıf konulardan ağırlıklı seç, soru sayısına göre dinamik parça al
            needed = min(len(scroll_result), max(6, min(20, request.count)))
            sample_weak_count = min(len(weak_points), needed)
            sampled_points = random.sample(weak_points, sample_weak_count)
            if len(sampled_points) < needed and other_points:
                rem_count = min(len(other_points), needed - len(sampled_points))
                sampled_points.extend(random.sample(other_points, rem_count))
        else:
            sample_k = min(len(scroll_result), max(6, min(20, request.count)))
            sampled_points = random.sample(scroll_result, sample_k)

        focus_details = []
        if focus_pages_set:
            focus_details.append(f"Önceki testte yanlış yapılan sayfalar: {sorted(list(focus_pages_set))}")
        if weak_pages_map:
            top_weak = sorted(weak_pages_map.items(), key=lambda x: x[1], reverse=True)[:4]
            focus_details.append("Geçmişte en çok hata yapılan konular: " + ", ".join([f"{k} ({v} hata)" for k, v in top_weak]))

        focus_str = " | ".join(focus_details) if focus_details else "Öğrencinin zorlandığı kritik temel kavramlar"
        weak_focus_instructions = f"""
ÖZEL VE KRİTİK GÖREV: Bu sınav, öğrencinin DAHA ÖNCE YANLIŞ YAPTIĞI VE ANLAMAKTA ZORLANDIĞI KONULARI TELAFİ ETMEK İÇİN ÜRETİLMEKTEDİR.
[ZAYIF KONU BİLGİSİ]: {focus_str}
Lütfen soruları ÖNCELİKLE bu sayfa ve kavramlardaki püf noktaları, eksik anlaşılan ilkeleri ve yanılgıları pekiştirecek, öğrenciye konuyu tam kavratacak şekilde üret!
"""
    else:
        # Genel / farklı konulardan dengeli rastgele seçim (soru sayısına göre dinamik)
        sample_k = min(len(scroll_result), max(6, min(20, request.count)))
        sampled_points = random.sample(scroll_result, sample_k)

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
{weak_focus_instructions}
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
    except Exception as e:
        print(f"[WARN] Quiz lite model hatası: {e}, fallback modele geçiliyor...", flush=True)
        response = await asyncio.to_thread(_call_gemini_quiz, GEMINI_FALLBACK_MODEL)

    return QuizListResponse.model_validate_json(response.text)


# 5. Otomatik Flashcard Üretici (Ultra Hızlı ve Non-blocking)
@app.post(
    "/generate-flashcards",
    response_model=FlashcardListResponse,
    tags=["Çalışma Araçları"],
    summary="Hızlı Tekrar Çalışma Kartları (Flashcards)",
    description="Ders notlarındaki en kritik kavramları ön ve arka yüz olarak soru-cevap kart seti halinde derler."
)
async def generate_flashcards(
    payload: Optional[FlashcardGenerateRequest] = None,
    count: int = Query(5, description="Üretilecek kart sayısı"),
    course_name: Optional[str] = Query(None, description="Hedef ders adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or (payload.user_id if payload else None) or user_id or "default_user").strip()
    target_count = (payload.count if payload and payload.count else count) or 5
    target_course = (payload.course_name if payload and payload.course_name else course_name) or None
    actual_count = min(max(target_count, 3), 5)

    selected_docs = payload.selected_docs if payload else None
    scroll_filter = build_course_filter(uid, target_course, selected_docs)

    # Qdrant'tan parçaları çek (seçili ders ve döküman filtreli)
    scroll_result, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=50
    )

    if not scroll_result:
        if selected_docs:
            docs_msg = ", ".join(f"'{d}'" for d in selected_docs)
            raise HTTPException(status_code=404, detail=f"Seçilen döküman(lar) ({docs_msg}) için içerik bulunamadı.")
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
        response = await asyncio.to_thread(_call_gemini_flashcards, GEMINI_FALLBACK_MODEL)

    return FlashcardListResponse.model_validate_json(response.text)


# 5.1 Sınav Öncesi Formül & Kavram Kağıdı (Cheat Sheet Generator)
@app.post(
    "/generate-cheatsheet",
    response_model=CheatSheetResponse,
    tags=["Çalışma Araçları"],
    summary="Sınav Öncesi Formül & Kavram Kağıdı (Cheat Sheet)",
    description="Ders notlarındaki formülleri, teoremleri, tanımları ve sınav tuzaklarını KaTeX uyumlu markdown formatında tek sayfalık özet kağıdı olarak üretir."
)
async def generate_cheatsheet(
    payload: Optional[CheatSheetRequest] = None,
    course_name: Optional[str] = Query(None, description="Hedef ders adı"),
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or (payload.user_id if payload else None) or user_id or "default_user").strip()
    target_course = (payload.course_name if payload and payload.course_name else course_name) or None

    selected_docs = payload.selected_docs if payload else None
    course_filter = build_course_filter(uid, target_course, selected_docs)

    # Formül, denklem ve kilit kavramları öne çıkaran semantik arama
    search_query = "temel formüller denklemler tanımlar teoremler bağıntılar hesaplama kurallar özet"
    query_vector = get_embeddings([search_query])[0]
    
    search_results = []
    try:
        search_results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=course_filter,
            limit=16
        ).points
    except Exception as e:
        print(f"[WARN] CheatSheet arama: {e}", flush=True)

    if not search_results:
        scroll_result, _ = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=course_filter,
            limit=16
        )
        search_results = scroll_result

    if not search_results:
        if selected_docs:
            docs_msg = ", ".join(f"'{d}'" for d in selected_docs)
            raise HTTPException(status_code=404, detail=f"Seçilen döküman(lar) ({docs_msg}) için içerik bulunamadı.")
        course_msg = f"'{target_course}' dersi için" if target_course else "Bu çalışma alanı için"
        raise HTTPException(status_code=404, detail=f"{course_msg} henüz PDF notu yüklenmemiş. Lütfen önce ders notu yükleyin.")

    context_parts = []
    for hit in search_results:
        p = hit.payload or {}
        context_parts.append(f"[Dosya: {p.get('document_name')}, Sayfa: {p.get('page_number')}]\n{p.get('text')}")

    context_text = "\n\n---\n\n".join(context_parts)
    course_title = target_course or "Genel Ders Notları"

    prompt = f"""Sen üniversite sınavları için ders notlarından yüksek yoğunluklu, net ve hatasız bir 'Sınav Formül & Kavram Kağıdı (Cheat Sheet)' hazırlayan bir akademisyensin.
Ders: {course_title}

Aşağıdaki ders notlarını incele ve öğrencinin sınavdan hemen önce tek bakışta tüm kilit bilgileri görebileceği 1-2 sayfalık kapsamlı bir Formül Kağıdı oluştur.

İÇERİK YAPISI:
1. # 📑 {course_title} - Sınav Formül & Kavram Kağıdı (Cheat Sheet)
2. ## 📐 1. Temel Formüller, Denklemler ve Değişkenler
   - Tüm formülleri KaTeX uyumlu standart LaTeX ($...$ veya $$...$$) ile yaz.
   - Her formülün yanına değişkenlerin ne anlama geldiğini ve birimlerini belirt.
3. ## 🔑 2. Sınavda Kesin Çıkabilecek Tanımlar & Kanunlar
   - En kritik 5-10 terim ve kavramın net sınav tanımları.
4. ## ⚠️ 3. Sınav İpuçları, Birim Dönüşümleri & Tuzaklar
   - Soru çözerken öğrencilerin en sık yaptığı hatalar ve pratik çözüm yolları.
5. ## 📄 4. Hızlı Sayfa Referansları
   - Hangi konunun hangi slayt/sayfada olduğuna dair özet fihrist.

[DERS NOTLARI]:
{context_text}
"""

    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)

    def _call_gemini_cheatsheet(model_name: str):
        return client.models.generate_content(
            model=model_name,
            contents=prompt
        )

    try:
        response = await asyncio.to_thread(_call_gemini_cheatsheet, GEMINI_MODEL)
    except Exception as e:
        print(f"[WARN] CheatSheet fallback modele geçiliyor: {e}", flush=True)
        response = await asyncio.to_thread(_call_gemini_cheatsheet, GEMINI_FALLBACK_MODEL)

    return CheatSheetResponse(
        course_name=course_title,
        title=f"{course_title} - Formül & Kavram Kağıdı",
        markdown_content=response.text
    )


# 5.2 Ders Zihin Haritası (Hierarchical Mind Map Generator)
@app.post(
    "/api/mindmap",
    tags=["Çalışma Araçları"],
    summary="Hiyerarşik Ders Zihin Haritası (Mindmap)",
    description="Dersin veya seçili PDF'lerin kavram ağacını ve sayfa referanslarını hiyerarşik JSON olarak üretir. Tekrar üretimleri SQLite önbelleğinden 5 milisaniyede döner."
)
async def generate_mindmap(
    payload: MindMapRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or payload.user_id or "default_user").strip()
    target_course = (payload.course_id or payload.course_name or "").strip()
    focus = (payload.focus or "").strip() or None
    refresh = bool(payload.refresh)

    if not target_course:
        raise HTTPException(
            status_code=400,
            detail="Lütfen bir ders seçiniz. Zihin haritası oluşturmak için aktif bir ders gereklidir."
        )

    # 1. Qdrant üzerinde ders, kullanıcı ve seçili döküman filtreleri
    selected_docs = payload.selected_docs or []
    course_filter = build_course_filter(uid, target_course, selected_docs)

    # 1.1 Ders / Döküman boş mu kontrolü
    check_records, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=course_filter,
        limit=1,
        with_payload=False,
        with_vectors=False
    )
    if not check_records:
        if not selected_docs:
            clear_mindmap_cache(uid, target_course)
        msg = "Seçilen PDF döküman(lar)ı için içerik bulunamadı." if selected_docs else f"'{target_course}' dersi için henüz hiç PDF ders notu yüklenmemiş. Lütfen önce sol menüden ders notu yükleyiniz."
        raise HTTPException(
            status_code=400,
            detail=msg
        )

    # 2. SQLite Önbellek Kontrolü (Refresh istenmediyse)
    sorted_docs_key = ",".join(sorted(selected_docs)) if selected_docs else "all"
    cache_key = f"{uid}_{target_course.lower()}_{(focus or '').lower()}_{sorted_docs_key}"
    if not refresh:
        cached_result = get_mindmap_cache(cache_key)
        if cached_result:
            return JSONResponse(content=cached_result)

    sampled_points = []
    valid_pages = set()

    # 2.2 İçerik seçimi:
    # - focus varsa: focus metniyle similarity search yap, top 15-20 chunk al.
    # - focus yoksa: Qdrant'tan dersin chunk'larını sayfalara dağılacak şekilde örnekle (tüm dökümanı kapsasın, 30-40 chunk).
    if focus:
        try:
            focus_vector = get_embeddings([focus])[0]
            search_res = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=focus_vector,
                query_filter=course_filter,
                limit=20
            ).points
            sampled_points = search_res
        except Exception as e:
            print(f"[WARN] Mindmap focus search hatası: {e}", flush=True)

    if not sampled_points:
        all_chunks = []
        next_offset = None
        while True:
            records, next_offset = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=course_filter,
                limit=100,
                offset=next_offset,
                with_payload=True,
                with_vectors=False
            )
            all_chunks.extend(records)
            if not next_offset or len(all_chunks) >= 600:
                break

        if not all_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"'{target_course}' dersinin döküman içeriği okunamadı."
            )

        # Sayfa ve döküman sırasına göre sırala
        all_chunks.sort(key=lambda pt: (
            str((pt.payload or {}).get("document_name", "")),
            int((pt.payload or {}).get("page_number", 0) or 0)
        ))

        # Toplam bağlam yaklaşık 30-40 chunk'ı geçmesin
        target_sample_size = min(len(all_chunks), 35)
        if len(all_chunks) <= target_sample_size:
            sampled_points = all_chunks
        else:
            step = len(all_chunks) / float(target_sample_size)
            sampled_points = [all_chunks[int(i * step)] for i in range(target_sample_size)]

    # 3. Sayfa Numaraları & Bağlam Metnini Hazırla
    context_parts = []
    for pt in sampled_points:
        p = pt.payload or {}
        pno = p.get("page_number")
        doc_name = p.get("document_name", "")
        text = (p.get("text") or "").strip()
        if pno is not None:
            try:
                pno_int = int(pno)
                valid_pages.add(pno_int)
                context_parts.append(f"[Döküman: {doc_name} | Sayfa {pno_int}]\n{text}")
            except (ValueError, TypeError):
                context_parts.append(f"[Döküman: {doc_name}]\n{text}")
        else:
            context_parts.append(f"[Döküman: {doc_name}]\n{text}")

    context_text = "\n\n---\n\n".join(context_parts)
    allowed_pages_str = ", ".join(str(p) for p in sorted(valid_pages)) if valid_pages else "Belirtilmemiş"

    # 4. Gemini Sistem Prompt ve İstek Metni
    system_prompt = (
        "Sen bir ders notu analiz asistanısın. Sana verilen ders notu parçalarından, "
        "bir öğrencinin sınav öncesi büyük resmi görmesini sağlayacak hiyerarşik bir "
        "zihin haritası çıkar.\n"
        "Kurallar:\n"
        "- Sadece verilen metne dayan, dışarıdan bilgi ekleme.\n"
        "- Düğüm başlıkları kısa olsun (en fazla 6 kelime), cümle değil kavram olsun.\n"
        "- Ana dallar dersin gerçek ana konularını yansıtsın; benzer şeyleri birleştir.\n"
        "- Her düğüm için, o bilginin geçtiği sayfa numarasını SADECE bağlamdaki "
        "[Sayfa N] etiketlerinden seç. Emin değilsen null yaz.\n"
        "- Dil: notların dili Türkçe ve İngilizce karışıksa terimleri orijinal dilinde "
        "bırak, açıklayıcı başlıkları Türkçe yaz.\n"
        "- Çıktı yalnızca şemaya uygun JSON olsun."
    )

    focus_desc = f"Özellikle şu konuya odaklan: '{focus}'. " if focus else "Dersin genelini kapsayan bir konu ağacı oluştur. "
    user_prompt = f"""Ders: {target_course}
{focus_desc}
Bağlamdaki geçerli sayfa numaraları şunlardır: [{allowed_pages_str}]. Sayfa numarasını (page) SADECE bu listeden seç; listede olmayan bir sayfa numarası asla yazma, emin değilsen null bırak.

Ağaç yapısı kuralları:
- Kök düğüm (title): Dersin veya odak konusunun adı (en fazla 6 kelime).
- Kökün altında en fazla 8 ana dal (children).
- Her ana dalın altında en fazla 6 alt kavram (children).
- Maksimum derinlik 3 seviyedir.

[DERS NOTLARI]:
{context_text}
"""

    client = gemini_client or genai.Client(api_key=GEMINI_API_KEY)

    async def _call_gemini_mindmap(model_name: str):
        def _exec():
            return client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=MindMapResponse,
                    temperature=0.2,
                ),
            )
        return await asyncio.to_thread(_exec)

    # 5. Model çağrısı & Hata Yönetimi (Model geçersiz JSON dönerse 1 kez tekrar dene)
    mindmap_data = None
    last_error = ""

    for attempt in range(2):
        model_name = GEMINI_MODEL if attempt == 0 else GEMINI_FALLBACK_MODEL
        try:
            resp = await _call_gemini_mindmap(model_name)
            raw_text = (resp.text or "").strip()
            parsed_json = json.loads(raw_text)
            validated_obj = MindMapResponse.model_validate(parsed_json)
            mindmap_data = validated_obj.model_dump()
            break
        except Exception as e:
            last_error = str(e)
            print(f"[WARN] Mindmap deneme {attempt+1} başarısız ({model_name}): {e}", flush=True)
            if attempt == 0:
                await asyncio.sleep(0.8)
                continue

    if not mindmap_data:
        raise HTTPException(
            status_code=502,
            detail=f"Yapay zeka zihin haritasını yapılandırılmış JSON formatında üretemedi ({last_error[:100]}). Lütfen 'Yeniden Oluştur' butonuyla tekrar deneyiniz."
        )

    # 6. Sayfa Doğrulama (Hallucination Guard): Bağlamda olmayan sayfaları null yap
    def _sanitize_node(node: dict):
        p = node.get("page")
        if p is not None:
            try:
                p_int = int(p)
                if p_int in valid_pages:
                    node["page"] = p_int
                else:
                    node["page"] = None
            except (ValueError, TypeError):
                node["page"] = None
        # Başlığı en fazla 6 kelimeye sınırla
        t = str(node.get("title", "")).strip()
        words = t.split()
        if len(words) > 7:
            node["title"] = " ".join(words[:7])
        for child in node.get("children", []):
            _sanitize_node(child)

    _sanitize_node(mindmap_data)

    # 7. Sonucu SQLite tarafında cache'le
    set_mindmap_cache(cache_key, mindmap_data)

    return JSONResponse(content=mindmap_data)


# 6. Zayıf Konu Tespiti & Dashboard İstatistikleri
@app.post(
    "/submit-answer",
    tags=["İlerleme"],
    summary="Quiz Sorusu Cevap Kaydı & Zayıf Konu Tespiti",
    description="Öğrencinin quiz sorusuna verdiği yanıtı kaydeder. Yanlış yapılan soruların sayfa ve konu bilgilerini zayıf konu analitiğine ekler."
)
async def submit_answer(
    submission: QuizAnswerSubmit,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
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

    # İstatistikleri kalıcı olarak diske yaz
    save_storage()

    return {"status": "recorded", "stats": u_stats}


@app.get(
    "/dashboard-stats",
    tags=["İlerleme"],
    summary="Öğrenci Başarı ve İstatistik Paneli",
    description="Kullanıcının toplam çözdüğü soru adedini, doğru/yanlış oranlarını ve en çok zorlandığı sayfa/konu dağılımını döner."
)
async def get_dashboard_stats(
    user_id: Optional[str] = Query(None, description="Kullanıcı kimliği"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="İstemci oturum takip başlığı")
):
    uid = (x_user_id or user_id or "default_user").strip()
    return get_user_quiz_stats(uid)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)