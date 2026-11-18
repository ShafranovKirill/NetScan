#ifndef AppVersion
  #error "Pass /DAppVersion matching pyproject.toml"
#endif
[Setup]
AppId={{D7064954-8B09-47DC-BEBB-F12986FB2E74}
AppName=NetScan
AppVersion={#AppVersion}
AppPublisher=Kirill Shafranov
AppPublisherURL=https://github.com/ShafranovKirill/NetScan
DefaultDirName={localappdata}\Programs\NetScan
DefaultGroupName=NetScan
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=NetScan-{#AppVersion}-windows-x64-setup
SetupIconFile=..\build\icons\netscan.ico
UninstallDisplayIcon={app}\NetScan.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
WizardStyle=modern
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\NetScan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\NetScan"; Filename: "{app}\NetScan.exe"
Name: "{autodesktop}\NetScan"; Filename: "{app}\NetScan.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\NetScan.exe"; Description: "Launch NetScan"; Flags: nowait postinstall skipifsilent
