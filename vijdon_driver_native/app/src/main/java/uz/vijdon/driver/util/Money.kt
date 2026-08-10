package uz.vijdon.driver.util

import java.util.Locale

/**
 * Server pul qiymatlarini har doim "8500.00" kabi kasr qismi bilan qator
 * sifatida beradi (Decimal serializatsiyasi) — kasr qismi olib tashlanadi
 * va veb'dagi `toLocaleString('uz-UZ')` bilan bir xil, minglik xonalar
 * bo'sh joy bilan ajratiladi ("39629" -> "39 629"), o'qishni osonlashtirish
 * uchun. `Locale.US` ataylab qo'yilgan — aks holda qurilma tili
 * o'zbek/rus bo'lsa, kasr ajratuvchisi vergul (","), butun ilova esa
 * nuqta (".") kutadi.
 */
fun formatMoney(raw: String?): String {
    if (raw == null) return "0"
    val value = raw.toDoubleOrNull() ?: return raw
    val whole = String.format(Locale.US, "%.0f", value)
    val negative = whole.startsWith("-")
    val digits = if (negative) whole.substring(1) else whole
    val grouped = digits.reversed().chunked(3).joinToString(" ").reversed()
    return if (negative) "-$grouped" else grouped
}
