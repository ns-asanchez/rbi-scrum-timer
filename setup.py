"""py2app build script — creates RBI Scrum Timer.app bundle for macOS."""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("assets", ["assets/AppIcon.icns"]),
    ("data", []),  # empty data dir created at runtime
]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/AppIcon.icns",
    "plist": {
        "CFBundleName": "RBI Scrum Timer",
        "CFBundleDisplayName": "RBI Scrum Timer",
        "CFBundleIdentifier": "com.netskope.rbi.scrumtimer",
        "CFBundleVersion": "1.1.0",
        "CFBundleShortVersionString": "1.1",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # supports dark mode
    },
    "packages": [
        "customtkinter",
        "matplotlib",
        "PIL",
        "mplcursors",
        "app",
    ],
    "includes": ["tkinter", "_tkinter"],
    "excludes": [],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
