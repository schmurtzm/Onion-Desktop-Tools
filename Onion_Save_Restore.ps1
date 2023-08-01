param (
    [Parameter(Mandatory = $false)]
    [string]$Update_File,
    [Parameter(Mandatory = $false)]
    [string]$Target
)



# $Target = "L:"
$script:SdCardState = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
[Environment]::CurrentDirectory = Get-Location

if (-not $Target) {
    . "$PSScriptRoot\Disk_selector.ps1"
    $selectedTagSplitted = $selectedTag.Split(",")
    $Drive_Number = $($selectedTagSplitted[0])
    $Drive_Letter = $($selectedTagSplitted[1])
    $Target = "$Drive_Letter`:"
}

$7zPath = "tools\7z.exe"
# Vérification de l'espace disponible sur le lecteur cible
$driveInfo = Get-PSDrive -PSProvider 'FileSystem' | Where-Object { $_.Root -eq "$Target\" }
$freeSpace = $driveInfo.Free


# Vérification de la disponibilité de l'espace nécessaire pour l'extraction


function Get_SDcardType {
    $driveLetter = $Target.Replace(":", "")

    $script:SDcard_description = ""
    $script:SDcard_description += "`r`n------------------------------ SD CARD ------------------------------`r`n"

    $script:SDcard_description += "`r`nDrive letter : $Target"

    $volume = Get-Volume -DriveLetter "$driveLetter"
    if ($volume.FileSystemType -eq $null) {
        Write-Host "Impossible to get current file system"
        $script:SDcard_description += "`r`n`r`n`r`nImpossible to get current file system"
        $script:SDcard_description += "`r`n Check that your SD card is formated in FAT32"
        $script:SDcard_description += "`r`n You can try to repair .net frame work : "
        $script:SDcard_description += "`r`n  https://aka.ms/DotnetRepairTool`r`n`r`n"
    }
    elseif ($volume.FileSystemType -ne "FAT32") {
        Write-Host "File system type: $($volume.FileSystemType)"
        Write-Host "⚠ This file system is not supported by Onion. ⚠"
        $script:SDcard_description += "`r`nFile system type: $($volume.FileSystemType)"
        $script:SDcard_description += "`r`n⚠ This file system is not supported by Onion. ⚠"
        $script:SDcard_description += "`r`n(You can use Onion Installer to format your SD card in FAT32)"
    }
    elseif ($volume.FileSystemType -eq "FAT32") {
        Write-Host "File system type is compatible with Onion: $($volume.FileSystemType)"
        $script:SDcard_description += "`r`nFile system type is compatible with Onion: $($volume.FileSystemType)"

    }

    $messageBoxText = ""

    if (Test-Path -Path "${Target}\") {
        $items = Get-ChildItem -Path "$($Target)\"
        if ($items.Count -eq 0) {
            #################### empty partition ####################
            Write-Host "Blank SD card."
            $script:SDcard_description += "`r`nEmpty SD card"
            $script:SdCardState = "empty"
        }
        else {
            #################### previous Onion ####################
            Write-Host "The SD card contains files/folders."
            $script:SDcard_description += "`r`n⚠ The SD card already contains files/folders :"
            Write-Host "Looking for previous Onion installation version..."

            $verionfilePath = "${Target}\.tmp_update\bin\installUI"
            if (Test-Path -Path "${Target}\.tmp_update\bin\installUI" -PathType Leaf) {
                $versionRegex = '--version\s+(.*?)\s'
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                if ($script:SdCard_Version -eq "") {
                    # if we don't get Onion version from InstallUI, we get it from version.txt
                    $verionfilePath = "${Target}\.tmp_update\onionVersion\version.txt"
                    if (Test-Path -Path $verionfilePath -PathType Leaf) {
                        $script:SdCard_Version = Get-Content -Path $verionfilePath -Raw
                    }
                }
            
                Write-Host "Onion version $script:SdCard_Version already installed on this SD card."
                $script:SDcard_description += "`r`nOnion $script:SdCard_Version on ${Target}"
                $script:SdCardState = "Onion"
            }
            elseif ((Test-Path -Path "${Target}\.tmp_update") -and (Test-Path -Path "${Target}\miyoo\app\.tmp_update\onion.pak")) {
                #################### Fresh Onion install files (not executed on MM) ####################
                $versionRegex = '--version\s+(.*?)\s'
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\miyoo\app\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                if ($script:SdCard_Version -eq "") {
                    $script:versiSdCard_Versionon = "(unknown version)"
                }
                Write-Host "It seems to be and non installed Onion version"
                $script:SDcard_description += "`r`nFresh Onion install files $script:SdCard_Version on ${Target}"
                $script:SdCardState = "Onion_InstallPending"
            }
            elseif (Test-Path -Path "${Target}\RApp\") {
                #################### previous Stock ####################
                Write-Host "It seems to be a stock SD card from Miyoo"
                $script:SDcard_description += "`r`nMiyoo Stock OS on ${Target}"
                $script:SdCardState = "Stock"
            }
            else {
                #################### unknown files ####################
                Write-Host "Unidentified : Not Onion or Stock"
                $script:SDcard_description += "`r`nNot Onion or Stock"
                $script:SdCardState = "Other"
            }


    
        }

        $script:SDcard_description += "`r`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB`r`n"
        $label_right.Text = $script:SDcard_description
    }

}



function DisplayBackupInfo($backupName) {
    $button_Restore.Enabled = 1
    $label_right.Text = ""
    
    $BackupFolder = $flowLayoutPanel.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Text
    Write-Host "Selected file: $BackupFolder"

    $backupInfoFiles = Get-ChildItem -Path "$ScriptDirectory\backups\$BackupFolder" -Filter "Backupinfo_*.txt"
    
    foreach ($backupInfoFile in $backupInfoFiles) {
        if ($backupInfoFile.Name -like "Backupinfo_*") {
            $backupInfo = Get-Content -Path $backupInfoFile.FullName -Raw
            $label_right.Text = $script:SDcard_description
            $label_right.Text += "`r`n`r`n`---------------------------- BACKUP INFO ----------------------------`r`n`r`n"

            $label_right.Text += $backupInfo
            # we get what is backuped
            Write-Host "$ScriptDirectory\backups\$BackupFolder\Roms"

            $backupGroupBox.Controls | Where-Object { $_ -is [System.Windows.Forms.CheckBox] } | ForEach-Object { $_.Checked = $false; $_.Enabled = $true }
            if (Test-Path -Path "$ScriptDirectory\backups\$BackupFolder\Roms" -PathType Container) { $checkBox_Roms.Checked = $true; $checkBox_Imgs.Checked = 1 }
            if (Test-Path -Path "$ScriptDirectory\backups\$BackupFolder\Saves" -PathType Container) { $checkBox_Saves.Checked = 1 }
            if (Test-Path -Path "$ScriptDirectory\backups\$BackupFolder\BIOS" -PathType Container) { $checkBox_BIOS.Checked = 1 }
            if (Test-Path -Path "$ScriptDirectory\backups\$BackupFolder\RetroArch" -PathType Container) { $checkBox_Retroarch.Checked = 1 }
            if (Test-Path -Path "$ScriptDirectory\backups\$BackupFolder\.tmp_update\config" -PathType Container) { $checkBox_OnionConfigFlags.Checked = 1 }
            $backupGroupBox.Controls | Where-Object { $_ -is [System.Windows.Forms.CheckBox] -and -not $_.Checked } | ForEach-Object {
                $_.Enabled = $false
            }

            return
        }
    }
    
    $label_right.Text += "Backup information not available."
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





function Perform_Restore {
    $BackupFolder = $flowLayoutPanel.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Text
    $messageBoxText = "Selected backup:`n$BackupFolder`nTarget:`n${Target}`n`n" +
    "Are you sure that you want to restore this backup ?`n"
    $messageBoxCaption = "Backup restoration Confirmation"
    $messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::YesNo
    $messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Warning
    $result = [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)

    if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {

        
    
        $label_right.Text += "`r`n`r`n------------------- BACKUP RESTORATION -------------------`r`n"
        $label_right.Text += "Selected backup:`r`n$BackupFolder`r`nTarget:${Target}`r`n"

        $RomsSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath 'Roms'
        $RomsDestination = Join-Path -Path ${Target} -ChildPath 'Roms'

        Write-Host "BackupFolder: $BackupFolder `nRomsSource: $RomsSource `nRomsDestination: $RomsDestination"
        # V�rification des cases coch�es
        if ($checkBox_Roms.Checked) {
            #Copy-Files -Source $RomsSource -Destination $RomsDestination
            # Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /E /NJH /IS /NJS /NDL /NC /BYTES /XD "Imgs" | Get-RobocopyProgress -Source $RomsSource -Title "Restoring Roms..." -Exclusion "Imgs"
            $label.Text = ""
            $label_right.Text += "`r`nRestoring Roms..."

            RoboCopy-WithProgress -Source $RomsSource -Destination $RomsDestination -Verbose
        }

        if ($checkBox_Imgs.Checked) {
            $ImgsSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath 'Roms'
            $ImgsDestination = Join-Path -Path ${Target} -ChildPath 'Roms'
            # Robocopy "$ImgsSource" "$ImgsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.png | Get-RobocopyProgress -Source $RomsSource -Title "Restoring images..." -Inclusion "Imgs"
            $label_right.Text += "`r`nRestoring images..."
            RoboCopy-WithProgress -Source $ImgsSource -Destination $ImgsDestination -Verbose
            #Copy-Files -Source $RomsSource -Destination $RomsDestination
        }

        if ($checkBox_Saves.Checked) {
            $SavesSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath 'Saves'
            $SavesDestination = Join-Path -Path ${Target} -ChildPath 'Saves'
            # Robocopy "$SavesSource" "$SavesDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $SavesSource -Title "Restoring Saves..."
            $label_right.Text += "`r`nRestoring Saves..."
            RoboCopy-WithProgress -Source $SavesSource -Destination $SavesDestination -Verbose
        }


        if ($checkBox_BIOS.Checked) {
            $BIOSSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath 'BIOS'
            $BiosDestination = Join-Path -Path ${Target} -ChildPath 'BIOS'
            # Robocopy "$BIOSSource" "$BiosDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $BIOSSource -Title "Restoring BIOS..."
            $label_right.Text += "`r`nRestoring BIOS..."
            RoboCopy-WithProgress -Source $BIOSSource -Destination $BiosDestination -Verbose
        }

        if ($checkBox_Retroarch.Checked) {
            $RetroarchSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath 'RetroArch\.retroarch'
            $RetroarchDestination = Join-Path -Path ${Target} -ChildPath '\RetroArch\.retroarch'
            #Copy-Files -Source $RetroarchSource -Destination $RetroarchDestination
            # Robocopy "$RetroarchSource" "$RetroarchDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.cfg  /LEV:1 | Get-RobocopyProgress -Source $RetroarchSource -Title "Restoring Retroarch configuration..." -Inclusion "retroarch.cfg"
            $label_right.Text += "`r`nRestoring Retroarch configuration..."
            RoboCopy-WithProgress -Source $RetroarchSource -Destination $RetroarchDestination -Verbose
        }

        if ($checkBox_OnionConfigFlags.Checked) {
            $OnionConfigFlagsSource = Join-Path -Path "$ScriptDirectory\backups\$BackupFolder" -ChildPath '.tmp_update\config'
            $OnionConfigFlagsDestination = Join-Path -Path ${Target} -ChildPath '.tmp_update\config'

            # Robocopy "$OnionConfigFlagsSource" "$OnionConfigFlagsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES .* | Get-RobocopyProgress -Source $OnionConfigFlagsSource -Title "Restoring Onion configuration..." 
            $label_right.Text += "`r`nRestoring Onion configuration..."
            RoboCopy-WithProgress -Source $OnionConfigFlagsSource -Destination $OnionConfigFlagsDestination -Verbose
            #Copy-Files -Source $OnionConfigFlagsSource -Destination $OnionConfigFlagsDestination
        }

        $label_right.Text += "`r`n`r`nBackup restoration Finished !"
        $soundPlayer = New-Object System.Media.SoundPlayer
        $soundPlayer.SoundLocation = "tools\res\success.wav"
        $soundPlayer.Play()
    }
}



function Button_Click {


    $Update_File = $flowLayoutPanel.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Text
    Write-Host "Selected file: $Update_File"
    Write-Host "Destination: $Target"

    $label_right.Text += "`r`n`r`n`------------------- EXTRACTION OF ONION -------------------`r`n"
    $label_right.Text += "`r`nSelected file: `"$Update_File`"`r`nDestination: $Target"
    $form.Refresh()

    $output = & $7zPath l "downloads\$Update_File" | Select-String 'files,' | Select-Object -Last 1
    if ($output) {
        $uncompressedSize = ($output.Line -split '\s+')[2]
        $uncompressedSize
    }
    else {
        Write-Host "Unable to recover decompressed zip file size."
    }

    Write-Host "Space required: $([Math]::Round($uncompressedSize / 1MB)) MB`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB"

    if (($freeSpace -gt $uncompressedSize) -or ($freeSpace -eq $null)) {
        # when WMI is broken $freeSpace is null
        



        If ($script:SdCardState -eq "empty") {
            $messageBoxText = "You're about to install $Update_File.`n" +
            "Are you sure that you want install it on ${Target}: ?`n"
        }
        elseif ($script:SdCardState -eq "Onion") {
            $messageBoxText = "You're about to upgrade Onion OS`n`"$script:SdCard_Version`" to `"$Update_File`".`n`n" +
            "Are you sure that you want update ?`n" +
            "(Saves, rom and configuration will be conserved)"
        
        }
        elseif ($script:SdCardState -eq "Onion_InstallPending") {
            $messageBoxText = "You're about to upgrade Onion OS ($script:SdCard_Version) which has never been used) with $Update_File.`n`n" +
            "If this previous install doesn't contains any data then you'll prefer to format your SD card and start again.`n`n" +
            "Are you sure that you want update ?`n"
    
        }
        elseif ($script:SdCardState -eq "Stock") {
            $messageBoxText = "You're about to upgrade a stock OS with $Update_File.`n`n" +
            "!!! it is clearly not recommended/supported and you could have many side effects.`n`n" +
            "Please use a new and guenuine SD card to install Onion`n" +
            "Then copy the data from Stock to this new SD card thanks to`n" +
            "the backup/restore functionalities of Onion installer.`n`n" +
            "Are you sure that you want to force this not recommanded installation ?`n`n"
        }
        elseif ($script:SdCardState -eq "Other") {
            $messageBoxText = "!!! You're about to install $Update_File on a non empty SD card.`n" +
            "It is possible to install Onion on a SD card which already contains some data however it's not recommended`n" +
            "If your SD card doesn't contains any important data then you'll prefer to format your SD card and start again.`n`n" +
            "Are you sure that you want to force this installation ?`n"
        }
        else {
            $messageBoxText = "You're about to install `"$Update_File`".`n" +
            "Are you sure that you want install it on ${Target}: ? $script:SdCardState `n"


        }


        $messageBoxCaption = "Installation Confirmation"
        $messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::YesNo
        $messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Warning
        $result = [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)

        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
         
        

            $label_right.Text += "`r`nExtraction in progress..."
 
            $label_right.SelectionStart = $label_right.Text.Length
            $label_right.ScrollToCaret()

            $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/c @title extracting $Update_File to $Target & mode con:cols=80 lines=1 & `"$7zPath`" x -y -aoa `"downloads\$Update_File`" -o`"$Target\`"" -PassThru
            while (!$wgetProcess.HasExited) {
                Start-Sleep -Milliseconds 1000  # Attendre une demi-seconde
            }

            if ($LASTEXITCODE -eq 0) {
                Write-Host "Decompression successful."
                Write-Host "`n`nUpdate $Release_Version applied.`nRebooting to run installation!`n"
                $label_right.Text += "`r`nExtraction successful"
            }
            else {
                Write-Host "`n`nError: Something went wrong during decompression.`nTry to run OTA update again or make a manual update.`nInstallation stopped."
                $label_right.Text += "`r`nError: Something went wrong during decompression.`nTry to run OTA update again or make a manual update.`r`nInstallation stopped."
            }
            # else {
            #     Write-Host "Insufficient space on $Target drive to extract file."
            #     $label_right.Text += "`r`nInsufficient space on $Target drive to extract file."
            # }

        }
        else {
            Write-Host "`n`nInstallation canceled by user."
            $label_right.Text += "`r`nInstallation canceled by user."
        }

        $form.Refresh()
        $label_right.SelectionStart = $label_right.Text.Length
        $label_right.ScrollToCaret()
    }
    else {
        Write-Host "`n`nError: No enough space for decompression."
        $label_right.Text += "`r`nError: No enough space for decompression.`r`nSpace required: $([Math]::Round($uncompressedSize / 1MB)) MB`r`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB`r`nInstallation canceled."
    }
}

if (-not $Update_File) {
    # Afficher un Windows Form pour sélectionner le fichier à extraire
    Add-Type -AssemblyName System.Windows.Forms

    $font = New-Object System.Drawing.Font("Microsoft Sans Serif", 8.25) 
    $bold = New-Object System.Drawing.Font("Microsoft Sans Serif", 8.25, [System.Drawing.FontStyle]::Bold)

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Onion Backup Restore"
    $form.Size = New-Object System.Drawing.Size(950, 480)
    $form.StartPosition = "CenterScreen"
    $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
    $icon = New-Object System.Drawing.Icon($iconPath)
    $form.Icon = $icon




    $SelectBackupGroupBox = New-Object System.Windows.Forms.GroupBox
    $SelectBackupGroupBox.Location = New-Object System.Drawing.Point(20, 20)
    $SelectBackupGroupBox.Size = New-Object System.Drawing.Size(330, 350)
    $SelectBackupGroupBox.Text = "Select a backup:"
    # $SelectBackupGroupBox.visible = 0
    $form.Controls.Add($SelectBackupGroupBox)


    $panel = New-Object System.Windows.Forms.Panel
    $panel.Location = New-Object System.Drawing.Point(5, 20)
    $panel.Size = New-Object System.Drawing.Size(310, 320)
    $panel.AutoScroll = $true
    $SelectBackupGroupBox.Controls.Add($panel)

    $flowLayoutPanel = New-Object System.Windows.Forms.FlowLayoutPanel
    $flowLayoutPanel.Location = New-Object System.Drawing.Point(0, 0)
    $flowLayoutPanel.AutoSize = $true  # Mettre à true pour ajuster automatiquement la taille du panneau
    $flowLayoutPanel.FlowDirection = "TopDown"
    $panel.Controls.Add($flowLayoutPanel)
    
    # $romSubDirectories = Get-ChildItem -Path "$ScriptDirectory\backups" -Directory
    $romSubDirectories = Get-ChildItem -Path "$ScriptDirectory\backups" -Directory | Sort-Object -Property Name -Descending
        
    foreach ($romSubDirectory in $romSubDirectories) {
        $radioButton = New-Object System.Windows.Forms.RadioButton
        $radioButton.AutoSize = $true
        $radioButton.Text = $romSubDirectory.Name
        $radioButton.Add_Click({ DisplayBackupInfo $radioButton.Text })
        $flowLayoutPanel.Controls.Add($radioButton)
        # $flowLayoutPanel.Controls.Insert(0, $radioButton)
    }





    # $label = New-Object System.Windows.Forms.Label
    # $label.Location = New-Object System.Drawing.Point(10, 20)
    # $label.Size = New-Object System.Drawing.Size(300, 20)
    # $label.Text = "Select a backup :"
    # $label.Font = $bold 
    # $label.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
    # $form.Controls.Add($label)





    # $Backup_Lbl = New-Object System.Windows.Forms.Label

    # $Backup_Lbl.Location = New-Object System.Drawing.Point(355, 20)
    # $Backup_Lbl.Size = New-Object System.Drawing.Size(280, 20)
    # $Backup_Lbl.Font = $bold 
    # $form.Controls.Add($Backup_Lbl)
    
    $backupGroupBox = New-Object System.Windows.Forms.GroupBox
    $backupGroupBox.Location = New-Object System.Drawing.Point(360, 20)
    $backupGroupBox.Size = New-Object System.Drawing.Size(260, 350)
    $backupGroupBox.Text = "Elements to restore from selected backup"
    # $backupGroupBox.visible = 0
    $form.Controls.Add($backupGroupBox)

    
    
    # Cr�ation des cases � cocher
    $checkBox_Roms = New-Object System.Windows.Forms.CheckBox
    $checkBox_Roms.Text = "Roms"
    $checkBox_Roms.Location = New-Object System.Drawing.Point(10, 20)
    $backupGroupBox.Controls.Add($checkBox_Roms)
    
    $checkBox_Imgs = New-Object System.Windows.Forms.CheckBox
    $checkBox_Imgs.Text = "Imgs"
    $checkBox_Imgs.Location = New-Object System.Drawing.Point(10, 50)
    $checkBox_Imgs.Size = New-Object System.Drawing.Size(130, 20)
    $backupGroupBox.Controls.Add($checkBox_Imgs)
    
    $checkBox_Saves = New-Object System.Windows.Forms.CheckBox
    $checkBox_Saves.Text = "Saves"
    $checkBox_Saves.Location = New-Object System.Drawing.Point(10, 80)
    $backupGroupBox.Controls.Add($checkBox_Saves)
    
    $checkBox_Retroarch = New-Object System.Windows.Forms.CheckBox
    $checkBox_Retroarch.Text = "Retroarch config"
    $checkBox_Retroarch.Location = New-Object System.Drawing.Point(10, 110)
    $checkBox_Retroarch.Size = New-Object System.Drawing.Size(130, 20)
    $backupGroupBox.Controls.Add($checkBox_Retroarch)
    
    $checkBox_BIOS = New-Object System.Windows.Forms.CheckBox
    $checkBox_BIOS.Text = "BIOS"
    $checkBox_BIOS.Location = New-Object System.Drawing.Point(10, 140)
    $checkBox_BIOS.Size = New-Object System.Drawing.Size(130, 20)
    $backupGroupBox.Controls.Add($checkBox_BIOS)
    
    $checkBox_OnionConfigFlags = New-Object System.Windows.Forms.CheckBox
    $checkBox_OnionConfigFlags.Text = "Onion config flags"
    $checkBox_OnionConfigFlags.Location = New-Object System.Drawing.Point(10, 170)
    $checkBox_OnionConfigFlags.Size = New-Object System.Drawing.Size(130, 20)
    $backupGroupBox.Controls.Add($checkBox_OnionConfigFlags)
    
    # Cr�ation du bouton Backup
    $button_Restore = New-Object System.Windows.Forms.Button
    $button_Restore.Text = "Restore"
    $button_Restore.Location = New-Object System.Drawing.Point(820, 400)
    $button_Restore.Add_Click({ Perform_Restore })
    $button_Restore.Enabled = 0
    $form.Controls.Add($button_Restore)
    
    
    # Cr�er une barre de progression
    $progressBar = New-Object System.Windows.Forms.ProgressBar
    $progressBar.Size = New-Object System.Drawing.Size(260, 20)
    $progressBar.Location = New-Object System.Drawing.Point(10, 370)
    $form.Controls.Add($progressBar)
    
    # Cr�er un label pour afficher le pourcentage
    $label = New-Object System.Windows.Forms.Label
    $label.Size = New-Object System.Drawing.Size(280, 20)
    $label.Location = New-Object System.Drawing.Point(10, 260)
    $form.Controls.Add($label)
    
    
    # We disable not present folders :
    
    
    $tooltip = New-Object System.Windows.Forms.ToolTip
    


    $label_right = New-Object System.Windows.Forms.TextBox
    $label_right.Multiline = $true
    $label_right.ReadOnly = $true
    $label_right.ScrollBars = "Vertical"
    $label_right.Location = New-Object System.Drawing.Point(630, 24)
    $label_right.Size = New-Object System.Drawing.Size(280, 346)
    
    $label_right.Font = $font
    $label_right.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
    $form.Controls.Add($label_right)
    $currentFont = $label_right.Font
   



    # $button = New-Object System.Windows.Forms.Button
    # $button.Location = New-Object System.Drawing.Point(200, 400)
    # $button.Size = New-Object System.Drawing.Size(75, 23)
    # $button.Add_Click({ Button_Click })
    # $button.Text = "OK"
    # $form.Controls.Add($button)

    Get_SDcardType

    $result = $form.ShowDialog()

    if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-Host "No update file selected. Exiting."
        exit 1
    }

    $selectedFile = $flowLayoutPanel.Controls | Where-Object { $_ -is [System.Windows.Forms.RadioButton] -and $_.Checked } | Select-Object -First 1
    if ($selectedFile -eq $null) {
        Write-Host "No update file selected. Exiting."
        exit 1
    }

    $Update_File = $selectedFile.Text
}
