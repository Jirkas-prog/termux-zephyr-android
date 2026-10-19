package cz.zephyr.termux;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

final class Updates {
    static final String REPO = "Jirkas-prog/termux-zephyr-android";
    static final String TERMUX_CERT = "b6da01480eefd5fbf2cd3771b8d1021ec791304bdd6c4bf41d3faabad48ee5e1";
    interface Progress { void report(String message); }

    static HttpURLConnection connect(String url) throws Exception {
        URL target = new URL(url);
        if (!"https".equals(target.getProtocol())) throw new Exception("Vyžadováno HTTPS.");
        HttpURLConnection connection = (HttpURLConnection) target.openConnection();
        connection.setConnectTimeout(30000);
        connection.setReadTimeout(60000);
        connection.setRequestProperty("User-Agent", "Termux-Zephyr-Android");
        if (connection.getResponseCode() != 200) {
            int status = connection.getResponseCode();
            connection.disconnect();
            throw new Exception("GitHub HTTP " + status + ". Zkuste to později; bez přihlášení platí limit GitHub API.");
        }
        return connection;
    }

    static String text(String url) throws Exception {
        HttpURLConnection connection = connect(url);
        try (InputStream input = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
                if (output.size() > 2 * 1024 * 1024) throw new Exception("Příliš velká metadata.");
            }
            return new String(output.toByteArray(), StandardCharsets.UTF_8);
        } finally { connection.disconnect(); }
    }

    static JSONObject release(String repo) throws Exception {
        return new JSONObject(text("https://api.github.com/repos/" + repo + "/releases/latest"));
    }

    static String asset(JSONObject release, String repo, String suffix) throws Exception {
        JSONArray assets = release.getJSONArray("assets");
        for (int i = 0; i < assets.length(); i++) {
            JSONObject item = assets.getJSONObject(i);
            if (item.getString("name").endsWith(suffix)) {
                String url = item.getString("browser_download_url");
                if (!url.startsWith("https://github.com/" + repo + "/releases/download/")) throw new Exception("Neočekávaná adresa souboru.");
                return url;
            }
        }
        throw new Exception("Vydání neobsahuje požadovaný soubor: " + suffix);
    }

    static String hex(byte[] bytes) {
        StringBuilder text = new StringBuilder();
        for (byte b : bytes) text.append(String.format(Locale.ROOT, "%02x", b & 255));
        return text.toString();
    }

    static String certificate(PackageInfo info) throws Exception {
        if (info == null) throw new Exception("Neplatný APK balíček.");
        Signature[] signatures = Build.VERSION.SDK_INT >= 28 ? info.signingInfo.getApkContentsSigners() : info.signatures;
        if (signatures == null || signatures.length != 1) throw new Exception("Neplatný podpis APK.");
        return hex(MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray()));
    }

    static int flags() { return Build.VERSION.SDK_INT >= 28 ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES; }

    static String abi() throws Exception {
        for (String abi : Build.SUPPORTED_64_BIT_ABIS) {
            if (abi.equals("arm64-v8a") || abi.equals("x86_64")) return abi;
        }
        throw new Exception("Zephyr vyžaduje 64bitový Android ARM64 nebo x86_64.");
    }

    static File download(Context context, boolean termux, Progress progress) throws Exception {
        String repo = termux ? "termux/termux-app" : REPO;
        progress.report("Zjišťuji nejnovější vydání na GitHubu…");
        JSONObject release = release(repo);
        String url = asset(release, repo, termux ? "github-debug_" + abi() + ".apk" : "zephyr-termux.apk");
        String checksumUrl = asset(release, repo, termux ? "github-debug_sha256sums" : "SHA256SUMS.txt");
        String filename = android.net.Uri.parse(url).getLastPathSegment();
        String expected = null;
        for (String line : text(checksumUrl).split("\n")) {
            String[] parts = line.trim().split("\\s+", 2);
            if (parts.length == 2 && parts[1].replaceFirst("^\\*", "").equals(filename) && parts[0].matches("[a-fA-F0-9]{64}")) expected = parts[0];
        }
        if (expected == null) throw new Exception("Chybí SHA-256 pro vybraný APK.");
        File target = new File(context.getFilesDir(), termux ? "termux.apk" : "zephyr.apk");
        File partial = new File(context.getFilesDir(), target.getName() + ".part");
        HttpURLConnection connection = connect(url);
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long total = 0, reported = -1;
            try (InputStream input = connection.getInputStream(); FileOutputStream output = new FileOutputStream(partial)) {
                byte[] buffer = new byte[65536];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    total += count;
                    if (total > 200L * 1024 * 1024) throw new Exception("APK přesahuje limit 200 MiB.");
                    output.write(buffer, 0, count);
                    digest.update(buffer, 0, count);
                    long mib = total / (1024 * 1024);
                    if (mib != reported) { reported = mib; progress.report("Stahuji " + release.getString("tag_name") + " · " + mib + " MiB"); }
                }
            }
            if (!hex(digest.digest()).equalsIgnoreCase(expected)) throw new Exception("Kontrolní součet SHA-256 nesouhlasí. Soubor se nenainstaluje.");
            PackageManager pm = context.getPackageManager();
            PackageInfo archive = pm.getPackageArchiveInfo(partial.getPath(), flags());
            String packageName = termux ? "com.termux" : context.getPackageName();
            if (archive == null || !packageName.equals(archive.packageName)) throw new Exception("Nesouhlasí název APK balíčku.");
            String cert = termux ? TERMUX_CERT : certificate(pm.getPackageInfo(packageName, flags()));
            if (!certificate(archive).equals(cert)) throw new Exception("APK nemá důvěryhodný podpis.");
            try {
                PackageInfo installed = pm.getPackageInfo(packageName, flags());
                if (!certificate(installed).equals(cert)) throw new Exception("Nainstalovaná aplikace je z jiného zdroje. Nejdříve zálohujte data; podpisy nelze míchat.");
                if (archive.versionCode < installed.versionCode) throw new Exception("Starší verze se nenainstaluje.");
            } catch (PackageManager.NameNotFoundException ignored) { }
            if (!partial.renameTo(target)) throw new Exception("APK nelze uložit.");
            progress.report("SHA-256 a podpis ověřeny. Připraveno k instalaci.");
            return target;
        } finally {
            connection.disconnect();
            if (partial.exists()) partial.delete();
        }
    }
}
