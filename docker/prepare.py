"""Apply the container compatibility changes to a private copy of game sources."""
from pathlib import Path
import re


def edit(root, filename, transform):
    path = root / filename
    original = path.read_bytes()
    bom = original.startswith(b"\xef\xbb\xbf")
    text = original.decode("utf-8-sig").replace("\r\n", "\n")
    updated = transform(text)
    if updated != text:
        if b"\r\n" in original:
            updated = updated.replace("\n", "\r\n")
        path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + updated.encode("utf-8"))


def replace_once(text, before, after):
    if after in text:
        return text
    if text.count(before) != 1:
        raise ValueError("Unsupported source version: expected one occurrence of " + before)
    return text.replace(before, after, 1)


def exclude_backend(text, first_case):
    pattern = r"(?m)^ +case " + re.escape(first_case) + r":.*?(?=^ +default:)"
    matches = list(re.finditer(pattern, text, re.DOTALL | re.MULTILINE))
    if len(matches) != 1:
        raise ValueError("Unsupported source version: " + first_case)
    match = matches[0]
    if text[:match.start()].endswith("#if !LINUX\n"):
        return text
    return text[:match.start()] + "#if !LINUX\n" + match[0] + "#endif\n" + text[match.end():]


def configure_linux(text):
    if "#if LINUX\n" in text:
        return text
    pattern = r"(public static void Load\(\)\s*\{\n)(.*?)(^        \})"
    def wrap(match):
        return match[1] + """#if LINUX
            Directory.CreateDirectory(DirPath);
            Video = eVideo.VIDEO_GDI_PLUS;
            Sound = eSound.SOUND_NOSOUND;
            Save();
#else
""" + match[2] + "#endif\n" + match[3]
    result, count = re.subn(pattern, wrap, text, flags=re.DOTALL | re.MULTILINE)
    if count != 1:
        raise ValueError("Unsupported source version: SetupConfig.Load")
    return result


def prepare_sources(root):
    edit(root, "RogueForm.Designer.cs", lambda s: exclude_backend(s, "SetupConfig.eVideo.VIDEO_MANAGED_DIRECTX"))
    edit(root, "Engine/RogueGame.cs", lambda s: exclude_backend(s, "SetupConfig.eSound.SOUND_MANAGED_DIRECTX"))
    edit(root, "SetupConfig.cs", configure_linux)
    edit(root, "Gameplay/GameImages.cs", lambda s: replace_once(
        s, 'string file = FOLDER + id + ".png";',
        'string file = (FOLDER + id + ".png").Replace(\'\\\\\', System.IO.Path.DirectorySeparatorChar);'))
    edit(root, "Program.cs", lambda s: replace_once(
        s, "catch (Exception e)\n                {",
        "catch (Exception e)\n                {\n                    Logger.WriteLine(Logger.Stage.RUN_MAIN, e.ToString());"))


if __name__ == "__main__":
    prepare_sources(Path("."))
