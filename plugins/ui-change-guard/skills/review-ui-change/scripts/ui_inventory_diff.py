#!/usr/bin/env python3
"""Diff the UI "inventory" of changed template/component files between a git base and the working tree.

Inventory = the things other code depends on or that users act on: forms, form fields, buttons,
links, htmx attributes, event handlers, element ids/test ids, template conditionals, template
variables, includes, external scripts/styles, and timers. Regex-based, framework-agnostic: works on
Jinja/Django/Twig/HTML, Vue/Svelte/Astro, JSX/TSX — and native UI: React Native/Expo (.tsx/.jsx),
SwiftUI/UIKit (.swift), Jetpack Compose (.kt), Android XML layouts (.xml), Flutter (.dart).
Native files produce the categories: actions, inputs, navigation, dialogs, a11y, ids, lists, timers,
permissions, conditionals (web categories stay empty for them).

Usage:
  ui_inventory_diff.py [--base REF] [--json] [FILE ...]

  --base REF   git ref to compare against (default: merge-base of HEAD and origin/main|main|master,
               falling back to HEAD). Working tree (incl. untracked files) is always the "new" side.
  FILE ...     restrict to these files; default = all changed UI files.

Output: per file, items REMOVED and ADDED per category. Items present in both are not printed.
"""
import argparse
import json
import re
import subprocess
import sys

UI_EXT = (".html", ".htm", ".jinja", ".jinja2", ".j2", ".twig", ".hbs", ".ejs", ".njk",
          ".vue", ".svelte", ".astro", ".jsx", ".tsx", ".swift", ".kt", ".kts", ".dart", ".xml")
NATIVE_EXT = (".swift", ".kt", ".kts", ".dart", ".xml")
NATIVE_CATS = ("actions", "inputs", "navigation", "dialogs", "a11y", "lists", "permissions")

# --- native extractors: (category, regex, formatter-group-indexes) per platform ---
# Each regex yields one inventory line; groups joined with " ". Kept deliberately shallow:
# the goal is "what did the user lose / what got wired", not a parser.
NATIVE = {
    "rn": [  # React Native / Expo (also matched inside .tsx/.jsx when RN imports are present)
        ("actions", re.compile(r"""<(Button|Pressable|TouchableOpacity|TouchableHighlight|TouchableWithoutFeedback|IconButton|FAB|Chip|MenuItem|ListItem)\b([^>]*?)(?:/>|>)""", re.S)),
        ("actions", re.compile(r"""\b(onPress|onLongPress|onSubmitEditing|onEndEditing|onValueChange|onRefresh|onEndReached|onTouchEnd|onTouchStart|onStartShouldSetResponder)\s*=\s*\{([^}]{0,60})""")),
        ("conditionals", re.compile(r"""\{\s*([\w.!?]+(?:\s*(?:===?|!==?)\s*[\w.'"]+)?)\s*&&\s*<""")),
        ("conditionals", re.compile(r"""\{\s*([\w.!?]+(?:\s*(?:===?|!==?)\s*[\w.'"]+)?)\s*\?\s*<""")),
        ("inputs", re.compile(r"""<(TextInput|Switch|Picker|Slider|Checkbox|RadioButton|DateTimePicker|Select)\b([^>]*?)(?:/>|>)""", re.S)),
        ("navigation", re.compile(r"""\b(?:navigation\.(?:navigate|push|replace|reset)|router\.(?:push|replace|navigate)|Linking\.openURL|<Link\s+href=)\s*\(?\s*[\"'`]([^\"'`]+)""")),
        ("dialogs", re.compile(r"""\b(Alert\.alert|ActionSheetIOS|<Modal\b|<BottomSheet|<Dialog\b|showActionSheetWithOptions)""")),
        ("a11y", re.compile(r"""\b(accessibilityLabel|accessibilityRole|accessibilityHint|accessible|aria-label|accessibilityState)\s*=\s*(?:\{?[\"'`]([^\"'`]*)[\"'`]|\{([^}]{0,40}))""")),
        ("ids", re.compile(r"""\b(testID|nativeID)\s*=\s*\{?[\"'`]([^\"'`]+)""")),
        ("lists", re.compile(r"""<(FlatList|SectionList|FlashList|VirtualizedList|ScrollView|LegendList)\b""")),
        ("lists", re.compile(r"""(\.map\(\s*\(?\s*\w+[^)]*\)?\s*=>\s*\(?\s*<)""")),  # inline .map rendering (unvirtualized)
        ("permissions", re.compile(r"""\b(request\w*Permissions?Async|PermissionsAndroid\.request|requestPermission|Camera\.requestCameraPermission|Location\.request\w+|Notifications\.requestPermissionsAsync)\b""")),
        ("timers", re.compile(r"""\b(setInterval|setTimeout|requestAnimationFrame|InteractionManager\.runAfterInteractions)\s*\(""")),
    ],
    "swift": [
        ("actions", re.compile(r"""\b(Button|NavigationLink|Toggle|Menu|Link|ShareLink|EditButton|ContextMenu)\s*\(\s*(?:[\"']([^\"']{0,50})[\"']|(\w+(?:\.\w+)*))?""")),
        ("actions", re.compile(r"""\.(onTapGesture|onLongPressGesture|swipeActions|onSubmit|refreshable|onDelete|onMove|contextMenu|gesture)\b""")),
        ("actions", re.compile(r"""\b(@IBAction\s+func\s+\w+|addTarget\([^,]+,\s*action:\s*#selector\((\w+))""")),
        ("inputs", re.compile(r"""\b(TextField|SecureField|TextEditor|Picker|DatePicker|Stepper|Slider|ColorPicker|Toggle)\s*\(\s*(?:[\"']([^\"']{0,50})[\"'])?[^)]*?(?:text|selection|isOn|value):\s*\$?([\w.]+)""", re.S)),
        ("inputs", re.compile(r"""\b(UITextField|UITextView|UISwitch|UISegmentedControl|UIDatePicker|UISlider|UIStepper)\b""")),
        ("navigation", re.compile(r"""\b(NavigationLink|\.navigationDestination|\.sheet|\.fullScreenCover|\.popover|pushViewController|present\(|performSegue\(withIdentifier:\s*[\"']([^\"']+)|\.navigationTitle\([\"']([^\"']+))""")),
        ("dialogs", re.compile(r"""\.(alert|confirmationDialog|sheet|fullScreenCover)\s*\(\s*(?:[\"']([^\"']{0,50})[\"'])?|\bUIAlertController\(""")),
        ("a11y", re.compile(r"""\.(accessibilityLabel|accessibilityHint|accessibilityValue|accessibilityHidden|accessibilityAddTraits|accessibilityIdentifier)\s*\(\s*([^)]{0,50})""")),
        ("ids", re.compile(r"""\.accessibilityIdentifier\(\s*[\"']([^\"']+)""")),
        ("lists", re.compile(r"""\b(List|ForEach|LazyVStack|LazyHStack|LazyVGrid|LazyHGrid|VStack|HStack|ScrollView|UITableView|UICollectionView)\s*[({]""")),
        ("permissions", re.compile(r"""\b(requestAuthorization|requestWhenInUseAuthorization|requestAlwaysAuthorization|requestAccess\(for:|AVCaptureDevice\.requestAccess|PHPhotoLibrary\.requestAuthorization|UNUserNotificationCenter)\b""")),
        ("timers", re.compile(r"""\b(Timer\.(?:publish|scheduledTimer)|DispatchQueue\.main\.asyncAfter|Task\.sleep|CADisplayLink|\.task\s*\{|\.onReceive\()""")),
        ("conditionals", re.compile(r"""^\s*(?:if|guard)\s+((?:let\s+\w+\s*=\s*)?[\w.]*(?:is[A-Z]\w*|can[A-Z]\w*|has[A-Z]\w*|role|permission|entitle\w*|premium|pro|admin|subscri\w*|feature\w*|flag\w*)[\w.!=() ]*)""", re.M | re.I)),
    ],
    "compose": [
        ("actions", re.compile(r"""\b(Button|TextButton|OutlinedButton|IconButton|FloatingActionButton|ExtendedFloatingActionButton|FilledTonalButton|ElevatedButton|Chip|AssistChip|FilterChip|DropdownMenuItem|NavigationBarItem|ListItem)\s*\(""")),
        ("actions", re.compile(r"""\b(onClick|onLongClick|onCheckedChange|onValueChange|onDismissRequest|onRefresh)\s*=\s*\{?\s*([^,)}\n]{0,50})""")),
        ("actions", re.compile(r"""Modifier\s*\.\s*(clickable|combinedClickable|toggleable|selectable|swipeable|draggable|pointerInput)\b""")),
        ("inputs", re.compile(r"""\b(TextField|OutlinedTextField|BasicTextField|Switch|Checkbox|RadioButton|Slider|RangeSlider|DatePicker|TimePicker|DropdownMenu|ExposedDropdownMenuBox)\s*\(""")),
        ("inputs", re.compile(r"""\bvalue\s*=\s*([\w.]+)\s*,\s*onValueChange""")),
        ("navigation", re.compile(r"""\b(?:navController|navigator|nav)\.(?:navigate|popBackStack|navigateUp)\s*\(\s*(?:[\"']([^\"']+)|([\w.]+))|composable\s*\(\s*(?:route\s*=\s*)?[\"']([^\"']+)""")),
        ("dialogs", re.compile(r"""\b(AlertDialog|Dialog|ModalBottomSheet|BottomSheetScaffold|Snackbar|SnackbarHost|BasicAlertDialog|DatePickerDialog)\s*\(""")),
        ("a11y", re.compile(r"""\b(contentDescription|semantics|clearAndSetSemantics|stateDescription|role)\s*(?:=|\{)\s*([^,)}\n]{0,50})""")),
        ("ids", re.compile(r"""\.testTag\(\s*[\"']([^\"']+)""")),
        ("lists", re.compile(r"""\b(LazyColumn|LazyRow|LazyVerticalGrid|LazyHorizontalGrid|LazyVerticalStaggeredGrid|Column|Row|verticalScroll|horizontalScroll|RecyclerView)\b""")),
        ("lists", re.compile(r"""(\.forEach\s*\{[^}]{0,40}(?:Text|Card|Row|Item|ListItem)\()""")),  # forEach inside Column = unvirtualized
        ("permissions", re.compile(r"""\b(rememberLauncherForActivityResult|RequestPermission|RequestMultiplePermissions|requestPermissions|ActivityCompat\.requestPermissions|rememberPermissionState|rememberMultiplePermissionsState)\b""")),
        ("timers", re.compile(r"""\b(LaunchedEffect|DisposableEffect|SideEffect|produceState|delay\(|while\s*\(\s*true|withFrameNanos|rememberInfiniteTransition|Timer\(|Handler\(|postDelayed)\b""")),
        ("conditionals", re.compile(r"""^\s*if\s*\(\s*([\w.!]*(?:is[A-Z]\w*|can[A-Z]\w*|has[A-Z]\w*|role|permission|entitle\w*|premium|pro|admin|subscri\w*|feature\w*|flag\w*)[\w.!=() ]*)\)""", re.M | re.I)),
    ],
    "android_xml": [
        ("actions", re.compile(r"""<(Button|ImageButton|FloatingActionButton|MaterialButton|Chip|MenuItem|item)\b[^>]*?(?:android:id=\"@\+?id/(\w+)\"|android:text=\"([^\"]*)\")""", re.S)),
        ("actions", re.compile(r"""android:onClick=\"(\w+)\"""")),
        ("inputs", re.compile(r"""<(EditText|TextInputEditText|AutoCompleteTextView|Spinner|Switch|SwitchMaterial|CheckBox|RadioButton|SeekBar|DatePicker|TimePicker|RatingBar)\b[^>]*?android:id=\"@\+?id/(\w+)\"""", re.S)),
        ("inputs", re.compile(r"""android:(inputType|hint|maxLength|imeOptions|autofillHints)=\"([^\"]*)\"""")),
        ("navigation", re.compile(r"""<(fragment|action|deepLink|activity)\b[^>]*?(?:android:id=\"@\+?id/(\w+)\"|app:destination=\"@\+?id/(\w+)\"|android:name=\"([\w.]+)\"|app:uri=\"([^\"]+)\")""", re.S)),
        ("a11y", re.compile(r"""android:(contentDescription|importantForAccessibility|labelFor|accessibilityHeading|screenReaderFocusable)=\"([^\"]*)\"""")),
        ("ids", re.compile(r"""android:id=\"@\+?id/(\w+)\"""")),
        ("lists", re.compile(r"""<(RecyclerView|androidx\.recyclerview\.widget\.RecyclerView|ListView|ScrollView|NestedScrollView|HorizontalScrollView|ViewPager2)\b""")),
        ("permissions", re.compile(r"""<uses-permission[^>]*android:name=\"([\w.]+)\"""")),
    ],
    "flutter": [
        ("actions", re.compile(r"""\b(ElevatedButton|TextButton|OutlinedButton|IconButton|FloatingActionButton|FilledButton|InkWell|GestureDetector|ListTile|PopupMenuButton|PopupMenuItem|Chip|ActionChip|CupertinoButton|Dismissible)\s*(?:\.icon)?\s*\(""")),
        ("actions", re.compile(r"""\b(onPressed|onTap|onLongPress|onChanged|onSubmitted|onDismissed|onRefresh|onSelected)\s*:\s*([^,\n]{0,50})""")),
        ("inputs", re.compile(r"""\b(TextField|TextFormField|CupertinoTextField|Switch|Checkbox|Radio|Slider|DropdownButton|DropdownButtonFormField|DatePicker|CupertinoSwitch)\s*(?:<[^>]+>)?\s*\(""")),
        ("inputs", re.compile(r"""\b(controller|validator|keyboardType|inputFormatters|autofillHints|obscureText)\s*:\s*([^,\n]{0,40})""")),
        ("navigation", re.compile(r"""\b(?:Navigator\.(?:of\(context\)\.)?(?:push|pushNamed|pushReplacement|pop|popUntil)|context\.(?:go|push|pop)|GoRoute\(\s*path:)\s*\(?\s*(?:[\"']([^\"']+))?""")),
        ("dialogs", re.compile(r"""\b(showDialog|showModalBottomSheet|showCupertinoDialog|showCupertinoModalPopup|AlertDialog|SnackBar|showSnackBar|SimpleDialog|showDatePicker|showTimePicker)\b""")),
        ("a11y", re.compile(r"""\b(Semantics|semanticLabel|excludeFromSemantics|MergeSemantics|ExcludeSemantics|tooltip)\s*[:(]\s*([^,)\n]{0,50})""")),
        ("ids", re.compile(r"""\b(?:Key|ValueKey)\(\s*[\"']([^\"']+)""")),
        ("lists", re.compile(r"""\b(ListView\.builder|ListView\.separated|GridView\.builder|SliverList|SliverGrid|CustomScrollView|ListView|GridView|Column|Row|SingleChildScrollView|PageView)\s*\(""")),
        ("lists", re.compile(r"""(\.map\(\s*\(?\s*\w+\)?\s*=>\s*\w+\()""")),
        ("permissions", re.compile(r"""\b(Permission\.\w+\.request|requestPermission|openAppSettings|Geolocator\.requestPermission|ImagePicker)\b""")),
        ("timers", re.compile(r"""\b(Timer\.periodic|Timer\(|Future\.delayed|Ticker|AnimationController\([^)]*repeat|\.repeat\()""")),
        ("conditionals", re.compile(r"""^\s*if\s*\(\s*([\w.!]*(?:is[A-Z]\w*|can[A-Z]\w*|has[A-Z]\w*|role|permission|entitle\w*|premium|pro|admin|subscri\w*|feature\w*|flag\w*)[\w.!=() ]*)\)""", re.M | re.I)),
    ],
}
RN_HINT = re.compile(r"""from\s+[\"'](?:react-native|expo|expo-router|@react-navigation|react-native-paper|@shopify/flash-list|nativewind)""")


def platform_of(path, src):
    low = path.lower()
    if low.endswith(".swift"):
        return "swift"
    if low.endswith((".kt", ".kts")):
        return "compose"
    if low.endswith(".dart"):
        return "flutter"
    if low.endswith(".xml"):
        return "android_xml" if ("android:" in src or "<manifest" in src) else None
    if low.endswith((".tsx", ".jsx")) and RN_HINT.search(src):
        return "rn"
    return "web"


def native_inventory(src, platform):
    inv = {k: set() for k in NATIVE_CATS + ("ids", "timers", "conditionals")}
    for cat, rx in NATIVE[platform]:
        for m in rx.finditer(src):
            parts = [g.strip() for g in m.groups() if g] or [m.group(0).strip()]
            inv[cat].add(" ".join(parts)[:100])
    return inv


TAG = re.compile(r"<(form|input|select|textarea|button|a|option)\b([^>]*)>", re.I | re.S)
ATTR = re.compile(r"""([@:\w.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\{[^}]*\}))""", re.S)
HX = re.compile(r"""\b(hx-[\w-]+)\s*=\s*["']([^"']*)["']""")
HANDLER = re.compile(r"""(?:^|\s)((?:@|x-on:|v-on:)[\w.:-]+|on[a-z]+)\s*=""", re.I)
ALPINE = re.compile(r"""\b(x-(?:model|show|if|for|data|html|text|init|effect))\s*=\s*["']([^"']*)["']""")
ID = re.compile(r"""\b(id|data-testid|data-test|data-cy)\s*=\s*["']([^"']+)["']""")
COND = re.compile(r"\{%-?\s*(if|elif)\s+(.+?)\s*-?%\}|\bv-if\s*=\s*\"([^\"]+)\"|\{#if\s+([^}]+)\}|\*ngIf\s*=\s*\"([^\"]+)\"")
INCLUDE = re.compile(r"\{%-?\s*(include|extends|import|from)\s+[\"']([^\"']+)[\"']|\bimport\s+.*?from\s+[\"']([^\"']+)[\"']")
URLFOR = re.compile(r"\burl_for\(\s*[\"']([^\"']+)[\"']|\{%\s*url\s+[\"']([^\"']+)[\"']|\burl\(\s*[\"']([^\"']+)[\"']|\bpath\(\s*[\"']([^\"']+)[\"']")
VAR = re.compile(r"\{\{-?\s*([A-Za-z_][\w]*)|\{%-?\s*for\s+[\w, ]+\s+in\s+([A-Za-z_][\w]*)")
EXTERNAL = re.compile(r"""<(?:script|link)\b[^>]*?(?:src|href)\s*=\s*["']([^"']+)["']""", re.I)
TIMER = re.compile(r"""\b(setInterval|setTimeout|requestAnimationFrame)\s*\(|hx-trigger\s*=\s*["'][^"']*\bevery\s+[\w.]+""")
JINJA_KEYWORDS = {"if", "for", "else", "endif", "endfor", "block", "endblock", "set", "with", "loop",
                  "super", "self", "range", "dict", "lipsum", "cycler", "joiner", "namespace", "true", "false", "none",
                  "True", "False", "None", "request", "url_for", "csrf_token", "_", "gettext", "ngettext"}
TEXT_STRIP = re.compile(r"<[^>]+>|\{\{.*?\}\}|\{%.*?%\}|\s+", re.S)


def attrs(s):
    out = {}
    for m in ATTR.finditer(s):
        out[m.group(1).lower()] = (m.group(2) or m.group(3) or m.group(4) or "").strip()
    return out


def inner_text(src, end_pos, tag):
    close = re.search(r"</%s\s*>" % tag, src[end_pos:], re.I)
    if not close:
        return ""
    return TEXT_STRIP.sub(" ", src[end_pos:end_pos + close.start()]).strip()[:60]


def inventory(src):
    inv = {k: set() for k in ("forms", "fields", "option_values", "buttons", "links", "htmx", "handlers",
                              "alpine", "ids", "conditionals", "includes", "routes", "variables",
                              "external_assets", "timers")}
    for m in TAG.finditer(src):
        tag, a = m.group(1).lower(), attrs(m.group(2))
        if tag == "form":
            inv["forms"].add("form action=%s method=%s enctype=%s" % (
                a.get("action", a.get("hx-post", a.get("hx-get", ""))), a.get("method", "get").lower(), a.get("enctype", "")))
        elif tag in ("input", "select", "textarea"):
            t = a.get("type", "text" if tag == "input" else tag).lower()
            if t in ("submit", "button", "reset", "image"):
                inv["buttons"].add("%s type=%s name=%s value=%s" % (tag, t, a.get("name", ""), a.get("value", "")))
                continue
            flags = " ".join(f for f in ("required", "disabled", "readonly", "multiple", "checked") if f in a)
            inv["fields"].add(("%s name=%s type=%s %s" % (tag, a.get("name", "(no name)"), t, flags)).rstrip())
        elif tag == "option":
            inv["option_values"].add("option value=%s" % a.get("value", inner_text(src, m.end(), "option")))
        elif tag == "button":
            inv["buttons"].add("button type=%s name=%s value=%s text=%r" % (
                a.get("type", "submit"), a.get("name", ""), a.get("value", ""), inner_text(src, m.end(), "button")))
        elif tag == "a":
            if "href" in a or "hx-get" in a or "hx-post" in a or "role" in a:
                inv["links"].add("a href=%s text=%r" % (a.get("href", a.get("hx-get", a.get("hx-post", ""))), inner_text(src, m.end(), "a")))
    for m in HX.finditer(src):
        inv["htmx"].add("%s=%s" % (m.group(1), m.group(2).strip()[:80]))
    for m in HANDLER.finditer(src):
        inv["handlers"].add(m.group(1))
    for m in ALPINE.finditer(src):
        inv["alpine"].add("%s=%s" % (m.group(1), m.group(2).strip()[:80]))
    for m in ID.finditer(src):
        inv["ids"].add("%s=%s" % (m.group(1), m.group(2)))
    for m in COND.finditer(src):
        inv["conditionals"].add(next(g for g in m.groups()[1:] if g).strip()[:100])
    for m in INCLUDE.finditer(src):
        inv["includes"].add(m.group(2) or m.group(3))
    for m in URLFOR.finditer(src):
        inv["routes"].add(next(g for g in m.groups() if g))
    loop_vars = set(re.findall(r"\{%-?\s*for\s+([\w, ]+?)\s+in\b", src))
    loop_vars = {v.strip() for grp in loop_vars for v in grp.split(",")}
    for m in VAR.finditer(src):
        v = m.group(1) or m.group(2)
        if v not in JINJA_KEYWORDS and v not in loop_vars:
            inv["variables"].add(v)
    for m in EXTERNAL.finditer(src):
        inv["external_assets"].add(m.group(1))
    for m in TIMER.finditer(src):
        inv["timers"].add(m.group(0).strip()[:60])
    return inv


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def default_base():
    for ref in ("origin/main", "origin/master", "main", "master"):
        mb = git("merge-base", "HEAD", ref)
        if mb:
            return mb.strip()
    return "HEAD"


def changed_files(base):
    files = set((git("diff", "--name-only", base) or "").split())
    files |= set((git("ls-files", "--others", "--exclude-standard") or "").split())
    return sorted(f for f in files if f.lower().endswith(UI_EXT))


def read_new(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""  # deleted in working tree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()
    base = args.base or default_base()
    files = args.files or changed_files(base)
    if not files:
        print("No changed UI files vs %s." % base)
        return
    report = {}
    for f in files:
        old_src, new_src = git("show", "%s:%s" % (base, f)) or "", read_new(f)
        platform = platform_of(f, new_src or old_src)
        if platform is None:
            continue  # non-UI .xml (configs, resources without android: namespace)
        build = inventory if platform == "web" else (lambda s_, p_=platform: native_inventory(s_, p_))
        old, new = build(old_src), build(new_src)
        diff = {"_platform": platform} if platform != "web" else {}
        for cat in old:
            removed, added = sorted(old[cat] - new[cat]), sorted(new[cat] - old[cat])
            if removed or added:
                diff[cat] = {"removed": removed, "added": added}
        report[f] = diff
    if args.json:
        json.dump({"base": base, "files": report}, sys.stdout, indent=2)
        return
    print("# UI inventory diff vs %s\n" % base[:12])
    for f, diff in report.items():
        platform = diff.pop("_platform", None)
        print("## %s%s" % (f, " (%s)" % platform if platform else ""))
        if not diff:
            print("(no inventory changes — text/style only)\n")
            continue
        for cat, d in diff.items():
            for item in d["removed"]:
                print("- REMOVED %s: %s" % (cat, item))
            for item in d["added"]:
                print("- ADDED   %s: %s" % (cat, item))
        print()


if __name__ == "__main__":
    main()
