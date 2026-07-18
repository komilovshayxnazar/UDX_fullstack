package com.udx.app.data

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

import okhttp3.OkHttpClient
import okhttp3.Interceptor
import okhttp3.logging.HttpLoggingInterceptor
import android.util.Log
import com.udx.app.BuildConfig

object NetworkModule {
    // Publicly visible so other layers (WebSocket chat, image URL
    // rewriting) can derive their own URLs from a single source of truth
    // instead of re-hardcoding the host.
    const val BASE_URL = "https://udx-marketplace.store/"

    private val authInterceptor = Interceptor { chain ->
        val token = TokenManager.getToken()
        val requestBuilder = chain.request().newBuilder()
        if (token != null && token.isNotBlank()) {
            requestBuilder.addHeader("Authorization", "Bearer $token")
        }
        chain.proceed(requestBuilder.build())
    }

    // Log full bodies only in debug builds so bearer tokens and payment
    // payloads don't leak through logcat on release APKs.
    private val loggingInterceptor = HttpLoggingInterceptor { message ->
        Log.d("OkHttp", message)
    }.apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
                else HttpLoggingInterceptor.Level.NONE
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .followRedirects(false)
        .followSslRedirects(false)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val apiService: ApiService = retrofit.create(ApiService::class.java)
}
