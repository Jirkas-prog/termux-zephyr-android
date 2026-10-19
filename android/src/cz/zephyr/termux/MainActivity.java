package cz.zephyr.termux;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.provider.Settings;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.json.JSONArray;
import org.json.JSONObject;

public final class MainActivity extends Activity {
    private static final String PERMISSION = "com.termux.permission.RUN_COMMAND";
    private static final int INK = Color.rgb(19, 42, 56), TEAL = Color.rgb(0, 112, 101);
    private final Handler handler = new Handler();
    private TextView state, notice, log, versions;
    private Spinner exercises;
    private LinearLayout body;
    private SharedPreferences prefs;
    private final List<Button> commands = new ArrayList<>();
    private final List<String> appNames = new ArrayList<>();
    private boolean active, downloading;
    private long lastRequest, lastReceived;
    private String selected = "hello_world";
    private Runnable afterPermission;
    private final Runnable poll = new Runnable() {
        @Override public void run() {
            if (!active) return;
            renderStatus();
            if (hasBridge() && System.currentTimeMillis() - lastRequest > 5000) command("status");
            handler.postDelayed(this, 1500);
        }
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        prefs = getSharedPreferences("bridge", 0);
        if (saved != null) selected = saved.getString("exercise", "hello_world");
        layout();
    }
    @Override protected void onSaveInstanceState(Bundle out) {
        selected = selection();
        out.putString("exercise", selected);
        super.onSaveInstanceState(out);
    }
    @Override public void onConfigurationChanged(Configuration config) {
        selected = selection();
        super.onConfigurationChanged(config);
        layout();
        renderStatus();
    }
    @Override protected void onResume() {
        super.onResume();
        active = true;
        handler.post(poll);
        String ready = prefs.getString("ready_apk", "");
        if (!ready.isEmpty() && (Build.VERSION.SDK_INT < 26 || getPackageManager().canRequestPackageInstalls())) installApk(new File(getFilesDir(), ready));
    }
    @Override protected void onPause() { active = false; handler.removeCallbacks(poll); super.onPause(); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(color);
        view.setPadding(0, dp(5), 0, dp(5));
        return view;
    }
    private void title(String value) {
        TextView label = text(value, 21, INK);
        label.setTypeface(null, Typeface.BOLD);
        label.setPadding(0, dp(24), 0, dp(10));
        if (Build.VERSION.SDK_INT >= 28) label.setAccessibilityHeading(true);
        body.addView(label);
    }
    private GradientDrawable background(int color, int stroke) {
        GradientDrawable result = new GradientDrawable();
        result.setColor(color); result.setCornerRadius(dp(12));
        if (stroke != 0) result.setStroke(dp(3), stroke);
        return result;
    }
    private Button button(String label, Runnable action) {
        Button button = new Button(this);
        button.setText(label); button.setTextSize(16); button.setAllCaps(false);
        button.setMinHeight(dp(56)); button.setPadding(dp(12), dp(10), dp(12), dp(10));
        button.setTextColor(Color.WHITE);
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[]{-android.R.attr.state_enabled}, background(Color.rgb(104, 122, 127), 0));
        states.addState(new int[]{android.R.attr.state_pressed}, background(INK, Color.rgb(99, 222, 203)));
        states.addState(new int[]{android.R.attr.state_focused}, background(INK, Color.rgb(99, 222, 203)));
        states.addState(new int[]{}, background(TEAL, 0));
        button.setBackground(states);
        button.setOnClickListener(view -> action.run());
        button.setFocusable(true);
        return button;
    }
    private GridLayout grid() {
        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(getResources().getConfiguration().screenWidthDp >= 600 ? 3 : 1);
        body.addView(grid, new LinearLayout.LayoutParams(-1, -2));
        return grid;
    }
    private void add(GridLayout grid, String label, Runnable action, boolean managed) {
        Button button = button(label, action);
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = 0; params.height = -2;
        params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        params.setMargins(dp(4), dp(4), dp(4), dp(4));
        grid.addView(button, params);
        if (managed) commands.add(button);
    }

    private void layout() {
        commands.clear(); appNames.clear();
        LinearLayout root = new LinearLayout(this); root.setOrientation(1);
        TextView header = text("ZEPHYR  /  TERMUX", 23, Color.WHITE);
        header.setTypeface(null, Typeface.BOLD); header.setBackgroundColor(INK);
        header.setPadding(dp(24), dp(20), dp(24), dp(18));
        root.addView(header);
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true);
        body = new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(20), dp(8), dp(20), dp(32));
        scroll.addView(body); root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        TextView intro = text("Zephyr na tabletu. Bez rootu.", 25, INK); intro.setTypeface(null, Typeface.BOLD);
        body.addView(intro);
        body.addView(text("Cvičení zephyr4squirrels · Ubuntu v proot · ESP32 v QEMU", 16, INK));
        state = text("Připraveno k propojení s Termuxem", 18, TEAL); body.addView(state);
        versions = text("", 14, INK); body.addView(versions);
        notice = text(prefs.getString("notice", "První spuštění: dokončete kroky 1–3 níže."), 16, INK); body.addView(notice);
        title("Začínáme");
        GridLayout setup = grid();
        add(setup, "1  Stáhnout Termux", () -> download(true), false);
        add(setup, "2  Propojit Termux", this::bootstrap, false);
        add(setup, "3  Povolit příkazy", () -> permission(() -> command("status")), false);
        body.addView(text("Termux jednou otevřete a vložte připravený příkaz. Android si vyžádá potvrzení instalace APK a oprávnění. Potom vše ovládáte zde.", 14, INK));
        title("Prostředí");
        GridLayout environment = grid();
        add(environment, "Instalovat / opravit", () -> permission(() -> command("install")), true);
        add(environment, "Aktualizovat prostředí", () -> permission(() -> command("update")), true);
        add(environment, "Zálohovat cvičení", () -> permission(() -> command("backup")), true);
        body.addView(text("První instalace: alespoň 12 GiB volného místa, doporučeno 20 GiB a 6 GiB RAM. Nechte Termux běžet; v nastavení baterie mu povolte neomezený běh.", 14, INK));
        title("Cvičení");
        TextView exerciseLabel = text("Vybrané cvičení", 16, INK); body.addView(exerciseLabel);
        exercises = new Spinner(this); exercises.setId(View.generateViewId()); exerciseLabel.setLabelFor(exercises.getId());
        exercises.setMinimumHeight(dp(56)); exercises.setContentDescription("Vybrané cvičení");
        body.addView(exercises, new LinearLayout.LayoutParams(-1, dp(56)));
        setExercises(new JSONArray().put("hello_world"));
        GridLayout work = grid();
        add(work, "Sestavit  ·  Ctrl+B", () -> permission(() -> command("build")), true);
        add(work, "Spustit  ·  Ctrl+R", () -> permission(() -> command("run")), true);
        add(work, "Upravit zdroj", () -> permission(() -> command("edit")), true);
        add(work, "Linuxový terminál", () -> permission(() -> command("shell")), true);
        add(work, "Otevřít Termux", this::openTermux, false);
        add(work, "Obnovit stav  ·  Ctrl+L", () -> permission(() -> command("status")), false);
        title("Aktualizace a nápověda");
        GridLayout more = grid();
        add(more, "Verze na GitHubu", this::checkUpdates, false);
        add(more, "Aktualizovat průvodce", () -> download(false), false);
        add(more, "Nápověda  ·  F1", this::help, false);
        title("Průběh operace");
        log = text("Zatím bez výpisu.", 13, Color.WHITE); log.setTypeface(Typeface.MONOSPACE);
        log.setTextIsSelectable(true); log.setPadding(dp(16), dp(16), dp(16), dp(16)); log.setBackground(background(INK, 0));
        body.addView(log, new LinearLayout.LayoutParams(-1, -2));
        body.addView(text("Tab / Shift+Tab: pohyb · Enter / mezerník: tlačítko · kolečko a touchpad: posun\nQEMU: Ctrl+A, potom X · nano: Ctrl+O uložit, Ctrl+X zavřít", 14, INK));
    }

    private void setExercises(JSONArray names) {
        List<String> next = new ArrayList<>();
        for (int i = 0; i < names.length(); i++) if (names.optString(i).matches("[a-zA-Z0-9_-]+")) next.add(names.optString(i));
        if (next.isEmpty()) next.add("hello_world");
        if (next.equals(appNames)) return;
        appNames.clear(); appNames.addAll(next);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, appNames);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item); exercises.setAdapter(adapter);
        exercises.setSelection(Math.max(0, appNames.indexOf(selected)));
    }
    private String selection() { return exercises != null && exercises.getSelectedItem() != null ? exercises.getSelectedItem().toString() : "hello_world"; }
    private void say(String message) {
        prefs.edit().putString("notice", message).apply();
        if (!isDestroyed()) runOnUiThread(() -> { if (notice != null) notice.setText(message); });
    }
    private boolean installed() { return getPackageManager().getLaunchIntentForPackage("com.termux") != null; }
    private boolean hasBridge() { return installed() && checkSelfPermission(PERMISSION) == PackageManager.PERMISSION_GRANTED; }
    private void permission(Runnable action) {
        if (!installed()) { say("Nejprve nainstalujte a otevřete Termux (krok 1)."); return; }
        if (hasBridge()) action.run();
        else { afterPermission = action; requestPermissions(new String[]{PERMISSION}, 10); }
    }
    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request == 10 && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            if (afterPermission != null) afterPermission.run();
        } else say("Povolte v informacích o aplikaci oprávnění ke spouštění příkazů v Termuxu.");
        afterPermission = null;
    }
    private void openTermux() {
        Intent launch = getPackageManager().getLaunchIntentForPackage("com.termux");
        if (launch == null) say("Termux ještě není nainstalován."); else startActivity(launch);
    }
    private void bootstrap() {
        String tag;
        try { tag = "v" + getPackageManager().getPackageInfo(getPackageName(), 0).versionName; }
        catch (PackageManager.NameNotFoundException error) { say("Nelze zjistit verzi průvodce."); return; }
        if (!tag.matches("v[0-9]+\\.[0-9]+\\.[0-9]+")) { say("Neplatné číslo vydání."); return; }
        String command = "apt-get update && apt-get upgrade -y --with-new-pkgs --no-install-recommends -o Dpkg::Options::=--force-confold && apt-get install -y --no-install-recommends git && "
            + "(test -d \"$HOME/termux-zephyr-android/.git\" || git clone --depth 1 --branch " + tag + " https://github.com/" + Updates.REPO + ".git \"$HOME/termux-zephyr-android\") && "
            + "test \"$(git -C \"$HOME/termux-zephyr-android\" remote get-url origin)\" = 'https://github.com/" + Updates.REPO + ".git' && "
            + "bash \"$HOME/termux-zephyr-android/scripts/termux-bootstrap.sh\"";
        ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("Propojení Termuxu", command));
        say("Příkaz je ve schránce. V Termuxu jej vložte dlouhým podržením → Paste (nebo Ctrl+Alt+V), potvrďte Enter. Po dokončení se vraťte ke kroku 3.");
        new AlertDialog.Builder(this).setTitle("Propojení bez rootu").setMessage("Příkaz byl zkopírován. Vložte jej do Termuxu a stiskněte Enter. Stáhne správce z tohoto veřejného repozitáře a povolí jeho propojení.\n\n" + command)
            .setPositiveButton("Otevřít Termux", (dialog, which) -> openTermux()).setNegativeButton("Zavřít", null).show();
    }

    private void command(String action) {
        if (!hasBridge()) return;
        try {
            boolean interactive = action.equals("run") || action.equals("shell") || action.equals("edit");
            String app = selection();
            if (!app.matches("[a-zA-Z0-9_-]+")) throw new Exception("Neplatné cvičení.");
            Intent callback = new Intent(this, ResultReceiver.class);
            String token = UUID.randomUUID().toString();
            callback.setData(Uri.parse("zephyr://result/" + token));
            String previous = prefs.getString("active:" + action, "");
            prefs.edit().remove("pending:" + previous).putString("pending:" + token, action).putString("active:" + action, token).apply();
            int flags = PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_CANCEL_CURRENT;
            if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
            PendingIntent pending = PendingIntent.getBroadcast(this, token.hashCode(), callback, flags);
            Intent intent = new Intent("com.termux.RUN_COMMAND");
            intent.setClassName("com.termux", "com.termux.app.RunCommandService");
            intent.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash");
            intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"-lc", "python \"$HOME/termux-zephyr-android/scripts/zephyrctl.py\" " + action + " --app " + app});
            intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", !interactive);
            intent.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
            intent.putExtra("com.termux.RUN_COMMAND_PENDING_INTENT", pending);
            startService(intent);
            lastRequest = System.currentTimeMillis();
            if (!action.equals("status")) say("Odesláno do Termuxu: " + action + ". Průběh se objeví níže.");
            // Start the terminal from our visible Activity; no overlay permission is needed.
            if (interactive) openTermux();
        } catch (Exception error) { say("Propojení: " + error.getMessage() + "\nDokončete krok 2 a nechte Termux spuštěný."); }
    }

    private void renderStatus() {
        try {
            JSONObject data = new JSONObject(prefs.getString("status", "{}"));
            boolean busy = data.optBoolean("busy");
            for (Button button : commands) button.setEnabled(!busy);
            String phase = data.optString("phase");
            String heading = busy ? "Probíhá: " + data.optString("action") : data.optString("message", "Čekám na propojení s Termuxem");
            state.setText(heading); state.setTextColor(phase.equals("error") || phase.equals("interrupted") ? Color.rgb(163, 48, 35) : TEAL);
            JSONObject env = data.optJSONObject("installed");
            String zephyr = env == null ? "" : env.optString("zephyr");
            versions.setText("Průvodce " + getPackageManager().getPackageInfo(getPackageName(), 0).versionName + "  ·  " + (zephyr.isEmpty() ? "Zephyr zatím neinstalován" : "Zephyr " + zephyr) + (data.has("free_gib") ? "  ·  Volno " + data.optDouble("free_gib") + " GiB" : ""));
            JSONArray apps = data.optJSONArray("apps");
            if (apps != null) { selected = selection(); setExercises(apps); }
            String output = data.optString("log", "Zatím bez výpisu.");
            if (!output.contentEquals(log.getText())) log.setText(output);
            long received = prefs.getLong("received", 0);
            String error = prefs.getString("error", "");
            if (received > lastReceived) {
                lastReceived = received;
                if (!error.isEmpty()) say("Termux: " + error + "\nPokud propojení chybí, dokončete krok 2.");
            }
        } catch (Exception error) { say("Stav zatím není dostupný: " + error.getMessage()); }
    }

    private void download(boolean termux) {
        if (downloading) { say("Stahování již probíhá."); return; }
        downloading = true;
        new Thread(() -> {
            try {
                File apk = Updates.download(getApplicationContext(), termux, this::say);
                prefs.edit().putString("ready_apk", apk.getName()).apply();
                runOnUiThread(() -> { if (active) installApk(apk); });
            } catch (Exception error) { say("Stahování selhalo: " + error.getMessage()); }
            finally { downloading = false; }
        }, "github-download").start();
    }
    private void installApk(File apk) {
        try {
            if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
                say("Povolte tomuto průvodci instalaci aplikací a vraťte se zpět.");
                startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getPackageName())));
                return;
            }
            Intent install = new Intent(Intent.ACTION_INSTALL_PACKAGE);
            install.setDataAndType(Uri.parse("content://" + getPackageName() + ".apk/" + apk.getName()), "application/vnd.android.package-archive");
            install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            prefs.edit().remove("ready_apk").apply();
            startActivity(install);
        } catch (Exception error) { say("Instalátor: " + error.getMessage()); }
    }
    private void checkUpdates() {
        say("Kontroluji GitHub…");
        new Thread(() -> {
            try {
                JSONObject ours = Updates.release(Updates.REPO), termux = Updates.release("termux/termux-app");
                say("Na GitHubu: průvodce a prostředí " + ours.getString("tag_name") + ", Termux " + termux.getString("tag_name") + ". Aktualizaci spusťte odpovídajícím tlačítkem.");
            } catch (Exception error) { say("Aktualizace: " + error.getMessage()); }
        }, "github-check").start();
    }
    private void help() {
        new AlertDialog.Builder(this).setTitle("Zephyr pro Termux")
            .setMessage("1. Nainstalujte GitHub Termux a jednou jej otevřete.\n2. Zkopírujte a vložte příkaz pro propojení.\n3. Povolte příkazy a zvolte Instalovat.\n4. Vyberte cvičení → Sestavit → Spustit.\n\nBez rootu. Ubuntu používá proot; označení root uvnitř Ubuntu není root Androidu.\n\nTab/Shift+Tab, šipky, Enter a mezerník ovládají běžné prvky Androidu. Dotyk, myš i touchpad používají stejné akce.\nCtrl+B sestaví, Ctrl+R spustí, Ctrl+L obnoví stav.\n\nQEMU: Ctrl+A, X. nano: Ctrl+O uloží, Ctrl+X zavře.\n\nZálohy: ~/zephyr-backups. Práce: ~/zephyr-work/zephyr4squirrels. Aktualizace zachovávají změny; při konfliktu se zastaví.\n\nFyzické ESP32 přes USB vyžaduje další řešení; tato verze používá emulátor. Žádná telemetrie.")
            .setPositiveButton("Zavřít", null)
            .setNeutralButton("Dokumentace", (dialog, which) -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/" + Updates.REPO))))
            .show();
    }
    @Override public boolean onKeyShortcut(int code, KeyEvent event) {
        if (event.isCtrlPressed()) {
            if (code == KeyEvent.KEYCODE_B) { permission(() -> command("build")); return true; }
            if (code == KeyEvent.KEYCODE_R) { permission(() -> command("run")); return true; }
            if (code == KeyEvent.KEYCODE_L) { permission(() -> command("status")); return true; }
        }
        return super.onKeyShortcut(code, event);
    }
    @Override public boolean onKeyDown(int code, KeyEvent event) {
        if (code == KeyEvent.KEYCODE_F1) { help(); return true; }
        return super.onKeyDown(code, event);
    }
}
