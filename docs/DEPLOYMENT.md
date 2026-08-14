# دليل النشر — Wolf Host + telegram-control-bot على AWS Lightsail

نشر بدون Kubernetes، باستخدام Docker Compose فقط، على Ubuntu 22.04/24.04.

## المتطلبات

- حساب AWS مع صلاحية إنشاء Lightsail instance
- دومين يمكنك توجيه DNS الخاص به (A record)

## 1. إنشاء Lightsail Instance

1. AWS Console → Lightsail → Create instance
2. Platform: **Linux/Unix** → Blueprint: **OS Only → Ubuntu 24.04 LTS**
3. الخطة (Instance plan) الموصى بها لهذا الحمل (backend + frontend + postgres +
   redis + celery worker/beat + telegram bot + nginx):
   - **الحد الأدنى المقبول:** 2 GB RAM / 1 vCPU / 60GB SSD (حوالي $10/شهر)
   - **1 GB RAM غير كافية** — عدد الحاويات (7 خدمات) والحمل الأساسي لنظام
     Ubuntu + Docker يستهلكان أكثر من ذلك بسهولة.
   - لو تتوقع عدد بوتات مستضافة كبير عبر الميزة الأساسية للمشروع، فكّر في
     4 GB RAM / 2 vCPU مستقبلًا (يمكن الترقية لاحقًا من نفس اللوحة).
4. اختر Static IP لاحقًا من تبويب Networking (خطوة 4).

## 2. ربط الدومين

في مزوّد الدومين لديك، أنشئ سجل DNS:

```
Type: A
Name: @ (أو subdomain مثل panel)
Value: <Lightsail Static IP>
```

## 3. رفع المشروع للسيرفر

```bash
scp -i your-key.pem -r wolfhost ubuntu@<STATIC_IP>:~/
ssh -i your-key.pem ubuntu@<STATIC_IP>
cd ~/wolfhost
```

## 4. ضبط منافذ الشبكة (Lightsail Networking tab)

من لوحة Lightsail → Instance → تبويب **Networking** → افتح فقط:

| Port | Protocol | الوصف |
|------|----------|-------|
| 22   | TCP      | SSH   |
| 80   | TCP      | HTTP (تحدي Let's Encrypt + إعادة توجيه لـ HTTPS) |
| 443  | TCP      | HTTPS (الموقع الفعلي) |

لا تفتح أي منفذ آخر (5432 لـ Postgres، 6379 لـ Redis، 8000 لـ FastAPI...).
هذه المنافذ أصلًا **غير منشورة على المضيف** في `docker-compose.yml`
(لا يوجد لها `ports:`) — تتواصل فيما بينها فقط عبر شبكة Docker الداخلية
`wolfhost_internal`. المنفذ الوحيد المكشوف فعليًا هو nginx (80/443).

اختياري (طبقة حماية إضافية على مستوى النظام نفسه):
```bash
bash scripts/setup-firewall.sh
```

## 5. إعداد ملف البيئة

```bash
cp .env.example .env
nano .env
```

املأ على الأقل:
- `DOMAIN_NAME` و`CERTBOT_EMAIL`
- `SECRET_KEY` (`openssl rand -hex 32`)
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `BOT_CONTROL_API_KEY` (قيم عشوائية قوية)
- `ADMIN_EMAIL` / `ADMIN_PASSWORD`
- `TELEGRAM_BOT_TOKEN` و`TELEGRAM_ALLOWED_USER_ID`
- `CORS_ORIGINS` و`NEXT_PUBLIC_API_URL` بنفس الدومين (`https://...`)
- (اختياري) متغيرات `LIGHTSAIL_BUCKET_*` للنسخ الاحتياطي — راجع القسم 7

## 6. النشر

سكربت واحد يقوم بكل شيء: تثبيت Docker (لو غير مثبت)، بناء الصور
(بما فيها telegram_control_bot)، تشغيل قاعدة البيانات، الترحيلات، تشغيل كل
الخدمات، والحصول على شهادة SSL تلقائيًا:

```bash
bash scripts/deploy.sh
```

بعدها يجب أن يكون الموقع متاحًا على `https://<DOMAIN_NAME>`.

تحقق من الحالة:
```bash
docker compose ps
bash scripts/healthcheck.sh
docker compose logs -f backend
```

## 7. النسخ الاحتياطي (محلي + Lightsail Object Storage)

### إنشاء Bucket يدويًا (مرة واحدة فقط)

1. AWS Console → Lightsail → **Storage** → **Create bucket**
2. اختر نفس المنطقة (Region) الخاصة بالـ Instance، واسمًا فريدًا عالميًا
3. اختر أصغر Bundle (يمكن تغييره لاحقًا)، واترك **Block public access** مفعّلة
4. بعد الإنشاء: افتح الـ Bucket → تبويب **Permissions** → **Create access key**
   → احفظ Access Key ID وSecret Access Key (تظهر مرة واحدة فقط)
5. من تبويب **Connect to your bucket** في نفس الصفحة يمكنك رؤية الـ endpoint
   الدقيق الخاص بمنطقتك للتأكد منه إن اختلف عن الصيغة الافتراضية

### ضبط `.env`

```
LIGHTSAIL_BUCKET_NAME=your-bucket-name
LIGHTSAIL_BUCKET_REGION=us-east-1
LIGHTSAIL_ACCESS_KEY_ID=...
LIGHTSAIL_SECRET_ACCESS_KEY=...
```

### تثبيت aws CLI وتشغيل النسخ الاحتياطي

```bash
sudo apt-get install -y awscli
bash scripts/backup.sh
```

### جدولة تلقائية (crontab)

```bash
crontab -e
```

أضف:
```
# نسخة احتياطية يومية الساعة 2 صباحًا
0 2 * * * cd /home/ubuntu/wolfhost && bash scripts/backup.sh >> /home/ubuntu/wolfhost/logs/backup.log 2>&1
# تجديد شهادة SSL يوميًا الساعة 3 صباحًا (لا يجدد إلا عند الاقتراب من الانتهاء)
0 3 * * * cd /home/ubuntu/wolfhost && bash scripts/renew-ssl.sh >> /home/ubuntu/wolfhost/logs/renew-ssl.log 2>&1
```

```bash
mkdir -p ~/wolfhost/logs
```

## 8. التحديث لاحقًا

```bash
cd ~/wolfhost
git pull   # أو ارفع الملفات المحدثة عبر scp
docker compose build
docker compose up -d
docker compose run --rm backend alembic upgrade head
```
