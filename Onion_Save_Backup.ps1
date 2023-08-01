$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
[Environment]::CurrentDirectory = Get-Location

$Drive_Letter = $args[0]
#  $Drive_Letter = "l"

if (-not $Drive_Letter) {
    . "$PSScriptRoot\Disk_selector.ps1" -Title "Select a drive to backup"
    $selectedTagSplitted = $selectedTag.Split(",")
    $Drive_Number = $($selectedTagSplitted[0])
    $Drive_Letter = $($selectedTagSplitted[1])
    $Target = "$Drive_Letter`:"
}


# File copy function
function Copy-Files {
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination,
        [Parameter(Mandatory = $false)]
        [string]$Exclusion,
        [Parameter(Mandatory = $false)]
        [string]$Inclusion
    )
    Copy-Item -Path $Source -Destination $Destination -Recurse -Force
}



function RoboCopy-WithProgress {
    # Credits  : https://stackoverflow.com/a/21209726
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string] $Source
        , [Parameter(Mandatory = $true)]
        [string] $Destination
        , [Parameter(Mandatory = $false)]
        [string] $AdditionalParameters
        , [int] $Gap = 200
        , [int] $ReportGap = 2000
    )
    # Define regular expression that will gather number of bytes copied
    $RegexBytes = '(?<=\s+)\d+(?=\s+)';

    #region Robocopy params
    # E = Copies subdirectories. This option automatically includes empty directories.
    # NP  = Don't show progress percentage in log
    # NC  = Don't log file classes (existing, new file, etc.)
    # BYTES = Show file sizes in bytes
    # NJH = Do not display robocopy job header (JH)
    # NJS = Do not display robocopy job summary (JS)
    # TEE = Display log in stdout AND in target log file
    $CommonRobocopyParams = '/E /NP /NDL /NC /BYTES /NJH /NJS';
    #endregion Robocopy params

    #region Robocopy Staging
    Write-Verbose -Message 'Analyzing robocopy job ...';
    $StagingLogPath = '{0}\temp\{1} robocopy staging.log' -f $env:windir, (Get-Date -Format 'yyyy-MM-dd HH-mm-ss');

    $StagingArgumentList = '"{0}" "{1}" /LOG:"{2}" /L {3}' -f $Source, $Destination, $StagingLogPath, $CommonRobocopyParams;
    Write-Verbose -Message ('Staging arguments: {0}' -f $StagingArgumentList);
    Start-Process -Wait -FilePath robocopy.exe -ArgumentList $StagingArgumentList -NoNewWindow;
    # Get the total number of files that will be copied
    $StagingContent = Get-Content -Path $StagingLogPath;
    $TotalFileCount = $StagingContent.Count - 1;

    # Get the total number of bytes to be copied
    [RegEx]::Matches(($StagingContent -join "`n"), $RegexBytes) | % { $BytesTotal = 0; } { $BytesTotal += $_.Value; };
    Write-Verbose -Message ('Total bytes to be copied: {0}' -f $BytesTotal);
    #endregion Robocopy Staging

    #region Start Robocopy
    # Begin the robocopy process
    $RobocopyLogPath = '{0}\temp\{1} robocopy.log' -f $env:windir, (Get-Date -Format 'yyyy-MM-dd HH-mm-ss');
    $ArgumentList = '"{0}" "{1}" /LOG:"{2}" /ipg:{3} {4} {5}' -f $Source, $Destination, $RobocopyLogPath, $Gap, $CommonRobocopyParams , $AdditionalParameters;
    Write-Verbose -Message ('Beginning the robocopy process with arguments: {0}' -f $ArgumentList);
    $Robocopy = Start-Process -FilePath robocopy.exe -ArgumentList $ArgumentList -Verbose -PassThru -NoNewWindow;
    Remove-Variable -Name AdditionalParameters 
    Start-Sleep -Milliseconds 100;
    #endregion Start Robocopy

    #region Progress bar loop
    while (!$Robocopy.HasExited) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds $ReportGap;
        $BytesCopied = 0;
        $LogContent = Get-Content -Path $RobocopyLogPath;
        $BytesCopied = [Regex]::Matches($LogContent, $RegexBytes) | ForEach-Object -Process { $BytesCopied += $_.Value; } -End { $BytesCopied; };
        $CopiedFileCount = $LogContent.Count - 1;
        Write-Verbose -Message ('Bytes copied: {0}' -f $BytesCopied);
        Write-Verbose -Message ('Files copied: {0}' -f $LogContent.Count);
        $Percentage = 0;
        if ($BytesCopied -gt 0) {
            $Percentage = (($BytesCopied / $BytesTotal) * 100)
        }
        Write-Progress -Activity Robocopy -Status ("Copied {0} of {1} files; Copied {2} of {3} bytes" -f $CopiedFileCount, $TotalFileCount, $BytesCopied, $BytesTotal) -PercentComplete $Percentage
        $ProgressBar.Value = $Percentage
        [System.Windows.Forms.Application]::DoEvents()
    }
    #endregion Progress loop
    $label.Text = ""

    #region Function output
    [PSCustomObject]@{
        BytesCopied = $BytesCopied;
        FilesCopied = $CopiedFileCount;
    };
    #endregion Function output
}





# Fonction pour annuler la sauvegarde
function Cancel_Backup {
    $form_desc.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
}

# Fonction pour enregistrer la description dans un fichier
function Save_Description {
    Write-Host "**************************************=-=-=-= $BackupFolder"
    New-Item -ItemType Directory -Path $BackupFolder | Out-Null
    $description = $textBox.Text
    $date = Get-Date -Format "yyyy-MM-dd_HH.mm.ss"
    $content = "Date: $date`r`nSource: ${script:SdCardState} ${script:SdCard_Version}`r`nDescription:`r`n$description"
    $content | Out-File -FilePath "$BackupFolder\Backupinfo_$date.txt" -Append
    $form_desc.DialogResult = [System.Windows.Forms.DialogResult]::OK
}



function Get_Version {
    $script:SdCardState = ""
    $script:SdCard_Version = ""

    if (Test-Path -Path "${Drive_Letter}:\") {
        $items = Get-ChildItem -Path "${Drive_Letter}:\"
        if ($items.Count -eq 0) {
            #################### empty partition ####################
            Write-Host "Blank SD card."
            $script:SdCardState = "empty"
            $Backup_Lbl.Text = "Empty SD card"
        }
        else {
            #################### previous Onion ####################
            Write-Host "The SD card contains files/folders."
            Write-Host "Looking for previous Onion installation version..."

            if (Test-Path -Path "${Drive_Letter}:\.tmp_update\bin\installUI" -PathType Leaf) {
                $versionRegex = '--version\s+(.*?)\s'
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Drive_Letter}:\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                if ($script:SdCard_Version -eq "") {
                    $verionfilePath = "${Drive_Letter}:\.tmp_update\onionVersion\version.txt"
                    if (Test-Path -Path "${Drive_Letter}:\.tmp_update\onionVersion\version.txt" -PathType Leaf) {
                        $script:SdCard_Version = Get-Content -Path $verionfilePath -Raw     # if we don't get Onion version from InstallUI, we get it from version.txt
                    }
                }
                Write-Host "Onion version $script:SdCard_Version already installed on this SD card."
                $script:SdCardState = "Onion"
            }
            elseif ((Test-Path -Path "${Drive_Letter}:\.tmp_update") -and (Test-Path -Path "${Drive_Letter}:\miyoo\app\.tmp_update\onion.pak")) {
                #################### Fresh Onion install files (not executed on MM) ####################
                $versionRegex = '--version\s+(.*?)\s'
                #$script:version = [regex]::Match((tools\strings.exe ${Drive_Letter}:\miyoo\app\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Drive_Letter}:\miyoo\app\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                Write-Host "It seems to be and non installed Onion version $script:SdCard_Version"
                $script:SdCardState = "Onion_InstallPending"
            }
            elseif (Test-Path -Path "${Drive_Letter}:\RApp\") {
                #################### previous Stock ####################
                Write-Host "It seems to be a stock SD card from Miyoo"
                $script:SdCardState = "Stock"
                $Backup_Lbl.Text = "Miyoo Stock OS on ${Drive_Letter}:"
                $checkBox_Retroarch.Enabled = 0
                $checkBox_Saves.Enabled = 0
                $checkBox_OnionConfigFlags.Enabled = 0
                $checkBox_Retroarch.Checked = 0
                $checkBox_Saves.Checked = 0
                $checkBox_OnionConfigFlags.Checked = 0
            }
            else {
                #################### unknown files ####################
                Write-Host "Unidentified : Not Onion or Stock"
                $script:SdCardState = "Other"
                    

                $checkBox_Roms.Enabled = 0
                $checkBox_Imgs.Enabled = 0
                $checkBox_Saves.Enabled = 0
                $checkBox_Retroarch.Enabled = 0
                $checkBox_BIOS.Enabled = 0
                $checkBox_OnionConfigFlags.Enabled = 0
        
                $checkBox_Roms.Checked = 0
                $checkBox_Imgs.Checked = 0
                $checkBox_Saves.Checked = 0
                $checkBox_Retroarch.Checked = 0
                $checkBox_BIOS.Checked = 0
                $checkBox_OnionConfigFlags.Checked = 0
            }


    
        }
    }
    Write-Host "${Drive_Letter}:\miyoo\app\.tmp_update\onion.pak"
}

################################################################

# Fonction pour effectuer la sauvegarde en fonction des cases coch�es
function Perform-Backup {



    if ($script:SdCard_Version -eq "") {
        $script:SdCard_Version = "(unknown version)"
    }
    Write-Host "  $script:SdCardState   --- $script:SdCard_Version"
    $BackupFolder = Join-Path -Path $ScriptDirectory\backups\ -ChildPath "$(Get-Date -Format 'yyyy-MM-dd HH.mm.ss')_${script:SdCardState}_${script:SdCard_Version}"
    Write-Host "  Local backup folder : $BackupFolder"
    # Cr�ation du formulaire
    $form_desc = New-Object System.Windows.Forms.Form
    $form_desc.Text = "Backup Description Form"
    $form_desc.Size = New-Object System.Drawing.Size(420, 230)
    $form_desc.StartPosition = "CenterScreen"
    $form_desc.Icon = $icon

    # Cr�ation de l'�tiquette
    $label_desc = New-Object System.Windows.Forms.Label
    $label_desc.Text = "Backup Description"
    $label_desc.AutoSize = $true
    $label_desc.Location = New-Object System.Drawing.Point(10, 5)

    # Cr�ation de la zone de texte multilignes
    $textBox = New-Object System.Windows.Forms.TextBox
    $textBox.Multiline = $true
    $textBox.ScrollBars = "Vertical"
    $textBox.Location = New-Object System.Drawing.Point(10, 30)
    $textBox.Size = New-Object System.Drawing.Size(380, 100)

    # Cr�ation du bouton Cancel
    $button_cancel = New-Object System.Windows.Forms.Button
    $button_cancel.Text = "Cancel"
    $button_cancel.Location = New-Object System.Drawing.Point(220, 140)
    $button_cancel.Add_Click({
            Cancel_Backup
        })

    # Cr�ation du bouton OK
    $button_ok = New-Object System.Windows.Forms.Button
    $button_ok.Text = "OK"
    $button_ok.Location = New-Object System.Drawing.Point(300, 140)
    $button_ok.Add_Click({
            Save_Description
        })

    # Ajout des contr�les au formulaire
    $form_desc.Controls.Add($label_desc)
    $form_desc.Controls.Add($textBox)
    $form_desc.Controls.Add($button_cancel)
    $form_desc.Controls.Add($button_ok)



    # Affichage du formulaire
    # Affichage du formulaire et r�cup�ration du r�sultat
    $form_result = $form_desc.ShowDialog()
    Write-Host "Form result : $form_result"


    ################################################################

    if ($form_result -eq [System.Windows.Forms.DialogResult]::OK) {

        $button_Backup.Enabled = 0
        $RomsSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'Roms'
        $RomsDestination = Join-Path -Path $BackupFolder -ChildPath 'Roms'

        




        if ($checkBox_Roms.Checked) {

            #Copy-Files -Source $RomsSource -Destination $RomsDestination
            # Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /E /NJH /IS /NJS /NDL /NC /BYTES /XD "Imgs" | Get-RobocopyProgress -Source $RomsSource -Title "Backuping Roms..." -Exclusion "Imgs"
            $label.Text = "Backuping Roms..."
            $AdditionalParameters = '/XD "Imgs"'
            RoboCopy-WithProgress -Source $RomsSource -Destination $RomsDestination -AdditionalParameters $AdditionalParameters -Verbose;
        }

        if ($checkBox_Imgs.Checked) {
            # copy from stock
            $ImgsSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'Imgs'
            $ImgsDestination = Join-Path -Path $BackupFolder -ChildPath 'Roms'
            if (Test-Path $ImgsSource -PathType Container) {
                $RomSubFolders = Get-ChildItem -Path $ImgsSource -Directory
                foreach ($RomSubFolder in $RomSubFolders) {
                    $RomSubFolderDestination = Join-Path -Path $ImgsDestination -ChildPath "$RomSubFolder\Imgs"
                    Write-Host "$RomSubFolder.FullName $RomSubFolderDestination"
                    $pngFiles = Get-ChildItem -Path $RomSubFolder.FullName -Filter "*.png"
                    if ($pngFiles.Count -gt 0) {
                        $label.Text = "Backuping images : $RomSubFolder "
                        $AdditionalParameters = '*.png /S'
                        RoboCopy-WithProgress -Source $RomSubFolder.FullName -Destination $RomSubFolderDestination -AdditionalParameters $AdditionalParameters -Verbose
                    }
                }
                
            }

            # copy for Onion
            # Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.png | Get-RobocopyProgress -Source $RomsSource -Title "Backuping images..." -Inclusion "Imgs"
            $label.Text = "Backuping images..."
            $AdditionalParameters = '*.png /S'
            RoboCopy-WithProgress -Source $RomsSource -Destination $RomsDestination -AdditionalParameters $AdditionalParameters -Verbose;
        }

        if ($checkBox_Saves.Checked) {
            if (Test-Path "${Drive_Letter}:\.tmp_update\onionVersion\version.txt") {
                $SavesSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'Saves'
                $SavesDestination = Join-Path -Path $BackupFolder -ChildPath 'Saves'
                # Robocopy "$SavesSource" "$SavesDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $SavesSource -Title "Backuping Saves..."
                $label.Text = "Backuping Saves..."
                RoboCopy-WithProgress -Source $SavesSource -Destination $SavesDestination -Verbose;
            }
		
            # automate saves migration is complex : the folder structure is too different on stock.
		
            # else {  
            # $SavesSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'RetroArch\.retroarch\saves'
            # $SavesDestination = Join-Path -Path $BackupFolder -ChildPath 'Saves\CurrentProfile\saves'
            ## Gets the list of files in the source directory
            # $files = Get-ChildItem -Path $SavesSource -File
            # foreach ($file in $files) {
            # $filename = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
            # Write-Host "$filename"
            ## Checks for matching files in destination subdirectories
            # $matchingFile = Get-ChildItem -Path "$BackupFolder\Roms\*\$filename.*" -File -ErrorAction SilentlyContinue
            # if ($matchingFile) {
            # $subfolder = Split-Path $matchingFile.Directory -Leaf
            # Write-Host "matching !!!  $subfolder"
            # $destinationPath = Join-Path -Path $destinationDirectory -ChildPath $subfolder
            # Copy-Item -Path $file.FullName -Destination $destinationPath
            # Write-Host "Fichier $($file.Name) copi� vers $($destinationPath)"
            # }
            # }

            # }
		
        }
	
	
        if ($checkBox_BIOS.Checked) {
            if (Test-Path "${Drive_Letter}:\.tmp_update\onionVersion\version.txt") {
                $BIOSSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'BIOS'
                $BiosDestination = Join-Path -Path $BackupFolder -ChildPath 'BIOS'
            }
            else {
                $BIOSSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'RetroArch\.retroarch\system'
                $BiosDestination = Join-Path -Path $BackupFolder -ChildPath 'BIOS'
            }
            # Start-Process -FilePath cmd.exe -ArgumentList "/c Robocopy "$BIOSSource" "$BiosDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES /XD "cheats" "cheats备用版"  "GLupeN64" "Mupen64plus" "system\scummvm" "pscnbios" /XF "scph39*"  | Get-RobocopyProgress -Source $BIOSSource -Title "Backuping BIOS..."
            # Write-Host  "$BIOSSource" "$BiosDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES /XD "cheats" "CHEATS~1" "GLupeN64" "Mupen64plus" "system\scummvm" "pscnbios" /XF "fbneo\*.ini" "scph39*" 
            $label.Text = "Backuping BIOS..."
            $AdditionalParameters = '/XD "cheats" "cheats备用版"  "GLupeN64" "Mupen64plus" "system\scummvm" "pscnbios" /XF "scph39*"'
            RoboCopy-WithProgress -Source $BIOSSource -Destination $BiosDestination -AdditionalParameters $AdditionalParameters -Verbose;
            # extract FB neo one file pack (cheats.dat from https://github.com/finalburnneo/FBNeo-cheats) instead of 8000 files of ini cheats initially included in stock
            $output = & "tools\7z.exe" x -y "tools\cheat.7z" "-o$BiosDestination\fbneo\cheats"
        }

        if ($checkBox_Retroarch.Checked) {
            $RetroarchSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath '\RetroArch\.retroarch'
            $RetroarchDestination = Join-Path -Path $BackupFolder -ChildPath 'RetroArch\.retroarch'
            #Copy-Files -Source $RetroarchSource -Destination $RetroarchDestination
            # Robocopy "$RetroarchSource" "$RetroarchDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.cfg  /LEV:1 | Get-RobocopyProgress -Source $RetroarchSource -Title "Backuping Retroarch configuration..." -Inclusion "retroarch.cfg"
            $label.Text = "Backuping Retroarch configuration..."
            $AdditionalParameters = '*.cfg /LEV:1'
            RoboCopy-WithProgress -Source $RetroarchSource -Destination $RetroarchDestination -AdditionalParameters $AdditionalParameters -Verbose;
        }

        if ($checkBox_OnionConfigFlags.Checked) {
            $OnionConfigFlagsDestination = Join-Path -Path $BackupFolder -ChildPath '.tmp_update\config'
            $OnionConfigFlagsSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath '.tmp_update\config'
            # Robocopy "$OnionConfigFlagsSource" "$OnionConfigFlagsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES .* | Get-RobocopyProgress -Source $OnionConfigFlagsSource -Title "Backuping Onion configuration..." 
            $label.Text = "Backuping Onion configuration..."
            $AdditionalParameters = '.*'
            RoboCopy-WithProgress -Source $OnionConfigFlagsSource -Destination $OnionConfigFlagsDestination -AdditionalParameters $AdditionalParameters -Verbose;
            #Copy-Files -Source $OnionConfigFlagsSource -Destination $OnionConfigFlagsDestination
        }

        $button_Backup.Enabled = 1
        $progressBar.Value = 0
    }
}





Add-Type -AssemblyName System.Windows.Forms


$form = New-Object System.Windows.Forms.Form
$form.Text = "Backup Script"
$form.Size = New-Object System.Drawing.Size(300, 350)
$form.StartPosition = "CenterScreen"


$Backup_Lbl = New-Object System.Windows.Forms.Label
$Backup_Lbl.Text = "Roms"
$Backup_Lbl.Location = New-Object System.Drawing.Point(20, 0)
$Backup_Lbl.Size = New-Object System.Drawing.Size(500, 20)
#$Backup_Lbl.Font = [System.Drawing.Font]::new("Microsoft Sans Serif", 12, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($Backup_Lbl)


$checkBox_Roms = New-Object System.Windows.Forms.CheckBox
$checkBox_Roms.Text = "Roms"
$checkBox_Roms.Location = New-Object System.Drawing.Point(50, 30)
$checkBox_Roms.Checked = 1
$form.Controls.Add($checkBox_Roms)

$checkBox_Imgs = New-Object System.Windows.Forms.CheckBox
$checkBox_Imgs.Text = "Imgs"
$checkBox_Imgs.Location = New-Object System.Drawing.Point(50, 60)
$checkBox_Imgs.Size = New-Object System.Drawing.Size(500, 20)
$checkBox_Imgs.Checked = 1
$form.Controls.Add($checkBox_Imgs)

$checkBox_Saves = New-Object System.Windows.Forms.CheckBox
$checkBox_Saves.Text = "Saves"
$checkBox_Saves.Location = New-Object System.Drawing.Point(50, 90)
$checkBox_Saves.Checked = 1
$form.Controls.Add($checkBox_Saves)

$checkBox_Retroarch = New-Object System.Windows.Forms.CheckBox
$checkBox_Retroarch.Text = "Retroarch config"
$checkBox_Retroarch.Location = New-Object System.Drawing.Point(50, 120)
$checkBox_Retroarch.Size = New-Object System.Drawing.Size(500, 20)
$checkBox_Retroarch.Checked = 1
$form.Controls.Add($checkBox_Retroarch)

$checkBox_BIOS = New-Object System.Windows.Forms.CheckBox
$checkBox_BIOS.Text = "BIOS"
$checkBox_BIOS.Location = New-Object System.Drawing.Point(50, 150)
$checkBox_BIOS.Size = New-Object System.Drawing.Size(500, 20)
$checkBox_BIOS.Checked = 1
$form.Controls.Add($checkBox_BIOS)

$checkBox_OnionConfigFlags = New-Object System.Windows.Forms.CheckBox
$checkBox_OnionConfigFlags.Text = "Onion config flags"
$checkBox_OnionConfigFlags.Location = New-Object System.Drawing.Point(50, 180)
$checkBox_OnionConfigFlags.Size = New-Object System.Drawing.Size(500, 20)
$checkBox_OnionConfigFlags.Checked = 1
$form.Controls.Add($checkBox_OnionConfigFlags)


$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Size = New-Object System.Drawing.Size(260, 20)
$progressBar.Location = New-Object System.Drawing.Point(10, 220)
$progressBar.max = 100
$form.Controls.Add($progressBar)

$button_Backup = New-Object System.Windows.Forms.Button
$button_Backup.Text = "Backup"
$button_Backup.Size = New-Object System.Drawing.Size(260, 30)
$button_Backup.Location = New-Object System.Drawing.Point(10, 250)
$button_Backup.Add_Click({ Perform-Backup })
$form.Controls.Add($button_Backup)

$label = New-Object System.Windows.Forms.Label
$label.Size = New-Object System.Drawing.Size(280, 20)
$label.Location = New-Object System.Drawing.Point(10, 285)
$label.Text = ""
$form.Controls.Add($label)



$tooltip = New-Object System.Windows.Forms.ToolTip




Get_Version

$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\OnionInstaller.ico"
$icon = New-Object System.Drawing.Icon($iconPath)
$form.Icon = $icon

If ($script:SdCardState -eq "empty") {
    $Backup_Lbl.Text = "This SD card seems empty."
}
elseif ($script:SdCardState -eq "Onion") {
    $Backup_Lbl.Text = "Onion OS on ${Drive_Letter}:"
    $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
    $icon = New-Object System.Drawing.Icon($iconPath)
    $form.Icon = $icon
        
}
elseif ($script:SdCardState -eq "Onion_InstallPending") {
    $Backup_Lbl.Text = "Onion OS on ${Drive_Letter}:"
    $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
    $icon = New-Object System.Drawing.Icon($iconPath)
    $form.Icon = $icon  
}
elseif ($script:SdCardState -eq "Stock") {
    $Backup_Lbl.Text = "Miyoo Stock OS on ${Drive_Letter}:"
    $checkBox_Retroarch.Enabled = 0
    $checkBox_Saves.Enabled = 0
    $checkBox_OnionConfigFlags.Enabled = 0

    $checkBox_Retroarch.Checked = 0
    $checkBox_Saves.Checked = 0
    $checkBox_OnionConfigFlags.Checked = 0
    

}
else {
    $Backup_Lbl.Text = "Not Onion or Stock on ${Drive_Letter}:"
    $checkBox_Retroarch.Enabled = 0

    $checkBox_Roms.Enabled = 0
    $checkBox_Imgs.Enabled = 0
    $checkBox_Saves.Enabled = 0
    $checkBox_Retroarch.Enabled = 0
    $checkBox_BIOS.Enabled = 0
    $checkBox_OnionConfigFlags.Enabled = 0
        
    $checkBox_Roms.Checked = 0
    $checkBox_Imgs.Checked = 0
    $checkBox_Saves.Checked = 0
    $checkBox_Retroarch.Checked = 0
    $checkBox_BIOS.Checked = 0
    $checkBox_OnionConfigFlags.Checked = 0
}










$form.ShowDialog()
