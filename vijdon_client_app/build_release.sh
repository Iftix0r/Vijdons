#!/bin/bash
# Yo'lovchilarga tarqatiladigan release APK'ni quradi.
#
# vijdon_driver_app/build_release.sh bilan bir xil sabablarga ko'ra faqat
# armeabi-v7a + arm64-v8a kiritiladi (x86/x86_64 emulyator uchun, real
# telefonlarda deyarli uchramaydi) — hajmni kichraytirish uchun.
set -e
cd "$(dirname "$0")"
flutter build apk --release --target-platform android-arm,android-arm64
echo ""
echo "Tayyor: build/app/outputs/flutter-apk/app-release.apk"
ls -lh build/app/outputs/flutter-apk/app-release.apk
