# WolfHost — بوت التحكم في تيليجرام

بوت تيليجرام تحكّم كامل مبني على `aiogram 3` يغطي كل ميزات لوحة الويب
(`frontend/src/app/dashboard`): إدارة البوتات، مدير الملفات، طرفية محدودة،
والإعدادات — عبر REST API فقط، دون لمس قاعدة البيانات مباشرة.

## المتغيرات المطلوبة في `.env` (بالمجلد الجذري للمشروع `wolfhost/`)

```env
# مفتاح ثابت يُستخدم من طرف البوت للمصادقة مع الباك اند (بديل عن JWT)
BOT_CONTROL_API_KEY=<قيمة عشوائية طويلة وقوية>

# صاحب الحساب الوحيد الذي سيُستخدم مع BOT_CONTROL_API_KEY (موجود مسبقًا في المشروع)
ADMIN_EMAIL=admin@wolfhost.local

TELEGRAM_BOT_TOKEN=<توكن البوت من BotFather>
TELEGRAM_ALLOWED_USER_ID=<الـ Telegram user_id الوحيد المسموح له بالتحكم>
WOLFHOST_API_BASE_URL=http://backend:8000/api/v1
WOLFHOST_API_KEY=${BOT_CONTROL_API_KEY}
```

> **مهم لمعرفة `TELEGRAM_ALLOWED_USER_ID`:** أرسل أي رسالة لبوتك عبر
> [@userinfobot](https://t.me/userinfobot) في تيليجرام ليعطيك رقم الـ user_id الخاص بك.

## التشغيل

الخدمة مُضافة بالفعل إلى `docker-compose.yml` الرئيسي باسم `telegram_control_bot`،
وتعمل مع باقي الخدمات بأمر واحد من جذر المشروع:

```bash
docker compose up -d --build
```

البوت يعمل بـ **Long Polling** فقط (لا يفتح أي منفذ وارد)، ويعتمد على وصول
شبكي داخلي إلى خدمة `backend` عبر `wolfhost_internal`.

## الأمان

- أي مستخدم تيليجرام غير `TELEGRAM_ALLOWED_USER_ID` يُتجاهل بالكامل وبصمت
  (بدون أي رد يكشف وجود البوت) — انظر `bot/middlewares/auth.py`.
- أي عملية حساسة (حذف بوت، حذف ملف، تنفيذ أمر طرفية) تتطلب ضغط زر
  "✅ تأكيد" قبل التنفيذ الفعلي. تفاصيل العملية تُخزَّن مؤقتًا (بحد أقصى 5
  دقائق) في ذاكرة العملية فقط، وليس داخل `callback_data` نفسها ولا بشكل
  دائم — انظر `bot/utils.py::create_pending_action`.
- حالة المحادثة (FSM) تُخزَّن في الذاكرة فقط (`MemoryStorage`) وتُمسح عند
  إعادة تشغيل الحاوية — لا نص لملفات أو أوامر يُخزَّن على القرص.
- كلمة المرور الحالية/الجديدة عند تغييرها تُرسل كرسالة نصية عادية من
  المستخدم، ويقوم البوت بحذفها فورًا من المحادثة بعد معالجتها.
- الطرفية المحدودة تستخدم *نفس* endpoint ونفس قائمة الأوامر البيضاء
  المستخدمة في لوحة الويب (`ALLOWED_CONSOLE_COMMANDS` في
  `backend/app/api/v1/endpoints/bots.py`) — لا صلاحيات إضافية.

## تعديلات أُضيفت على الباك اند (كانت ناقصة قبل هذا البوت)

| الإضافة | الملف | السبب |
|---|---|---|
| دعم `X-API-Key` في `get_current_user` | `backend/app/core/dependencies.py` | لم يوجد أي مسار مصادقة غير JWT؛ البوت يحتاج مفتاحًا ثابتًا من `.env` بدل تسجيل دخول تفاعلي |
| `GET /users/me/audit-logs` | `backend/app/api/v1/endpoints/users.py` | لم يكن هناك أي endpoint لعرض سجل التدقيق (`AuditLog`)، فقط كتابة داخلية |
| `POST /bots/{bot_id}/files/copy` | `backend/app/api/v1/endpoints/bots.py` | `FileManager.copy()` كانت موجودة في الخدمة لكن بلا route مكشوف |
| `GET /bots/{bot_id}/files/download` | `backend/app/api/v1/endpoints/bots.py` + `file_manager.py` | endpoint المحتوى القديم (`/files/content`) يقرأ الملف كنص فقط (`errors="replace"`) ويُتلف الملفات غير النصية؛ التحميل الحقيقي يحتاج بايتات خام |

## هيكلة الكود

```
telegram-control-bot/
  Dockerfile
  requirements.txt
  bot/
    config.py          # إعدادات من .env
    api_client.py       # عميل REST (X-API-Key فقط)
    states.py            # FSM لتدفقات إنشاء البوت/تعديل الملفات/الطرفية...
    keyboards.py          # كل لوحات الأزرار InlineKeyboard + Pagination
    utils.py               # تنسيق، ومخزن التأكيد المؤقت، ومهام السجلات الحية
    middlewares/auth.py      # قفل البوت على مستخدم تيليجرام واحد
    handlers/
      start.py, bots.py, bot_create.py, files.py,
      console.py, env.py, logs.py, settings_menu.py,
      confirm.py, fallback.py
    main.py               # نقطة الدخول (Long Polling)
```
