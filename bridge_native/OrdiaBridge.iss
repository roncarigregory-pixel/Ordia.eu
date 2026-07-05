; Ordia Bridge — Windows installer (Inno Setup).
; Produces a professional double-click installer: no terminal, no Docker, no config files.
; Installs the native agent, registers it as an auto-start Windows service (via WinSW),
; and opens the friendly setup window at the end.

#define AppName "Ordia Bridge"
#define AppVersion "1.0.0"
#define AppPublisher "Ordia"
#define AppExe "OrdiaBridge.exe"
#define SvcExe "OrdiaBridgeService.exe"
#define SvcName "OrdiaBridge"

[Setup]
AppId={{7C2F9E3A-8B41-4E2D-9A77-ORDIABRIDGE01}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Ordia Bridge
DefaultGroupName=Ordia Bridge
DisableProgramGroupPage=yes
OutputBaseFilename=OrdiaBridgeSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; SetupIconFile=assets\ordia.ico     ; add a branded icon before release
UninstallDisplayName={#AppName}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "winsw\{#SvcExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "winsw\OrdiaBridgeService.xml"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Ordia Bridge"; Filename: "{app}\{#AppExe}"
Name: "{group}\Disinstalla Ordia Bridge"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Ordia Bridge"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Extra:"

[Run]
; Register + start the background service (auto-start on boot).
Filename: "{app}\{#SvcExe}"; Parameters: "install"; Flags: runhidden waituntilterminated; StatusMsg: "Installazione del servizio in corso..."
Filename: "{app}\{#SvcExe}"; Parameters: "start"; Flags: runhidden; StatusMsg: "Avvio del Bridge..."
; Open the friendly setup window so the user can enter the pairing code.
Filename: "{app}\{#AppExe}"; Description: "Apri la configurazione di Ordia Bridge"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\{#SvcExe}"; Parameters: "stop"; Flags: runhidden; RunOnceId: "StopSvc"
Filename: "{app}\{#SvcExe}"; Parameters: "uninstall"; Flags: runhidden; RunOnceId: "RemoveSvc"
