#!/bin/bash
# Haydovchilarga tarqatiladigan release APK'ni quradi.
#
# Diqqat: shunchaki "flutter build apk --release" universal (barcha protsessor
# arxitekturasi uchun) APK quradi — bu ~47MB bo'ladi va eski/joyi kam
# telefonlarda "joy yetarli emas" xatosi bilan o'rnatilmay qolishi mumkin.
#
# --target-platform android-arm bilan faqat 32-bit ARM (armeabi-v7a) uchun
# quramiz — hajmi ~3 baravar kichikroq (~14-15MB) bo'ladi. ARM protsessorlar
# orqaga moslashuvchan bo'lgani uchun bu yangi (64-bit) telefonlarda ham
# muammosiz ishlayveradi.
set -e
cd "$(dirname "$0")"
flutter build apk --release --target-platform android-arm
echo ""
echo "Tayyor: build/app/outputs/flutter-apk/app-release.apk"
ls -lh build/app/outputs/flutter-apk/app-release.apk
