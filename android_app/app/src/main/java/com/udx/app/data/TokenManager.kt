package com.udx.app.data

import android.content.Context
import android.content.SharedPreferences

object TokenManager {
    private var sharedPreferences: SharedPreferences? = null

    fun init(context: Context) {
        if (sharedPreferences == null) {
            sharedPreferences = context.applicationContext.getSharedPreferences("auth_prefs", Context.MODE_PRIVATE)
        }
    }

    fun saveToken(token: String) {
        sharedPreferences?.edit()?.putString("jwt_token", token)?.apply()
    }

    fun getToken(): String? {
        return sharedPreferences?.getString("jwt_token", null)
    }

    fun clearToken() {
        sharedPreferences?.edit()?.remove("jwt_token")?.remove("my_id")?.apply()
    }

    fun saveMyId(id: String) {
        sharedPreferences?.edit()?.putString("my_id", id)?.apply()
    }

    fun getMyId(): String? {
        return sharedPreferences?.getString("my_id", null)
    }
}
