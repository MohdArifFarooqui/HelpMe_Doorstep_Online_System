package com.helpmedoorstep.app

import android.annotation.SuppressLint
import android.graphics.*
import android.graphics.drawable.ColorDrawable
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import kotlin.math.cos
import kotlin.math.sin

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var splashView: HelpMeSplashView

    private var mediaPlayer: MediaPlayer? = null
    private var pageLoaded = false
    private var animationFinished = false
    private var splashClosed = false

    private val handler = Handler(Looper.getMainLooper())

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        /*
         * ROOT
         */
        val root = FrameLayout(this)
        root.setBackgroundColor(Color.WHITE)

        /*
         * WEBVIEW
         *
         * Central Login Portal:
         * /login
         */
        webView = WebView(this)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.loadsImagesAutomatically = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true

        webView.webViewClient = object : WebViewClient() {

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)

                pageLoaded = true
                tryCloseSplash()
            }
        }

        /*
         * WebView background me load hoga.
         * Splash ke neeche rahega.
         */
        webView.alpha = 0f
        webView.visibility = View.VISIBLE

        val webParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        )

        root.addView(webView, webParams)

        /*
         * SPLASH
         */
        splashView = HelpMeSplashView(this@MainActivity)

        val splashParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        )

        root.addView(splashView, splashParams)

        setContentView(root)

        /*
         * MUSIC
         */
        try {
            mediaPlayer = MediaPlayer.create(
                this,
                R.raw.helpme_splash_music
            )

            mediaPlayer?.isLooping = false
            mediaPlayer?.start()
        } catch (_: Exception) {
            mediaPlayer = null
        }

        /*
         * CENTRAL LOGIN PAGE LOAD
         */
        webView.loadUrl(
            "https://helpme-doorstep-online-system.onrender.com/login"
        )

        /*
         * Minimum splash duration.
         *
         * Animation ko beech me cut nahi hone denge.
         */
        handler.postDelayed({
            animationFinished = true
            tryCloseSplash()
        }, 4500L)
    }

    /*
     * Splash tabhi close hoga jab:
     *
     * 1. Animation complete
     * 2. Central Login page loaded
     *
     * Dono conditions zaroori hain.
     */
    private fun tryCloseSplash() {

        if (!pageLoaded) return
        if (!animationFinished) return
        if (splashClosed) return

        splashClosed = true

        /*
         * WebView ko visible karne se pehle splash fade hoga.
         * Isse white blank screen nahi aayegi.
         */
        webView.animate()
            .alpha(1f)
            .setDuration(350L)
            .start()

        splashView.animate()
            .alpha(0f)
            .setDuration(350L)
            .withEndAction {
                splashView.visibility = View.GONE
                splashView.alpha = 1f
            }
            .start()

        handler.postDelayed({
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
        }, 500L)
    }

    override fun onDestroy() {

        handler.removeCallbacksAndMessages(null)

        mediaPlayer?.stop()
        mediaPlayer?.release()
        mediaPlayer = null

        webView.destroy()

        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {

        if (::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    /*
     * ============================================================
     * HELP ME DOORSTEP SPLASH ANIMATION
     * ============================================================
     */
    private inner class HelpMeSplashView(
        context: android.content.Context
    ) : View(context) {

        private val poster = BitmapFactory.decodeResource(
            resources,
            R.drawable.helpme_doorstep_splash
        )

        private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            isFilterBitmap = true
            isDither = true
        }

        private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeWidth = 3f
        }

        private val particlePaint = Paint(Paint.ANTI_ALIAS_FLAG)

        private val startTime = android.os.SystemClock.uptimeMillis()

        private val animationDuration = 5200L

        init {
            setLayerType(View.LAYER_TYPE_SOFTWARE, null)
            postInvalidateOnAnimation()
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)

            val now = android.os.SystemClock.uptimeMillis()
            val elapsed = now - startTime

            val progress = (elapsed.toFloat() / animationDuration)
                .coerceIn(0f, 1f)

            /*
             * ---------------------------------------------------------
             * 1. CLEAN BACKGROUND
             * ---------------------------------------------------------
             */

            canvas.drawColor(Color.rgb(238, 250, 255))

            /*
             * ---------------------------------------------------------
             * 2. COMPLETE POSTER
             *
             * Poster is shown as ONE COMPLETE PAGE.
             * No logo pieces.
             * No rectangular logo blocks.
             * ---------------------------------------------------------
             */

            val viewWidth = width.toFloat()
            val viewHeight = height.toFloat()

            val bitmapWidth = poster.width.toFloat()
            val bitmapHeight = poster.height.toFloat()

            val scale = minOf(
                viewWidth / bitmapWidth,
                viewHeight / bitmapHeight
            )

            val drawWidth = bitmapWidth * scale
            val drawHeight = bitmapHeight * scale

            val left = (viewWidth - drawWidth) / 2f
            val top = (viewHeight - drawHeight) / 2f

            val posterRect = RectF(
                left,
                top,
                left + drawWidth,
                top + drawHeight
            )

            /*
             * Smooth poster entrance:
             * starts slightly smaller and becomes full size.
             */
            val entrance = easeOutCubic(
                ((progress / 0.35f).coerceIn(0f, 1f))
            )

            val scaleAnim = 0.965f + (0.035f * entrance)

            val cx = viewWidth / 2f
            val cy = viewHeight / 2f

            canvas.save()

            canvas.scale(
                scaleAnim,
                scaleAnim,
                cx,
                cy
            )

            paint.alpha = (
                    255f * easeOutCubic(
                        (progress / 0.28f).coerceIn(0f, 1f)
                    )
                    ).toInt()

            canvas.drawBitmap(
                poster,
                null,
                posterRect,
                paint
            )

            canvas.restore()

            /*
             * ---------------------------------------------------------
             * 3. AI / DIGITAL WATERMARK EFFECT
             *
             * Very subtle — poster remains clearly visible.
             * ---------------------------------------------------------
             */

            val watermarkProgress =
                ((progress - 0.10f) / 0.65f).coerceIn(0f, 1f)

            if (watermarkProgress > 0f) {

                val watermarkAlpha =
                    (45f * sin(watermarkProgress * Math.PI))
                        .toInt()
                        .coerceIn(0, 45)

                glowPaint.color = Color.rgb(30, 145, 220)
                glowPaint.alpha = watermarkAlpha
                glowPaint.strokeWidth = 2.5f

                val radiusBase =
                    minOf(viewWidth, viewHeight) * 0.30f

                for (i in 0..2) {

                    val radius =
                        radiusBase +
                                (i * 24f) +
                                (sin(
                                    elapsed * 0.0025 +
                                            i
                                ) * 5f).toFloat()

                    canvas.drawCircle(
                        cx,
                        viewHeight * 0.43f,
                        radius,
                        glowPaint
                    )
                }
            }

            /*
             * ---------------------------------------------------------
             * 4. WATER / ENERGY RIPPLE
             * ---------------------------------------------------------
             */

            val rippleProgress =
                ((progress - 0.18f) / 0.70f)
                    .coerceIn(0f, 1f)

            if (rippleProgress > 0f) {

                val rippleY = viewHeight * 0.57f

                for (i in 0..4) {

                    val wave =
                        (rippleProgress * 220f) +
                                (i * 28f)

                    val alpha =
                        (75f *
                                (1f - rippleProgress) *
                                (1f - i / 6f))
                            .toInt()
                            .coerceAtLeast(0)

                    glowPaint.color =
                        Color.rgb(0, 135, 225)

                    glowPaint.alpha = alpha

                    glowPaint.strokeWidth =
                        2f + (i * 0.7f)

                    val ovalWidth =
                        minOf(viewWidth * 0.72f, wave * 2.2f)

                    val ovalHeight =
                        18f + (i * 5f)

                    val rect = RectF(
                        cx - ovalWidth / 2f,
                        rippleY - ovalHeight / 2f,
                        cx + ovalWidth / 2f,
                        rippleY + ovalHeight / 2f
                    )

                    canvas.drawOval(rect, glowPaint)
                }
            }

            /*
             * ---------------------------------------------------------
             * 5. AI PARTICLES
             * ---------------------------------------------------------
             */

            val particleProgress =
                ((progress - 0.05f) / 0.80f)
                    .coerceIn(0f, 1f)

            if (particleProgress > 0f) {

                particlePaint.style = Paint.Style.FILL

                for (i in 0 until 26) {

                    val seed = i * 17.31f

                    val angle =
                        (seed % 360f) *
                                (Math.PI.toFloat() / 180f)

                    val distance =
                        minOf(viewWidth, viewHeight) *
                                (0.12f + ((i % 7) * 0.035f))

                    val rotation =
                        elapsed * 0.00035f *
                                (if (i % 2 == 0) 1f else -1f)

                    val x =
                        cx +
                                cos(
                                    angle + rotation
                                ) * distance

                    val y =
                        viewHeight * 0.44f +
                                sin(
                                    angle + rotation
                                ) * distance

                    val alpha =
                        (
                                100f *
                                        sin(
                                            particleProgress *
                                                    Math.PI
                                        )
                                ).toInt()
                            .coerceIn(0, 100)

                    particlePaint.color =
                        if (i % 3 == 0) {
                            Color.rgb(20, 170, 225)
                        } else {
                            Color.rgb(40, 170, 110)
                        }

                    particlePaint.alpha = alpha

                    val radius =
                        1.5f +
                                ((i % 3) * 0.8f)

                    canvas.drawCircle(
                        x.toFloat(),
                        y.toFloat(),
                        radius,
                        particlePaint
                    )
                }
            }

            /*
             * ---------------------------------------------------------
             * 6. LIGHT SWEEP
             *
             * Gives the poster an AI / premium reveal effect.
             * ---------------------------------------------------------
             */

            val sweepProgress =
                ((progress - 0.22f) / 0.58f)
                    .coerceIn(0f, 1f)

            if (sweepProgress > 0f &&
                sweepProgress < 1f
            ) {

                val sweepX =
                    -viewWidth +
                            (2f * viewWidth * sweepProgress)

                val gradientPaint =
                    Paint(Paint.ANTI_ALIAS_FLAG)

                gradientPaint.shader =
                    LinearGradient(
                        sweepX - 90f,
                        0f,
                        sweepX + 90f,
                        0f,
                        intArrayOf(
                            Color.TRANSPARENT,
                            Color.argb(
                                55,
                                255,
                                255,
                                255
                            ),
                            Color.TRANSPARENT
                        ),
                        null,
                        Shader.TileMode.CLAMP
                    )

                canvas.drawRect(
                    0f,
                    0f,
                    viewWidth,
                    viewHeight,
                    gradientPaint
                )
            }

            /*
             * ---------------------------------------------------------
             * 7. FINISH
             *
             * Tell MainActivity that animation is complete.
             * ---------------------------------------------------------
             */

            if (elapsed >= animationDuration) {
                animationFinished = true
            }

            if (!animationFinished) {
                postInvalidateOnAnimation()
            }
        }

        private fun easeOutCubic(value: Float): Float {
            val x = 1f - value
            return 1f - (x * x * x)
        }
    }
}
