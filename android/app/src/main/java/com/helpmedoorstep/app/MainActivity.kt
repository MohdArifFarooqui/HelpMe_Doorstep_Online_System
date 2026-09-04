package com.helpmedoorstep.app

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val title = TextView(this).apply {
            text = "HelpMe Doorstep"
            textSize = 28f
            setPadding(40, 80, 40, 40)
        }

        setContentView(title)
    }
}
