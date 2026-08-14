#!/bin/bash
# جدار ناري إضافي على مستوى نظام Ubuntu نفسه (طبقة حماية ثانية فوق
# Lightsail Networking Firewall الذي يجب ضبطه من لوحة تحكم AWS Lightsail).
#
# هذا اختياري لكنه موصى به: حتى لو نُسي منفذ مفتوح بالخطأ في لوحة Lightsail،
# يمنع UFW أي اتصال لأي منفذ غير 22/80/443.
set -euo pipefail

echo "تثبيت وضبط UFW للسماح فقط بمنافذ 22 (SSH), 80 (HTTP), 443 (HTTPS)..."
sudo apt-get update -y
sudo apt-get install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

sudo ufw --force enable
sudo ufw status verbose

echo ""
echo "تنبيه: Docker يتجاوز أحيانًا قواعد UFW الافتراضية لأنه يكتب قواعده الخاصة"
echo "في iptables مباشرة. في هذا المشروع لا مشكلة لأن كل الخدمات الداخلية"
echo "(postgres, redis, backend, frontend, telegram_control_bot) لا تنشر أي"
echo "منفذ (ports:) على المضيف إطلاقًا في docker-compose.yml — فقط nginx ينشر"
echo "80 و443. لذلك لا توجد منافذ داخلية مكشوفة للإنترنت أصلاً."
