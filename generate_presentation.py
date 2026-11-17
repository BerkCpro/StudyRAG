import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette
    BG_COLOR = RGBColor(11, 18, 16)         # Deep Teal Dark
    SURFACE_COLOR = RGBColor(20, 32, 28)    # Surface Card
    BORDER_COLOR = RGBColor(34, 51, 45)     # Subtle Border
    ACCENT_TEAL = RGBColor(20, 184, 166)    # Primary Teal
    ACCENT_CYAN = RGBColor(45, 212, 191)    # Bright Teal/Cyan
    TEXT_WHITE = RGBColor(248, 250, 252)    # Pure White
    TEXT_MUTED = RGBColor(143, 165, 157)    # Muted Teal-Gray
    CODE_BG = RGBColor(15, 23, 42)          # Dark Code Surface
    CODE_TEXT = RGBColor(56, 189, 248)      # Code Cyan

    def set_slide_bg(slide):
        background = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
        )
        background.fill.solid()
        background.fill.fore_color.rgb = BG_COLOR
        background.line.color.rgb = BG_COLOR
        return background

    def add_header(slide, tag_text, title_text, subtitle_text=""):
        # Tag pill
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8), Inches(0.35))
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = tag_text.upper()
        p_tag.font.size = Pt(11)
        p_tag.font.bold = True
        p_tag.font.color.rgb = ACCENT_TEAL

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_WHITE

        if subtitle_text:
            p_sub = tf_title.add_paragraph()
            p_sub.text = subtitle_text
            p_sub.font.size = Pt(13)
            p_sub.font.color.rgb = TEXT_MUTED

    def add_card(slide, left, top, width, height, bg=SURFACE_COLOR, border=BORDER_COLOR):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg
        card.line.color.rgb = border
        card.line.width = Pt(1.2)
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1)

    # Decorative background card
    add_card(s1, Inches(0.8), Inches(1.2), Inches(11.733), Inches(5.1), bg=RGBColor(16, 26, 23), border=BORDER_COLOR)

    # Title box inside
    tbox = s1.shapes.add_textbox(Inches(1.4), Inches(1.8), Inches(10.5), Inches(3.8))
    tf1 = tbox.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "ADVANCED COMPUTER PROGRAMMING — FINAL PROJECT"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_TEAL
    p0.space_after = Pt(16)

    p1 = tf1.add_paragraph()
    p1.text = "StudyRAG: High-Performance Educational Platform"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(14)

    p2 = tf1.add_paragraph()
    p2.text = "Production-Grade Asynchronous Web Architecture, Real-Time Streaming & Vector RAG with FastAPI"
    p2.font.size = Pt(17)
    p2.font.color.rgb = ACCENT_CYAN
    p2.space_after = Pt(30)

    p3 = tf1.add_paragraph()
    p3.text = "Geliştirici: Berk & Proje Ekibi   •   Tarih: Kasım 2026   •   Teknoloji Yığını: FastAPI, Uvicorn, Pydantic, Qdrant, Gemini"
    p3.font.size = Pt(12)
    p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & PROJECT VISION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2)
    add_header(s2, "Proje Vizyonu", "Öğrenci Odaklı RAG & İleri Düzey Web İhtiyacı", "Genel amaçlı yapay zeka modelleri üniversite ders notlarında neden yetersiz kalır?")

    # 3 Cards Layout
    cards_data = [
        ("1. Genel LLM Problemleri", [
            ("Halüsinasyon Riski", "Modeller spesifik ders notunu bilmediği için uydurma cevap verebilir."),
            ("Sayfa/Kaynak Yoksunluğu", "Öğrenci cevabın hangi slayttan geldiğini teyit edemez."),
            ("Ders İzolasyonu Eksikliği", "Farklı derslerin müfredatları ve sınav formatları birbirine karışır.")
        ]),
        ("2. StudyRAG Çözümü", [
            ("Kişisel Ders Hafızası", "Öğrencinin kendi PDF'leri vektörleştirilerek ders bazlı saklanır."),
            ("Sayfa Referanslı Cevaplar", "Her açıklama doğrudan ilgili sayfa rozetleriyle doğrulanır."),
            ("Akıllı Çalışma Modülleri", "Quiz simülatörü, flashcard'lar, formül kağıdı ve zihin haritası.")
        ]),
        ("3. FastAPI'nin Rolü", [
            ("Sıfır Gecikmeli Canlı Akış", "SSE (Server-Sent Events) ile token'ların milisaniye düzeyinde iletimi."),
            ("Asenkron Concurrency", "Ağır PDF ayrıştırma ve embedding süreçlerinin sunucuyu kitlememesi."),
            ("Sıkı Tip Güvenliği", "Pydantic ile sıfır hatalı veri sözleşmesi ve anında API dökümantasyonu.")
        ])
    ]

    for i, (head, points) in enumerate(cards_data):
        cx = Inches(0.8 + i * 4.0)
        card = add_card(s2, cx, Inches(2.0), Inches(3.7), Inches(4.8))
        tb = s2.shapes.add_textbox(cx + Inches(0.25), Inches(2.2), Inches(3.2), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True
        p_h = tf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(17)
        p_h.font.bold = True
        p_h.font.color.rgb = ACCENT_TEAL
        p_h.space_after = Pt(14)

        for b_title, b_desc in points:
            pb = tf.add_paragraph()
            pb.text = f"• {b_title}: "
            pb.font.size = Pt(12)
            pb.font.bold = True
            pb.font.color.rgb = TEXT_WHITE
            pb.space_after = Pt(2)

            pd = tf.add_paragraph()
            pd.text = f"  {b_desc}"
            pd.font.size = Pt(11)
            pd.font.color.rgb = TEXT_MUTED
            pd.space_after = Pt(10)

    # =========================================================================
    # SLIDE 3: WHY FASTAPI? ARCHITECTURAL JUSTIFICATION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3)
    add_header(s3, "Mimari Karar", "Neden FastAPI? Modern Python Framework Karşılaştırması", "İleri programlama dersi kapsamında performans, tip güvenliği ve asenkron yetenekler")

    # Left: Comparison Table / Points
    add_card(s3, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.8))
    tb_l = s3.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    pl_h = tf_l.paragraphs[0]
    pl_h.text = "Framework Kıyaslaması"
    pl_h.font.size = Pt(18)
    pl_h.font.bold = True
    pl_h.font.color.rgb = ACCENT_TEAL
    pl_h.space_after = Pt(14)

    comp_items = [
        ("Django", "Monolitik yapı, ağır ORM yükü, senkron kökenli mimari. Yapay zeka ve mikroservis akışlarında fazla hantal kalıyor."),
        ("Flask", "WSGI tabanlı, yerel asenkron (async/await) desteği sınırlı, tip doğrulaması ve OpenAPI için 3. parti eklenti karmaşası gerekiyor."),
        ("FastAPI (Seçimimiz)", "Starlette ASGI omurgası üzerine kurulu. Yerel async/await event loop, sıfır maliyetli Pydantic v2 entegrasyonu ve otomatik Swagger / OpenAPI dökümantasyonu.")
    ]
    for c_name, c_text in comp_items:
        p_cn = tf_l.add_paragraph()
        p_cn.text = f"▸ {c_name}"
        p_cn.font.size = Pt(14)
        p_cn.font.bold = True
        p_cn.font.color.rgb = ACCENT_CYAN if "FastAPI" in c_name else TEXT_WHITE
        p_cn.space_after = Pt(3)

        p_ct = tf_l.add_paragraph()
        p_ct.text = c_text
        p_ct.font.size = Pt(11)
        p_ct.font.color.rgb = TEXT_MUTED
        p_ct.space_after = Pt(12)

    # Right: Technical Pillars of FastAPI
    add_card(s3, Inches(6.8), Inches(2.0), Inches(5.7), Inches(4.8))
    tb_r = s3.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.1), Inches(4.4))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    pr_h = tf_r.paragraphs[0]
    pr_h.text = "FastAPI'ın Sunduğu 4 Ana Avantaj"
    pr_h.font.size = Pt(18)
    pr_h.font.bold = True
    pr_h.font.color.rgb = ACCENT_TEAL
    pr_h.space_after = Pt(14)

    pillars = [
        ("1. ASGI & Uvicorn ile Üstün Hız", "NodeJS ve Go seviyesinde I/O performansı (uvloop destekli asenkron motor)."),
        ("2. Pydantic Runtime Tip Denetimi", "Python type hints ile kod yazarken IDE desteği + çalışma zamanında otomatik doğrulama."),
        ("3. Dependency Injection Sistemi", "Header, User ID ve oturum kontrollerini tek merkezden bağımlılık olarak yönetebilme."),
        ("4. StreamingResponse (SSE Desteği)", "Yapay zeka modellerinin ürettiği token'ları beklemeden doğrudan tarayıcıya basabilme.")
    ]
    for p_t, p_d in pillars:
        p_pt = tf_r.add_paragraph()
        p_pt.text = p_t
        p_pt.font.size = Pt(13)
        p_pt.font.bold = True
        p_pt.font.color.rgb = TEXT_WHITE
        p_pt.space_after = Pt(2)

        p_pd = tf_r.add_paragraph()
        p_pd.text = p_d
        p_pd.font.size = Pt(11)
        p_pd.font.color.rgb = TEXT_MUTED
        p_pd.space_after = Pt(10)

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE & DATA FLOW
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4)
    add_header(s4, "Sistem Mimarisi", "Uçtan Uca Asenkron Veri Akışı ve Katmanlar", "Kullanıcı arayüzünden vektör veritabanına ve LLM sentezine uzanan köprü")

    # 4 Architecture Flow Blocks
    flow_steps = [
        ("1. İstemci Katmanı", "SPA (HTML5 / Vanilla JS)", "Kullanıcı etkileşimi, dinamik filtreleme, SSE canlı akış okuyucu (fetch reader), KaTeX formül render."),
        ("2. FastAPI Gateway", "Asenkron REST & Streaming", "CORS Middleware, Header & Body Pydantic doğrulaması, StaticFiles SPA fallback, Hata yönetimi."),
        ("3. RAG & İşlem Motoru", "PyMuPDF & Embedding", "Ders notu ayrıştırma (2200 char slayt korumalı), 25'li kota dostu batch embedding, asyncio.to_thread."),
        ("4. Depolama & Çıkarım", "Qdrant + SQLite + Gemini", "Qdrant Cosine vektör araması, dinamik FieldCondition ders/döküman filtresi, SQLite mindmap önbelleği.")
    ]

    for i, (step_title, tech_sub, step_desc) in enumerate(flow_steps):
        left_pos = Inches(0.8 + i * 2.95)
        card = add_card(s4, left_pos, Inches(2.0), Inches(2.8), Inches(4.8))
        tb = s4.shapes.add_textbox(left_pos + Inches(0.18), Inches(2.2), Inches(2.44), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = step_title
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_TEAL
        p1.space_after = Pt(4)

        p2 = tf.add_paragraph()
        p2.text = tech_sub
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = ACCENT_CYAN
        p2.space_after = Pt(12)

        p3 = tf.add_paragraph()
        p3.text = step_desc
        p3.font.size = Pt(11)
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 5: FASTAPI CORE 1 — REAL-TIME STREAMING (/chat-stream)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5)
    add_header(s5, "FastAPI Derinlemesine 1", "StreamingResponse & Server-Sent Events (SSE)", "LLM yanıtlarında Time-to-First-Token gecikmesini sıfıra indiren jeneratör mimarisi")

    # Left: Explanation
    add_card(s5, Inches(0.8), Inches(2.0), Inches(5.2), Inches(4.8))
    tb5_l = s5.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(4.6), Inches(4.4))
    tf5_l = tb5_l.text_frame
    tf5_l.word_wrap = True

    p = tf5_l.paragraphs[0]
    p.text = "Geleneksel vs. Akış (Streaming)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    points5 = [
        ("Neden Streaming?", "Normal REST isteklerinde 500 kelimelik bir akademik cevap 8-12 saniye sürer. Bu süreçte kullanıcı ekranda donma hisseder."),
        ("FastAPI Çözümü", "FastAPI'ın `StreamingResponse` sınıfı, asenkron bir Python jeneratörünü `text/event-stream` protokolüyle tarayıcıya bağlar."),
        ("Non-blocking Concurrency", "`async def event_generator()` yapısı sayesinde bir öğrencinin cevabı akarken diğer öğrenciler sisteme rahatça istek atabilir; worker kilitlenmez."),
        ("Multimodal Entegrasyon", "Sohbet isteği metinle birlikte Base64 görsel (soru fotoğrafı) içerse bile bağlam tek seferde çözülüp akışa aktarılır.")
    ]
    for pt_t, pt_d in points5:
        p_t = tf5_l.add_paragraph()
        p_t.text = f"• {pt_t}: "
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf5_l.add_paragraph()
        p_d.text = f"  {pt_d}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    # Right: Actual Code Snippet
    add_card(s5, Inches(6.3), Inches(2.0), Inches(6.2), Inches(4.8), bg=CODE_BG)
    tb5_r = s5.shapes.add_textbox(Inches(6.5), Inches(2.2), Inches(5.8), Inches(4.4))
    tf5_r = tb5_r.text_frame
    tf5_r.word_wrap = True
    p = tf5_r.paragraphs[0]
    p.text = "main.py: Streaming Endpoint Uygulaması"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CODE_TEXT
    p.space_after = Pt(8)

    code_stream = (
        "@app.post(\"/chat-stream\")\n"
        "async def chat_stream(request: ChatRequest):\n"
        "    context, sources = prepare_chat_context(request)\n"
        "\n"
        "    async def event_generator():\n"
        "        # Kaynak referanslarını ilk paket olarak ilet\n"
        "        yield f\"data: {json.dumps({'sources': sources})}\\n\\n\"\n"
        "\n"
        "        # Gemini asenkron token akışı\n"
        "        response = await client.aio.models.generate_content_stream(\n"
        "            model=GEMINI_MODEL, contents=prompt\n"
        "        )\n"
        "        async for chunk in response:\n"
        "            if chunk.text:\n"
        "                yield f\"data: {json.dumps({'chunk': chunk.text})}\\n\\n\"\n"
        "        yield \"data: [DONE]\\n\\n\"\n"
        "\n"
        "    return StreamingResponse(\n"
        "        event_generator(), media_type=\"text/event-stream\"\n"
        "    )"
    )
    p_code = tf5_r.add_paragraph()
    p_code.text = code_stream
    p_code.font.size = Pt(10)
    p_code.font.name = "Consolas"
    p_code.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 6: FASTAPI CORE 2 — PDF INGESTION & BATCHING (/upload-pdf)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6)
    add_header(s6, "FastAPI Derinlemesine 2", "Asenkron Dosya Yükleme & Döküman Ayrıştırma", "Multipart form-data, bellek koruması ve kota dostu 25'lik embedding paketleme")

    add_card(s6, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.8))
    tb6_l = s6.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf6_l = tb6_l.text_frame
    tf6_l.word_wrap = True

    p = tf6_l.paragraphs[0]
    p.text = "Ingestion Pipeline Tasarım İlkeleri"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    ingest_points = [
        ("UploadFile = File(...) Parametresi", "FastAPI'ın SpooledTemporaryFile desteği sayesinde büyük PDF'ler belleği (RAM) tüketmeden disk tamponunda güvenle karşılanır."),
        ("150 Sayfalık Bellek Bariyeri", "Sunucu bellek taşmasını ve uzun zaman aşımı kilitlenmelerini önlemek amacıyla 150 sayfa üzeri yüklemelerde anında 400 Bad Request fırlatılır."),
        ("Slayt Bütünlüğünü Koruyan Chunking", "2200 karakterden kısa slaytlar bölünmeden tek parça tutulur. Böylece cümlenin ortadan bölünmesi önlenir ve API çağrıları %50 azalır."),
        ("Thread Offloading (asyncio.to_thread)", "PyMuPDF metin çekme ve senkron embedding çağrıları ana event loop'u kilitlemesin diye thread havuzuna delege edilir.")
    ]
    for ip_t, ip_d in ingest_points:
        p_t = tf6_l.add_paragraph()
        p_t.text = f"✔ {ip_t}"
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf6_l.add_paragraph()
        p_d.text = f"   {ip_d}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    add_card(s6, Inches(6.7), Inches(2.0), Inches(5.8), Inches(4.8), bg=CODE_BG)
    tb6_r = s6.shapes.add_textbox(Inches(6.9), Inches(2.2), Inches(5.4), Inches(4.4))
    tf6_r = tb6_r.text_frame
    tf6_r.word_wrap = True
    p = tf6_r.paragraphs[0]
    p.text = "main.py: 25'li Batch & Rate-Limit Güvenliği"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CODE_TEXT
    p.space_after = Pt(8)

    code_ingest = (
        "@app.post(\"/upload-pdf\")\n"
        "async def upload_pdf(\n"
        "    file: UploadFile = File(...),\n"
        "    course_name: str = Form(\"Genel Ders\"),\n"
        "    user_id: Optional[str] = Form(None)\n"
        "):\n"
        "    pdf_bytes = await file.read()\n"
        "    doc = pymupdf.open(stream=pdf_bytes, filetype=\"pdf\")\n"
        "\n"
        "    # Slayt duyarlı metin parçalama\n"
        "    chunks_to_embed = extract_slide_chunks(doc)\n"
        "\n"
        "    # Dakika başı API kota limitini aşmamak için 25'li gruplama\n"
        "    embeddings = []\n"
        "    batch_size = 25\n"
        "    for i in range(0, len(chunks_to_embed), batch_size):\n"
        "        batch = chunks_to_embed[i : i + batch_size]\n"
        "        batch_embs = await asyncio.to_thread(get_embeddings, batch)\n"
        "        embeddings.extend(batch_embs)\n"
        "        if i + batch_size < len(chunks_to_embed):\n"
        "            await asyncio.sleep(0.8)  # Kota nefes alma payı\n"
        "\n"
        "    await upsert_to_qdrant(embeddings, payloads)"
    )
    p_code = tf6_r.add_paragraph()
    p_code.text = code_ingest
    p_code.font.size = Pt(10)
    p_code.font.name = "Consolas"
    p_code.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 7: FASTAPI CORE 3 — PYDANTIC TYPE CONTRACTS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7)
    add_header(s7, "FastAPI Derinlemesine 3", "Pydantic v2 Veri Doğrulama & Tip Güvenliği", "Çalışma zamanında runtime tip kontrolü ve otomatik JSON serileştirme")

    # 3 Column Cards
    col_data = [
        ("Girdi Sözleşmeleri (Request)", "ChatRequest & QuizRequest", [
            ("Otomatik Doğrulama", "Eksik parametrede doğrudan 422 Unprocessable Entity döner."),
            ("Literal Kısıtlamaları", "question_type: Literal['mixed', 'mcq', 'tf', 'open'] ile hatalı girişler engellenir."),
            ("Varsayılan Değerler", "difficulty: str = 'Orta', count: int = 10.")
        ]),
        ("Çıktı Sözleşmeleri (Response)", "QuizResponse & Flashcard", [
            ("Kalıplı Şemalar", "questions: list[QuizQuestion] ile LLM cevabı JSON formatında zorlanır."),
            ("Tip Dönüşümü", "İç içe geçmiş objeler Pydantic tarafından anında Python nesnesine çevrilir."),
            ("Kaynak Teyidi", "source_document ve page_number alanları zorunlu kılınır.")
        ]),
        ("İleri Düzey: Özyinelemeli Ağaç", "MindMapNode (Recursive)", [
            ("Ağaç Hiyerarşisi", "Konu başlığı, sayfa numarası ve alt başlıklar hiyerarşisi."),
            ("Self-Referencing", "children: list['MindMapNode'] = [] ile sınırsız derinlikte zihin haritası."),
            ("Swagger Entegrasyonu", "İç içe JSON ağaç yapısı Swagger dökümanında şema olarak çizilir.")
        ])
    ]

    for i, (title, sub, bullets) in enumerate(col_data):
        cx = Inches(0.8 + i * 4.0)
        card = add_card(s7, cx, Inches(2.0), Inches(3.7), Inches(4.8))
        tb = s7.shapes.add_textbox(cx + Inches(0.2), Inches(2.2), Inches(3.3), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_TEAL
        p1.space_after = Pt(2)

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = ACCENT_CYAN
        p2.space_after = Pt(12)

        for b_t, b_d in bullets:
            p_bt = tf.add_paragraph()
            p_bt.text = f"▸ {b_t}"
            p_bt.font.size = Pt(12)
            p_bt.font.bold = True
            p_bt.font.color.rgb = TEXT_WHITE
            p_bt.space_after = Pt(2)

            p_bd = tf.add_paragraph()
            p_bd.text = b_d
            p_bd.font.size = Pt(11)
            p_bd.font.color.rgb = TEXT_MUTED
            p_bd.space_after = Pt(8)

    # =========================================================================
    # SLIDE 8: VECTOR DB INTEGRATION & HYBRID FILTERING
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8)
    add_header(s8, "Vektör Veritabanı & RAG", "Qdrant Entegrasyonu & Dinamik Çoklu Döküman Filtresi", "Sadece seçili PDF'lerden soru sorma ve zihin haritası üretme mimarisi")

    add_card(s8, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.8))
    tb8_l = s8.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf8_l = tb8_l.text_frame
    tf8_l.word_wrap = True

    p = tf8_l.paragraphs[0]
    p.text = "Çok Kiracılı (Multi-Tenant) İzolasyon"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    rag_points = [
        ("Kullanıcı & Ders İzolasyonu", "Her vektör kaydında `user_id` ve `course_name` payload olarak tutulur. Farklı öğrencilerin ders notları asla birbirine karışmaz."),
        ("Dinamik 'build_course_filter' Fonksiyonu", "Öğrenci 'Yalnızca Vize Notlarından Soru Sor' dediğinde, FastAPI arka planda dinamik Qdrant FieldCondition koşulları üretir."),
        ("OR (Should) Mantığı ile Çoklu Seçim", "Birden fazla PDF seçildiğinde Qdrant `Filter(should=[FieldCondition(document_name=doc)...])` bileşkesi oluşturulur."),
        ("Dinamik Geri Dönüş (Fallback)", "Hiçbir PDF seçilmemişse filtre döküman kısıtını kaldırarak tüm dersi kapsayacak şekilde genişler.")
    ]
    for rp_t, rp_d in rag_points:
        p_t = tf8_l.add_paragraph()
        p_t.text = f"• {rp_t}: "
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf8_l.add_paragraph()
        p_d.text = f"  {rp_d}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    add_card(s8, Inches(6.7), Inches(2.0), Inches(5.8), Inches(4.8), bg=CODE_BG)
    tb8_r = s8.shapes.add_textbox(Inches(6.9), Inches(2.2), Inches(5.4), Inches(4.4))
    tf8_r = tb8_r.text_frame
    tf8_r.word_wrap = True
    p = tf8_r.paragraphs[0]
    p.text = "main.py: Dinamik Qdrant Filtreleyici"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CODE_TEXT
    p.space_after = Pt(8)

    code_filter = (
        "def build_course_filter(uid, course_name, selected_docs=None):\n"
        "    must_conditions = [\n"
        "        FieldCondition(key=\"user_id\", match=MatchValue(value=uid))\n"
        "    ]\n"
        "    if course_name:\n"
        "        must_conditions.append(\n"
        "            FieldCondition(key=\"course_name\", match=MatchValue(value=course_name))\n"
        "        )\n"
        "\n"
        "    # Çoklu veya tekli döküman seçimi\n"
        "    if selected_docs and len(selected_docs) == 1:\n"
        "        must_conditions.append(\n"
        "            FieldCondition(key=\"document_name\", match=MatchValue(value=selected_docs[0]))\n"
        "        )\n"
        "    elif selected_docs and len(selected_docs) > 1:\n"
        "        doc_or_conditions = [\n"
        "            FieldCondition(key=\"document_name\", match=MatchValue(value=d))\n"
        "            for d in selected_docs\n"
        "        ]\n"
        "        must_conditions.append(Filter(should=doc_or_conditions))\n"
        "\n"
        "    return Filter(must=must_conditions)"
    )
    p_code = tf8_r.add_paragraph()
    p_code.text = code_filter
    p_code.font.size = Pt(9.5)
    p_code.font.name = "Consolas"
    p_code.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 9: PERFORMANCE & CACHING STRATEGY
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9)
    add_header(s9, "Optimizasyon & Güvenlik", "Performans İyileştirmeleri, Önbellek & Middleware", "Kurumsal düzeyde stabilite, kaynak tasarrufu ve hata toleransı")

    perf_cards = [
        ("1. Thread Offloading", [
            ("Event Loop Koruması", "Python GIL ve CPU yoğun işlemler async loop'u yavaşlatabilir."),
            ("asyncio.to_thread", "PyMuPDF text parsing, Gemini embedding ve senkron DB işlemleri worker thread'e devredilir."),
            ("Sıfır Donma", "Büyük bir PDF işlenirken diğer kullanıcıların sohbet veya quiz talepleri milisaniye hızında karşılanır.")
        ]),
        ("2. SQLite Çok Katmanlı Önbellek", [
            ("Maliyetli Zihin Haritaları", "Büyük bir dersin zihin haritasını sıfırdan çıkarmak 15-20 saniye sürebilir."),
            ("Döküman Parmak İzi", "Önbellek anahtarı seçili dökümanların sıralı özetiyle oluşturulur: `sorted_docs_key`."),
            ("Anında Yanıt", "Daha önce aynı döküman kombinasyonundan harita üretilmişse SQLite'tan 5 milisaniyede döner.")
        ]),
        ("3. Güvenlik & Middleware", [
            ("CORSMiddleware", "Cross-Origin isteklerine karşı yetkilendirilmiş domain ve metot kontrolleri."),
            ("Özel Başlıklar (X-User-Id)", "Frontend ile backend arasında anonim oturum takibi sağlayan hafif kimlik mimarisi."),
            ("Merkezi HTTPException", "İstemciye dönen hata mesajları (400, 404, 503) standart ve anlaşılır formatta iletilir.")
        ])
    ]

    for i, (title, items) in enumerate(perf_cards):
        cx = Inches(0.8 + i * 4.0)
        card = add_card(s9, cx, Inches(2.0), Inches(3.7), Inches(4.8))
        tb = s9.shapes.add_textbox(cx + Inches(0.2), Inches(2.2), Inches(3.3), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_TEAL
        p1.space_after = Pt(12)

        for it_title, it_desc in items:
            p_t = tf.add_paragraph()
            p_t.text = f"✔ {it_title}"
            p_t.font.size = Pt(12)
            p_t.font.bold = True
            p_t.font.color.rgb = TEXT_WHITE
            p_t.space_after = Pt(2)

            p_d = tf.add_paragraph()
            p_d.text = it_desc
            p_d.font.size = Pt(11)
            p_d.font.color.rgb = TEXT_MUTED
            p_d.space_after = Pt(8)

    # =========================================================================
    # SLIDE 10: INTERACTIVE API DOCUMENTATION (/docs)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10)
    add_header(s10, "Geliştirici Deneyimi", "Otomatik OpenAPI & Swagger UI Entegrasyonu", "Kod yazılırken canlı olarak üretilen interaktif API dökümantasyonu (/docs)")

    # Left: Explanation
    add_card(s10, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.8))
    tb10_l = s10.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf10_l = tb10_l.text_frame
    tf10_l.word_wrap = True

    p = tf10_l.paragraphs[0]
    p.text = "Swagger UI'ın Projeye Katkıları"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    swagger_points = [
        ("Otomatik Güncellik", "FastAPI kodunda bir Pydantic modeli veya endpoint parametresi değiştiği anda `/docs` kendini otomatik yeniler. Ek döküman yazma zahmeti yoktur."),
        ("Postman / Canlı Test İhtiyacını Karşılama", "Tarayıcı üzerinden 'Try it out' butonuna basarak tüm parametreler, request body'ler ve dosyalar doğrudan test edilebilir."),
        ("Sözleşme Tabanlı Geliştirme (Contract-First)", "Frontend ve Backend eş zamanlı geliştirilirken şema uyuşmazlıkları sıfıra indirildi."),
        ("ReDoc Alternatifi", "Daha detaylı teknik analiz için `/redoc` arayüzü de yerel olarak sunulmaktadır.")
    ]
    for sp_t, sp_d in swagger_points:
        p_t = tf10_l.add_paragraph()
        p_t.text = f"▸ {sp_t}"
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf10_l.add_paragraph()
        p_d.text = sp_d
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    # Right: Endpoints list
    add_card(s10, Inches(6.7), Inches(2.0), Inches(5.8), Inches(4.8), bg=CODE_BG)
    tb10_r = s10.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.2), Inches(4.4))
    tf10_r = tb10_r.text_frame
    tf10_r.word_wrap = True
    p = tf10_r.paragraphs[0]
    p.text = "StudyRAG FastAPI Endpoint Haritası"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = CODE_TEXT
    p.space_after = Pt(10)

    endpoints = [
        ("POST", "/upload-pdf", "Multipart PDF yükleme, slayt ayrıştırma & embedding"),
        ("POST", "/chat-stream", "Server-Sent Events ile canlı token akışlı asistan"),
        ("POST", "/generate-quiz", "Zorluk, soru adedi ve zayıf konu odaklı sınav üretimi"),
        ("POST", "/generate-flashcards", "Ders notlarından kritik kavram/soru kart seti üretimi"),
        ("POST", "/generate-cheatsheet", "Sınav öncesi tek sayfalık formül ve tanım kağıdı"),
        ("POST", "/api/mindmap", "Hiyerarşik konu ağacı & SQLite önbellekli zihin haritası"),
        ("GET ", "/documents", "Seçili dersteki yüklü PDF listesi ve sayfa bilgileri"),
        ("DELETE", "/documents/{name}", "Qdrant vektör noktaları ve disk dosyasının silinmesi")
    ]
    for meth, ep, desc in endpoints:
        p_ep = tf10_r.add_paragraph()
        p_ep.text = f"{meth} {ep}"
        p_ep.font.size = Pt(11)
        p_ep.font.name = "Consolas"
        p_ep.font.bold = True
        p_ep.font.color.rgb = ACCENT_CYAN if meth.strip() == "POST" else (RGBColor(248, 113, 113) if "DELETE" in meth else ACCENT_TEAL)

        p_desc = tf10_r.add_paragraph()
        p_desc.text = f"   └ {desc}"
        p_desc.font.size = Pt(9.5)
        p_desc.font.color.rgb = TEXT_MUTED
        p_desc.space_after = Pt(4)

    # =========================================================================
    # SLIDE 11: PRODUCTION ARCHITECTURE & SCALABILITY
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s11)
    add_header(s11, "Gelecek & Ölçeklenebilirlik", "Canlı Dağıtım (Production) ve Gelecek Yol Haritası", "Yerel prototipten binlerce eşzamanlı öğrenciye hizmet veren bulut mimarisine")

    add_card(s11, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.8))
    tb11_l = s11.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf11_l = tb11_l.text_frame
    tf11_l.word_wrap = True

    p = tf11_l.paragraphs[0]
    p.text = "Mevcut Dağıtım Mimarisi"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    cur_points = [
        ("Uvicorn ASGI Sunucusu", "0.0.0.0:8000 üzerinde çalışan yüksek performanslı asenkron web sunucusu."),
        ("Cloudflare Tunnel Entegrasyonu", "Modem portu açmaya veya statik IP'ye gerek duymadan güvenli global HTTPS tüneli (`trycloudflare.com`)."),
        ("Yerel Kalıcı Qdrant Deposu", "Diske bağlı `./qdrant_storage` klasörü ile sunucu kapansa bile korunabilen gömülü vektör veritabanı.")
    ]
    for cp_t, cp_d in cur_points:
        p_t = tf11_l.add_paragraph()
        p_t.text = f"• {cp_t}"
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf11_l.add_paragraph()
        p_d.text = cp_d
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    add_card(s11, Inches(6.7), Inches(2.0), Inches(5.8), Inches(4.8))
    tb11_r = s11.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.2), Inches(4.4))
    tf11_r = tb11_r.text_frame
    tf11_r.word_wrap = True

    p = tf11_r.paragraphs[0]
    p.text = "Ölçekleme & Gelecek Planı"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    fut_points = [
        ("Celery / Redis Arka Plan Kuyruğu", "Çok sayfalı yüzlerce PDF yüklendiğinde yükleme işlemini ayrı worker pod'larına devretme."),
        ("Docker & Kubernetes Containerization", "Uvicorn worker'larını CPU çekirdek sayısına göre orkestre ederek yatayda ölçekleme (horizontal scaling)."),
        ("PostgreSQL (pgvector) Alternatifi", "İlişkisel veriler ile vektör aramalarını tek bir veritabanı çatısı altında toplama."),
        ("WebSockets Tabanlı Sesli Çalışma Odaları", "FastAPI'ın yerel WebSocket desteğiyle öğrenciler için sesli ve etkileşimli çalışma oturumları.")
    ]
    for fp_t, fp_d in fut_points:
        p_t = tf11_r.add_paragraph()
        p_t.text = f"▸ {fp_t}"
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_d = tf11_r.add_paragraph()
        p_d.text = fp_d
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(8)

    # =========================================================================
    # SLIDE 12: CONCLUSION & Q&A
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s12)

    add_card(s12, Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5), bg=RGBColor(16, 26, 23), border=BORDER_COLOR)

    tb12 = s12.shapes.add_textbox(Inches(2.0), Inches(2.0), Inches(9.333), Inches(3.5))
    tf12 = tb12.text_frame
    tf12.word_wrap = True

    p = tf12.paragraphs[0]
    p.text = "TEŞEKKÜRLER & SORU - CEVAP"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_TEAL
    p.space_after = Pt(12)

    p_main = tf12.add_paragraph()
    p_main.text = "StudyRAG: Geleceğin Çalışma Platformu"
    p_main.font.size = Pt(32)
    p_main.font.bold = True
    p_main.font.color.rgb = TEXT_WHITE
    p_main.space_after = Pt(14)

    p_sum = tf12.add_paragraph()
    p_sum.text = (
        "FastAPI sayesinde yüksek asenkron performans, sıfır hatalı Pydantic tip denetimi, "
        "canlı Server-Sent Events akışı ve dinamik vektör arama entegrasyonu tek bir zarif "
        "mimaride bir araya getirildi."
    )
    p_sum.font.size = Pt(14)
    p_sum.font.color.rgb = ACCENT_CYAN
    p_sum.space_after = Pt(24)

    p_foot = tf12.add_paragraph()
    p_foot.text = "Sorularınızı yanıtlamaktan memnuniyet duyarız.   |   Canlı Demo: /docs"
    p_foot.font.size = Pt(12)
    p_foot.font.color.rgb = TEXT_MUTED

    output_path = "StudyRAG_FastAPI_Presentation.pptx"
    prs.save(output_path)
    print(f"SUCCESS: Saved presentation to {output_path}")

if __name__ == "__main__":
    create_deck()
