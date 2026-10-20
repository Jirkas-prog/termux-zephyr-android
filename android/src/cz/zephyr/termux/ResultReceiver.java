package cz.zephyr.termux;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;

/** Explicit, single-use PendingIntent callbacks. No exported command receiver. */
public final class ResultReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (intent.getData() == null) return;
        String token = intent.getData().getLastPathSegment();
        SharedPreferences prefs = context.getSharedPreferences("bridge", 0);
        String purpose = prefs.getString("pending:" + token, null);
        if (purpose == null) return;
        prefs.edit().remove("pending:" + token).remove("active:" + purpose).apply();
        Bundle result = intent.getBundleExtra("result");
        if (result == null) return;
        int exit = result.getInt("exitCode", -1);
        int error = result.getInt("err", -1);
        String stdout = result.getString("stdout", "");
        String stderr = result.getString("stderr", "");
        String message = result.getString("errmsg", "");
        SharedPreferences.Editor editor = prefs.edit();
        if (purpose.equals("status") && exit == 0 && error == -1) {
            editor.putString("status", stdout);
            // A successful poll must not erase an operation failure before it is shown.
            if (prefs.getString("error_action", "status").equals("status")) editor.putString("error", "");
        } else if (exit != 0 || error != -1) {
            editor.putString("error", (message + "\n" + stderr + "\n" + stdout).trim()).putString("error_action", purpose);
        }
        editor.putLong("received", System.currentTimeMillis()).apply();
    }
}
