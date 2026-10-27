; Inno Setup script for Genis installer
; Generate with: ISCC installer.iss

#define MyAppName "Genis"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "Crazy Monkeys"
#define MyAppURL "https://github.com/ficksj/genis"
#define MyAppExeName "Genis.exe"

[Setup]
AppId={{9F1C3A2B-4E5D-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename=Genis-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no
DisableProgramGroupPage=no
LicenseFile=LICENSE
InfoBeforeFile=README.md
InfoAfterClick=yes
ChangesAssociations=false
ChangesEnvironment=false
CreateAppDir=yes
CreateUninstallRegEntry=yes
UpdateUninstallLogAppName=yes
DisableFinishedPage=no
CloseApplications=no
RestartApplications=false
SignTool=signtool

[Languages]
Name: "rus"; MessagesFile: "compiler:Languages\Russian.rld"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: uncheckedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: uncheckedonly; Checked: yes

[Files]
Source: "dist\Genis\Genis.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Genis\*" ; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir="{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir="{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir="{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppString}}"; Flags: nowait postinstall skipifsilent