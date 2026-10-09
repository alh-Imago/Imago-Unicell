// unicell_unit_web.ino -- WiFi remote control of the small unit (Tang Nano 20K + SD card) from an ESP32 (ledger #1036).
//
//  * Open  http://unicell.local/   (or the IP address printed on the Serial Monitor) in a browser on the same WiFi.
//  * Login: user "unicell", password = the web password (printed at first boot; change it with  webpass <new>  in the Serial Monitor).
//  * First time:  Serial Monitor (115200, Newline), type   wifi <ssid> <password>   then it joins your WiFi and prints the address.
//    Until WiFi is set (or if it cannot connect) the ESP32 makes its own network "UniCell-Unit" (password = the web password): join it and open http://192.168.4.1/
//  * SECURITY: this is plain HTTP with a password, for a trusted home/lab network only. Do not expose it to the internet. It can overwrite raw SD-card blocks (never blocks below 16).
//
// Pick the design that is loaded on the FPGA (one line below), then upload this sketch.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <FS.h>
#include <SD.h>
#include "unit_link.h"
#include "sensors.h"

// ---- which design is on the FPGA --------------------------------------------------------------------------------------------------------------------
#define DESIGN_CORDIC 1      // 1 input word per item, 1 result: the CORDIC z-convergence (fpga/build/unit_cordic_v1)
// #define DESIGN_TREE4 1    // 4 input words per item, 1 result: the sum of the four (nano/examples/parallel_reduction_tree)
// #define DESIGN_RELAY 1    // 1 input word per item, the same word back (nano/examples/small_relay_chain)

#if defined(DESIGN_TREE4)
  #define DESIGN_NAME  "Parallel reduction tree (sum of 4)"
  #define LANES        4
  #define LANE_NAMES   "four input words per item"
  #define EXAMPLE      "1 2 3 4\n10 20 30 40\n100 200 300 400"
#elif defined(DESIGN_RELAY)
  #define DESIGN_NAME  "Relay chain (word passes through)"
  #define LANES        1
  #define LANE_NAMES   "one input word per item"
  #define EXAMPLE      "7\n123456\n-5"
#else
  #define DESIGN_NAME  "CORDIC z convergence"
  #define LANES        1
  #define LANE_NAMES   "angle z0"
  #define EXAMPLE      "50000\n-50000\n0\n12345\n-12345\n90000"
#endif

// ---- the ESP32's OWN SD card (optional; holds bitstreams, input files, results, the offline kit) ----------------------------------------------------
// A separate SPI bus (HSPI) on four free pins, so it cannot disturb the link to the unit (IO5/18/19/23). Use a 3.3 V-ONLY microSD breakout (see docs/unit_bringup_guide.md).
#define FILE_CS    32
#define FILE_SCK   33
#define FILE_MOSI  25
#define FILE_MISO  26
#define FILE_MAX_BYTES (32UL * 1024UL * 1024UL)
static SPIClass fileSpi(HSPI);
static bool haveFiles = false;
static File upFile;
static String upError;
static uint32_t upBytes = 0;

static WebServer server(80);
static Preferences prefs;
static String wifiSsid, wifiPass, webPass;
static bool apMode = false;

#include "page.h"   // the web page (kept in a header so the Arduino IDE does not mangle its JavaScript)

static bool authed() {
  if (server.authenticate("unicell", webPass.c_str())) return true;
  server.requestAuthentication(BASIC_AUTH, "UniCell unit");
  return false;
}
static void sendJson(int code, const String& body) { server.sendHeader("Cache-Control", "no-store"); server.send(code, "application/json", body); }
static void sendErr(int code, const String& e) { sendJson(code, String("{\"ok\":false,\"error\":\"") + e + "\"}"); }

static String exampleJson() { String s = EXAMPLE; s.replace("\n", "\\n"); return s; }

static void handleRoot() { if (!authed()) return; server.sendHeader("Cache-Control", "no-store"); server.send_P(200, "text/html", PAGE); }

static void handleStatus() {
  if (!authed()) return;
  uint32_t id = rd_reg(R_ID), s = rd_reg(R_STATUS), cap = rd_reg(R_CAP_COUNT);
  String j = "{\"ok\":true,\"design\":\"" DESIGN_NAME "\",\"lanes\":" + String(LANES) + ",\"laneNames\":\"" LANE_NAMES "\",\"example\":\"" + exampleJson() + "\"";
  j += ",\"id\":\"0x" + String(id, HEX) + "\",\"idOk\":" + (id == UNIT_ID ? "true" : "false");
  j += ",\"sdReady\":" + String((s & S_SD_READY) ? "true" : "false") + ",\"sdError\":" + String((s & S_SD_ERROR) ? "true" : "false");
  j += ",\"errCode\":" + String((s >> 8) & 31) + ",\"errCmd\":" + String((s >> 16) & 63) + ",\"errRx\":" + String(s >> 24);
  j += ",\"readyPin\":" + String(digitalRead(PIN_READY)) + ",\"capCount\":" + String(cap);
  j += ",\"ip\":\"" + (apMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) + "\",\"rssi\":" + String(apMode ? 0 : WiFi.RSSI()) + ",\"uptime\":" + String(millis()) + "}";
  sendJson(200, j);
}

static void handleRun() {
  if (!authed()) return;
  static int32_t in[MAX_WORDS], out[MAX_WORDS];
  String txt = server.arg("items"); int n = 0; const char* p = txt.c_str();
  while (*p) {                                   // numbers separated by anything that is not a digit or a minus sign
    if ((*p >= '0' && *p <= '9') || (*p == '-' && p[1] >= '0' && p[1] <= '9')) {
      if (n >= MAX_WORDS) { sendErr(400, "too many words (limit 512)"); return; }
      char* e; long long v = strtoll(p, &e, 10); in[n++] = (int32_t)v; p = e;
    } else p++;
  }
  if (n == 0 || n % LANES) { sendErr(400, String("need a multiple of ") + LANES + " numbers per run (" + LANE_NAMES + ")"); return; }
  int items = n / LANES;
  const char* err = run_items(in, items, LANES, out);
  if (*err) { sendErr(500, err); return; }
  String j = "{\"ok\":true,\"results\":[";
  for (int i = 0; i < items; i++) { if (i) j += ","; j += String((long)out[i]); }
  sendJson(200, j + "]}");
}

// Live sensor feed: read the first LANES sensors, make one item (one word per lane), run it through the design, return readings + result.
// Tree / relay designs get the packed SensorTrix word (amount<<16 | location); the CORDIC gets the raw 16-bit amount as its angle (scale it in your sensor function).
static void handleLive() {
  if (!authed()) return;
  if (SENSOR_COUNT < LANES) { sendErr(400, String("this design needs ") + LANES + " sensor(s); sensors.h lists " + SENSOR_COUNT); return; }
  int32_t in[LANES], out[1]; String r = "";
  uint32_t t0 = millis();
  for (int i = 0; i < LANES; i++) {
    uint16_t a = sensor_amount(SENSORS[i]);
#if defined(DESIGN_CORDIC)
    in[i] = (int32_t)a;
#else
    in[i] = (int32_t)sensor_word(SENSORS[i], a);
#endif
    if (i) r += ",";
    r += String("{\"name\":\"") + SENSORS[i].name + "\",\"loc\":" + SENSORS[i].loc + ",\"amount\":" + a + "}";
  }
  const char* err = run_items(in, 1, LANES, out);
  if (*err) { sendErr(500, err); return; }
  sendJson(200, String("{\"ok\":true,\"readings\":[") + r + "],\"result\":" + String((long)out[0]) + ",\"ms\":" + String(millis() - t0) + "}");
}

static void handleSd() {
  if (!authed()) return;
  String op = server.arg("op"); uint32_t block = strtoul(server.arg("block").c_str(), NULL, 10), n = strtoul(server.arg("n").c_str(), NULL, 10);
  if (op != "load" && op != "save") { sendErr(400, "op must be load or save"); return; }
  const char* err = sd_op(op == "save", block, n);
  if (*err) { sendErr(500, err); return; }
  sendJson(200, "{\"ok\":true}");
}
static void handleSdInit() { if (!authed()) return; wr_reg(R_CONTROL, C_SD_REINIT); delay(300); sendJson(200, "{\"ok\":true}"); }

// file names: letters, digits, dot, dash, underscore, space; 1-40 characters; no path, no leading dot (the card's root folder only)
static bool goodName(const String& n) {
  if (n.length() < 1 || n.length() > 40 || n[0] == '.') return false;
  for (unsigned i = 0; i < n.length(); i++) { char c = n[i]; if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '-' || c == '_' || c == ' ')) return false; }
  return true;
}
static void handleFiles() {
  if (!authed()) return;
  if (!haveFiles) { sendJson(200, "{\"ok\":true,\"card\":false,\"files\":[]}"); return; }
  // NOTE: SD.usedBytes() scans the whole card's allocation table and can block this single-threaded server for many seconds on a big card (the page then looks dead),
  // so "used" is the sum of the listed files' sizes and "total" is the card size, both instant.
  String list = ""; bool first = true; uint64_t used = 0;
  File root = SD.open("/");
  for (File f = root.openNextFile(); f; f = root.openNextFile()) {
    if (f.isDirectory()) continue;
    String n = f.name(); if (!goodName(n)) continue;
    if (!first) list += ","; first = false; used += f.size();
    list += "{\"name\":\"" + n + "\",\"size\":" + String((unsigned long)f.size()) + "}";
  }
  sendJson(200, "{\"ok\":true,\"card\":true,\"total\":" + String((unsigned long)(SD.cardSize() / 1024)) + ",\"used\":" + String((unsigned long)(used / 1024)) + ",\"files\":[" + list + "]}");
}
static void handleDownload() {
  if (!authed()) return;
  String n = server.arg("name");
  if (!haveFiles || !goodName(n)) { sendErr(404, "no such file"); return; }
  File f = SD.open("/" + n, FILE_READ);
  if (!f || f.isDirectory()) { sendErr(404, "no such file"); return; }
  server.sendHeader("Content-Disposition", "attachment; filename=\"" + n + "\"");
  server.streamFile(f, "application/octet-stream"); f.close();
}
static void handleFileDelete() {
  if (!authed()) return;
  String n = server.arg("name");
  if (!haveFiles || !goodName(n)) { sendErr(400, "bad name"); return; }
  if (!SD.remove("/" + n)) { sendErr(404, "could not delete"); return; }
  sendJson(200, "{\"ok\":true}");
}
static void handleUploadDone() {
  if (!authed()) return;
  if (upError.length()) { sendErr(400, upError); return; }
  sendJson(200, String("{\"ok\":true,\"bytes\":") + upBytes + "}");
}
static void handleUploadData() {            // runs while the file arrives; it cannot send a reply, so it records an error for handleUploadDone
  HTTPUpload& u = server.upload();
  if (u.status == UPLOAD_FILE_START) {
    upError = ""; upBytes = 0;
    if (!server.authenticate("unicell", webPass.c_str())) { upError = "not logged in"; return; }
    if (!haveFiles) { upError = "no SD card in the ESP32"; return; }
    if (!goodName(u.filename)) { upError = "file name not allowed (letters, digits . - _ space; at most 40; no folders)"; return; }
    upFile = SD.open("/" + u.filename, FILE_WRITE);
    if (!upFile) upError = "could not create the file";
  } else if (u.status == UPLOAD_FILE_WRITE) {
    if (upError.length() || !upFile) return;
    upBytes += u.currentSize;
    if (upBytes > FILE_MAX_BYTES) { upError = "file too big (limit 32 MB)"; upFile.close(); return; }
    if (upFile.write(u.buf, u.currentSize) != u.currentSize) upError = "write failed (card full?)";
  } else if (u.status == UPLOAD_FILE_END) { if (upFile) upFile.close(); }
  else if (u.status == UPLOAD_FILE_ABORTED) { if (upFile) upFile.close(); upError = "upload aborted"; }
}
static void handleNotFound() { sendErr(404, "not found"); }

static String randomPass() {
  const char* a = "abcdefghjkmnpqrstuvwxyz23456789"; String s; for (int i = 0; i < 10; i++) s += a[esp_random() % 31]; return s;
}
static void startNetwork() {
  apMode = false;
  if (wifiSsid.length()) {
    WiFi.mode(WIFI_STA); WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
    Serial.printf("Joining WiFi \"%s\" ...", wifiSsid.c_str());
    for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
    Serial.println();
  }
  if (WiFi.status() != WL_CONNECTED) {
    apMode = true; WiFi.mode(WIFI_AP); WiFi.softAP("UniCell-Unit", webPass.c_str());
    Serial.printf("No WiFi: own network \"UniCell-Unit\" (password = the web password). Open http://%s/\n", WiFi.softAPIP().toString().c_str());
  } else Serial.printf("WiFi up. Open  http://%s/   or  http://unicell.local/\n", WiFi.localIP().toString().c_str());
  MDNS.begin("unicell");
}

static String line;
static void serialCmd(char* s) {
  char* cmd = strtok(s, " "); if (!cmd) return; char* a = strtok(NULL, " "); char* b = strtok(NULL, "");
  if (!strcmp(cmd, "wifi") && a) { wifiSsid = a; wifiPass = b ? b : ""; prefs.putString("ssid", wifiSsid); prefs.putString("pass", wifiPass); Serial.println("saved; restarting"); delay(300); ESP.restart(); }
  else if (!strcmp(cmd, "wificlear")) { prefs.remove("ssid"); prefs.remove("pass"); Serial.println("WiFi forgotten; restarting"); delay(300); ESP.restart(); }
  else if (!strcmp(cmd, "webpass") && a && strlen(a) >= 8) { webPass = a; prefs.putString("webpass", webPass); Serial.println("web password changed (the own-network password too, after a restart)"); }
  else if (!strcmp(cmd, "webpass")) Serial.println("usage: webpass <at least 8 characters, no spaces>");
  else if (!strcmp(cmd, "ip")) Serial.printf("http://%s/  user: unicell  password: %s\n", (apMode ? WiFi.softAPIP() : WiFi.localIP()).toString().c_str(), webPass.c_str());
  else if (!strcmp(cmd, "id")) { uint32_t v = rd_reg(R_ID); Serial.printf("ID = 0x%08X %s\n", (unsigned)v, v == UNIT_ID ? "OK" : "WRONG"); }
  else if (!strcmp(cmd, "reboot")) ESP.restart();
  else Serial.println("commands: wifi <ssid> <password> | wificlear | webpass <pw> | ip | id | reboot");
}

void setup() {
  Serial.begin(115200);
  link_begin();
  sensors_begin();
  fileSpi.begin(FILE_SCK, FILE_MISO, FILE_MOSI, FILE_CS);
  haveFiles = SD.begin(FILE_CS, fileSpi, 4000000);
  Serial.println(haveFiles ? "ESP32 SD card: found" : "ESP32 SD card: none (fine; the file panel will say so)");
  prefs.begin("unicell", false);
  wifiSsid = prefs.getString("ssid", ""); wifiPass = prefs.getString("pass", ""); webPass = prefs.getString("webpass", "");
  if (webPass.length() < 8) { webPass = randomPass(); prefs.putString("webpass", webPass); Serial.printf("\nFirst boot: web password generated: %s   (change with: webpass <new>)\n", webPass.c_str()); }
  Serial.println("\nUniCell unit web control. Design: " DESIGN_NAME);
  startNetwork();
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/run", HTTP_POST, handleRun);
  server.on("/api/live", HTTP_GET, handleLive);
  server.on("/api/sd", HTTP_POST, handleSd);
  server.on("/api/sdinit", HTTP_POST, handleSdInit);
  server.on("/api/files", HTTP_GET, handleFiles);
  server.on("/files", HTTP_GET, handleDownload);
  server.on("/api/filedel", HTTP_POST, handleFileDelete);
  server.on("/api/upload", HTTP_POST, handleUploadDone, handleUploadData);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("Type  ip  to see the address and password; help = any other word.");
}

void loop() {
  server.handleClient();
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (line.length()) { char buf[160]; line.toCharArray(buf, sizeof buf); line = ""; serialCmd(buf); } }
    else if (line.length() < 150) line += c;
  }
  if (!apMode && WiFi.status() != WL_CONNECTED) { static uint32_t t = 0; if (millis() - t > 15000) { t = millis(); WiFi.reconnect(); } }
}
