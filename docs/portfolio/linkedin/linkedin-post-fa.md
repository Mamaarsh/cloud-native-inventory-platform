# متن فارسی لینکدین

مدتی بود که می‌خواستم یادگیری ابزارهای DevOps را از حالت جزیره‌ای خارج کنم و آن‌ها را در یک پروژه واقعی کنار هم قرار دهم؛ نه فقط چند فایل YAML و یک سرویس Hello World، بلکه اپلیکیشنی که رفتار، داده، ذخیره‌سازی، انتشار و مانیتورینگ آن واقعاً به هم وابسته باشند.

نتیجه، پروژه **Cloud Native Inventory Platform** شد: یک سامانه مدیریت کالا، انبار و سفارش با Django REST Framework و React که PostgreSQL، Redis و Celery را هم در مسیر واقعی برنامه استفاده می‌کند. قابلیت‌هایی مثل احراز هویت JWT، کنترل دسترسی مبتنی بر نقش، تغییرات تراکنشی موجودی، تاریخچه سفارش، Audit Log و آپلود تصویر محصول، workload این آزمایشگاه DevOps را تشکیل می‌دهند.

در محیط محلی، Docker Compose تمام سرویس‌ها را اجرا می‌کند. در مسیر تحویل، Push روی GitHub با GitHub Actions به Hamgit/GitLab همگام می‌شود. GitLab CI ابتدا ۲۴۶ تست backend، lint و build فرانت‌اند و دسترسی GitLab Kubernetes Agent را بررسی می‌کند. سپس imageها با base imageهای عبوری از Nexus ساخته می‌شوند، با tag دقیق commit در registry داخلی ذخیره می‌شوند و Trivy قبل از deploy آن‌ها را از نظر آسیب‌پذیری‌های قابل‌رفع HIGH و CRITICAL اسکن می‌کند. فقط بعد از عبور از این gate، migration اجرا و نسخه دقیق همان commit روی کلاستر kubeadm منتشر می‌شود.

سه چالش این پروژه برای من از خود نصب ابزارها مهم‌تر بودند:

اول، مسیر GitLab Runner به Nexus روی پورت 8083 دچار اختلال شد. با تفکیک لایه‌های شبکه، listener و Docker connector مشخص شد endpoint مورد انتظار HTTP با connector اشتباه HTTPS بالا آمده است. معماری دور زده نشد؛ connector و تنظیم trust خود Runner اصلاح شدند تا همان مسیر داخلی دوباره کار کند.

دوم، تصویر محصول در چند Pod به فضای مشترک و ماندگار نیاز داشت. volume موقت پاسخ‌گو نبود و سیاست سه replica نیز با ظرفیت آزمایشگاه دو worker سازگار نبود. یک StorageClass اختصاصی Longhorn با RWX، ظرفیت 2 GiB، دو replica روی worker-1 و worker-2 و share-manager ایجاد شد. backend روی `/app/media` می‌نویسد و frontend همان داده را از `/var/www/media` فقط‌خواندنی ارائه می‌کند؛ تصاویر بعد از restart شدن Podها باقی می‌مانند.

سوم، gate امنیتی واقعاً اثر گذاشت: Trivy آسیب‌پذیری HIGH با شناسه `CVE-2026-93990` را در `libexpat 2.8.4-r0` پیدا کرد و deploy را متوقف کرد. runtime image بدون ضعیف‌کردن policy یا ignore کردن CVE به `2.8.5-r0` ارتقا یافت؛ اسکن بعدی بدون finding عبور کرد و نسخه اصلاح‌شده منتشر شد.

برای observability از kube-prometheus-stack، Prometheus، Grafana، node-exporter، kube-state-metrics و metricهای NGINX Ingress استفاده شده است. dashboard نیز به‌صورت کد در repository نگهداری می‌شود.

این پروژه را «production-oriented» می‌دانم، نه production-ready: TLS خودکار، secret manager خارجی، logging متمرکز، tracing، HA کامل داده و چرخه DR هنوز در roadmap هستند.

کد و مستندات:
https://github.com/Mamaarsh/cloud-native-inventory-platform

#DevOps #Kubernetes #Docker #CICD #GitLabCI #DevSecOps #Prometheus #Grafana #CloudNative #Linux
