package com.udx.app.data

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

import okhttp3.OkHttpClient
import okhttp3.Interceptor

object NetworkModule {
    // 10.0.2.2 is the special alias to your host loopback interface (localhost)
    private const val BASE_URL = "http://10.0.2.2:8000/"

    private val authInterceptor = Interceptor { chain ->
        val token = TokenManager.getToken()
        val requestBuilder = chain.request().newBuilder()
        if (token != null && token.isNotBlank()) {
            requestBuilder.addHeader("Authorization", "Bearer $token")
        }
        chain.proceed(requestBuilder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
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
