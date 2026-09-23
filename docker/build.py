"""Derive a Mono build from the original project's explicit source/resource lists."""
import xml.etree.ElementTree as ET
from pathlib import Path
from prepare import prepare_sources

prepare_sources(Path('.'))

ns = "http://schemas.microsoft.com/developer/msbuild/2003"
ET.register_namespace("", ns)
tree = ET.parse("RogueSurvivor.csproj")
root = tree.getroot()
files = {str(p).casefold(): str(p) for p in Path('.').rglob('*') if p.is_file()}
excluded = ("UI\\DXGameCanvas", "Engine\\MDXSoundManager", "Engine\\SFMLSoundManager")
for parent in root.iter():
    for node in list(parent):
        tag = node.tag.split("}")[-1]
        name = node.get("Include", "")
        actual = files.get(name.replace('\\', '/').casefold())
        if actual:
            node.set("Include", actual.replace('/', '\\'))
        if (tag == "Reference" and name.startswith(("Microsoft.DirectX", "Microsoft.VisualC", "sfmlnet-"))
                or tag in ("Compile", "EmbeddedResource") and name.startswith(excluded)
                or tag == "Content" and name.lower().endswith(".dll")
                or tag == "PostBuildEvent"):
            parent.remove(node)
        elif tag == "TargetFrameworkVersion":
            node.text = "v4.5"
        elif tag == "DefineConstants":
            node.text = "TRACE;LINUX"
        elif tag == "GenerateSerializationAssemblies":
            node.text = "Off"
tree.write("RogueSurvivor.Linux.csproj", encoding="utf-8", xml_declaration=True)
with open("app.config", "w") as config:
    config.write('<configuration><startup><supportedRuntime version="v4.0"/></startup></configuration>\n')
