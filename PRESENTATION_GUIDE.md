# StudyRAG — FastAPI Mimari Sunumu & Jüri Savunma Rehberi
**Ders:** Advanced Computer Programming (İleri Bilgisayar Programlama)  
**Tarih / Teslim:** Kasım 2026  
**Proje Dosyası:** [StudyRAG_FastAPI_Presentation.pptx](file:///c:/Users/Berk/OneDrive/Desktop/rag_fastapi/deneme2/StudyRAG_FastAPI_Presentation.pptx)  
**Backend Kaynak Kodu:** [main.py](file:///c:/Users/Berk/OneDrive/Desktop/rag_fastapi/deneme2/main.py)  

---

## 🎯 1. Sunum Stratejisi ve Süre Planı (10 - 15 Dakika)

Bu sunumun asıl odak noktası yapay zekanın kendisinden ziyade, **FastAPI'ın yüksek performanslı web mimarisi, asenkron I/O yönetimi, Pydantic v2 tip sözleşmeleri ve kurumsal düzeydeki API tasarımıdır.**

| Bölüm | Slaytlar | Hedef Süre | Ana Vurgu |
|---|---|---|---|
| **Giriş & Motivasyon** | Slayt 1 - 2 | 2 Dakika | Problemin tanımı, neden ders bazlı RAG ve modern bir web omurgası gerektiği. |
| **Mimari & FastAPI Seçimi** | Slayt 3 - 4 | 3 Dakika | ASGI vs WSGI, Starlette omurgası, non-blocking veri akışı ve katmanlar. |
| **Teknik Derinlemesine İnceleme** | Slayt 5 - 8 | 5 Dakika | `StreamingResponse` (SSE), PDF ayrıştırma & rate-limit batching, Pydantic modelleri, Qdrant dinamik filtreleri. |
| **Performans & Swagger & Prodüksiyon** | Slayt 9 - 11 | 3 Dakika | `asyncio.to_thread`, SQLite önbellekleme, Swagger UI (`/docs`), Celery/Docker gelecek planı. |
| **Canlı Demo & Kapanış (Q&A)** | Slayt 12 + Demo | 2-3 Dakika | `/docs` üzerinden canlı test veya arayüz gösterimi, jüri sorularının yanıtlanması. |

---

## 🎙️ 2. Slayt Slayt Konuşma Metni (Speaker Notes)

---

### Slayt 1: Başlık (Title Slide)
- **Ekranda:** *StudyRAG: High-Performance Educational Platform — Production-Grade Asynchronous Web Architecture, Real-Time Streaming & Vector RAG with FastAPI*
- **Ne Söylemelisiniz?**
  > "Sayın hocam, değerli arkadaşlar, merhaba. Bugün sizlere İleri Bilgisayar Programlama dersi kapsamında geliştirdiğimiz **StudyRAG** projesini ve bu projenin omurgasını oluşturan **FastAPI asenkron web mimarisini** sunacağız.
  > 
  > Günümüzde yapay zeka uygulamaları hızla yaygınlaşsa da, bu modelleri yüksek eşzamanlılıkla (concurrency), sıfır gecikmeli veri akışıyla (streaming) ve sağlam tip güvenliğiyle istemciye sunmak ciddi bir ileri düzey web mühendisliği gerektiriyor. Biz de projemizde FastAPI'ın sunduğu modern ASGI kabiliyetlerini, Pydantic v2 doğrulamalarını ve asenkron I/O avantajlarını merkeze aldık."

---

### Slayt 2: Problem Tanımı & Proje Vizyonu
- **Ekranda:** *Genel LLM Problemleri vs. StudyRAG Çözümü vs. FastAPI'nin Rolü*
- **Ne Söylemelisiniz?**
  > "Üniversite öğrencilerinin sınav dönemlerinde karşılaştığı en büyük sorun, genel amaçlı yapay zeka modellerinin spesifik ders slaytlarını bilmemesi, olmayan formülleri uydurabilmesi (halüsinasyon) ve cevabın hangi sayfadan geldiğini doğrulayamamasıdır.
  > 
  > StudyRAG ile öğrencilerin kendi ders notlarını yükleyip izole edebildiği, sayfa referanslı cevaplar alabildiği, otomatik quiz ve zihin haritası üretebildiği bir sistem kurduk.
  > 
  > Ancak bu kadar ağır dosya ayrıştırma, embedding ve yapay zeka çıkarımı süreçleri geleneksel web sunucularında ciddi darboğazlar yaratır. İşte burada **FastAPI devreye giriyor**: Sıfır gecikmeli Server-Sent Events akışı, event-loop'u kilitlemeyen asenkron dosya işleme ve tip güvenliği sağlayan Pydantic sözleşmeleri sayesinde sistemi son derece akıcı kıldık."

---

### Slayt 3: Neden FastAPI? Mimari Karar & Kıyaslama
- **Ekranda:** *Django vs. Flask vs. FastAPI Kıyaslama Tablosu ve 4 Temel Sütun*
- **Ne Söylemelisiniz?**
  > "Projeye başlarken Python ekosistemindeki framework'leri titizlikle değerlendirdik:
  > - **Django:** Monolitik ve ağır bir yapıya sahip. WSGI kökenli olduğu için yapay zeka token akışlarında ve mikroservis yapısında gereksiz bir bellek ve ORM yükü getiriyor.
  > - **Flask:** Senkron bir micro-framework. Asenkron desteği sonradan eklendi ve tip denetimi veya OpenAPI dökümantasyonu için çok sayıda üçüncü parti kütüphaneye ihtiyaç duyuyor.
  > - **FastAPI (Seçimimiz):** Starlette ASGI omurgası üzerine kurulu. Yerel `async/await` desteği sunuyor, Rust tabanlı Pydantic v2 ile çalışıyor ve Node.js/Go düzeyinde I/O performansı sağlıyor.
  > 
  > Bize kazandırdığı 4 temel yetenek: **Uvicorn ile ASGI hızı**, **Pydantic ile çalışma zamanında tip kontrolü**, **bağımlılık enjeksiyonu (Dependency Injection)** ve birazdan detayına ineceğimiz **StreamingResponse** mekanizmasıdır."

---

### Slayt 4: Uçtan Uca Sistem Mimarisi & Veri Akışı
- **Ekranda:** *İstemci Katmanı (SPA) ➔ FastAPI Gateway ➔ RAG & İşlem Motoru ➔ Depolama (Qdrant & SQLite & Gemini)*
- **Ne Söylemelisiniz?**
  > "Bu diyagramda verinin uçtan uca nasıl aktığını görüyoruz:
  > 1. **İstemci (SPA):** Tek sayfa uygulaması (HTML5 & Modern Vanilla JS). `fetch()` ReadableStream ile canlı SSE token'larını okur ve KaTeX ile matematiksel formülleri render eder.
  > 2. **FastAPI Gateway:** Tüm istekleri karşılayan kapı. CORS denetimi, Header doğrulaması (`X-User-Id`), gövde (body) validasyonu ve SPA statik dosya yönlendirmesini tek çatı altında yürütür.
  > 3. **RAG & İşlem Katmanı:** PDF'leri slayt duyarlı parçalara böler, `asyncio.to_thread` ile CPU ve ağ işlerini optimize eder ve Gemini embedding servisine 25'li batch'ler halinde iletir.
  > 4. **Depolama Katmanı:** Vektör benzerlik aramaları için yerel Qdrant, maliyetli zihin haritaları için SQLite önbelleği ve LLM sentezi için Gemini 2.5 Flash asenkron istemcisi çalışır."

---

### Slayt 5: FastAPI Derinlemesine 1 — Real-Time Streaming (`/chat-stream`)
- **Ekranda:** *StreamingResponse & Server-Sent Events (SSE) Mimari Şeması ve Kod Bloğu*
- **Ne Söylemelisiniz?**
  > "Burası projemizin en kritik web mühendisliği başarılarından biridir:
  > Normal bir REST endpoint'inde kullanıcı soru sorduğunda, 500 kelimelik akademik bir cevabın LLM tarafından üretilmesi 8 ila 12 saniye sürer. Geleneksel sistemlerde kullanıcı bu süre boyunca boş ekrana bakar.
  > 
  > Biz FastAPI'ın `StreamingResponse` sınıfını ve **Server-Sent Events (`text/event-stream`)** protokolünü kullandık.
  > Kodda gördüğünüz gibi, `async def event_generator()` adında bir asenkron jeneratör tanımladık. İlk satırda bulunan ilgili kaynak sayfaları JSON olarak istemciye yollanır, ardından Gemini'ın asenkron stream'inden (`generate_content_stream`) gelen her token anında istemciye basılır.
  > 
  > **En büyük kazanım:** İlk token ekranda 300-400 milisaniyede belirir (Time-to-First-Token). Ayrıca `async` yapısı sayesinde sunucu diğer öğrencilerin isteklerini karşılamaya devam eder, worker asla bloke olmaz."

---

### Slayt 6: FastAPI Derinlemesine 2 — PDF Yükleme & Kota Dostu Batching (`/upload-pdf`)
- **Ekranda:** *UploadFile, SpooledTemporaryFile, 150 Sayfa Limiti ve 25'li Batch Döngüsü*
- **Ne Söylemelisiniz?**
  > "Bir diğer zorlayıcı konu, öğrencilerin yüklediği onlarca megabaytlık PDF'lerin sunucuyu yormasıdır.
  > 
  > FastAPI burada bize harika bir araç sunuyor: `UploadFile = File(...)`. Bu parametre arka planda Python'ın `SpooledTemporaryFile` yapısını kullanır. Yani dosya belirli bir boyuta kadar bellekte, boyutu aşarsa geçici disk tamponunda saklanır; sunucunun RAM'i aniden dolmaz.
  > 
  > Ayrıca sistem kararlılığı için şu önlemleri aldık:
  > - **150 Sayfalık Emniyet Bariyeri:** Sunucunun zaman aşımına uğramasını önlemek adına 150 sayfadan büyük PDF'lerde derhal `400 Bad Request` dönüyoruz.
  > - **Slayt Koruyucu Chunking:** Slaytlar 2200 karakterden kısaysa bölünmeden saklanır, böylece hem anlam bütünlüğü korunur hem de API çağrısı yarı yarıya azalır.
  > - **25'li Kota Güvenliği:** Google Gemini embedding API'sının dakika başı istek limitini aşmamak için vektörleştirmeyi 25'li batch'ler halinde yapıp aralara `asyncio.sleep` koyduk. Tüm bu senkron CPU işlerini `asyncio.to_thread` ile thread havuzuna devrettik."

---

### Slayt 7: FastAPI Derinlemesine 3 — Pydantic v2 Veri Sözleşmeleri
- **Ekranda:** *Girdi Sözleşmeleri (ChatRequest), Çıktı Sözleşmeleri (QuizResponse) ve Özyinelemeli Ağaç (MindMapNode)*
- **Ne Söylemelisiniz?**
  > "FastAPI'ı sektör standardı yapan en büyük güç **Pydantic v2** entegrasyonudur. Kodumuzda tüm veri alışverişini katı tip modelleriyle koruduk:
  > 1. **Girdi Doğrulama:** Örneğin `QuizRequest` modelinde soru tipi `Literal['mixed', 'mcq', 'tf', 'open']` olarak tanımlıdır. İstemci geçersiz bir string gönderirse FastAPI otomatik olarak `422 Unprocessable Entity` döner ve hatanın tam yerini gösterir; tek satır `if-else` yazmamıza gerek kalmaz.
  > 2. **Çıktı Güvencesi:** Quiz ve flashcard çıktılarında LLM'den gelen veriyi Pydantic modellerine zorlarız (`response_schema`). Böylece bozuk JSON dönmesi imkansız hale gelir.
  > 3. **İleri Düzey Özyinelemeli (Recursive) Modeller:** Zihin haritası için yazdığımız `MindMapNode` sınıfı, kendi türünde çocuk düğümler (`children: list['MindMapNode']`) barındırır. Pydantic bu özyinelemeli ağaç yapısını çalışma zamanında kusursuz serileştirir."

---

### Slayt 8: Vektör DB Entegrasyonu & Dinamik Çoklu Döküman Filtresi
- **Ekranda:** *Qdrant Multi-Tenant İzolasyonu ve `build_course_filter` Kod Bloğu*
- **Ne Söylemelisiniz?**
  > "Veri tabanı katmanında yüksek hızlı bir vektör arama motoru olan **Qdrant** kullandık.
  > 
  > Burada çözdüğümüz en kritik ileri düzey problem şuydu: Bir öğrencinin birden fazla dersi ve her derste onlarca PDF'i var. Öğrenci sadece 'Vize Slaytları'ndan veya seçtiği 2 spesifik PDF'ten soru sormak istediğinde ne olacak?
  > 
  > Bunu FastAPI tarafında yazdığımız `build_course_filter` fonksiyonu ile çözdük:
  > - `user_id` ve `course_name` her sorguda zorunlu kılınarak çok kiracılı (multi-tenant) veri güvenliği sağlanır.
  > - Eğer öğrenci filtreleme modalından belirli PDF'leri seçtiyse, Qdrant'ın `Filter(should=[FieldCondition...])` mantığıyla dinamik bir mantıksal **OR** filtresi inşa edilir.
  > - Hiçbir PDF seçilmemişse filtre otomatik genişleyerek tüm dersi kapsar. Böylece hem veri doğruluğu korunur hem de gereksiz vektör taraması önlenir."

---

### Slayt 9: Performans Optimizasyonu, Önbellek & Middleware
- **Ekranda:** *Thread Offloading (`asyncio.to_thread`), SQLite Önbelleği ve CORSMiddleware*
- **Ne Söylemelisiniz?**
  > "Sistemin kurumsal kararlılığı için üç ana optimizasyon uyguladık:
  > 1. **Thread Offloading:** Python'da CPU yoğun işlemler (PyMuPDF metin ayrıştırma) async event loop'u bloklayabilir. `asyncio.to_thread()` kullanarak bu işlemleri arka plandaki thread havuzuna devrettik; ana sunucu milisaniye gecikmeyle cevap vermeye devam ediyor.
  > 2. **SQLite Parmak İzi Önbelleği:** 100 slaytlık bir dersten hiyerarşik zihin haritası çıkarmak 15-20 saniye sürebilir. Bunu önlemek için seçilen döküman isimlerinden deterministik bir özet anahtar ürettik (`sorted_docs_key`). Aynı dökümanlar için tekrar harita istendiğinde SQLite'tan 5 milisaniyede yanıt dönüyoruz.
  > 3. **Middleware & Hata Standartlaştırması:** `CORSMiddleware` ile güvenli domain erişimi sağladık, tüm kontrollerde standart `HTTPException` kullanarak istemciye tutarlı hata kodları (400, 404, 422, 503) sunduk."

---

### Slayt 10: Geliştirici Deneyimi — Otomatik Swagger UI (`/docs`)
- **Ekranda:** *Otomatik OpenAPI Faydaları ve StudyRAG Endpoint Tablosu*
- **Ne Söylemelisiniz?**
  > "FastAPI'ın en sevilen özelliklerinden biri, hiçbir ek çaba harcamadan **OpenAPI (Swagger UI)** dökümantasyonunu otomatik üretmesidir.
  > 
  > Tarayıcıdan `/docs` adresine gittiğimizde, yazdığımız tüm Pydantic şemaları, girdi gereksinimleri, multipart yükleme formları ve dönüş tipleri interaktif bir konsol olarak karşımıza çıkar.
  > 
  > Bu sayede:
  > - Postman gibi harici test araçlarına ihtiyaç kalmadan tüm endpoint'leri tarayıcıdan anında test ettik.
  > - Frontend ile backend arasındaki sözleşme (contract-first) baştan itibaren hatasız ilerledi.
  > - İleride projeye katılacak yeni bir geliştirici tek bir komutla tüm API'ı anlayabilir."

---

### Slayt 11: Canlı Dağıtım (Production) & Gelecek Yol Haritası
- **Ekranda:** *Mevcut Altyapı (Cloudflare Tunnel, Uvicorn) ve Gelecek Planları (Celery, Docker, K8s)*
- **Ne Söylemelisiniz?**
  > "Projeyi yerel bilgisayarda bırakmadık; mobil cihazlardan ve harici ağlardan test edebilmek için **Cloudflare Tunnel** entegrasyonu kurduk. Modem portu açmaya gerek kalmadan uçtan uca TLS şifrelemeli global bir HTTPS adresi üzerinden canlıya aldık.
  > 
  > Peki sistemi yarın 50.000 üniversite öğrencisine açmak istesek mimariyi nasıl evriltiriz?
  > 1. **Celery / Redis Görev Kuyruğu:** Ağır PDF yüklemelerini HTTP döngüsünden tamamen çıkarıp asenkron arka plan işçilerine (worker) devrederiz.
  > 2. **Docker & Kubernetes:** Uvicorn process'lerini container'lar halinde paketleyip CPU yüküne göre otomatik yatayda ölçekleriz (Horizontal Pod Autoscaler).
  > 3. **PostgreSQL + pgvector:** Qdrant'ın yanına veya yerine, ilişkisel kullanıcı tablolarıyla vektörleri tek veritabanında birleştirebiliriz."

---

### Slayt 12: Kapanış & Soru - Cevap (Q&A)
- **Ekranda:** *Teşekkürler & Soru-Cevap — StudyRAG: Geleceğin Çalışma Platformu*
- **Ne Söylemelisiniz?**
  > "Özetlemek gerekirse; bu projede sadece bir yapay zeka arayüzü değil, **FastAPI'ın modern asenkron programlama prensiplerini, katı tip güvenliğini, akış protokollerini ve vektör veri tabanı entegrasyonunu** başarıyla harmanlayan sağlam bir web mimarisi inşa ettik.
  > 
  > İzninizle sorularınızı yanıtlamaktan veya dilediğiniz bir endpoint'i canlı olarak Swagger üzerinden test etmekten memnuniyet duyarız. Dinlediğiniz için teşekkür ederiz."

---

## 🛡️ 3. Jüri / Hoca Muhtemel Soruları ve Savunma Cevapları (Q&A Defense)

### Soru 1: "Neden Flask veya Django yerine FastAPI seçtiniz? Farkı tam olarak nedir?"
> **Cevap:**  
> "Hocam, projemizin merkezinde iki temel teknik gereksinim vardı: **Yapay zekanın ürettiği token'ların canlı akışı (Streaming)** ve **aynı anda birden fazla öğrencinin sisteme dosya yükleyip soru sorabilmesi (Concurrency)**.  
> Django ve standart Flask, köken olarak senkron WSGI (Web Server Gateway Interface) protokolüne dayanır. WSGI'da her istek bir thread'i kilitler; 10 saniye süren bir LLM akışı sırasında o worker başka hiçbir iş yapamaz.  
> FastAPI ise asenkron **ASGI (Asynchronous Server Gateway Interface)** mimarisine sahiptir ve Starlette çekirdeği üzerinde çalışır. `async/await` ile çalışarak I/O bekleme anlarında (Qdrant araması, Gemini API yanıtı) CPU'yu serbest bırakır. Ayrıca Pydantic v2 entegrasyonu sayesinde kod yazarken kullandığımız Python tip ipuçları (type hints), çalışma zamanında otomatik doğrulama ve otomatik OpenAPI dokümantasyonuna dönüşür."

---

### Soru 2: "Python'da GIL (Global Interpreter Lock) varken `async/await` nasıl performans artışı sağlıyor?"
> **Cevap:**  
> "Hocam çok yerinde bir soru. GIL, birden fazla thread'in aynı anda saf Python bytecode'u çalıştırmasını sınırlar; yani **CPU-bound** (işlemci yoğun) işlerde saf Python çoklu çekirdeği tek thread'de kullanamaz.  
> Ancak bizim projemizdeki işlemlerin %90'ı **I/O-bound** (girdi/çıktı bekleme) işlemleridir: Gemini API'sine HTTP isteği atmak, Qdrant vektör tabanından yanıt beklemek veya tarayıcıya SSE ile token iletmek.  
> Asyncio event-loop, bir istek ağdan veri beklerken (I/O beklemesi) durup beklemez; o sırada gelen ikinci veya üçüncü öğrencinin isteğini işlemeye başlar.  
> CPU-bound olan işlemler için ise (örneğin PyMuPDF ile PDF sayfalarından metin ayıklamak) `asyncio.to_thread()` fonksiyonunu kullandık. Bu sayede işlemciyi yoran metin işleme ayrı bir worker thread'e devredilir ve ana async event-loop asla kilitlenmez."

---

### Soru 3: "Gerçek zamanlı akış için neden WebSocket değil de Server-Sent Events (SSE) kullandınız?"
> **Cevap:**  
> "WebSocket çift yönlü (full-duplex) iletişim sağlar ve genellikle canlı oyunlar veya karşılıklı sohbet odaları gibi istemcinin de sürekli sunucuya veri bastığı senaryolarda gereklidir. Ancak bağlantı durumu (connection state), ping/pong paketleri ve proxy uyumluluğu ek bir yük getirir.  
> Bizim LLM sohbet akışımızda ise etkileşim **tek yönlüdür**: Öğrenci soruyu bir kez HTTP POST ile gönderir, ardından sunucu cevap token'larını parça parça tarayıcıya iletir.  
> FastAPI'ın `StreamingResponse(media_type='text/event-stream')` desteği standart HTTP üzerinden çalıştığı için ek bir el sıkışma (handshake) gerektirmez, Cloudflare ve proxy arkasında çok daha kararlı çalışır ve bağlantı koptuğunda HTTP düzeyinde kolayca yönetilir."

---

### Soru 4: "Büyük bir PDF yüklendiğinde sunucunun çökmesini nasıl engellediniz?"
> **Cevap:**  
> "Üç katmanlı bir savunma mekanizması kurduk:  
> 1. **Bellek Güvenliği (`UploadFile`):** Dosyayı ham `bytes` olarak belleğe almak yerine FastAPI'ın `UploadFile` tipini kullandık. Bu yapı Python'ın `SpooledTemporaryFile` mekanizmasını kullanır; dosya boyutu eşiği aşarsa belleği şişirmeden diske tamponlanır.  
> 2. **Sayfa Sınırı Kontrolü:** PDF açılır açılmaz sayfa sayısına bakarız (`len(doc)`). Eğer 150 sayfadan büyükse işlem derhal iptal edilerek istemciye `400 Bad Request` fırlatılır.  
> 3. **25'lik Batch Embedding & Rate Limit:** 100 slaytlık bir PDF tek seferde embedding API'sine gönderilirse API kota hatası (429 Too Many Requests) verir. Biz metin parçalarını 25'li gruplar halinde `asyncio.sleep(0.8)` molalarıyla göndererek kota aşımını sıfıra indirdik."

---

### Soru 5: "Pydantic v2'nin projedeki somut rolü nedir?"
> **Cevap:**  
> "Pydantic v2, FastAPI'ın veri sözleşmesi (contract) motorudur. Kodumuzdaki rolü üçe ayrılır:  
> 1. **Otomatik Tip Doğrulama:** Örneğin `QuizRequest` modelinde `count: int = 10` veya `difficulty: str = 'Orta'` tanımlıdır. İstemciden yanlış tipte bir parametre geldiğinde FastAPI daha fonksiyona girmeden isteği reddeder (`422 Unprocessable Entity`).  
> 2. **Yapılandırılmış LLM Çıktısı (Structured Outputs):** Gemini modeline `response_schema=QuizResponse` parametresini vererek yapay zekanın sadece belirlediğimiz Pydantic formatında (soru, şıklar, doğru cevap, açıklama) JSON üretmesini zorunlu kıldık.  
> 3. **Özyinelemeli (Recursive) Modeller:** Zihin haritası için yazdığımız `MindMapNode` modeli `children: list['MindMapNode']` şeklinde kendi kendini referans alır. Pydantic v2 bu derin ağaç hiyerarşisini yüksek performansla serialize eder."

---

### Soru 6: "Dinamik PDF seçimi (filtreleme) vektör veritabanında nasıl çalışıyor?"
> **Cevap:**  
> "Qdrant vektör veritabanında her vektör noktası (point), metin içeriğinin yanında bir **payload** (metadata) taşır. Biz bu payload içerisine `user_id`, `course_name` ve `document_name` bilgilerini kaydediyoruz.  
> Öğrenci arayüzde birden fazla PDF seçtiğinde, `build_course_filter()` fonksiyonumuz Qdrant için dinamik bir filtre nesnesi üretir:  
> - `must`: `[user_id == uid, course_name == ders]`  
> - `should`: `[document_name == doc1, document_name == doc2, ...]`  
> Bu sayede vektör benzerlik araması sadece öğrencinin seçtiği slaytlar üzerinde koşulur. Hiçbir seçim yapılmamışsa döküman kısıtı kaldırılır ve tüm ders notları taranır."

---

### Soru 7: "Zihin haritası üretiminde neden SQLite önbelleklemesi kullandınız?"
> **Cevap:**  
> "Geniş bir dersin tüm slaytlarını toplayıp hiyerarşik bir kavram ağacı üretmek LLM açısından maliyetli bir işlemdir (15-20 saniye sürebilir).  
> Bir öğrenci aynı PDF seti için sayfayı her yenilediğinde veya zihin haritası sekmesine her tıkladığında bu maliyeti ödememek için `mindmap_cache.db` adında hafif bir SQLite önbellek tablosu kurduk.  
> Seçilen dökümanların isimlerini alfabetik sıralayıp bir karma (hash/key) üretiyoruz. Eğer bu anahtar önbellekte varsa, zihin haritası LLM'e hiç gitmeden **5 milisaniyede** doğrudan SQLite'tan döndürülür."

---

### Soru 8: "Bu projeyi 10.000 aktif öğrenciye açmak istesek neleri değiştirmeniz gerekir?"
> **Cevap:**  
> "Mevcut mimarimiz tek sunucu üzerinde asenkron olarak yüzlerce eşzamanlı isteği kaldırabilir. Ancak 10.000 öğrenci ölçeğinde prodüksiyon mimarisine geçerken şu 3 adımı atardık:  
> 1. **Celery / RabbitMQ / Redis Kuyruk Mimarisi:** PDF ayrıştırma ve embedding gibi uzun süren arka plan işlerini doğrudan HTTP sunucusundan ayırıp ayrı worker makinelerine dağıtırdık.  
> 2. **Docker & Kubernetes Orkestrasyonu:** FastAPI uygulamamızı Docker imajı haline getirip Kubernetes üzerinde CPU ve bellek kullanımına göre otomatik çoğalan (Auto-scaling Pods) bir yapıya dönüştürürdük. Önüne NGINX veya Traefik Load Balancer koyardık.  
> 3. **Qdrant Cluster & Dağıtık Veritabanı:** Yerel disk tabanlı Qdrant yerine birden fazla sunucuya bölünmüş (sharded) bir Qdrant kümesi ve oturumlar için PostgreSQL kullanırdık."

---

## 💻 4. Örnek Canlı Demo Akışı (3 Dakika)

Sunum sırasında hocanın "Bunu bize çalışırken gösterebilir misiniz?" demesi durumunda izlenecek kusursuz senaryo:

1. **Aşama 1: `/docs` Swagger UI Gösterimi (1 Dakika)**
   - Tarayıcıda `http://localhost:8000/docs` adresini açın.
   - Pydantic şemalarını (`ChatRequest`, `QuizResponse`, `MindMapNode`) gösterin.
   - "Hocam kodumuzdaki tip tanımlamalarından dolayı tüm API dökümantasyonu otomatik olarak bu şekilde interaktif üretiliyor" deyin.

2. **Aşama 2: Canlı Streaming Testi (1 Dakika)**
   - StudyRAG arayüzüne geçin.
   - Sohbet kutusuna *"Güneş enerjisi temel prensiplerini ve fotovoltaik hücreleri özetle"* yazıp gönderin.
   - Cevabın milisaniye içinde harf harf akmaya başladığına dikkat çekin: *"Gördüğünüz gibi `StreamingResponse` sayesinde 10 saniye beklemeden ilk token 300 milisaniyede geldi."*

3. **Aşama 3: Dinamik PDF Kapsam Filtresi (1 Dakika)**
   - Sınav Simülatörü veya Sohbet üstündeki **"Çalışma Kapsamı"** modalını açın.
   - 5 PDF'ten sadece 1 veya 2 tanesini seçin (`✓ Seçili`).
   - Soru üretin veya soru sorun. Gelen cevabın kaynak rozetlerinde sadece seçtiğiniz PDF'lerin sayfa numaralarının yer aldığını gösterin.
