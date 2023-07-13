$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory

$Drive_Letter = $args[0]
#  $Drive_Letter = "l"

if (-not $Drive_Letter) {
    . "$PSScriptRoot\Disk_selector.ps1" -Title "Select a drive to backup"
    $selectedTagSplitted = $selectedTag.Split(",")
    $Drive_Number = $($selectedTagSplitted[0])
    $Drive_Letter = $($selectedTagSplitted[1])
    # $Target = "$Drive_Letter`:"
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



Function Get-RobocopyProgress {

    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        $InputObject,
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Title, # will be in the textbox
        [Parameter(Mandatory = $false)]
        [string]$Exclusion, # Exclude filter (only files which not match will be in the total files count)
        [Parameter(Mandatory = $false)]
        [string]$Inclusion              # Include filter (only files which match will be in the total files count)
    )

    begin {
        [string]$file = " "
        [double]$percent = 0
        [double]$size = $Null
        if ($PSBoundParameters.ContainsKey('Exclusion')) { 
            [double]$count = (gci $source -file -fo -re | ? { $_.FullName -inotmatch "$Exclusion" }).Count
            Write-Host "exclude $Exclusion -> $count files to copy"
        }
        elseif ($PSBoundParameters.ContainsKey('Inclusion')) { 
            [double]$count = (gci $source -file -fo -re | ? { $_.FullName -imatch "$Inclusion" }).Count
            Write-Host "inclde $Inclusion -> $count files to copy"
        }
        else {
            [double]$count = (gci $source -file -fo -re).Count
            Write-Host "$count to copy"
        }
        [double]$filesLeft = $count
        [double]$number = 0
        $progressBar.Maximum = $count

    }

    process {

        #$Host.PrivateData.ProgressBackgroundColor = 'Cyan' 
        #$Host.PrivateData.ProgressForegroundColor = 'Black'
        (gci $source -file -fo -re).Count
        $data = $InputObject -split '\x09'

        If (![String]::IsNullOrEmpty("$($data[4])")) {
            $file = $data[4] -replace '.+\\(?=(?:.(?!\\))+$)'
            $filesLeft--
            $number++
        }
        If (![String]::IsNullOrEmpty("$($data[0])")) {
            $percent = ($data[0] -replace '%') -replace '\s'
        }
        If (![String]::IsNullOrEmpty("$($data[3])")) {
            $size = $data[3]
        }
        [String]$sizeString = switch ($size) {
            { $_ -gt 1TB -and $_ -lt 1024TB } {
                "$("{0:n2}" -f ($size / 1TB) + " TB")"
            }
            { $_ -gt 1GB -and $_ -lt 1024GB } {
                "$("{0:n2}" -f ($size / 1GB) + " GB")"
            }
            { $_ -gt 1MB -and $_ -lt 1024MB } {
                "$("{0:n2}" -f ($size / 1MB) + " MB")"
            }
            { $_ -ge 1KB -and $_ -lt 1024KB } {
                "$("{0:n2}" -f ($size / 1KB) + " KB")"
            }
            { $_ -lt 1KB } {
                "$size B"
            }
        }

        Write-Progress -Activity "   Currently Copying: ..\$file"`
            -CurrentOperation  "Copying: $(($number).ToString()) of $(($count).ToString())     Copied: $(if($number -le 0){($number).ToString()}else{($number - 1).ToString()}) / $(($count).ToString())     Files Left: $(($filesLeft + 1).ToString())"`
            -Status "Size: $sizeString       Complete: $percent%"`
            -PercentComplete $percent

        $progressBar.Value = $number
        $label.Text = "$Title $number / $count..."
        $form.Refresh()
    }
    #   END
    #   {
    #       $label.Text = ""
    #   }
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
                $Backup_Lbl.Text = "Miyoo Stock OS on ${Drive_Letter}"
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

    # Cr�ation de l'�tiquette
    $label = New-Object System.Windows.Forms.Label
    $label.Text = "Backup Description"
    $label.AutoSize = $true
    $label.Location = New-Object System.Drawing.Point(10, 5)

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
    $form_desc.Controls.Add($label)
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
            Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /E /NJH /IS /NJS /NDL /NC /BYTES /XD "Imgs" | Get-RobocopyProgress -Source $RomsSource -Title "Backuping Roms..." -Exclusion "Imgs"
            $label.Text = ""
        }

        if ($checkBox_Imgs.Checked) {
            # copy from stock
            $ImgsSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'Imgs'
            $ImgsDestination = Join-Path -Path $BackupFolder -ChildPath 'Roms'
            if (Test-Path $ImgsSource -PathType Container) {
                $RomSubFolders = Get-ChildItem -Path $ImgsSource -Directory
                foreach ($RomSubFolder in $RomSubFolders) {
                    $RomSubFolderDestination = Join-Path -Path $ImgsDestination -ChildPath "$RomSubFolder\Imgs"
                    Write-Host $RomSubFolder.FullName "$RomSubFolderDestination"
                    Robocopy $RomSubFolder.FullName `"$RomSubFolderDestination`" /R:3 /W:1 /E /NJH /IS /NJS /NDL /NC /BYTES *.png | Get-RobocopyProgress -Source $RomSubFolder.FullName -Title "Backuping images..." -Inclusion "Imgs"
                    $label.Text = ""
                    #Copy-Files -Source $RomSubFolder.FullName -Destination $RomSubFolderDestination
                }
            }

            # copy for Onion
            Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.png | Get-RobocopyProgress -Source $RomsSource -Title "Backuping images..." -Inclusion "Imgs"
            $label.Text = ""
        }

        if ($checkBox_Saves.Checked) {
            if (Test-Path "${Drive_Letter}:\.tmp_update\onionVersion\version.txt") {
                $SavesSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath 'Saves'
                $SavesDestination = Join-Path -Path $BackupFolder -ChildPath 'Saves'
                Robocopy "$SavesSource" "$SavesDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $SavesSource -Title "Backuping Saves..."
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
		
            $label.Text = ""
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
            Robocopy "$BIOSSource" "$BiosDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $BIOSSource -Title "Backuping BIOS..."
            $label.Text = ""
        }

        if ($checkBox_Retroarch.Checked) {
            $RetroarchSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath '\RetroArch\.retroarch'
            $RetroarchDestination = Join-Path -Path $BackupFolder -ChildPath 'RetroArch\.retroarch'
            #Copy-Files -Source $RetroarchSource -Destination $RetroarchDestination
            Robocopy "$RetroarchSource" "$RetroarchDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.cfg  /LEV:1 | Get-RobocopyProgress -Source $RetroarchSource -Title "Backuping Retroarch configuration..." -Inclusion "retroarch.cfg"
            $label.Text = ""
        }

        if ($checkBox_OnionConfigFlags.Checked) {
            $OnionConfigFlagsDestination = Join-Path -Path $BackupFolder -ChildPath '.tmp_update\config'
            $OnionConfigFlagsSource = Join-Path -Path ${Drive_Letter}:\ -ChildPath '.tmp_update\config'
            Robocopy "$OnionConfigFlagsSource" "$OnionConfigFlagsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES .* | Get-RobocopyProgress -Source $OnionConfigFlagsSource -Title "Backuping Onion configuration..." 
            $label.Text = ""
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
$form.Controls.Add($progressBar)

$button_Backup = New-Object System.Windows.Forms.Button
$button_Backup.Text = "Backup"
$button_Backup.Size = New-Object System.Drawing.Size(260, 30)
$button_Backup.Location = New-Object System.Drawing.Point(10, 250)
$button_Backup.Add_Click({ Perform-Backup })
$form.Controls.Add($button_Backup)

$label = New-Object System.Windows.Forms.Label
$label.Size = New-Object System.Drawing.Size(280, 20)
$label.Location = New-Object System.Drawing.Point(10, 280)
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
    $Backup_Lbl.Text = "Miyoo Stock OS on ${Drive_Letter}"
    $checkBox_Retroarch.Enabled = 0
    $checkBox_Saves.Enabled = 0
    $checkBox_OnionConfigFlags.Enabled = 0

    $checkBox_Retroarch.Checked = 0
    $checkBox_Saves.Checked = 0
    $checkBox_OnionConfigFlags.Checked = 0
    

}
else {
    $Backup_Lbl.Text = "Not Onion or Stock on ${Drive_Letter}"
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
