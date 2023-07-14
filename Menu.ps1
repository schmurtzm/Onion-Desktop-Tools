# Onion-Desktop-Tools-v0.0.2
param (
    [Parameter(Mandatory = $false)]
    [string]$HighDPI
)
$selectedTag = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory

Add-Type -AssemblyName System.Windows.Forms

if ($HighDPI -eq 1) {
    #scaling
    ##################################################
    # $DPISetting = (Get-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name AppliedDPI).AppliedDPI
    # $dpiKoef = $DPISetting / 96
    # [System.Windows.Forms.Application]::EnableVisualStyles();
    
    Add-Type -TypeDefinition '
    public class DPIAware {
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern bool SetProcessDPIAware();
    }
    '
    [System.Windows.Forms.Application]::EnableVisualStyles()
    [void] [DPIAware]::SetProcessDPIAware() 
}

# create environnement



# Cr�ation de la fen�tre principale
$Form = New-Object System.Windows.Forms.Form
$Form.Text = "Onion Desktop Tools"
$Form.Size = New-Object System.Drawing.Size(500  , 320 )
$form.StartPosition = "CenterScreen"
$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\OnionInstaller.ico"
$icon = New-Object System.Drawing.Icon($iconPath)
$form.Icon = $icon

$Form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$Form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen

# Cr�ation du contr�le TabControl
$TabControl = New-Object System.Windows.Forms.TabControl
$TabControl.Dock = [System.Windows.Forms.DockStyle]::Fill

# Fonction pour obtenir l'option coch�e de l'onglet courant
function GetSelectedOption {
    $currentTab = $TabControl.SelectedTab

    foreach ($control in $currentTab.Controls) {
        if ($control.GetType().Name -eq "GroupBox") {
            foreach ($radioButton in $control.Controls) {
                if ($radioButton.Checked) {
                    return $radioButton.Text
                }
            }
        }
    }

    return $null
}

# Ajouter l'�v�nement Click pour le bouton "OK"
$OKButton_Click = {
    $selectedOption = GetSelectedOption

    if ($selectedOption -ne $null) {
        Write-Host "Selected option in '$($TabControl.SelectedTab.Text)': $selectedOption"
        Write-Host "$PSScriptRoot"
        #$scriptPath = Join-Path $PSScriptRoot "downloadupdate.ps1"

        if ($selectedOption -eq $InstallUpdateRadioButton0.Text) {
            #Install / Upgrade / Reinstall Onion without formating SD card
            $CurrentDrive = Get_Drive "Select target drive for Onion"
            if ($CurrentDrive -ne $null) {
                Write-Host "{$CurrentDrive[1]}:"
                . "$PSScriptRoot\Onion_Install_Download.ps1"
                . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
            }
        }
        

        if ($selectedOption -eq $InstallUpdateRadioButton1.Text) {
            # "Format SD card and install Onion"
            $CurrentDrive = Get_Drive "Select target drive for Onion"
            if ($CurrentDrive -ne $null) {
                # Sometime a scandisk is required to format 
                # $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                # $wgetProcess.WaitForExit()
                . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[0]
                . "$PSScriptRoot\Onion_Install_Download.ps1"
                . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
            }
        }

        if ($selectedOption -eq $InstallUpdateRadioButton2.Text) {
            # "Format SD card and install Onion"
            $CurrentDrive = Get_Drive "Select stock SD card"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Backup.ps1" -Drive_Number $CurrentDrive[0]
            }
            $CurrentDrive = Get_Drive "Select target drive for Onion"
            if ($CurrentDrive -ne $null) {
                # Sometime a scandisk is required to format 
                # $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                # $wgetProcess.WaitForExit()
                . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[0]
                . "$PSScriptRoot\Onion_Install_Download.ps1"
                . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
            }
        }
        if ($selectedOption -eq "Check for errors (scandisk)") {
            $CurrentDrive = Get_Drive "Select a drive to check"
            if ($CurrentDrive -ne $null) {
                $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                $wgetProcess.WaitForExit()
            }
        }

        if ($selectedOption -eq "Format SD card in FAT32") {
            $CurrentDrive = Get_Drive "Select a drive to format"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[1]
            }
        }

        if ($selectedOption -eq $BackupRestoreRadioButton1.Text) {
            $CurrentDrive = Get_Drive "Select a drive to backup"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Backup.ps1" $CurrentDrive[1]
            }
        }

        if ($selectedOption -eq $BackupRestoreRadioButton2.Text) {
            $CurrentDrive = Get_Drive "Select a destination drive"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Restore.ps1" -Target $CurrentDrive[1]
            }
        }
             
    }
}

function Get_Drive($Title) {
    # Call Disk_selector.ps1 to get selectedTag
    . "$PSScriptRoot\Disk_selector.ps1" -Title $Title

    # Check if selectedTag is not empty
    if ($selectedTag -ne "") {
        $selectedTagSplitted = $selectedTag.Split(",")
        $Drive_Number = $selectedTagSplitted[0]
        $Drive_Letter = $selectedTagSplitted[1]
        Write-Host "Disk Number: $Drive_Number"
        Write-Host "Disk Letter: $Drive_Letter"
        Write-Host "Selected Tag: $selectedTag"
        return , $Drive_Number, $Drive_Letter
    }
    else {
        return $null
    }
}


# Onglet "Install and Update Onion"
$InstallUpdateTab = New-Object System.Windows.Forms.TabPage
$InstallUpdateTab.Text = "Install and Update Onion"
$TabControl.TabPages.Add($InstallUpdateTab)

# Cr�ation du contr�le GroupBox pour l'onglet "Install and Update Onion"
$InstallUpdateGroupBox = New-Object System.Windows.Forms.GroupBox
$InstallUpdateGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$InstallUpdateGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$InstallUpdateTab.Controls.Add($InstallUpdateGroupBox)

# Ajouter les boutons � bascule dans le GroupBox
$InstallUpdateRadioButton0 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton0.Location = New-Object System.Drawing.Point(20, 30)
$InstallUpdateRadioButton0.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton0.Text = "Install / Upgrade / Reinstall Onion without formating SD card"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton0)
$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($InstallUpdateRadioButton0, "This will download and update Onion. It will keep your data`n(including roms, saves and retroarch configuration)")


# Ajouter les boutons � bascule dans le GroupBox
$InstallUpdateRadioButton1 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton1.Location = New-Object System.Drawing.Point(20, 60)
$InstallUpdateRadioButton1.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton1.Text = "Format SD card and install Onion"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton1)
$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($InstallUpdateRadioButton1, "This will format your SD card in FAT32`n(all the data on the SD card will be deleted),`nThen it will download and install Onion on your SD Card.")


$InstallUpdateRadioButton2 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton2.Location = New-Object System.Drawing.Point(20, 90)
$InstallUpdateRadioButton2.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton2.Text = "Migrate stock SD card to a new SD card with Onion"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton2)
$tooltip.SetToolTip($InstallUpdateRadioButton2, "This is a complete migration procedure for Onion.`nIt will backup your Miyoo stock SD card (bios, roms and saves)`nthen it will format your new SD card in FAT32, download and`ninstall Onion and then restore your stock backup data.")



# Onglet "Other Tools"
$OnionConfigTab = New-Object System.Windows.Forms.TabPage
$OnionConfigTab.Text = "Onion configuration"
$TabControl.TabPages.Add($OnionConfigTab)


# Création du contrôle GroupBox pour l'onglet "Onion configuration"
$OnionConfigGroupBox = New-Object System.Windows.Forms.GroupBox
$OnionConfigGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$OnionConfigGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$OnionConfigTab.Controls.Add($OnionConfigGroupBox)

# Récupération des fichiers de configuration Onion
$onionConfigFiles = Get-ChildItem -Path $PSScriptRoot -Filter "Onion_Config_*.ps1"

# Position initiale des boutons
$buttonLeft = 20
$buttonTop = 30
$buttonMargin = 10

# Création des boutons pour chaque fichier de configuration Onion
foreach ($configFile in $onionConfigFiles) {
    # Lecture de la première ligne en commentaire pour le nom du bouton
    $buttonText = Get-Content -Path $configFile.FullName | Where-Object { $_ -match "^#" } | Select-Object -First 1 | ForEach-Object { $_ -replace "#", "" }

    # Création du bouton
    $button = New-Object System.Windows.Forms.Button
    $button.Text = $buttonText
    $button.Tag = $configFile.FullName
    $button.SetBounds($buttonLeft, $buttonTop, 250, 20)
    $button.Add_Click({
            $clickedButton = $this
            & $clickedButton.Tag
        })

    Write-Host "$configFile.FullName"

    $OnionConfigGroupBox.Controls.Add($button)

    # Mise à jour des positions pour le prochain bouton
    $buttonTop += $button.Height + $buttonMargin
}

# Redimensionnement du groupe OnionConfigGroupBox en fonction des boutons
# $OnionConfigGroupBox.Height = $buttonTop + $buttonMargin




#$InstallUpdateRadioButton3 = New-Object System.Windows.Forms.RadioButton
#$InstallUpdateRadioButton3.Location = New-Object System.Drawing.Point(20, 120)
#$InstallUpdateRadioButton3.Size = New-Object System.Drawing.Size(380, 20)
#$InstallUpdateRadioButton3.Text = "Install Onion on existing SD card"
#$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton3)
#$tooltip.SetToolTip($InstallUpdateRadioButton3, "This will move your current SD card files in`na sub directory and install a new Onion on your SD Card.`nThis option is useful for testing and allows an`neasy roll back if needed.")


# Onglet "Backup and Restore Onion"
$BackupRestoreTab = New-Object System.Windows.Forms.TabPage
$BackupRestoreTab.Text = "Backup and Restore Onion"
$TabControl.TabPages.Add($BackupRestoreTab)

# Cr�ation du contr�le GroupBox pour l'onglet "Backup and Restore Onion"
$BackupRestoreGroupBox = New-Object System.Windows.Forms.GroupBox
$BackupRestoreGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$BackupRestoreGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$BackupRestoreTab.Controls.Add($BackupRestoreGroupBox)

# Ajouter les boutons � bascule dans le GroupBox
$BackupRestoreRadioButton1 = New-Object System.Windows.Forms.RadioButton
$BackupRestoreRadioButton1.Location = New-Object System.Drawing.Point(20, 30)
$BackupRestoreRadioButton1.Size = New-Object System.Drawing.Size(250, 20)
$BackupRestoreRadioButton1.Text = "Backup Onion or Stock SD card data"
$BackupRestoreGroupBox.Controls.Add($BackupRestoreRadioButton1)

$BackupRestoreRadioButton2 = New-Object System.Windows.Forms.RadioButton
$BackupRestoreRadioButton2.Location = New-Object System.Drawing.Point(20, 60)
$BackupRestoreRadioButton2.Size = New-Object System.Drawing.Size(250, 20)
$BackupRestoreRadioButton2.Text = "Restore a backup on Onion"
$BackupRestoreGroupBox.Controls.Add($BackupRestoreRadioButton2)

# Onglet "Other Tools"
$OtherToolsTab = New-Object System.Windows.Forms.TabPage
$OtherToolsTab.Text = "SD card tools"
$TabControl.TabPages.Add($OtherToolsTab)

# Cr�ation du contr�le GroupBox pour l'onglet "Other Tools"
$OtherToolsGroupBox = New-Object System.Windows.Forms.GroupBox
$OtherToolsGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$OtherToolsGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$OtherToolsTab.Controls.Add($OtherToolsGroupBox)

# Ajouter les boutons � bascule dans le GroupBox
# $OtherToolsRadioButton1 = New-Object System.Windows.Forms.RadioButton
# $OtherToolsRadioButton1.Location = New-Object System.Drawing.Point(20, 30)
# $OtherToolsRadioButton1.Size = New-Object System.Drawing.Size(250, 20)
# $OtherToolsRadioButton1.Text = "Save/Restore image disk"
# $OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton1)

$OtherToolsRadioButton2 = New-Object System.Windows.Forms.RadioButton
$OtherToolsRadioButton2.Location = New-Object System.Drawing.Point(20, 30)
$OtherToolsRadioButton2.Size = New-Object System.Drawing.Size(250, 20)
$OtherToolsRadioButton2.Text = "Format SD card in FAT32"
$OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton2)

$OtherToolsRadioButton3 = New-Object System.Windows.Forms.RadioButton
$OtherToolsRadioButton3.Location = New-Object System.Drawing.Point(20, 60)
$OtherToolsRadioButton3.Size = New-Object System.Drawing.Size(250, 20)
$OtherToolsRadioButton3.Text = "Check for errors (scandisk)"
$OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton3)






# Cr�ation du bouton "OK"
$OKButton = New-Object System.Windows.Forms.Button
$OKButton.Location = New-Object System.Drawing.Point(350, 200)
$OKButton.Size = New-Object System.Drawing.Size(75, 23)
$OKButton.Text = "OK"
$OKButton.Add_Click($OKButton_Click)
$Form.Controls.Add($OKButton)

# Ajouter le contr�le TabControl � la fen�tre principale
$Form.Controls.Add($TabControl)

# Afficher la fen�tre
$Form.ShowDialog()
