# Wifi

param (
    [Parameter(Mandatory = $false)]
    [string]$Target
)

$SdCard_Version = ""
$SdCardState = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory


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

# Création du formulaire
$form = New-Object System.Windows.Forms.Form
$form.Text = "WiFi Configuration"
$form.Size = New-Object System.Drawing.Size(400, 200)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle

# Création de la première TextBox pour le SSID
$textboxSSID = New-Object System.Windows.Forms.TextBox
$textboxSSID.Location = New-Object System.Drawing.Point(10, 20)
$textboxSSID.Size = New-Object System.Drawing.Size(360, 20)
$form.Controls.Add($textboxSSID)

# Création de la deuxième TextBox pour le mot de passe
$textboxPassword = New-Object System.Windows.Forms.TextBox
$textboxPassword.Location = New-Object System.Drawing.Point(10, 50)
$textboxPassword.Size = New-Object System.Drawing.Size(360, 20)
$form.Controls.Add($textboxPassword)

# Création du bouton OK
$buttonOK = New-Object System.Windows.Forms.Button
$buttonOK.Location = New-Object System.Drawing.Point(10, 90)
$buttonOK.Size = New-Object System.Drawing.Size(75, 23)
$buttonOK.Text = "OK"
$buttonOK.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $buttonOK
$form.Controls.Add($buttonOK)

# Création du bouton Annuler
$buttonCancel = New-Object System.Windows.Forms.Button
$buttonCancel.Location = New-Object System.Drawing.Point(95, 90)
$buttonCancel.Size = New-Object System.Drawing.Size(75, 23)
$buttonCancel.Text = "Cancel"
$buttonCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $buttonCancel
$form.Controls.Add($buttonCancel)

# Création du bouton pour obtenir les informations Wi-Fi du PC
$buttonGetWifiInfo = New-Object System.Windows.Forms.Button
$buttonGetWifiInfo.Location = New-Object System.Drawing.Point(180, 90)
$buttonGetWifiInfo.Size = New-Object System.Drawing.Size(180, 23)
$buttonGetWifiInfo.Text = "Get Wifi info from this PC"
$form.Controls.Add($buttonGetWifiInfo)

# Ajout d'un gestionnaire d'événement pour le bouton Get Wifi info
$buttonGetWifiInfo.Add_Click({
    $wifiInfo = .\PC_WifiInfo.ps1
    $textboxSSID.Text = $wifiInfo.SSID
    $textboxPassword.Text = $wifiInfo.Password
})

# Affichage du formulaire
$result = $form.ShowDialog()

# Traitement des résultats du formulaire
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {

    # Récupération des valeurs des TextBox
    $ssid = $textboxSSID.Text
    $password = $textboxPassword.Text

    # Renommer le fichier runtime.sh en runtime_ori.sh
    $sourceFilePath = "$Target\.tmp_update\runtime.sh"
    $targetFilePath = "$Target\.tmp_update\runtime_ori.sh"
    if (Test-Path $sourceFilePath) {

        if (-not (Test-Path $targetFilePath)) {
            Rename-Item -Path $sourceFilePath -NewName $targetFilePath -Force
        }
        
        # Contenu du fichier runtime.sh à écrire
        $runtimeContent = @"
killall -9 main
killall -9 updater
if [ ! -f /appconfigs/wpa_supplicant.conf ]; then
    echo "ctrl_interface=/var/run/wpa_supplicant" > /appconfigs/wpa_supplicant.conf
    echo "update_config=1" >> /appconfigs/wpa_supplicant.conf
fi
echo -e "\nnetwork={\n        ssid=`\"$ssid`\"\n        psk=`\"$password`\"\n}" >> /appconfigs/wpa_supplicant.conf
mv "/mnt/SDCARD/.tmp_update/runtime_ori.sh" "/mnt/SDCARD/.tmp_update/runtime.sh"
/mnt/SDCARD/.tmp_update/runtime.sh
"@
    
        # Écrire le contenu dans le fichier runtime.sh
        $runtimeContent = $runtimeContent -replace "`r`n", "`n"  # Remplace les CRLF par LF
        $runtimeContent | Out-File -FilePath "$Target\.tmp_update\runtime.sh" -Encoding utf8 -NoNewline
        
    }
    else {
        # Remplacer le fichier updater avec le nouveau contenu
        $updaterContent = @"
#!/bin/sh
killall -9 main
if [ ! -f /appconfigs/wpa_supplicant.conf ]; then
    echo "ctrl_interface=/var/run/wpa_supplicant" > /appconfigs/wpa_supplicant.conf
    echo "update_config=1" >> /appconfigs/wpa_supplicant.conf
fi
echo -e "\nnetwork={\n        ssid=`"$ssid`"\n        psk=`"$password`"\n}" >> /appconfigs/wpa_supplicant.conf
cd /mnt/SDCARD/miyoo/app
./MainUI

"@

$updaterContent = $updaterContent -replace "`r`n", "`n"  # Remplace les CRLF par LF
        $updaterContent | Out-File -FilePath "$Target\.tmp_update\updater" -Encoding utf8 -NoNewline
        
    }
}
