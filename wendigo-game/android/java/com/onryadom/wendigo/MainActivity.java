package com.onryadom.wendigo;

import android.app.Activity;
import android.content.Context;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;

import java.lang.reflect.Method;
import java.util.concurrent.ConcurrentLinkedQueue;

/** Полноэкранный WebView с игрой и мост AndroidNet для сетевой игры по Wi-Fi. */
public class MainActivity extends Activity implements NetCore.Listener {
    private WebView web;
    private NetCore net;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ConcurrentLinkedQueue<String[]> queue = new ConcurrentLinkedQueue<String[]>();
    private volatile boolean flushPosted;
    private Method evalJs;
    private WifiManager.MulticastLock mlock;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this);
        web.setBackgroundColor(0xFF000000);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        call(s, "setMediaPlaybackRequiresUserGesture", boolean.class, false);
        web.setWebChromeClient(new WebChromeClient());
        net = new NetCore(this);
        web.addJavascriptInterface(new Bridge(), "AndroidNet");
        try { evalJs = WebView.class.getMethod("evaluateJavascript", String.class, ValueCallback.class); } catch (Exception e) { evalJs = null; }
        try {
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            mlock = wm.createMulticastLock("wendigo"); mlock.setReferenceCounted(false);
        } catch (Exception e) { mlock = null; }
        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
    }

    private static void call(Object o, String name, Class<?> t, Object arg) {
        try { o.getClass().getMethod(name, t).invoke(o, arg); } catch (Exception e) { /* старый WebView */ }
    }

    /** Вызывается из JavaScript (поток JavaBridge). */
    public class Bridge {
        @JavascriptInterface public void host(String name) { net.host(name); }
        @JavascriptInterface public void scan() {
            if (mlock != null) try { mlock.acquire(); } catch (Exception e) { /* нет Wi-Fi */ }
            net.scan(6000);
        }
        @JavascriptInterface public void join(String ip) { net.join(ip); }
        @JavascriptInterface public void send(int to, String line) { net.send(to, line); }
        @JavascriptInterface public void stop() { net.stop(); }
        @JavascriptInterface public String localIp() { return NetCore.localIp(); }
    }

    /** События сети копятся и пачкой передаются в JavaScript на главном потоке. */
    @Override
    public void onEvent(String type, String data) {
        if ("scandone".equals(type) && mlock != null) { try { mlock.release(); } catch (Exception e) { /* уже */ } }
        queue.add(new String[] { type, data });
        if (!flushPosted) { flushPosted = true; ui.post(flusher); }
    }

    private final Runnable flusher = new Runnable() {
        @Override public void run() {
            flushPosted = false;
            StringBuilder arr = new StringBuilder("[");
            String[] e; int n = 0;
            while (n < 200 && (e = queue.poll()) != null) {
                if (n > 0) arr.append(',');
                arr.append('['); quote(arr, e[0]); arr.append(','); quote(arr, e[1]); arr.append(']'); n++;
            }
            arr.append(']');
            if (!queue.isEmpty()) { flushPosted = true; ui.post(this); }
            if (n == 0 || web == null) return;
            String js = "window.__net&&window.__net(" + arr + ")";
            if (evalJs != null) { try { evalJs.invoke(web, js, null); return; } catch (Exception ex) { evalJs = null; } }
            web.loadUrl("javascript:" + js);
        }
    };

    /** Строка как JSON-литерал: безопасно вставлять в JavaScript. */
    static void quote(StringBuilder sb, String v) {
        sb.append('"');
        for (int i = 0; i < v.length(); i++) {
            char c = v.charAt(i);
            if (c == '"' || c == '\\') sb.append('\\').append(c);
            else if (c < 0x20 || c == 0x2028 || c == 0x2029 || c == '<' || c == '>') sb.append(String.format("\\u%04x", (int) c));
            else sb.append(c);
        }
        sb.append('"');
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) getWindow().getDecorView().setSystemUiVisibility(0x1706);
    }
    @Override protected void onPause() { super.onPause(); if (web != null) web.onPause(); }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override protected void onDestroy() { if (net != null) net.stop(); if (web != null) web.destroy(); super.onDestroy(); }
}
