<#
  Generate the function blocks from plc\*.scl in a new TIA Portal V18 project and compile.

  Needs: TIA Portal V18 with STEP 7 Professional (licence), the Windows user in the
  "Siemens TIA Openness" group, Windows PowerShell 5.1.

  Usage:  powershell -ExecutionPolicy Bypass -File scripts\tia_build.ps1 -Blocks FB_A,FB_B
  Blocks are generated in the order given (a called block before its caller).
  Result: the compile messages, printed and written to results\tia_compile.txt.

  A name may carry a subfolder of plc\ (test\DB_TestData). A source file may hold data blocks
  and an organization block as well as function blocks.

  Test project for S7-PLCSIM (docs\PLCSIM_RUN.md):
    powershell -ExecutionPolicy Bypass -File scripts\tia_build.ps1 `
      -Blocks "FB_CurveEval,FB_HandleStation,test\DB_TestData,test\DB_TestResult,test\FB_TestPlant,test\FB_TestBench,test\OB_Main" `
      -OutDir C:\TIA_build\plcsim -ProjectName handle37_plcsim_test `
      -ArchiveDir C:\TIA_build\plcsim -ArchiveName handle37_plcsim_test.zap18 `
      -ResultFile results\tia_compile_testbench.txt
  With -ArchiveDir the project is set to "support simulation during block compilation", compiled,
  saved and archived (compressed). The record then also lists the blocks and the archive file.
#>
param(
    [Parameter(Mandatory = $true)][string[]]$Blocks,
    [string]$PlcDir = "",
    [string]$OutDir = "C:\TIA_build",
    [string]$ResultFile = "",
    [string]$Version = "V18",
    [string]$Cpu = "OrderNumber:6ES7 513-1AL02-0AB0/V2.9",
    [string]$ProjectName = "",
    [string]$ArchiveDir = "",
    [string]$ArchiveName = ""
)
$ErrorActionPreference = "Stop"
$Blocks = @($Blocks | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$root = Split-Path -Parent $PSScriptRoot
if ($PlcDir -eq "") { $PlcDir = Join-Path $root "plc" }
if ($ResultFile -eq "") { $ResultFile = Join-Path $root "results\tia_compile.txt" }
if (-not [System.IO.Path]::IsPathRooted($ResultFile)) { $ResultFile = Join-Path $root $ResultFile }
if ($ProjectName -eq "") { $ProjectName = "build_" + (Get-Date -Format "yyyyMMdd_HHmmss") }
if ($ArchiveDir -ne "" -and $ArchiveName -eq "") { $ArchiveName = $ProjectName + ".zap" + $Version.Substring(1) }
# a named project is built from scratch: remove the folder of the previous build (only if it is a TIA project folder)
$old = Join-Path $OutDir $ProjectName
if ((Test-Path $old) -and (Get-ChildItem $old -Filter "*.ap*" -File)) { Remove-Item -Recurse -Force $old }
$api = "C:\Program Files\Siemens\Automation\Portal $Version\PublicAPI\$Version\Siemens.Engineering.dll"
if (-not (Test-Path $api)) { throw "Openness API not found: $api" }

$code = @"
using System;
using System.IO;
using System.Linq;
using System.Text;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.ExternalSources;
using Siemens.Engineering.Compiler;

public static class SclBuild {
    static void Walk(CompilerResultMessage m, StringBuilder sb, int depth) {
        sb.AppendLine(new string(' ', 2 * depth) + m.State + "  " + m.Path + "  " + m.Description);
        foreach (var c in m.Messages) Walk(c, sb, depth + 1);
    }
    public static string Run(string outDir, string plcDir, string cpu, string[] blocks, string projectName,
                             string archiveDir, string archiveName) {
        var sb = new StringBuilder();
        using (var tia = new TiaPortal(TiaPortalMode.WithoutUserInterface)) {
            var dir = new DirectoryInfo(outDir);
            var project = tia.Projects.Create(dir, projectName);
            if (archiveDir != "") {
                try {
                    project.SetAttribute("IsSimulationDuringBlockCompilationEnabled", true);
                    sb.AppendLine("simulation support during block compilation: "
                        + project.GetAttribute("IsSimulationDuringBlockCompilationEnabled"));
                } catch (Exception ex) {
                    sb.AppendLine("simulation support NOT set: " + (ex.InnerException ?? ex).Message);
                }
            }
            var dev = project.Devices.CreateWithItem(cpu, "PLC_1", "PLC_1");
            PlcSoftware plc = null;
            foreach (var item in dev.DeviceItems) {
                var sc = item.GetService<SoftwareContainer>();
                if (sc != null && sc.Software is PlcSoftware) { plc = (PlcSoftware)sc.Software; break; }
            }
            if (plc == null) throw new Exception("no PLC software in " + cpu);
            foreach (var entry in blocks) {
                var name = Path.GetFileName(entry);     // an entry may carry a subfolder of plcDir
                var src = plc.ExternalSourceGroup.ExternalSources.CreateFromFile(
                    name, Path.Combine(plcDir, entry + ".scl"));
                try {
                    src.GenerateBlocksFromSource();
                    sb.AppendLine("generated " + name);
                } catch (Exception ex) {
                    sb.AppendLine("GENERATE FAILED " + name + ": " + (ex.InnerException ?? ex).Message);
                }
            }
            var result = plc.GetService<ICompilable>().Compile();
            sb.AppendLine("COMPILE " + result.State + "  errors=" + result.ErrorCount + "  warnings=" + result.WarningCount);
            foreach (var m in result.Messages) Walk(m, sb, 1);
            project.Save();
            if (archiveDir != "") {
                sb.AppendLine("blocks in the project:");
                foreach (PlcBlock b in plc.BlockGroup.Blocks)
                    sb.AppendLine("  " + b.Name + "  " + b.GetType().Name + " " + b.Number + "  " + b.ProgrammingLanguage
                        + "  consistent=" + b.IsConsistent);
                try {
                    var target = Path.Combine(archiveDir, archiveName);
                    if (File.Exists(target)) File.Delete(target);
                    project.Archive(new DirectoryInfo(archiveDir), archiveName, ProjectArchivationMode.Compressed);
                    foreach (var f in new DirectoryInfo(archiveDir).GetFiles(Path.GetFileNameWithoutExtension(archiveName) + "*.zap*"))
                        sb.AppendLine("ARCHIVE " + f.FullName + "  " + f.Length + " bytes");
                } catch (Exception ex) {
                    sb.AppendLine("ARCHIVE FAILED: " + (ex.InnerException ?? ex).Message);
                }
            }
            project.Close();
        }
        return sb.ToString();
    }
}
"@

$resolver = @"
using System; using System.IO; using System.Reflection;
public static class OpnResolve {
    static string[] dirs;
    public static void Init(string[] d) {
        dirs = d;
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) => {
            var n = new AssemblyName(e.Name).Name;
            if (n.EndsWith(".resources")) return null;
            foreach (var dir in dirs) { var p = Path.Combine(dir, n + ".dll"); if (File.Exists(p)) return Assembly.LoadFrom(p); }
            return null;
        };
    }
}
"@
Add-Type -TypeDefinition $resolver
$portal = "C:\Program Files\Siemens\Automation\Portal $Version"
[OpnResolve]::Init(@((Split-Path -Parent $api), "$portal\Bin\PublicAPI", "$portal\Bin"))
New-Item -ItemType Directory -Force $OutDir | Out-Null
if ($ArchiveDir -ne "") { New-Item -ItemType Directory -Force $ArchiveDir | Out-Null }
[void][System.Reflection.Assembly]::LoadFrom($api)
Add-Type -TypeDefinition $code -ReferencedAssemblies $api
$text = "TIA Portal $Version, CPU $Cpu, " + (Get-Date -Format "yyyy-MM-dd HH:mm") + "`r`n" + [SclBuild]::Run($OutDir, $PlcDir, $Cpu, $Blocks, $ProjectName, $ArchiveDir, $ArchiveName)
$text
$text | Out-File -Encoding utf8 $ResultFile
