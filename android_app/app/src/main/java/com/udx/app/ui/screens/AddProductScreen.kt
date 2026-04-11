@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.udx.app.data.NetworkModule
import com.udx.app.data.ProductCreate
import kotlinx.coroutines.launch
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.PickVisualMediaRequest
import android.net.Uri
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import coil.compose.AsyncImage
import com.udx.app.R
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream

@Composable
fun AddProductScreen(onBack: () -> Unit, onSuccess: () -> Unit) {
    var name by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    var categoryId by remember { mutableStateOf("") }
    var categories by remember { mutableStateOf<List<com.udx.app.data.Category>>(emptyList()) }
    val regionOptions = listOf(
        "Toshkent", "Toshkent viloyati", "Samarqand", "Buxoro", "Andijon",
        "Farg'ona", "Namangan", "Qashqadaryo", "Surxondaryo", "Jizzax",
        "Sirdaryo", "Xorazm", "Navoiy", "Qoraqalpog'iston"
    )
    var region by remember { mutableStateOf(regionOptions[0]) }
    var regionDropdownExpanded by remember { mutableStateOf(false) }
    var isB2b by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var isCategoriesLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    val unitOptions = listOf("kg", "g", "ton", "lb", "oz", "l", "ml", "m", "cm", "m²", "m³", "pcs", "box", "pack")
    val savedUnit = context.getSharedPreferences("udx_prefs", android.content.Context.MODE_PRIVATE)
        .getString("unit", "kg") ?: "kg"
    var unit by remember { mutableStateOf(if (savedUnit in unitOptions) savedUnit else "kg") }
    var unitDropdownExpanded by remember { mutableStateOf(false) }
    
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia(),
        onResult = { uri -> imageUri = uri }
    )

    val fallbackCategories = listOf(
        com.udx.app.data.Category("vegetables", "Vegetables", "🥕"),
        com.udx.app.data.Category("fruits", "Fruits", "🍎"),
        com.udx.app.data.Category("dairy", "Dairy", "🥛"),
        com.udx.app.data.Category("meat", "Meat", "🥩")
    )
    
    val displayCategories = if (categories.isEmpty() && !isCategoriesLoading) fallbackCategories else categories
    
    LaunchedEffect(Unit) {
        try {
            categories = NetworkModule.apiService.getCategories()
            if (categories.isNotEmpty()) {
                categoryId = categories[0].id
            } else {
                categoryId = fallbackCategories[0].id
            }
        } catch (e: Exception) {
            error = "Failed to load categories, using defaults"
            categoryId = fallbackCategories[0].id
        } finally {
            isCategoriesLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.add_new_product)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            if (error != null) {
                Text(error!!, color = MaterialTheme.colorScheme.secondary, modifier = Modifier.padding(bottom = 8.dp))
            }

            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text(stringResource(R.string.product_name)) },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))

            if (isCategoriesLoading) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp))
            } else {
                var expanded by remember { mutableStateOf(false) }
                val currentCategory = displayCategories.find { it.id == categoryId }

                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { expanded = !expanded },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    OutlinedTextField(
                        value = "${currentCategory?.icon ?: ""} ${currentCategory?.name ?: "Select Category"}",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Category") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = expanded,
                        onDismissRequest = { expanded = false }
                    ) {
                        displayCategories.forEach { category ->
                            DropdownMenuItem(
                                text = { Text("${category.icon} ${category.name}") },
                                onClick = {
                                    categoryId = category.id
                                    expanded = false
                                }
                            )
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = price,
                onValueChange = { price = it },
                label = { Text(stringResource(R.string.price)) },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))

            ExposedDropdownMenuBox(
                expanded = unitDropdownExpanded,
                onExpandedChange = { unitDropdownExpanded = it }
            ) {
                OutlinedTextField(
                    value = unit,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text(stringResource(R.string.unit)) },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = unitDropdownExpanded) },
                    modifier = Modifier.fillMaxWidth().menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = unitDropdownExpanded,
                    onDismissRequest = { unitDropdownExpanded = false }
                ) {
                    unitOptions.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(option) },
                            onClick = {
                                unit = option
                                unitDropdownExpanded = false
                            }
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))

            ExposedDropdownMenuBox(
                expanded = regionDropdownExpanded,
                onExpandedChange = { regionDropdownExpanded = it }
            ) {
                OutlinedTextField(
                    value = region,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Hudud (viloyat)") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = regionDropdownExpanded) },
                    modifier = Modifier.fillMaxWidth().menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = regionDropdownExpanded,
                    onDismissRequest = { regionDropdownExpanded = false }
                ) {
                    regionOptions.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(option) },
                            onClick = {
                                region = option
                                regionDropdownExpanded = false
                            }
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text("Product Image", style = MaterialTheme.typography.titleSmall)
            Spacer(modifier = Modifier.height(8.dp))
            Button(
                onClick = { 
                    photoPickerLauncher.launch(
                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                    ) 
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
            ) {
                Text(stringResource(R.string.select_image))
            }
            
            if (imageUri != null) {
                Spacer(modifier = Modifier.height(8.dp))
                AsyncImage(
                    model = imageUri,
                    contentDescription = "Selected image",
                    modifier = Modifier.fillMaxWidth().height(200.dp)
                )
            }
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text(stringResource(R.string.description)) },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3
            )
            
            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text("B2B Wholesale Item", style = MaterialTheme.typography.bodyLarge)
                Switch(checked = isB2b, onCheckedChange = { isB2b = it })
            }

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = {
                    val priceDouble = price.toDoubleOrNull()
                    if (name.isBlank() || priceDouble == null || imageUri == null) {
                        error = "Please fill all required fields correctly"
                        return@Button
                    }
                    
                    isLoading = true
                    error = null
                    scope.launch {
                        try {
                            // 1. Upload Image
                            val inputStream = context.contentResolver.openInputStream(imageUri!!)
                            val tempFile = File(context.cacheDir, "upload_temp.jpg")
                            val outputStream = FileOutputStream(tempFile)
                            inputStream?.copyTo(outputStream)
                            inputStream?.close()
                            outputStream.close()
                            
                            val requestFile = tempFile.asRequestBody("image/*".toMediaTypeOrNull())
                            val body = MultipartBody.Part.createFormData("file", tempFile.name, requestFile)
                            
                            val uploadResponse = NetworkModule.apiService.uploadImage(body)
                            
                            // 2. Create Product
                            NetworkModule.apiService.createProduct(
                                ProductCreate(name, priceDouble, unit, uploadResponse.url, description, categoryId, isB2b, region)
                            )
                            onSuccess()
                        } catch (e: Exception) {
                            error = e.message ?: "Failed to add product"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Text(stringResource(R.string.create_product))
                }
            }
        }
    }
}
