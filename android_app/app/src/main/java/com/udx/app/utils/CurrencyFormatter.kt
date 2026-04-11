package com.udx.app.utils

import java.text.NumberFormat
import java.util.Locale

object CurrencyFormatter {

    private const val CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"

    val CURRENCY_SYMBOLS = mapOf(
        "USD" to "$",   "EUR" to "€",   "GBP" to "£",
        "JPY" to "¥",   "CNY" to "¥",   "KRW" to "₩",
        "RUB" to "₽",   "TRY" to "₺",   "KZT" to "₸",
        "KGS" to "с",   "TJS" to "SM",  "TMT" to "T",
        "AZN" to "₼",   "GEL" to "₾",   "AMD" to "֏",
        "UAH" to "₴",   "BYN" to "Br",  "CHF" to "Fr",
        "SAR" to "﷼",   "AED" to "د.إ", "QAR" to "﷼",
        "KWD" to "د.ك", "BHD" to "BD",  "INR" to "₹",
        "PKR" to "₨",   "BDT" to "৳",   "IDR" to "Rp",
        "MYR" to "RM",  "SGD" to "S$",  "THB" to "฿",
        "VND" to "₫",   "PHP" to "₱",   "HKD" to "HK$",
        "CAD" to "CA$", "AUD" to "A$",  "NZD" to "NZ$",
        "MXN" to "MX$", "BRL" to "R$",  "ZAR" to "R",
        "NOK" to "kr",  "SEK" to "kr",  "DKK" to "kr",
        "PLN" to "zł",  "CZK" to "Kč",  "HUF" to "Ft",
        "RON" to "lei", "BGN" to "лв",  "ILS" to "₪",
        "EGP" to "E£",  "MNT" to "₮",   "AFN" to "؋",
        "LAK" to "₭",   "IRR" to "﷼",   "MDL" to "L",
        "RSD" to "din", "UYU" to "\$U", "ARS" to "AR$",
        "BND" to "B$",  "JOD" to "JD",  "OMR" to "﷼"
    )

    /**
     * CBU API dan kurslarni oladi.
     * Qaytaradi: Map<valyuta kodi, 1 USD uchun qancha shu valyuta>
     * Masalan: "RUB" -> 77.9, "UZS" -> 12198.0, "USD" -> 1.0
     * Shuningdek date ni qaytaradi: Pair(rates, "10.04.2026")
     */
    suspend fun fetchCbuRates(): Pair<Map<String, Double>, String> {
        return kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            val json = java.net.URL(CBU_URL).readText()
            val array = org.json.JSONArray(json)

            var usdRateInUzs = 12198.28 // fallback
            var ratesDate = ""

            // Avval USD kursini topamiz
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                if (obj.getString("Ccy") == "USD") {
                    val nominal = obj.getString("Nominal").toIntOrNull() ?: 1
                    usdRateInUzs = obj.getString("Rate").toDoubleOrNull()?.div(nominal) ?: usdRateInUzs
                    ratesDate = obj.optString("Date", "")
                    break
                }
            }

            val result = mutableMapOf<String, Double>()
            result["USD"] = 1.0
            // UZS = USD kursining o'zi (1 USD = usdRateInUzs so'm)
            result["UZS"] = usdRateInUzs

            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                val code = obj.getString("Ccy")
                if (code == "USD") continue
                val nominal = obj.getString("Nominal").toIntOrNull() ?: 1
                val rateInUzs = obj.getString("Rate").toDoubleOrNull()?.div(nominal) ?: continue
                if (rateInUzs > 0) {
                    result[code] = usdRateInUzs / rateInUzs
                }
            }

            Pair(result, ratesDate)
        }
    }

    /** X so'm formatida chiqaradi: "152 875 so'm" */
    fun formatUzs(usdPrice: Double, uzsRate: Double = 12198.28): String {
        val uzs = (usdPrice * uzsRate).toLong()
        val formatted = NumberFormat.getNumberInstance(Locale("ru")).format(uzs)
        return "$formatted so'm"
    }

    /** USD narxini tanlangan valyutaga konvert qilib formatlaydi */
    fun formatPrice(usdPrice: Double, currency: String, rate: Double): String {
        if (currency == "UZS") return formatUzs(usdPrice, rate)
        val converted = usdPrice * rate
        val symbol = CURRENCY_SYMBOLS[currency] ?: "$currency "
        return "$symbol${String.format("%.2f", converted)}"
    }
}
