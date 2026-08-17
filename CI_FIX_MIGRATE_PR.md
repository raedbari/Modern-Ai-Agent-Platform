# CI Fix: Diagnostic Migrate Entrypoint

## ✅ التنفيذ مكتمل

### الملفات المعدلة (4 ملفات):

1. **backend/ci_migrate_entrypoint.sh** (NEW)
   - Diagnostic shell script
   - يطبع: user, paths, alembic.ini location, env vars
   - يشغّل: alembic upgrade head
   - Executable: chmod +x

2. **backend/Dockerfile**
   - يضيف: COPY ci_migrate_entrypoint.sh
   - يجعله executable داخل الصورة

3. **compose.local.yaml**
   - خدمة migrate تشغّل: /app/backend/ci_migrate_entrypoint.sh
   - بدل الأمر القديم

4. **.github/workflows/pr-quality.yml**
   - خطوة جديدة: "Ensure .env.compose.ci exists"
   - تنشئ .env.compose.ci إذا ما كان موجود
   - تستخدم GitHub secrets

---

## 🎯 الهدف

إصلاح فشل migrate في CI (exit 255) بإضافة diagnostic logging لتحديد السبب الحقيقي.

---

## 📋 الخطوات المنفذة

```bash
# 1. إنشاء فرع
git checkout -b ci/fix-migrate

# 2. إنشاء diagnostic script
# ✅ backend/ci_migrate_entrypoint.sh

# 3. تعديل Dockerfile
# ✅ يضيف COPY + chmod

# 4. تعديل compose.local.yaml
# ✅ migrate service يشغّل script

# 5. تعديل workflow
# ✅ خطوة "Ensure .env.compose.ci exists"

# 6. Commit
git add backend/ci_migrate_entrypoint.sh backend/Dockerfile compose.local.yaml .github/workflows/pr-quality.yml
git commit -m "ci(migrate): add diagnostic migrate entrypoint, wire into Dockerfile & compose, ensure .env.compose.ci exists in CI"

# 7. Push
git push -u origin ci/fix-migrate
```

---

## 🧪 اختبار محلي

```bash
# إنشاء .env.compose.ci
cat > .env.compose.ci <<EOF
MAAP_POSTGRES_PASSWORD=changeme
MAAP_POSTGRES_USER=maap
MAAP_POSTGRES_DB=maap
MAAP_POSTGRES_PORT=5433
EOF

# تشغيل migrate
docker compose --env-file .env.compose.ci -f compose.local.yaml up migrate

# عرض السجلات
docker compose --env-file .env.compose.ci -f compose.local.yaml logs migrate --no-log-prefix
```

---

## 🔍 ما يجب البحث عنه في السجلات

1. **=== CI MIGRATE ENTRYPOINT ===**
2. **User: 10001:10001**
3. **CWD: /app**
4. **Listing /app:** (يعرض الملفات)
5. **Listing /app/backend:** (يعرض الملفات)
6. **Found /app/backend/alembic.ini** أو **ALEMBIC_INI_NOT_FOUND**
7. **MAAP_POSTGRES_USER=maap**
8. **Running alembic (upgrade head)...**
9. **=== MIGRATE COMPLETED ===**

---

## 📝 PR Details

**Branch:** ci/fix-migrate
**Title:** "ci: diagnostic migrate entrypoint + ensure .env.compose.ci in CI"

**Description:**
- هدف: إضافة مدخل تشخيصي لـ migrate ليطبع سياق الحاوية ثم يشغّل alembic
- سبب: migrate كانت تفشل بـ exit 255؛ هذا يزودنا بسجلات تفصيلية
- أمان: لا نعرض كلمات السر في السجلات

**Files Changed:**
- backend/ci_migrate_entrypoint.sh (NEW)
- backend/Dockerfile
- compose.local.yaml
- .github/workflows/pr-quality.yml

---

## ✅ الحالة

- [x] الفرع منشأ
- [x] الملفات معدلة (4 ملفات)
- [x] Commit مكتمل
- [ ] Push (يحتاج authentication - راجع git config)
- [ ] PR مفتوح (بعد push ناجح)

---

## 🚀 الخطوة التالية

**إذا الـ push فشل:**
```bash
# تأكد من git config
git config --list | grep remote

# أو push يدوياً من IDE/GitHub Desktop
```

**بعد push ناجح:**
1. افتح PR في GitHub
2. انتظر CI يشتغل
3. راجع سجلات migrate في workflow logs
4. حلل السبب وطبّق الحل الدائم

---

## 📞 المساعدة

إذا واجهت مشكلة:
1. شارك سجلات migrate
2. شارك رابط PR
3. سأحلل وأقدّم التوصيات
