#Onion OS Configuration

param (
    [Parameter(Mandatory = $false)]
    [string]$Target
)

$SdCard_Version = ""
$SdCardState = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
[Environment]::CurrentDirectory = Get-Location

if (-not $Target) {
    . "$PSScriptRoot\Disk_selector.ps1"
    if ($selectedTag -ne "") {
        $selectedTagSplitted = $selectedTag.Split(",")
        $Drive_Number = $($selectedTagSplitted[0])
        $Drive_Letter = $($selectedTagSplitted[1])
        $Target = "$Drive_Letter`:"
        Write-Host "Selected Tag: $selectedTag"
        Write-Host "Disk Number: $Drive_Number"
        Write-Host "Disk Letter: $Drive_Letter"
    }
    else {
        return
    }

}



Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing


if (Test-Path -Path "${Target}\") {
    $items = Get-ChildItem -Path "$($Target)\"
    if ($items.Count -eq 0) {
        #################### empty partition ####################
        Write-Host "Blank SD card."
        $SdCardState = "empty"
    }
    else {
        #################### previous Onion ####################
        Write-Host "The SD card contains files/folders."
        Write-Host "Looking for previous Onion installation version..."

        $verionfilePath = "${Target}\.tmp_update\bin\installUI"
        if (Test-Path -Path "${Target}\.tmp_update\bin\installUI" -PathType Leaf) {
            $versionRegex = '--version\s+(.*?)\s'
            $SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
            if ($SdCard_Version -eq "") {
                # if we don't get Onion version from InstallUI, we get it from version.txt
                $verionfilePath = "${Target}\.tmp_update\onionVersion\version.txt"
                if (Test-Path -Path $verionfilePath -PathType Leaf) {
                    $SdCard_Version = Get-Content -Path $verionfilePath -Raw
                }
            }
        
            Write-Host "Onion version $SdCard_Version already installed on this SD card."
            $SdCardState = "Onion"
        }
        elseif ((Test-Path -Path "${Target}\.tmp_update") -and (Test-Path -Path "${Target}\miyoo\app\.tmp_update\onion.pak")) {
            #################### Fresh Onion install files (not executed on MM) ####################
            $versionRegex = '--version\s+(.*?)\s'
            $SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\miyoo\app\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
            if ($SdCard_Version -eq "") {
                $script:versiSdCard_Versionon = "(unknown version)"
            }
            Write-Host "It seems to be and non installed Onion version"
            $SdCardState = "Onion_InstallPending"
        }
        elseif (Test-Path -Path "${Target}\RApp\") {
            #################### previous Stock ####################
            Write-Host "It seems to be a stock SD card from Miyoo"
            $SdCardState = "Stock"
        }
        else {
            #################### unknown files ####################
            Write-Host "Unidentified : Not Onion or Stock"
            $SdCardState = "Other"
        }



    }
}

if ($SdCardState -ne "Onion") {
    if ($SdCardState -eq "Onion_InstallPending") {
        [System.Windows.Forms.MessageBox]::Show("Your SD card contains a pending installation of Onion. Please make the install process on your Mini and come here after intallation.", "Installation not completed", 'Ok', 'Error') 
        return
    }
    else {
        [System.Windows.Forms.MessageBox]::Show("Onion not detected on this SD card", 'Error', 'Ok', 'Error') 
        return
    }
}


# Chemin du fichier config.json
$configFile = "config.json"

# Fonction pour créer et afficher la fenêtre Windows Form
function Show-Form {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Configuration Onion"
    $form.Size = New-Object System.Drawing.Size(400, 350)
    $form.StartPosition = "CenterScreen"
    $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
    $icon = New-Object System.Drawing.Icon($iconPath)
    $form.Icon = $icon

    $tabControl = New-Object System.Windows.Forms.TabControl
    $tabControl.Size = New-Object System.Drawing.Size(380, 250)
    $tabControl.Dock = "Fill"

    # Ajouter les sous-sections en tant que groupes d'onglets
    foreach ($section in $configContent.Onion_Configuration.PSObject.Properties) {
        $tabPage = New-Object System.Windows.Forms.TabPage
        $tabPage.Text = $section.Name

        $panel = New-Object System.Windows.Forms.Panel
        $panel.Location = New-Object System.Drawing.Point(10, 10)
        $panel.Size = New-Object System.Drawing.Size(300, 250)
        $panel.AutoScroll = $true

        $currentY = 10
        $currentX = 10

        # Ajouter les fichiers de chaque sous-section en tant que cases à cocher
        foreach ($item in $section.Value) {
            $filePath = Join-Path -Path $directory -ChildPath $item.filename
            $fileName = Split-Path -Leaf $filePath
            $shortDescription = $item.short_description
            $description = $item.description
            $suboption = $item.sub_option

            # Créer une case à cocher pour le fichier
            $checkBox = New-Object System.Windows.Forms.CheckBox
            $checkBox.Text = $shortDescription
            if ($suboption -eq 1) { $currentX = 25 } else { $currentX = 10 }
            $checkBox.Location = New-Object System.Drawing.Point($currentX, $currentY)
            $checkBox.AutoSize = $true
            $checkBox.Tag = $filePath
            
            if (Test-Path -Path $filePath) {
                $checkbox.Checked = 1
            }
            else {
                $checkbox.Checked = 0
            }
            
            
            $checkBox.Add_Click({
                    $checkbox = $this
                    $filePath = $checkbox.Tag
                    $underscoreFilePath = $filePath + "_"
                    if (Test-Path -Path $filePath) {
                        Rename-Item -Path $filePath -NewName $underscoreFilePath
                    }
                    else {
                        Rename-Item -Path $underscoreFilePath -NewName $filePath
                    }


     
                })

            # Ajouter un tooltip pour la description détaillée
            $toolTip = New-Object System.Windows.Forms.ToolTip
            $toolTip.AutoPopDelay = 32767

            $toolTip.SetToolTip($checkBox, $description.Replace("`n", [Environment]::NewLine))

            # Ajouter la case à cocher au panneau
            $panel.Controls.Add($checkBox)

            $currentY += 20
        }

        # Ajouter le panneau au groupe d'onglets
        $tabPage.Controls.Add($panel)
        $tabControl.Controls.Add($tabPage)
    }

    $form.Controls.Add($tabControl)

    $button = New-Object System.Windows.Forms.Button
    $button.Location = New-Object System.Drawing.Point(160, 220)
    $button.Size = New-Object System.Drawing.Size(80, 30)
    $button.Text = "Fermer"
    $button.Add_Click({ $form.Close() })    

    $form.Controls.Add($button)

    $form.ShowDialog() | Out-Null
}

# Charger le contenu du fichier config.json
$configContent = Get-Content -Raw -Path $configFile | ConvertFrom-Json

# Chemin du répertoire où se trouvent les fichiers
$directory = "$Target\.tmp_update\config"

# Afficher la fenêtre Windows Form
Show-Form
