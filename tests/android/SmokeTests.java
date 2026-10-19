package cz.zephyr.termux;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ScrollView;
import java.io.File;
import java.io.FileOutputStream;

/** Actual Android input events, without root or third-party test dependencies. */
public final class SmokeTests extends Instrumentation {
    private Activity activity;
    private ScrollView scroll;
    private Button setup;
    private int checkedButtons;
    private String operation;
    private boolean portrait;
    @Override public void onCreate(Bundle args) {
        super.onCreate(args); operation = args == null ? null : args.getString("operation");
        portrait = args != null && "portrait".equals(args.getString("orientation")); start();
    }
    private void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
    private void inspect(View view) {
        if (view instanceof ScrollView) scroll = (ScrollView) view;
        if (view instanceof Button) {
            Button button = (Button) view;
            checkedButtons++;
            require(button.isFocusable(), "Button is not keyboard focusable");
            require(button.getHeight() >= 48 * activity.getResources().getDisplayMetrics().density, "Touch target smaller than 48dp");
            if (button.getText().toString().contains("Propojit")) setup = button;
        }
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) inspect(((ViewGroup) view).getChildAt(i));
    }
    private Button find(View view, String label) {
        if (view instanceof Button && ((Button) view).getText().toString().startsWith(label)) return (Button) view;
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) {
            Button result = find(((ViewGroup) view).getChildAt(i), label);
            if (result != null) return result;
        }
        return null;
    }
    private void key(int code) { sendKeyDownUpSync(code); waitForIdleSync(); }
    private android.view.accessibility.AccessibilityNodeInfo window() {
        for (int i = 0; i < 25; i++) {
            android.view.accessibility.AccessibilityNodeInfo root = getUiAutomation().getRootInActiveWindow();
            if (root != null) return root;
            SystemClock.sleep(200);
        }
        throw new AssertionError("No active accessibility window");
    }
    private void dialog(String title) {
        SystemClock.sleep(400);
        require(!window().findAccessibilityNodeInfosByText(title).isEmpty(), "Dialog not opened: " + title);
    }
    private void tap(View view) {
        int[] location = new int[2];
        runOnMainSync(() -> view.getLocationOnScreen(location));
        float x = location[0] + view.getWidth() / 2f, y = location[1] + view.getHeight() / 2f;
        long time = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(time, time, MotionEvent.ACTION_DOWN, x, y, 0);
        down.setSource(InputDevice.SOURCE_TOUCHSCREEN); sendPointerSync(down); down.recycle();
        MotionEvent up = MotionEvent.obtain(time, time + 30, MotionEvent.ACTION_UP, x, y, 0);
        up.setSource(InputDevice.SOURCE_TOUCHSCREEN); sendPointerSync(up); up.recycle(); waitForIdleSync();
    }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            require(android.os.Process.myUid() >= 10000, "Test must run as an ordinary app UID");
            getUiAutomation();
            Intent intent = new Intent(Intent.ACTION_MAIN).setClassName("cz.zephyr.termux", "cz.zephyr.termux.MainActivity")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            activity = startActivitySync(intent);
            if (portrait) {
                runOnMainSync(() -> activity.setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));
                SystemClock.sleep(1500);
            }
            waitForIdleSync();
            runOnMainSync(() -> inspect(activity.getWindow().getDecorView()));
            require(checkedButtons >= 15 && scroll != null && setup != null, "Dashboard incomplete");
            if (operation != null) {
                if (operation.equals("download-termux") || operation.equals("download-self")) {
                    File apk = Updates.download(getTargetContext(), operation.equals("download-termux"), message -> android.util.Log.i("ZephyrTest", message));
                    require(apk.length() > 10000, "Downloaded APK is incomplete");
                    result.putString("stream", "PASS: GitHub release API, APK download, official SHA-256, package and signing certificate verified.");
                    finish(Activity.RESULT_OK, result); return;
                }
                if (operation.equals("installer")) {
                    runOnMainSync(() -> activity.startActivity(new Intent(Intent.ACTION_INSTALL_PACKAGE)
                        .setDataAndType(android.net.Uri.parse("content://cz.zephyr.termux.apk/termux.apk"), "application/vnd.android.package-archive")
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)));
                    SystemClock.sleep(3000);
                    String packageName = window().getPackageName().toString();
                    require(packageName.contains("packageinstaller"), "Android installer did not open: " + packageName);
                    key(KeyEvent.KEYCODE_BACK);
                    result.putString("stream", "PASS: verified APK opened by Android package installer via read-only content URI; installation cancelled by test.");
                    finish(Activity.RESULT_OK, result); return;
                }
                String label;
                switch (operation) {
                    case "install": label = "Instalovat /"; break;
                    case "build": label = "Sestavit"; break;
                    case "run": label = "Spustit"; break;
                    case "edit": label = "Upravit zdroj"; break;
                    case "shell": label = "Linuxový terminál"; break;
                    case "backup": label = "Zálohovat"; break;
                    default: label = "Obnovit stav";
                }
                Button[] action = new Button[1];
                for (int i = 0; i < 30; i++) {
                    runOnMainSync(() -> action[0] = find(activity.getWindow().getDecorView(), label));
                    if (action[0].isEnabled()) break;
                    SystemClock.sleep(500);
                }
                require(action[0].isEnabled(), "Operation button remains disabled: " + label);
                runOnMainSync(() -> action[0].performClick());
                SystemClock.sleep(7000);
                if (operation.equals("run") || operation.equals("edit") || operation.equals("shell"))
                    require("com.termux".contentEquals(window().getPackageName()), "Interactive action did not open Termux");
                result.putString("stream", "BRIDGE: " + getTargetContext().getSharedPreferences("bridge", 0).getString("status", "")
                    + "\nERROR: " + getTargetContext().getSharedPreferences("bridge", 0).getString("error", ""));
                finish(Activity.RESULT_OK, result); return;
            }
            key(KeyEvent.KEYCODE_TAB);
            View[] focus = new View[1]; runOnMainSync(() -> focus[0] = activity.getCurrentFocus());
            require(focus[0] != null, "Tab did not focus a control");
            key(KeyEvent.KEYCODE_TAB);
            runOnMainSync(() -> require(activity.getCurrentFocus() != focus[0], "Tab did not advance focus"));
            runOnMainSync(() -> { scroll.scrollTo(0, 0); setup.requestFocus(); });
            key(KeyEvent.KEYCODE_ENTER);
            dialog("Propojení bez rootu");
            key(KeyEvent.KEYCODE_BACK);
            tap(setup); dialog("Propojení bez rootu"); key(KeyEvent.KEYCODE_BACK);
            runOnMainSync(() -> scroll.scrollTo(0, 0)); waitForIdleSync();
            MotionEvent.PointerProperties props = new MotionEvent.PointerProperties(); props.id = 0; props.toolType = MotionEvent.TOOL_TYPE_MOUSE;
            MotionEvent.PointerCoords coords = new MotionEvent.PointerCoords(); coords.x = 500; coords.y = 400; coords.setAxisValue(MotionEvent.AXIS_VSCROLL, -10);
            MotionEvent wheel = MotionEvent.obtain(SystemClock.uptimeMillis(), SystemClock.uptimeMillis(), MotionEvent.ACTION_SCROLL, 1,
                new MotionEvent.PointerProperties[]{props}, new MotionEvent.PointerCoords[]{coords}, 0, 0, 1, 1, 0, 0, InputDevice.SOURCE_MOUSE, 0);
            getUiAutomation().injectInputEvent(wheel, true); wheel.recycle(); waitForIdleSync();
            runOnMainSync(() -> require(scroll.getScrollY() > 0, "Mouse / touchpad wheel did not scroll"));
            key(KeyEvent.KEYCODE_F1); dialog("Zephyr pro Termux"); key(KeyEvent.KEYCODE_BACK);
            runOnMainSync(() -> scroll.scrollTo(0, 0)); waitForIdleSync();
            SystemClock.sleep(4000); // Let dialog/clipboard animations finish before visual capture.
            File screenshot = new File(getTargetContext().getExternalFilesDir(null), "dashboard.png");
            try (FileOutputStream stream = new FileOutputStream(screenshot)) {
                getUiAutomation().takeScreenshot().compress(Bitmap.CompressFormat.PNG, 100, stream);
            }
            result.putString("stream", "PASS: ordinary app UID, dashboard, 48dp targets, Tab focus, Enter, touch, mouse/touchpad scrolling, F1.\nScreenshot: " + screenshot);
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", "FAIL: " + error.toString()); finish(Activity.RESULT_CANCELED, result);
        }
    }
}
