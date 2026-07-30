# دليل التشغيل المحلي لمنصة MAAP

هذا التشغيل مخصص للتطوير والـPilot المحلي. قاعدة PostgreSQL معزولة داخل
Docker، والـAPI لا يستمع إلا على `127.0.0.1` حتى نضيف بوابة HTTPS آمنة
ومصادقة مناسبة للـWidget.

## المتطلبات

- Docker Desktop يعمل.
- Ollama يعمل على `http://127.0.0.1:11434`.
- نموذج `qwen3-embedding:0.6b` مثبت.
- مفتاح DeepSeek الحقيقي محفوظ داخل `backend/.env` فقط.

## بدء البيئة

من جذر المشروع في PowerShell:

```powershell
.\scripts\local-up.ps1 -Build
```

السكربت يقوم آليًا بما يلي:

1. يتحقق من Docker وOllama ونموذج Embeddings.
2. ينشئ `.env.compose` بكلمة مرور عشوائية إذا لم يكن موجودًا.
3. يشغّل PostgreSQL 16 مع `pgvector 0.8.6`.
4. يطبق Alembic migrations.
5. يشغّل FastAPI ويتحقق من `/ready`.

## إنشاء أول عميل ووكيل

```powershell
docker compose --env-file .env.compose -f compose.local.yaml exec api `
  python -m backend.app.cli.bootstrap_customer `
  --tenant-id tenant-demo `
  --tenant-name "Demo Tenant" `
  --agent-id agent-demo `
  --agent-name "Demo Agent" `
  --system-prompt "أجب اعتمادًا على المعرفة الموثقة فقط."
```

سيظهر مفتاح API مرة واحدة فقط. لا تضع هذا المفتاح داخل `widget.js` أو أي
كود يصل إلى متصفح العميل.

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
