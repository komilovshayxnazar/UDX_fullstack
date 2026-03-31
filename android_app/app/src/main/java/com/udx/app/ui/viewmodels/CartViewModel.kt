package com.udx.app.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.udx.app.data.ProductRemote
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map

data class CartItem(
    val product: ProductRemote,
    var quantity: Int
)

class CartViewModel : ViewModel() {
    private val _cartItems = MutableStateFlow<List<CartItem>>(emptyList())
    val cartItems: StateFlow<List<CartItem>> = _cartItems.asStateFlow()

    val totalItems: StateFlow<Int> = _cartItems.map { items ->
        items.sumOf { it.quantity }
    }.let { flow ->
        val stateFlow = MutableStateFlow(0)
        // In a real app we'd use stateIn, but for simplicity we'll mirror
        stateFlow
    }
    
    // Better way to handle derived state for simple demo:
    fun getTotalCount(): Int = _cartItems.value.sumOf { it.quantity }
    fun getTotalPrice(): Double = _cartItems.value.sumOf { it.product.price * it.quantity }

    fun addToCart(product: ProductRemote) {
        val currentItems = _cartItems.value.toMutableList()
        val existingItem = currentItems.find { it.product.id == product.id }
        
        if (existingItem != null) {
            existingItem.quantity += 1
        } else {
            currentItems.add(CartItem(product, 1))
        }
        _cartItems.value = currentItems
    }

    fun removeFromCart(productId: String) {
        _cartItems.value = _cartItems.value.filter { it.product.id != productId }
    }

    fun updateQuantity(productId: String, quantity: Int) {
        if (quantity <= 0) {
            removeFromCart(productId)
            return
        }
        val currentItems = _cartItems.value.toMutableList()
        val index = currentItems.indexOfFirst { it.product.id == productId }
        if (index != -1) {
            currentItems[index] = currentItems[index].copy(quantity = quantity)
            _cartItems.value = currentItems
        }
    }

    fun clearCart() {
        _cartItems.value = emptyList()
    }
}
