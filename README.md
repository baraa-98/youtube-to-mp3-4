# YouTube → MP3/MP4 Telegram Bot

## تشغيل محلي (اختبار سريع)
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="التوكن بتاعك"
python bot.py
```
لازم يكون ffmpeg مثبت على جهازك (`sudo apt install ffmpeg` على لينكس/Termux).

## Deploy على Railway
1. اعمل bot توكن جديد من [@BotFather](https://t.me/BotFather) على تليجرام (`/newbot`).
2. اعمل push للمجلد ده على GitHub repo.
3. في Railway: New Project → Deploy from GitHub repo.
4. في Variables ضيف: `TELEGRAM_BOT_TOKEN` = التوكن اللي جبته من BotFather.
5. Railway هيقرأ `nixpacks.toml` تلقائي ويثبت ffmpeg، ومفيش حاجة تانية مطلوبة.
6. بعد الـ deploy، ابعت `/start` للبوت على تليجرام.

## ملاحظات مهمة
- حد رفع الملفات في تليجرام العادي 50MB، فالفيديو بيتحمّل بجودة 480p علشان يفضل تحت الحد ده غالبًا.
- الأداة دي بتستخدم yt-dlp اللي بيخالف Terms of Service بتاعة يوتيوب، وتحميل محتوى محمي بحقوق نشر من غير إذن مشكلة قانونية في أغلب الدول. استخدمها لمحتواك أو لمحتوى معاك ترخيص له.
- لو عايز تحسينات بعدين: قائمة انتظار (queue) لو أكتر من مستخدم بيحمّل في نفس الوقت، اختيار جودة يدوي، أو حد أقصى لطول الفيديو.
