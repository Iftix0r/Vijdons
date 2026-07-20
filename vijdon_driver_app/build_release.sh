#!/bin/bash
# Haydovchilarga tarqatiladigan release APK'ni quradi.
#
# Diqqat: shunchaki "flutter build apk --release" universal (barcha protsessor
# arxitekturasi — arm64-v8a, armeabi-v7a, x86, x86_64 — uchun) APK quradi —
# bu ~47MB bo'ladi va eski/joyi kam telefonlarda "joy yetarli emas" xatosi
# bilan o'rnatilmay qolishi mumkin.
#
# Avval faqat --target-platform android-arm (32-bit armeabi-v7a) bilan
# qurilgan edi, "ARM protsessorlar orqaga moslashuvchan" degan taxmin bilan —
# lekin bu NOTO'G'RI chiqdi: ko'plab zamonaviy (64-bit-only) qurilmalar
# 32-bit kutubxonalarni UMUMAN topa olmaydi va ilova ochilishi bilan
# "Could not find libflutter.so... only found armeabi-v7a" xatosi bilan
# yopilib qoladi. Shu sabab endi HAM 32-bit (armeabi-v7a) HAM 64-bit
# (arm64-v8a) kutubxonalari bitta APK ichiga qo'shib quriladi — hajmi
# universal (~47MB) dan ancha kichik qoladi (~25-30MB), chunki faqat shu
# ikkitasi qo'shiladi, x86/x86_64 (haydovchi telefonlarida deyarli
# uchramaydigan, faqat emulyatorlarga kerak arxitekturalar) qo'shilmaydi.
set -e
cd "$(dirname "$0")"
flutter build apk --release --target-platform android-arm,android-arm64
echo ""
echo "Tayyor: build/app/outputs/flutter-apk/app-release.apk"
ls -lh build/app/outputs/flutter-apk/app-release.apk
