# R�cup�ration de l'argument $SDcard_Letter
$SDcard_Letter = $args[0]
$SDcard_Letter="g:"
# D�finition du r�pertoire du script courant
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path

# D�finition du r�pertoire de sauvegarde
$BackupFolder = Join-Path -Path $ScriptDirectory -ChildPath "$(Get-Date -Format 'yyyy-MM-dd HH.mm.ss')"




# Fonction pour effectuer la copie des fichiers
function Copy-Files {
    Param(
        [Parameter(Mandatory=$true)]
        [string]$Source,
        [Parameter(Mandatory=$true)]
        [string]$Destination,
        [Parameter(Mandatory=$false)]
        [string]$Exclusion,
        [Parameter(Mandatory=$false)]
        [string]$Inclusion
    )
    Copy-Item -Path $Source -Destination $Destination -Recurse -Force
}



Function Get-RobocopyProgress {

    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        $InputObject,
        [Parameter(Mandatory=$true)]
        [string]$Source,
        [Parameter(Mandatory=$true)]
        [string]$Title,
        [Parameter(Mandatory=$false)]
        [string]$Exclusion,
        [Parameter(Mandatory=$false)]
        [string]$Inclusion
    )

    begin {
        [string]$file = " "
        [double]$percent = 0
        [double]$size = $Null
		if ($PSBoundParameters.ContainsKey('Exclusion')) { 
            [double]$count = (gci $source -file -fo -re | ? { $_.FullName -inotmatch "$Exclusion" }).Count
            Write-Host "excluuuuuuuuuuuuuuuuuuuuuuuuuuuuusion1 $count"
        }elseif ($PSBoundParameters.ContainsKey('Inclusion')) { 
            [double]$count = (gci $source -file -fo -re | ? { $_.FullName -imatch "$Inclusion" }).Count
            Write-Host "incluuuuuuuuuuuuuuuuuuuuuuuuuuuuusion $count   $Inclusion"
        }else {
            [double]$count = (gci $source -file -fo -re).Count
            Write-Host "ellllllllllllllllllllllllllllllse $count"
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
# Fonction pour effectuer la sauvegarde en fonction des cases coch�es
function Perform-Backup {

        $RomsSource = Join-Path -Path $BackupFolder -ChildPath 'Roms'
        $RomsDestination = Join-Path -Path $SDcard_Letter -ChildPath 'Roms'

    # V�rification des cases coch�es
    if ($checkBox_Roms.Checked) {
        #Copy-Files -Source $RomsSource -Destination $RomsDestination
            Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /E /NJH /IS /NJS /NDL /NC /BYTES /XD "Imgs" | Get-RobocopyProgress -Source $RomsSource -Title "Backuping Roms..." -Exclusion "Imgs"
            $label.Text = ""
    }

    if ($checkBox_Imgs.Checked) {
        $RomsSource = Join-Path -Path $SDcard_Letter -ChildPath 'Roms'
        $RomsDestination = Join-Path -Path $BackupFolder -ChildPath 'Roms'
        Robocopy "$RomsSource" "$RomsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.png | Get-RobocopyProgress -Source $RomsSource -Title "Backuping images..." -Inclusion "Imgs"
        $label.Text = ""

        #Copy-Files -Source $RomsSource -Destination $RomsDestination
    }

    if ($checkBox_Saves.Checked) {
        if (Test-Path "$SDcard_Letter\.tmp_update\onionVersion\version.txt") {
            $SavesSource = Join-Path -Path $BackupFolder -ChildPath 'Saves'
			$SavesDestination = Join-Path -Path $SDcard_Letter -ChildPath 'Saves'
        }
		Robocopy "$SavesSource" "$SavesDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $SavesSource -Title "Backuping Saves..."
		$label.Text = ""
    }
	
	
	if ($checkBox_BIOS.Checked) {
        if (Test-Path "$SDcard_Letter\.tmp_update\onionVersion\version.txt") {
            $BIOSSource = Join-Path -Path $BackupFolder -ChildPath 'BIOS'
			$BiosDestination = Join-Path -Path $SDcard_Letter -ChildPath 'BIOS'
        }

		Robocopy "$BIOSSource" "$BiosDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES | Get-RobocopyProgress -Source $BIOSSource -Title "Backuping BIOS..."
        $label.Text = ""
	}

    if ($checkBox_Retroarch.Checked) {
        $RetroarchSource = Join-Path -Path $BackupFolder -ChildPath 'RetroArch\.retroarch'
        $RetroarchDestination = Join-Path -Path $SDcard_Letter -ChildPath '\RetroArch\.retroarch'
        #Copy-Files -Source $RetroarchSource -Destination $RetroarchDestination
        Robocopy "$RetroarchSource" "$RetroarchDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES *.cfg  /LEV:1 | Get-RobocopyProgress -Source $RetroarchSource -Title "Backuping Retroarch configuration..." -Inclusion "retroarch.cfg"
        $label.Text = ""
    }

    if ($checkBox_OnionConfigFlags.Checked) {
        $OnionConfigFlagsSource = Join-Path -Path $BackupFolder -ChildPath '.tmp_update\config\.*'
        # $OnionConfigFlagsSource = Join-Path -Path $SDcard_Letter -ChildPath '.tmp_update\config'
        $OnionConfigFlagsDestination = Join-Path -Path $SDcard_Letter -ChildPath '.tmp_update\config'

        
        Robocopy "$OnionConfigFlagsSource" "$OnionConfigFlagsDestination" /R:3 /W:1 /s /E /NJH /IS /NJS /NDL /NC /BYTES .* | Get-RobocopyProgress -Source $OnionConfigFlagsSource -Title "Backuping Onion configuration..." 
        $label.Text = ""
        #Copy-Files -Source $OnionConfigFlagsSource -Destination $OnionConfigFlagsDestination
    }


}

# Chargement de l'assembly Windows Forms
Add-Type -AssemblyName System.Windows.Forms

# Cr�ation de la fen�tre Windows Form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Backup Script"
$form.Size = New-Object System.Drawing.Size(300, 400)
$form.StartPosition = "CenterScreen"


$Backup_Lbl = New-Object System.Windows.Forms.Label
$Backup_Lbl.Text = "Roms"
$Backup_Lbl.Location = New-Object System.Drawing.Point(50, 0)
$Backup_Lbl.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($Backup_Lbl)



# Cr�ation des cases � cocher
$checkBox_Roms = New-Object System.Windows.Forms.CheckBox
$checkBox_Roms.Text = "Roms"
$checkBox_Roms.Location = New-Object System.Drawing.Point(50, 20)
$form.Controls.Add($checkBox_Roms)

$checkBox_Imgs = New-Object System.Windows.Forms.CheckBox
$checkBox_Imgs.Text = "Imgs"
$checkBox_Imgs.Location = New-Object System.Drawing.Point(50, 50)
$checkBox_Imgs.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($checkBox_Imgs)

$checkBox_Saves = New-Object System.Windows.Forms.CheckBox
$checkBox_Saves.Text = "Saves"
$checkBox_Saves.Location = New-Object System.Drawing.Point(50, 80)
$form.Controls.Add($checkBox_Saves)

$checkBox_Retroarch = New-Object System.Windows.Forms.CheckBox
$checkBox_Retroarch.Text = "Retroarch config"
$checkBox_Retroarch.Location = New-Object System.Drawing.Point(50, 110)
$checkBox_Retroarch.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($checkBox_Retroarch)

$checkBox_BIOS = New-Object System.Windows.Forms.CheckBox
$checkBox_BIOS.Text = "BIOS"
$checkBox_BIOS.Location = New-Object System.Drawing.Point(50, 140)
$checkBox_BIOS.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($checkBox_BIOS)

$checkBox_OnionConfigFlags = New-Object System.Windows.Forms.CheckBox
$checkBox_OnionConfigFlags.Text = "Onion config flags"
$checkBox_OnionConfigFlags.Location = New-Object System.Drawing.Point(50, 170)
$checkBox_OnionConfigFlags.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($checkBox_OnionConfigFlags)

# Cr�ation du bouton Backup
$button_Backup = New-Object System.Windows.Forms.Button
$button_Backup.Text = "Backup"
$button_Backup.Location = New-Object System.Drawing.Point(50, 200)
$button_Backup.Add_Click({ Perform-Backup })
$form.Controls.Add($button_Backup)


# Cr�er une barre de progression
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Size = New-Object System.Drawing.Size(260, 20)
$progressBar.Location = New-Object System.Drawing.Point(10, 230)
$form.Controls.Add($progressBar)

# Cr�er un label pour afficher le pourcentage
$label = New-Object System.Windows.Forms.Label
$label.Size = New-Object System.Drawing.Size(280, 20)
$label.Location = New-Object System.Drawing.Point(10, 260)
$form.Controls.Add($label)


# We disable not present folders :


$tooltip = New-Object System.Windows.Forms.ToolTip


    # V�rifier si la carte SD est vierge
    $items = Get-ChildItem -Path "$($SDcard_Letter)\"
    if ($items.Count -eq 0) {
        #################### empty partition ####################
        Write-Host "Blank SD card."
        $messageBoxText = "It seems that your SD card is empty so no backup required."
        $Backup_Lbl.Text = "Empty SD card"
    }
    else {
        Write-Host "The SD card contains files/folders."
        Write-Host "Looking for a previous Onion installation in ${SDcard_Letter}\.tmp_update\onionVersion\version.txt"
        $verionfilePath = "${SDcard_Letter}\.tmp_update\onionVersion\version.txt"
        if (Test-Path -Path $verionfilePath -PathType Leaf) {
            #################### previous Onion ####################
            $content = Get-Content -Path $verionfilePath -Raw
            Write-Host "Onion version $content already installed on this SD card."
            $Backup_Lbl.Text = "Onion $content on ${SDcard_Letter}"

        }
        elseif (Test-Path -Path "${SDcard_Letter}\RApp\") {
            #################### previous Stock ####################
            Write-Host "It seems to be a stock SD card from Miyoo"
            $Backup_Lbl.Text = "Miyoo Stock OS on ${SDcard_Letter}"
            $checkBox_Retroarch.Enabled = 0
            $tooltip.SetToolTip($checkBox_Retroarch, "This is a complete migration procedure for Onion.`nIt will backup your Miyoo stock SD card (bios, roms and saves)`nthen it will format your new SD card in FAT32, download and`ninstall Onion and then restore your stock backup data.")

        }
        else {
            #################### unknown files ####################
            Write-Host "Not Onion or Stock"
            $Backup_Lbl.Text = "Not Onion or Stock"
            $checkBox_Retroarch.Enabled = 0
            $tooltip.SetToolTip($checkBox_Retroarch, "This is a complete migration procedure for Onion.`nIt will backup your Miyoo stock SD card (bios, roms and saves)`nthen it will format your new SD card in FAT32, download and`ninstall Onion and then restore your stock backup data.")
        }


}



# Affichage de la fen�tre
$form.ShowDialog()
