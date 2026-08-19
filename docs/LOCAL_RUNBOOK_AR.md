# دليل التشغيل المحلي لمنصة MAAP

هذا التشغيل مخصص للتطوير والـPilot المحلي. قاعدة PostgreSQL معزولة داخل
Docker، والـAPI لا يستمع إلا على `127.0.0.1` حتى نضيف بوابة HTTPS آمنة
ومصادقة مناسبة للـWidget.

## المتطلبات

- Docker Desktop يعمل.
- مفتاحا DeepSeek وVoyage متاحان ومحفوظان في ملفات البيئة المحلية فقط.

## بدء البيئة

من جذر المشروع في PowerShell:

```powershell
Copy-Item .env.compose.example .env.compose
Copy-Item backend\.env.example backend\.env
```

استبدل القيم المؤقتة للمتغيرين `MAAP_DEEPSEEK_API_KEY` و
`MAAP_VOYAGE_API_KEY` داخل `.env.compose`، ثم شغّل البيئة:

```powershell
docker compose --env-file .env.compose -f compose.local.yaml up -d --build
```

يشغّل Compose قاعدة PostgreSQL 16 مع `pgvector 0.8.6`، ويطبق Alembic
migrations، ثم يشغّل FastAPI وWorker منفصلًا لمعالجة الملفات. يستخدم DeepSeek
للتوليد وVoyage للـEmbeddings وإعادة الترتيب.

## إنشاء أول عميل وChatbot

```powershell
docker compose --env-file .env.compose -f compose.local.yaml exec api `
  python -m backend.app.cli.bootstrap_customer `
  --tenant-id tenant-demo `
  --tenant-name "Demo Tenant" `
  --agent-id agent-demo `
  --agent-name "Demo Chatbot" `
  --system-prompt "أجب اعتمادًا على المعرفة الموثقة فقط." `
  --contact-message "لا أملك معلومات مؤكدة كافية. تواصل مع الشركة على 012345678 أو support@example.com."
```

سيظهر مفتاح API مرة واحدة فقط. لا تضع هذا المفتاح داخل `widget.js` أو أي
كود يصل إلى متصفح العميل.

## رفع الملفات بطريقة غير متزامنة

للعملاء استخدم:

```text
POST /api/knowledge-bases/{knowledge_base_id}/document-jobs
```

يعيد الطلب `202` مع `job_id`. تابع الحالة عبر:

```text
GET /api/knowledge-bases/{knowledge_base_id}/document-jobs/{job_id}
```

الـAPI يحتفظ بالملف الأصلي داخل Volume خاص، والـWorker ينفذ Parsing وChunking
وVoyage Embeddings. لا ينتظر طلب HTTP انتهاء الفهرسة.

## المحادثة ورسالة التواصل

المسار العام الوحيد للمحادثة هو:

```text
POST /api/chat
```

عندما يكون `knowledge_mode=required` ولا توجد معرفة كافية، لا يُستدعى نموذج
التوليد، ولا تُنشأ أي عملية تحويل أو رد بشري داخل المنصة. يعيد الـChatbot نص
`contact_message` الخاص به، وفيه أرقام الشركة أو بريدها أو قنوات التواصل
المعتمدة.

## التحقق

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready

docker compose --env-file .env.compose -f compose.local.yaml ps
docker compose --env-file .env.compose -f compose.local.yaml logs --tail 100
```

## الإيقاف دون حذف البيانات

```powershell
docker compose --env-file .env.compose -f compose.local.yaml down
```

لا تستخدم `down -v`؛ الخيار `-v` يحذف Volume قاعدة البيانات.
