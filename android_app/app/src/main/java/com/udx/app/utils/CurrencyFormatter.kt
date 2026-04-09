package com.udx.app.utils

import java.text.NumberFormat
import java.util.Locale

object CurrencyFormatter {
    const val USD_TO_UZS = 12_230.0

    /** 12.5 → "152 875 so'm" */
    fun formatUzs(usdPrice: Double): String {
        val uzs = (usdPrice * USD_TO_UZS).toLong()
        val formatted = NumberFormat.getNumberInstance(Locale("ru")).format(uzs)
        return "$formatted so'm"
    }
}
